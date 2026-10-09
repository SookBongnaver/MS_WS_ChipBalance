"""Run administrator setup cells against SDK stubs, without cloud access."""
import ast
import json
import sys
import types
import unittest
from enum import Enum
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_notebooks

SOURCE = ROOT / "admin" / "00_admin_setup.py"
CELLS = build_notebooks.cells_from_source(SOURCE)
CODE = ["".join(c["source"]) for c in CELLS if c["cell_type"] == "code"]
SERVICE_CELL = next(c for c in CODE if "w = WorkspaceClient()" in c)
GRANT_CELL = next(c for c in CODE if "GRANT ACCESS ON SERVICE CREDENTIAL" in c)
FEDERATION_CELL = next(c for c in CODE if "w.storage_credentials.get" in c)
CONNECTOR = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Databricks/accessConnectors/ac-chipbalance"
WORKSPACE = "11111111-1111-1111-1111-111111111111"
LAKEHOUSE = "22222222-2222-2222-2222-222222222222"


class NotFound(Exception):
    pass


class CredentialPurpose(Enum):
    SERVICE = "SERVICE"
    STORAGE = "STORAGE"


class ManagedIdentity:
    def __init__(self, access_connector_id, managed_identity_id=None):
        self.access_connector_id = access_connector_id
        self.managed_identity_id = managed_identity_id


def credential(connector=CONNECTOR, purpose=CredentialPurpose.SERVICE):
    return types.SimpleNamespace(azure_managed_identity=ManagedIdentity(connector), purpose=purpose)


def connection():
    return types.SimpleNamespace(options={"workspace": WORKSPACE, "credential": "storage"})


def catalog(number="p001"):
    return types.SimpleNamespace(catalog_type=types.SimpleNamespace(value="FOREIGN_CATALOG"),
                                 connection_name=f"onelake_connection_{number}",
                                 options={"data_item": LAKEHOUSE, "item_type": "Lakehouse"})


