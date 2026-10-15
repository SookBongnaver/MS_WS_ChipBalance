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
import notebook_source

SOURCE = ROOT / "admin" / "00_admin_setup.ipynb"
CELLS = notebook_source.cells(SOURCE)
CODE = [notebook_source.cell_text(c) for c in CELLS if c["cell_type"] == "code"]
PYTHON_CODE = notebook_source.code_cells(SOURCE)
SOURCE_TEXT = "\n".join(notebook_source.cell_text(c) for c in CELLS)
SERVICE_CELL = next(c for c in CODE if "w = WorkspaceClient()" in c)
GRANT_CELL = next(c for c in CODE if "GRANT ACCESS ON SERVICE CREDENTIAL" in c)
FEDERATION_CELL = next(c for c in CODE if "w.storage_credentials.get" in c)
CONNECTOR = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Databricks/accessConnectors/ac-chipbalance"
WORKSPACE = "11111111-1111-1111-1111-111111111111"


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


class AdminSetupTests(unittest.TestCase):
    def test_sdk_preparation_precedes_configuration_and_api_imports(self):
        install = next(i for i, cell in enumerate(CODE) if '%pip install "databricks-sdk>=0.122.0,<1"' in cell)
        restart = next(i for i, cell in enumerate(CODE) if "dbutils.library.restartPython()" in cell)
        configuration = next(i for i, cell in enumerate(CODE) if "participants = {" in cell)
        service = CODE.index(SERVICE_CELL)
        self.assertLess(install, restart)
        self.assertLess(restart, configuration)
        self.assertLess(configuration, service)
        self.assertNotIn("%pip install databricks-sdk==0.81.0", SOURCE_TEXT)

    def setUp(self):
        self.client = types.SimpleNamespace(
            credentials=types.SimpleNamespace(get_credential=Mock(return_value=credential()), create_credential=Mock()),
            storage_credentials=types.SimpleNamespace(get=Mock(return_value=credential()), create=Mock()),
            connections=types.SimpleNamespace(get=Mock(return_value=connection())),
        )
        self.sql = Mock()
        self.env = {"access_connector_id": CONNECTOR, "service_credential": "service", "storage_credential": "storage",
                    "participants": {"p001": "participant@example.com"}, "fabric_workspace_ids": {"p001": WORKSPACE},
                    "spark": types.SimpleNamespace(sql=self.sql)}
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
        self.assertEqual(2, self.sql.call_count)
        statements = [c.args[0] for c in self.sql.call_args_list]
        self.assertFalse(any(statement.lstrip().startswith("CREATE FOREIGN CATALOG") for statement in statements))
        self.assertIn("GRANT CREATE CATALOG ON METASTORE", statements[0])
        self.assertIn("GRANT CREATE FOREIGN CATALOG ON CONNECTION", statements[1])

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

    def test_later_participant_connection_mismatch_prevents_all_grants(self):
        self.env["participants"]["p002"] = "second@example.com"
        self.env["fabric_workspace_ids"]["p002"] = WORKSPACE
        wrong = connection()
        wrong.options["workspace"] = "33333333-3333-3333-3333-333333333333"
        self.client.connections.get.side_effect = [connection(), wrong]
        with self.assertRaisesRegex(ValueError, "workspace"):
            self.run_federation()
        self.assert_no_grants()

    def test_missing_federation_resources_are_created_and_read_back(self):
        self.client.storage_credentials.get.side_effect = [NotFound(), credential()]
        self.client.connections.get.side_effect = [NotFound(), connection()]
        self.run_federation()
        self.client.storage_credentials.create.assert_called_once()
        self.assertEqual(2, self.client.connections.get.call_count)
        statements = [c.args[0] for c in self.sql.call_args_list]
        self.assertIn("CREATE CONNECTION", statements[0])
        self.assertIn("GRANT CREATE CATALOG ON METASTORE", statements[1])
        self.assertIn("GRANT CREATE FOREIGN CATALOG ON CONNECTION", statements[2])

    def test_create_race_with_wrong_existing_connection_stops(self):
        wrong = connection()
        wrong.options["workspace"] = "33333333-3333-3333-3333-333333333333"
        self.client.connections.get.side_effect = [NotFound(), wrong]
        with self.assertRaisesRegex(ValueError, "workspace"):
            self.run_federation()
        self.assert_no_grants()

    def test_permission_errors_are_not_treated_as_missing_resources(self):
        for api in (self.client.credentials.get_credential, self.client.storage_credentials.get,
                    self.client.connections.get):
            with self.subTest(api=api):
                api.side_effect = PermissionError("not authorized")
                try:
                    with self.assertRaises(PermissionError):
                        self.run_federation()
                    self.assert_no_grants()
                finally:
                    api.side_effect = None

    def test_invalid_or_missing_workspace_id_stops_before_ddl(self):
        for value in (None, "not-a-guid"):
            with self.subTest(value=value):
                if value is None:
                    self.env["fabric_workspace_ids"].pop("p001")
                else:
                    self.env["fabric_workspace_ids"]["p001"] = value
                try:
                    with self.assertRaisesRegex(ValueError, "fabric_workspace_ids"):
                        self.run_federation()
                    self.sql.assert_not_called()
                finally:
                    self.env["fabric_workspace_ids"]["p001"] = WORKSPACE

    def test_source_has_no_broad_exception_handler_or_delete(self):
        tree = ast.parse("\n".join(PYTHON_CODE))
        handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
        self.assertTrue(handlers)
        self.assertTrue(all(isinstance(n.type, ast.Name) and n.type.id in ("NotFound", "ValueError") for n in handlers))
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr == "delete" for n in ast.walk(tree)))

    def test_admin_notebook_has_no_outputs(self):
        for cell in CELLS:
            self.assertFalse(cell.get("outputs"))
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])

    def test_catalog_cell_uses_managed_location_and_checks_visibility(self):
        cell = next(c for c in CODE if "CREATE CATALOG IF NOT EXISTS" in c)
        self.assertIn("managed_location", "\n".join(CODE))
        for location, expected in (("", ""), (" abfss://c@a.dfs.core.windows.net/root/ ",
                                            " MANAGED LOCATION 'abfss://c@a.dfs.core.windows.net/root/lab_factory_p001'")):
            with self.subTest(location=location):
                statements = []
                shown = {"lab_factory_p001"}

                class Spark:
                    @staticmethod
                    def sql(statement):
                        statements.append(statement)
                        return types.SimpleNamespace(collect=lambda: [(name,) for name in shown])

                env = {"spark": Spark, "participants": {"p001": "a@b.c"}, "managed_location": location.strip()}
                exec(cell, env)
                self.assertEqual("CREATE CATALOG IF NOT EXISTS `lab_factory_p001`" + expected, statements[0])
        shown = set()
        with self.assertRaisesRegex(ValueError, "보이지 않습니다"):
            exec(cell, {"spark": Spark, "participants": {"p001": "a@b.c"}, "managed_location": ""})


if __name__ == "__main__":
    unittest.main()
