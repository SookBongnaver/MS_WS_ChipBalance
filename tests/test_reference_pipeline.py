from __future__ import annotations

import hashlib
import shutil
import unittest
from collections import defaultdict
from pathlib import Path

from tools.generate_source_data import generate_all
from tools import reference_pipeline as rp
from tools.reference_pipeline import build_gold, DATA_DIR

ROOT = Path(__file__).resolve().parents[1]


class ReferencePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate_all(DATA_DIR)
        cls.result = build_gold(DATA_DIR)
        cls.src = cls.result["source"]
        cls.silver = cls.result["silver"]

    def test_source_row_counts_and_limits(self):
        counts = {name: len(rows) for name, rows in self.src.items()}
        self.assertEqual(41412, sum(counts.values()))
        self.assertGreaterEqual(sum(counts.values()), 35000)
        self.assertLessEqual(sum(counts.values()), 42000)
        self.assertEqual(17278, counts["pvss_bunker_level_2026-09.json"])
        self.assertEqual(735, counts["sap_purchase_order_open_2026Q4.csv"])
        self.assertEqual(547, counts["fpims_production_plan_2026Q4.csv"])
        self.assertEqual(118, counts["fpims_recipe.csv"])
        self.assertEqual(16252, counts["fpims_material_consumption_2025-10_2026-09.csv"])
        gold_total = sum(len(rows) for rows in self.result["gold"].values())
        self.assertEqual(6633, gold_total)
        self.assertLess(sum(counts.values()) + gold_total, 50000)

    def test_source_files_have_no_hidden_parameters(self):
        self.assertEqual(
            ["supplier_id", "supplier_name", "standard_lead_time_days", "max_pull_in_days", "order_unit_kg"],
            list(self.src["sap_supplier.csv"][0].keys()),
        )
        self.assertNotIn("historical_delay_bucket_days", self.src["sap_supplier.csv"][0])
        self.assertEqual(["product_id", "line_id", "material_id", "std_kg_per_kg"], list(self.src["fpims_recipe.csv"][0].keys()))
        self.assertNotIn("loss_pct", self.src["fpims_recipe.csv"][0])
        self.assertFalse(any(r["std_kg_per_kg"] == "0.000" for r in self.src["fpims_recipe.csv"]))
        self.assertFalse(any(int(r["consumed_kg"]) == 0 for r in self.src["fpims_material_consumption_2025-10_2026-09.csv"]))
        factor = next(r for r in self.result["gold"]["chip_fact_usage_factor"] if r["product_id"] == "P-L3-05" and r["material_id"] == "PET-SD")
        self.assertNotEqual(factor["actual_kg_per_kg"], factor["std_kg_per_kg"])

    def test_generator_is_byte_deterministic(self):
        tmp = ROOT / "tests" / "_tmp_generated_data"
        try:
            generate_all(tmp)
            original = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA_DIR.iterdir()) if p.is_file()}
            regenerated = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(tmp.iterdir()) if p.is_file()}
            self.assertEqual(original, regenerated)
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)

    def test_quarantine_counts(self):
        self.assertEqual({
            "open_po_duplicate": 5,
            "open_po_null_quantity": 4,
            "open_po_to_converted": 8,
            "open_po_unknown_material": 3,
            "sensor_duplicate": 5,
            "sensor_missing_hour": 7,
            "sensor_spike": 6,
            "total_quarantine_rows": 23,
        }, self.result["quarantine_metrics"])

    def test_supplier_delay_averages_are_varied_and_round_stably(self):
        expected = {
            "SUP-ADD-A": ("2.696203", "3"),
            "SUP-MB-A": ("1.287975", "1"),
            "SUP-NY-A": ("1.202532", "1"),
            "SUP-NY-B": ("2.196203", "2"),
            "SUP-PET-A": ("0.295597", "0"),
            "SUP-PET-B": ("0.245283", "0"),
        }
        rows = {r["supplier_id"]: r for r in self.result["gold"]["chip_fact_supplier_delay"]}
        for supplier_id, (avg, rounded) in expected.items():
            self.assertEqual(avg, rows[supplier_id]["avg_delay_days"])
            self.assertEqual(rounded, rows[supplier_id]["rounded_delay_days"])
            distance_to_half = abs((float(avg) % 1) - 0.5)
            self.assertGreater(distance_to_half, 0.1)

    def test_displaced_rows_preserved_and_spare_days_used(self):
        baseline = rp.plan_rows(self.src["fpims_production_plan_2026Q4.csv"], "baseline")
        emergency = rp.plan_rows(self.src["fpims_production_plan_2026Q4.csv"], "emergency")
        self.assertEqual(547, len(baseline))
        self.assertEqual(549, len(emergency))
        self.assertEqual(["2026-10-11", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"], self.result["key"]["spare_dates"])
        normal_sales = {r["sales_order_id"] for r in baseline}
        base_qty = defaultdict(int)
        emg_qty = defaultdict(int)
        for r in baseline:
            base_qty[r["sales_order_id"]] += int(r["planned_output_kg"])
        for r in emergency:
            if r["sales_order_id"] in normal_sales:
                emg_qty[r["sales_order_id"]] += int(r["planned_output_kg"])
        self.assertEqual(dict(base_qty), dict(emg_qty))
        self.assertEqual(100000, sum(int(r["planned_output_kg"]) for r in emergency if r["sales_order_id"] == rp.URGENT_ORDER["sales_order_id"]))

    def test_baseline_and_emergency_normal_orders_on_time(self):
        due = rp.sales_due_dates(self.src["sap_sales_order_open_2026Q4.csv"])
        self.assertEqual(0, rp.late_order_count(rp.plan_rows(self.src["fpims_production_plan_2026Q4.csv"], "baseline"), due))
        self.assertEqual(0, rp.late_order_count(rp.plan_rows(self.src["fpims_production_plan_2026Q4.csv"], "emergency"), due))

    def test_baseline_has_no_below_safety_days(self):
        baseline = [r for r in self.result["gold"]["chip_fact_balance"] if r["scenario_id"] == "baseline"]
        self.assertTrue(all(r["below_safety"] == "false" for r in baseline))
        self.assertTrue(all(r["shortage"] == "false" for r in baseline))

    def test_emergency_affected_bunker_summary(self):
        summary = self.result["key"]["emergency_affected"]
        self.assertEqual("BNK-L3-2", summary["bunker_id"])
        self.assertEqual("PET-SD", summary["material_id"])
        self.assertEqual("2026-10-06", summary["first_below_safety_date"])
        self.assertEqual("2026-10-06", summary["first_shortage_date"])
        self.assertEqual("-19188", summary["min_closing_kg"])
        self.assertEqual("31188", summary["required_topup_kg"])
        baseline = self.result["key"]["baseline_affected"]
        self.assertEqual("", baseline["first_below_safety_date"])
        self.assertEqual("42622", baseline["min_closing_kg"])

    def test_option_parameters_match_derivation_rules(self):
        options = {r["option_id"]: r for r in self.result["gold"]["chip_response_option"]}
        topup = int(self.result["key"]["emergency_affected"]["required_topup_kg"])
        self.assertEqual(str(rp.ceil_to_unit(topup, 5000)), options["OPT-2"]["qty_kg"])
        self.assertEqual("BNK-L1-2", options["OPT-2"]["source_bunker_id"])
        self.assertEqual("BNK-L3-2", options["OPT-2"]["target_bunker_id"])
        self.assertEqual("2026-10-03", options["OPT-2"]["first_arrival_date"])
        supplier = next(s for s in self.src["sap_supplier.csv"] if s["supplier_id"] == "SUP-PET-B")
        self.assertEqual(str(rp.ceil_to_unit(topup, int(supplier["order_unit_kg"]))), options["OPT-3"]["qty_kg"])
        self.assertEqual("2026-10-05", options["OPT-3"]["first_arrival_date"])

    def test_option_results_and_ranking(self):
        options = {r["option_id"]: r for r in self.result["gold"]["chip_response_option"]}
        self.assertEqual(("false", "52", "0"), (options["OPT-1"]["meets_all"], options["OPT-1"]["below_safety_days"], options["OPT-1"]["late_order_count"]))
        self.assertEqual(("true", "1", "875000", "0", "0"), (options["OPT-2"]["meets_all"], options["OPT-2"]["rank"], options["OPT-2"]["added_cost_krw"], options["OPT-2"]["below_safety_days"], options["OPT-2"]["late_order_count"]))
        self.assertEqual(("true", "2", "62500000", "0", "0"), (options["OPT-3"]["meets_all"], options["OPT-3"]["rank"], options["OPT-3"]["added_cost_krw"], options["OPT-3"]["below_safety_days"], options["OPT-3"]["late_order_count"]))
        self.assertEqual("false", options["OPT-4"]["c3_due_date_pass"])
        self.assertEqual("1", options["OPT-4"]["late_order_count"])

    def test_risk_event_content(self):
        event = self.result["gold"]["chip_risk_event"][0]
        self.assertEqual("EVT-20261001-001", event["event_id"])
        self.assertEqual("<current_timestamp>", event["detected_at"])
        self.assertEqual("emergency", event["scenario_id"])
        self.assertEqual("BNK-L3-2", event["bunker_id"])
        self.assertEqual("OPT-2", event["recommended_option_id"])
        self.assertEqual("open", event["status"])
        self.assertIn("PET-SD 35,000kg", event["recommended_action"])


if __name__ == "__main__":
    unittest.main()