class AdminSetupTests(unittest.TestCase):
    def test_sdk_preparation_precedes_configuration_and_api_imports(self):
        install = next(i for i, cell in enumerate(CODE) if '%pip install "databricks-sdk>=0.122.0,<1"' in cell)
        restart = next(i for i, cell in enumerate(CODE) if "dbutils.library.restartPython()" in cell)
        configuration = next(i for i, cell in enumerate(CODE) if "participants = {" in cell)
        service = CODE.index(SERVICE_CELL)
        self.assertLess(install, restart)
        self.assertLess(restart, configuration)
        self.assertLess(configuration, service)
        self.assertNotIn("%pip install databricks-sdk==0.81.0", SOURCE.read_text(encoding="utf-8"))

    def setUp(self):
        self.client = types.SimpleNamespace(
            credentials=types.SimpleNamespace(get_credential=Mock(return_value=credential()), create_credential=Mock()),
            storage_credentials=types.SimpleNamespace(get=Mock(return_value=credential()), create=Mock()),
            connections=types.SimpleNamespace(get=Mock(return_value=connection())),
            catalogs=types.SimpleNamespace(get=Mock(return_value=catalog())),
        )
        self.sql = Mock()
        self.env = {"access_connector_id": CONNECTOR, "service_credential": "service", "storage_credential": "storage",
                    "participants": {"p001": "participant@example.com"}, "fabric_workspace_ids": {"p001": WORKSPACE},
                    "fabric_lakehouse_ids": {"p001": LAKEHOUSE}, "spark": types.SimpleNamespace(sql=self.sql)}
        modules = {name: types.ModuleType(name) for name in
                   ("databricks", "databricks.sdk", "databricks.sdk.errors", "databricks.sdk.service", "databricks.sdk.service.catalog")}
        modules["databricks.sdk"].WorkspaceClient = lambda: self.client
        modules["databricks.sdk.errors"].NotFound = NotFound
        modules["databricks.sdk.service.catalog"].AzureManagedIdentity = ManagedIdentity
        modules["databricks.sdk.service.catalog"].AzureManagedIdentityRequest = ManagedIdentity
        modules["databricks.sdk.service.catalog"].CredentialPurpose = CredentialPurpose
        self.module_patch = patch.dict(sys.modules, modules)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.print_patch = patch("builtins.print")
        self.print_patch.start()
        self.addCleanup(self.print_patch.stop)

    def run_service(self):
        exec(SERVICE_CELL, self.env)

    def run_federation(self):
        self.run_service()
        exec(FEDERATION_CELL, self.env)

    def assert_no_grants(self):
        self.assertFalse(any("GRANT " in call.args[0] for call in self.sql.call_args_list))

    def test_matching_service_is_reused(self):
        self.client.credentials.get_credential.return_value = credential(CONNECTOR.upper() + "/")
        self.run_service()
        exec(GRANT_CELL, self.env)
        self.client.credentials.create_credential.assert_not_called()
        self.assertTrue(any("GRANT ACCESS" in c.args[0] for c in self.sql.call_args_list))

    def test_missing_service_is_created_and_read_back(self):
        self.client.credentials.get_credential.side_effect = [NotFound(), credential()]
        self.run_service()
        self.client.credentials.create_credential.assert_called_once()
        self.assertEqual(2, self.client.credentials.get_credential.call_count)

    def test_wrong_service_connector_stops_before_grants(self):
        self.client.credentials.get_credential.return_value = credential("/different/connector")
        with self.assertRaisesRegex(ValueError, "access_connector_id"):
            self.run_service()
            exec(GRANT_CELL, self.env)
        self.assert_no_grants()
        self.client.credentials.create_credential.assert_not_called()

    def test_wrong_service_authentication_or_purpose_stops(self):
        cases = [types.SimpleNamespace(azure_managed_identity=None, purpose=CredentialPurpose.SERVICE),
                 credential(purpose=CredentialPurpose.STORAGE),
                 types.SimpleNamespace(azure_managed_identity=ManagedIdentity(CONNECTOR, "/user/assigned"),
                                       purpose=CredentialPurpose.SERVICE)]
        for existing in cases:
            with self.subTest(existing=existing):
                self.client.credentials.get_credential.return_value = existing
                with self.assertRaises(ValueError):
                    self.run_service()
                self.assert_no_grants()

    def test_matching_federation_only_grants_after_checks(self):
        self.run_federation()
        self.client.storage_credentials.create.assert_not_called()
        self.assertEqual(1, self.sql.call_count)
        self.assertIn("GRANT USE CATALOG", self.sql.call_args.args[0])

    def test_wrong_storage_connector_stops_before_ddl_and_grants(self):
        self.client.storage_credentials.get.return_value = credential("/different/connector")
        with self.assertRaisesRegex(ValueError, "access_connector_id"):
            self.run_federation()
        self.sql.assert_not_called()
        self.client.storage_credentials.create.assert_not_called()

    def test_wrong_connection_workspace_or_credential_stops(self):
        for field in ("workspace", "credential"):
            with self.subTest(field=field):
                existing = connection()
                existing.options[field] = "wrong-target"
                self.client.connections.get.return_value = existing
                with self.assertRaisesRegex(ValueError, field):
                    self.run_federation()
                self.assert_no_grants()

    def test_wrong_catalog_target_stops(self):
        for field in ("catalog_type", "connection_name", "data_item", "item_type"):
            with self.subTest(field=field):
                existing = catalog()
                if field in ("data_item", "item_type"):
                    existing.options[field] = "wrong-target"
                else:
                    setattr(existing, field, "wrong-target")
                self.client.catalogs.get.return_value = existing
                with self.assertRaisesRegex(ValueError, field):
                    self.run_federation()
                self.assert_no_grants()

    def test_later_participant_mismatch_prevents_all_foreign_grants(self):
        self.env["participants"]["p002"] = "second@example.com"
        self.env["fabric_workspace_ids"]["p002"] = WORKSPACE
        self.env["fabric_lakehouse_ids"]["p002"] = LAKEHOUSE
        wrong = catalog("p002")
        wrong.options["data_item"] = "33333333-3333-3333-3333-333333333333"
        self.client.catalogs.get.side_effect = [catalog(), wrong]
        with self.assertRaisesRegex(ValueError, "data_item"):
            self.run_federation()
        self.assert_no_grants()

    def test_missing_federation_resources_are_created_and_read_back(self):
        self.client.storage_credentials.get.side_effect = [NotFound(), credential()]
        self.client.connections.get.side_effect = [NotFound(), connection()]
        self.client.catalogs.get.side_effect = [NotFound(), catalog()]
        self.run_federation()
        self.client.storage_credentials.create.assert_called_once()
        self.assertEqual(2, self.client.connections.get.call_count)
        self.assertEqual(2, self.client.catalogs.get.call_count)
        statements = [c.args[0] for c in self.sql.call_args_list]
        self.assertIn("CREATE CONNECTION", statements[0])
        self.assertIn("CREATE FOREIGN CATALOG", statements[1])
        self.assertIn("GRANT USE CATALOG", statements[2])

    def test_create_race_with_wrong_existing_connection_stops(self):
        wrong = connection()
        wrong.options["workspace"] = "33333333-3333-3333-3333-333333333333"
        self.client.connections.get.side_effect = [NotFound(), wrong]
        with self.assertRaisesRegex(ValueError, "workspace"):
            self.run_federation()
        self.assert_no_grants()

    def test_permission_errors_are_not_treated_as_missing_resources(self):
        for api in (self.client.credentials.get_credential, self.client.storage_credentials.get,
                    self.client.connections.get, self.client.catalogs.get):
            with self.subTest(api=api):
                api.side_effect = PermissionError("not authorized")
                try:
                    with self.assertRaises(PermissionError):
                        self.run_federation()
                    self.assert_no_grants()
                finally:
                    api.side_effect = None

    def test_invalid_or_missing_fabric_ids_stop_before_ddl(self):
        for ids in ("fabric_workspace_ids", "fabric_lakehouse_ids"):
            with self.subTest(ids=ids):
                value = self.env[ids].pop("p001")
                try:
                    with self.assertRaisesRegex(ValueError, ids):
                        self.run_federation()
                    self.sql.assert_not_called()
                finally:
                    self.env[ids]["p001"] = value

    def test_source_has_no_broad_exception_handler_or_delete(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
        self.assertTrue(handlers)
        self.assertTrue(all(isinstance(n.type, ast.Name) and n.type.id in ("NotFound", "ValueError") for n in handlers))
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr == "delete" for n in ast.walk(tree)))

    def test_admin_notebook_matches_source_and_has_no_outputs(self):
        notebook = json.loads(SOURCE.with_suffix(".ipynb").read_text(encoding="utf-8"))
        self.assertEqual(CELLS, notebook["cells"])
        for cell in notebook["cells"]:
            self.assertFalse(cell.get("outputs"))
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])


if __name__ == "__main__":
    unittest.main()
