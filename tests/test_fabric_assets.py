"""Offline checks of the approval guards and report schema references."""
import ast
import json
import re
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def approval_cells():
    notebook = json.loads((ROOT / "fabric" / "nb_record_decision.ipynb").read_text(encoding="utf-8"))
    return ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]


class ApprovalTests(unittest.TestCase):
    def test_guide_verification_cell_only_reads_approval_data(self):
        text = (ROOT / "docs" / "11-operations-agent.md").read_text(encoding="utf-8")
        code = next(code for code in re.findall(r"``` python\n(.*?)\n\s*```", text, re.DOTALL)
                    if "approval_log = spark.sql" in code)
        import textwrap
        tree = ast.parse(textwrap.dedent(code))
        queries = [node.args[0].value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == "sql"]
        self.assertEqual(2, len(queries))
        for query in queries:
            self.assertTrue(query.lstrip().startswith("SELECT "))
            self.assertIn("EVT-20261001-001", query)
            self.assertNotRegex(query, r"\b(?:INSERT|UPDATE|DELETE|MERGE|CREATE|DROP)\b")
        self.assertIn("FROM dbo.chip_decision_log", queries[0])
        self.assertIn("FROM gold.fact_risk_event", queries[1])

    def run_validation(self, events, options, option_id="OPT-2"):
        class Frame:
            def __init__(self, rows):
                self.rows = rows

            def where(self, condition):
                return self

            def select(self, *columns):
                return self

            def take(self, count):
                return self.rows[:count]

        functions = types.SimpleNamespace(col=MagicMock())
        tables = {"gold.fact_risk_event": Frame(events), "gold.fact_response_option": Frame(options)}
        namespace = {
            "spark": types.SimpleNamespace(table=lambda name: tables[name]),
            "display": lambda frame: None,
            "event_id": "EVT-20261001-001",
            "option_id": option_id,
        }
        with patch.dict("sys.modules", {"pyspark": types.ModuleType("pyspark"),
                                       "pyspark.sql": types.SimpleNamespace(functions=functions)}):
            exec(next(cell for cell in approval_cells() if "events = event.take(2)" in cell), namespace)
        return namespace

    def event(self, status="open"):
        return types.SimpleNamespace(recommended_option_id="OPT-2", scenario_id="emergency", status=status)

    def test_matching_eligible_recommendation_is_accepted(self):
        for status in ("open", "approved"):
            event = self.event(status)
            result = self.run_validation([event], [types.SimpleNamespace(meets_all=True)])
            self.assertIs(event, result["ev"])

    def test_event_must_exist_and_be_unique(self):
        for events in ([], [self.event(), self.event()]):
            with self.assertRaisesRegex(ValueError, "정확히 1행"):
                self.run_validation(events, [])

    def test_mismatched_action_option_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "현재 추천안"):
            self.run_validation([self.event()], [], option_id="OPT-3")

    def test_missing_duplicate_or_ineligible_option_is_rejected(self):
        for options in ([], [types.SimpleNamespace(meets_all=False)],
                        [types.SimpleNamespace(meets_all=True), types.SimpleNamespace(meets_all=True)]):
            with self.assertRaisesRegex(ValueError, "기준 충족"):
                self.run_validation([self.event()], options)

    def test_invalid_event_state_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "상태"):
            self.run_validation([self.event("cancelled")], [types.SimpleNamespace(meets_all=True)])

    def kusto_function(self, payload):
        response = MagicMock()
        response.json.return_value = payload
        post = MagicMock(return_value=response)
        namespace = {"requests": types.SimpleNamespace(post=post),
                     "pd": types.SimpleNamespace(DataFrame=lambda rows, columns: (rows, columns)),
                     "kusto_uri": "https://example.kusto.fabric.microsoft.com",
                     "headers": {}, "KQL_DATABASE": "eh_chipbalance"}
        node = next(node for cell in approval_cells() for node in ast.parse(cell).body
                    if isinstance(node, ast.FunctionDef) and node.name == "kusto")
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<approval-kusto>", "exec"), namespace)
        return namespace["kusto"], post

    def test_kusto_partial_failure_is_not_reported_as_success(self):
        kusto, _ = self.kusto_function({"Exceptions": ["request failed"]})
        with self.assertRaisesRegex(RuntimeError, "Kusto"):
            kusto("mgmt", ".set-or-append RiskEventStatus <| print event_status='approved'")

    def test_kusto_v1_error_rows_in_any_result_table_are_rejected(self):
        for row in ({"OneApiErrors": [{"code": "PartialQueryFailure"}]},
                    [{"OneApiErrors": [{"code": "PartialQueryFailure"}]}]):
            with self.subTest(row=row):
                kusto, _ = self.kusto_function({"Tables": [
                    {"Columns": [{"ColumnName": "event_status"}], "Rows": [["approved"]]},
                    {"Columns": [], "Rows": [row]},
                ]})
                with self.assertRaisesRegex(RuntimeError, "부분 실패"):
                    kusto("mgmt", ".set-or-append RiskEventStatus <| print event_status='approved'")

    def test_kusto_result_preserves_column_names(self):
        kusto, post = self.kusto_function({"Tables": [{"Columns": [{"ColumnName": "event_status"}],
                                                     "Rows": [["approved"]]}]})
        self.assertEqual(([["approved"]], ["event_status"]), kusto("query", "RiskEventStatus | take 1"))
        self.assertEqual(60, post.call_args.kwargs["timeout"])


class ReportAssetTests(unittest.TestCase):
    def test_model_references_match_documented_gold_columns(self):
        text = (ROOT / "fabric" / "sm_chipbalance.tmdl").read_text(encoding="utf-8")
        design = (ROOT / "admin" / "data-design.md").read_text(encoding="utf-8")
        columns = {}
        for line in design.splitlines():
            if line.startswith("| gold."):
                cells = re.split(r"(?<!\\)\|", line)[1:-1]
                columns[cells[0].strip().removeprefix("gold.")] = set(cells[1].strip().split(", "))
        for table, column in re.findall(r"\b(\w+)\[([^\]]+)\]", text):
            with self.subTest(reference=f"{table}.{column}"):
                self.assertIn(column, columns[table])
        relationships = re.findall(r"\b(?:fromColumn|toColumn): (\w+)\.(\w+)", text)
        self.assertEqual(16, len(relationships))
        for table, column in relationships:
            self.assertIn(column, columns[table])
        self.assertEqual(19, len(re.findall(r"^\s*measure ", text, re.MULTILINE)))
        self.assertEqual(7, len(set(re.findall(r"^\s*ref table (\w+)", text, re.MULTILINE)) |
                                {table for table, _ in relationships}))

    def test_theme_and_guide_have_matching_series_colors(self):
        theme = json.loads((ROOT / "fabric" / "chipbalance-theme.json").read_text(encoding="utf-8"))
        self.assertEqual(["#0078D4", "#D13438", "#8A8886"], theme["dataColors"][:3])
        self.assertEqual("Chip Balance", theme["name"])


if __name__ == "__main__":
    unittest.main()
