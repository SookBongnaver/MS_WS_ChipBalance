"""Keep guide tables and Genie instructions aligned with the local reference data."""
import ast
import re
import shutil
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import generate_source_data as gen
import reference_pipeline as rp


def markdown_rows(text):
    return [[cell.strip() for cell in re.split(r"(?<!\\)\|", line)[1:-1]]
            for line in text.splitlines() if line.startswith("|")]


def number(text):
    return int(text.replace(",", ""))


def day(value):
    return value.isoformat() if value else ""


class GuideDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = ROOT / "data" / f"guide-validation-{uuid.uuid4().hex}"
        cls.addClassCleanup(lambda: shutil.rmtree(cls.fixture) if cls.fixture.exists() else None)
        cls.counts = gen.generate_all(cls.fixture)
        cls.res = rp.build(cls.fixture)
        cls.gold, cls.emergency = cls.res["gold"], cls.res["emergency"]
        cls.final = {name: list(cls.gold.get(name, ())) + list(cls.emergency.get(name, ()))
                     for name in cls.gold.keys() | cls.emergency.keys()}
        cls.design = (ROOT / "admin" / "data-design.md").read_text(encoding="utf-8")
        cls.rows = markdown_rows(cls.design)
        cls.gold_rows = {r[0].removeprefix("gold."): r for r in cls.rows if r[0].startswith("gold.")}

    def test_source_file_counts_and_columns_match_generated_data(self):
        rows = {r[0]: r for r in self.rows if r[0].endswith((".csv", ".json"))}
        for filename, count in self.counts.items():
            basename = Path(filename).name
            count_rows = [r for r in self.rows if r[0] == basename and len(r) == 5]
            self.assertEqual(1, len(count_rows), basename)
            self.assertEqual(count, number(count_rows[0][3]), basename)
            fields = [s.strip() for s in rows[basename][1].split(",")]
            self.assertEqual(list(self.res["source"][Path(basename).stem][0]), fields, basename)
        self.assertIn(f"{sum(self.counts.values()):,}행", self.design)

    def test_gold_table_names_counts_and_columns_match_reference_and_notebooks(self):
        setup = ast.parse((ROOT / "src" / "notebooks" / "01_setup.py").read_text(encoding="utf-8"))
        names = {}
        for node in setup.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in ("GOLD_TABLES", "EMERGENCY_GOLD_TABLES"):
                    names[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(set(names["GOLD_TABLES"]), set(self.gold))
        self.assertEqual(set(names["GOLD_TABLES"] + names["EMERGENCY_GOLD_TABLES"]), set(self.gold_rows))
        self.assertEqual(set(self.final), set(self.gold_rows))
        for name, row in self.gold_rows.items():
            with self.subTest(table=name):
                self.assertEqual(list(self.final[name][0]), row[1].split(", "))
                self.assertEqual(len(self.final[name][0]), len(row[2].split(", ")))
                self.assertEqual(len(self.gold.get(name, ())), 0 if row[3] == "—" else number(row[3]))
                self.assertEqual(len(self.final[name]), number(row[4]))
        self.assertEqual(4765, sum(map(len, self.gold.values())))
        self.assertEqual(8335, sum(map(len, self.final.values())))
        for total in (4765, 8335, sum(self.counts.values()) + sum(map(len, self.final.values()))):
            self.assertIn(f"{total:,}행", self.design)
        self.assertNotRegex(self.design, r"\bchip_(?:dim_|fact_|scenario_summary|response_option|option_balance|risk_event)")

    def test_dimension_integer_types_follow_silver_casts(self):
        silver = ast.parse((ROOT / "src" / "notebooks" / "04_silver.py").read_text(encoding="utf-8"))
        typed = next(ast.literal_eval(n.value) for n in silver.body
                     if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "typed_tables")
        for name in ("dim_material", "dim_supplier", "dim_route"):
            row = self.gold_rows[name]
            documented_types = dict(zip(row[1].split(", "), row[2].split(", ")))
            source_name = {"dim_material": "material", "dim_supplier": "supplier", "dim_route": "transfer_route"}[name]
            for kind, column in re.findall(r"CAST\(\w+ AS (INT|BIGINT)\) AS (\w+)", typed[f"silver_{source_name}"]):
                self.assertEqual(kind.lower(), documented_types[column], f"{name}.{column}")

    def test_baseline_and_emergency_summary_values_match_reference(self):
        rows = {r[0]: r for r in self.rows if r[0] in ("baseline", "emergency")}
        for sid, tables in (("baseline", self.gold), ("emergency", self.emergency)):
            summary = next(r for r in tables["fact_bunker_summary"] if r["bunker_id"] == "BNK-L3-2")
            last = max((r for r in tables["fact_balance"] if r["bunker_id"] == "BNK-L3-2"),
                       key=lambda r: r["balance_date"])
            documented = rows[sid]
            self.assertEqual(day(summary["first_below_safety_date"]), documented[1])
            self.assertEqual(day(summary["first_shortage_date"]), documented[2])
            self.assertEqual(summary["min_closing_kg"], number(documented[3]))
            self.assertEqual(day(summary["min_closing_date"]), documented[4])
            self.assertEqual(last["closing_kg"], number(documented[5]))
            self.assertEqual(summary["required_topup_kg"], number(documented[6]))
        self.assertNotIn("ending_closing_kg", self.gold_rows["fact_bunker_summary"][1])

    def test_option_results_and_recommended_action_match_reference(self):
        rows = {r[0]: r for r in self.rows if r[0].startswith("OPT-") and len(r) == 12}
        for option in self.emergency["fact_response_option"]:
            row = rows[option["option_id"]]
            self.assertEqual([str(option[k]).lower() for k in
                              ("c1_safety_pass", "c2_capacity_pass", "c3_due_date_pass", "c4_route_limit_pass")], row[1:5])
            self.assertEqual(option["added_cost_krw"], number(row[5]))
            self.assertEqual(option["below_safety_days"], number(row[6]))
            below = [r["balance_date"] for r in self.emergency["fact_option_balance"]
                     if r["option_id"] == option["option_id"] and r["below_safety"]]
            self.assertEqual(day(min(below) if below else None), row[7])
            self.assertEqual(option["late_order_count"], number(row[8]))
            self.assertEqual(option["qty_kg"], number(row[9]))
            self.assertEqual(day(option["first_arrival_date"]), row[10])
            self.assertEqual(str(option["recommendation_rank"] or ""), row[11])
        risk = self.emergency["fact_risk_event"][0]
        risk_rows = {r[0]: r[1] for r in self.rows if len(r) == 2}
        self.assertEqual(risk["recommended_option_id"], risk_rows["recommended_option_id"])
        self.assertEqual(risk["recommended_action"], risk_rows["recommended_action"])
        self.assertEqual(risk["sales_order_id"], risk_rows["sales_order_id"])
        self.assertEqual(risk["next_inbound_key"], risk_rows["next_inbound_key"].replace(r"\|", "|"))
        self.assertEqual("open", risk_rows["status"])

    def test_purchase_and_transfer_have_explicit_distinct_start_days(self):
        purchase = next(row for row in self.emergency["fact_response_option"] if row["option_id"] == "OPT-3")
        supplier = next(row for row in self.gold["dim_supplier"] if row["supplier_id"] == purchase["supplier_id"])
        from datetime import timedelta
        self.assertEqual(rp.TODAY + timedelta(days=supplier["standard_lead_time_days"] +
                                             supplier["planning_delay_days"]), purchase["first_arrival_date"])
        source = (ROOT / "src" / "notebooks" / "06_emergency_order.py").read_text(encoding="utf-8")
        self.assertIn("이송 출고는 다음 날부터, 신규 구매 발주는 당일부터", source)
        self.assertIn("판단 기준일 `TODAY` 당일 발주", self.design)

    def test_bunker_capacity_safety_and_margin_match_reference(self):
        bunkers = {r["bunker_id"]: r for r in self.gold["dim_bunker"]}
        for bid in ("BNK-L1-2", "BNK-L3-2"):
            policy = next(r for r in self.rows if r[0] == f"PET-SD ({bid})")
            self.assertEqual(bunkers[bid]["capacity_kg"], number(policy[1]))
            self.assertEqual(bunkers[bid]["safety_stock_kg"], number(policy[2]))
            margin = next(r for r in self.rows if r[0] == bid)
            summary = next(r for r in self.gold["fact_bunker_summary"] if r["bunker_id"] == bid)
            balance = [r for r in self.gold["fact_balance"] if r["bunker_id"] == bid]
            self.assertEqual(bunkers[bid]["safety_stock_kg"], number(margin[1]))
            self.assertEqual(f"{sum(r['requirement_kg'] for r in balance) / len(balance):,.1f}", margin[2])
            self.assertEqual(summary["min_closing_kg"], number(margin[3]))
            self.assertEqual(f"{summary['min_closing_kg'] / bunkers[bid]['safety_stock_kg']:.2f}", margin[4])

    def test_quarantine_reason_names_and_counts_match_reference(self):
        counts = {}
        for rejected in self.res["silver"]["quarantine"]:
            counts[rejected["reason"]] = counts.get(rejected["reason"], 0) + 1
        for reason, count in counts.items():
            row = next(r for r in self.rows if f"`{reason}`" in r[-1])
            self.assertEqual(count, number(row[1]))
        self.assertEqual({"duplicate_line", "blank_quantity", "unknown_material", "out_of_range", "duplicate_reading"}, set(counts))

    def test_genie_instructions_use_actual_tables_and_scenario_fields(self):
        text = (ROOT / "docs" / "07-genie.md").read_text(encoding="utf-8")
        instructions = re.search(r"``` text\n(.*?)\n```", text, re.DOTALL).group(1)
        self.assertIn("fabric_chipbalance_<참가자>.gold.fact_bunker_summary", instructions)
        self.assertNotIn("모든 fact 테이블에는 scenario_id", instructions)
        self.assertNotIn("gold_fact_bunker_summary", instructions)
        scenario_facts = {name for name, rows in self.final.items()
                          if name.startswith("fact_") and "scenario_id" in rows[0]}
        self.assertEqual({"fact_plan", "fact_order_fulfillment", "fact_balance", "fact_bunker_summary",
                          "fact_response_option", "fact_risk_event"}, scenario_facts)
        for name in scenario_facts:
            self.assertIn(name, instructions)
        self.assertIn("is_urgent", instructions)
        self.assertIn("fact_option_balance에도 scenario_id가 없고 option_id", instructions)
        self.assertIn("로컬 메타데이터", text)
        self.assertIn("비결정적", text)
        self.assertIn("Serverless 또는 Pro", text)
        self.assertIn("2025.40", text)
        self.assertIn("18.0", text)

    def test_genie_missing_table_diagnostic_does_not_blindly_rerun_emergency(self):
        text = (ROOT / "docs" / "07-genie.md").read_text(encoding="utf-8")
        self.assertIn("SHOW TABLES IN fabric_chipbalance_p001.gold", text)
        self.assertIn("REFRESH FOREIGN CATALOG fabric_chipbalance_p001", text)
        self.assertIn("4, 460, 1", text)
        self.assertIn("**원본에 세 테이블이 없을 때만**", text)
        self.assertIn("위험 이벤트 `status`를 `open`으로 덮어쓰", text)
        self.assertNotIn("목록에 테이블이 18개만 보이면 06장을 다시 실행", text)
        gold = (ROOT / "src" / "notebooks" / "05_gold.py").read_text(encoding="utf-8")
        self.assertIn("06장까지 실행해도 18행", gold)
        self.assertNotIn("18행 이상(06장까지 실행했다면 21행)", gold)


if __name__ == "__main__":
    unittest.main()
