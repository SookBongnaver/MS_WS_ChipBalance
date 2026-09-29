"""Checks that the generated source data behaves like one factory and answers the workshop questions.

The source files are generated into a temporary folder, so the repository holds no data files.
Run: python -m unittest discover -s tests
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import generate_source_data as gen  # noqa: E402
import reference_pipeline as rp  # noqa: E402

D = date.fromisoformat


FIXTURE = {}


def setUpModule():
    FIXTURE["tmp"] = tempfile.mkdtemp()
    FIXTURE["counts"] = gen.generate_all(FIXTURE["tmp"])
    FIXTURE["res"] = rp.build(FIXTURE["tmp"])


def tearDownModule():
    shutil.rmtree(FIXTURE["tmp"], ignore_errors=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = FIXTURE["tmp"]
        self.counts = FIXTURE["counts"]
        self.res = FIXTURE["res"]
        self.src = self.res["source"]
        self.s = self.res["silver"]
        self.g = self.res["gold"]
        self.e = self.res["emergency"]


class SourceDataTests(Base):
    def test_files_and_row_counts(self):
        expected = {
            "sap/sap_material.csv": 12, "sap/sap_supplier.csv": 6, "sap/sap_purchase_receipt_2025-10_2026-09.csv": 2849,
            "sap/sap_purchase_order_open_2026Q4.csv": 731, "sap/sap_sales_order_open_2026Q4.csv": 321,
            "fpims/fpims_line.csv": 6, "fpims/fpims_bunker.csv": 24, "fpims/fpims_product.csv": 30, "fpims/fpims_recipe.csv": 118,
            "fpims/fpims_bunker_transfer_route.csv": 12, "fpims/fpims_production_lot_2025-10_2026-09.csv": 4308,
            "fpims/fpims_material_consumption_2025-10_2026-09.csv": 17168, "fpims/fpims_production_plan_2026Q4.csv": 547,
            "pvss/pvss_bunker_level_2026-09.json": 17278,
        }
        self.assertEqual(expected, self.counts)
        self.assertEqual(43410, sum(self.counts.values()))
        for name in expected:
            self.assertTrue((Path(self.tmp) / name).is_file(), name)

    def test_generation_is_repeatable(self):
        other = tempfile.mkdtemp()
        try:
            gen.generate_all(other)
            for name in self.counts:
                self.assertEqual((Path(self.tmp) / name).read_bytes(), (Path(other) / name).read_bytes(), name)
        finally:
            shutil.rmtree(other, ignore_errors=True)

    def test_ids_look_like_system_keys(self):
        patterns = {
            "fpims_production_lot_2025-10_2026-09": ("lot_id", r"L[1-6]-\d{6}-[DN]"),
            "fpims_material_consumption_2025-10_2026-09": ("consumption_id", r"MC\d{7}"),
            "sap_purchase_receipt_2025-10_2026-09": ("receipt_id", r"50000\d{5}"),
            "sap_sales_order_open_2026Q4": ("sales_order_id", r"SO-1\d{4}"),
            "fpims_production_plan_2026Q4": ("plan_id", r"PP-2026\d{4}-L[1-6]"),
        }
        for table, (column, pattern) in patterns.items():
            for r in self.src[table]:
                self.assertRegex(r[column], f"^{pattern}$")
        for r in self.src["sap_purchase_order_open_2026Q4"]:
            self.assertRegex(r["purchase_order_id"], r"^45000\d{5}$")
            self.assertRegex(r["po_line_no"], r"^\d{5}$")
        text = "".join(p.read_text(encoding="utf-8") for p in Path(self.tmp).glob("*/*"))
        self.assertNotRegex(text, r"BAD|UNK|TEST|DUMMY")

    def test_lots_run_in_two_twelve_hour_shifts(self):
        shifts = Counter((l["start_ts"].hour, (l["end_ts"] - l["start_ts"]).total_seconds() / 3600) for l in self.s["production_lot"])
        self.assertEqual({(8, 12.0), (20, 12.0)}, set(shifts))
        outputs = [l["output_kg"] for l in self.s["production_lot"]]
        self.assertGreater(len(set(outputs)), 3000)

    def test_products_run_in_campaigns(self):
        def run_lengths(seq):
            runs, n = [], 1
            for a, b in zip(seq, seq[1:]):
                if a == b:
                    n += 1
                else:
                    runs.append(n)
                    n = 1
            return runs + [n]

        history, plan = [], []
        for line in ("L1", "L2", "L3", "L4", "L5", "L6"):
            history += run_lengths([l["product_id"] for l in self.s["production_lot"] if l["line_id"] == line and l["lot_id"].endswith("-D")])
            plan += run_lengths([p["product_id"] for p in sorted(self.s["production_plan"], key=lambda p: p["plan_date"]) if p["line_id"] == line])
        self.assertGreaterEqual(sum(history) / len(history), 3.5)
        self.assertGreaterEqual(sum(plan) / len(plan), 3.5)

    def test_receipts_match_consumption_over_the_year(self):
        used, received = Counter(), Counter()
        for c in self.s["material_consumption"]:
            used[c["material_id"]] += c["consumed_kg"]
        for r in self.s["purchase_receipt"]:
            received[r["material_id"]] += r["quantity_kg"]
        for mat in used:
            self.assertAlmostEqual(1.0, received[mat] / used[mat], delta=0.03, msg=mat)

    def test_receipts_follow_order_units_and_delivery_days(self):
        unit = {s["supplier_id"]: s["order_unit_kg"] for s in self.s["supplier"]}
        for r in self.s["purchase_receipt"]:
            self.assertEqual(0, r["quantity_kg"] % unit[r["supplier_id"]])
        weekdays = {r["received_date"].weekday() for r in self.s["purchase_receipt"] if r["bunker_id"] == "BNK-L3-2"}
        self.assertEqual({4}, weekdays)

    def test_september_sensor_change_matches_receipts_minus_consumption(self):
        first, last = datetime(2026, 9, 1, 0), datetime(2026, 9, 30, 23)
        lot_start = {l["lot_id"]: l["start_ts"] for l in self.s["production_lot"]}
        used = defaultdict(float)
        for c in self.s["material_consumption"]:
            for h in range(12):
                t = lot_start[c["lot_id"]] + timedelta(hours=h)
                if first <= t < last:
                    used[c["bunker_id"]] += c["consumed_kg"] / 12
        received = defaultdict(int)
        for r in self.s["purchase_receipt"]:
            if first.date() <= r["received_date"] <= last.date():
                received[r["bunker_id"]] += r["quantity_kg"]
        reading = {(r["bunker_id"], r["reading_ts"]): r["level_kg"] for r in self.s["bunker_level"]}
        for b in self.s["bunker"]:
            bid = b["bunker_id"]
            change = reading[(bid, last)] - reading[(bid, first)]
            self.assertAlmostEqual(received[bid] - used[bid], change, delta=b["capacity_kg"] * 0.003 + 2, msg=bid)

    def test_plan_rows_belong_to_orders_for_the_same_product(self):
        orders = {o["sales_order_id"]: o for o in self.s["sales_order"]}
        planned, last_day = Counter(), {}
        for p in self.s["production_plan"]:
            o = orders[p["sales_order_id"]]
            self.assertEqual(o["product_id"], p["product_id"])
            planned[o["sales_order_id"]] += p["planned_output_kg"]
            last_day[o["sales_order_id"]] = max(last_day.get(o["sales_order_id"], p["plan_date"]), p["plan_date"])
        for so, o in orders.items():
            self.assertLessEqual(o["order_qty_kg"], planned[so])
            self.assertGreaterEqual(o["order_qty_kg"], planned[so] * 0.9)
            self.assertGreater(o["due_date"], last_day[so])
            self.assertLess(o["order_date"], min(p["plan_date"] for p in self.s["production_plan"] if p["sales_order_id"] == so))
        self.assertGreater(len({o["due_date"] for o in orders.values()}), 60)


class SilverTests(Base):
    def test_quarantine_counts(self):
        self.assertEqual({
            "open_po_unit_converted": 8, "open_po_duplicate_line": 5, "open_po_blank_quantity": 4, "open_po_unknown_material": 3,
            "sensor_out_of_range": 6, "sensor_duplicate_reading": 5, "sensor_missing_hour": 7, "quarantine_rows": 23,
        }, self.res["quarantine_metrics"])

    def test_ton_lines_become_kilograms(self):
        line = next(r for r in self.s["purchase_order_open"] if (r["purchase_order_id"], r["po_line_no"]) == ("4500010294", "00010"))
        self.assertEqual(("TO", 50, 50000), (line["source_unit"], line["source_quantity"], line["quantity_kg"]))
        self.assertEqual({"KG", "TO"}, {r["source_unit"] for r in self.s["purchase_order_open"]})
        self.assertEqual(719, len(self.s["purchase_order_open"]))


class GoldTests(Base):
    def test_gold_row_counts(self):
        self.assertEqual({
            "dim_line": 6, "dim_bunker": 24, "dim_material": 12, "dim_product": 30, "dim_supplier": 6,
            "dim_customer": 12, "dim_route": 12, "dim_date": 92, "dim_scenario": 1, "fact_usage_factor": 118,
            "fact_monthly_usage": 288, "fact_opening_stock": 24, "fact_inbound": 719, "fact_sales_order": 321,
            "fact_plan": 547, "fact_order_fulfillment": 321, "fact_balance": 2208, "fact_bunker_summary": 24,
        }, {k: len(v) for k, v in self.g.items()})

    def test_opening_stock_is_the_last_september_reading(self):
        for r in self.g["fact_opening_stock"]:
            self.assertEqual(datetime(2026, 9, 30, 23), r["reading_ts"])
            self.assertEqual(gen.OPENING[r["bunker_id"]], r["opening_kg"])

    def test_supplier_planning_delay(self):
        delay = {s["supplier_id"]: s["planning_delay_days"] for s in self.g["dim_supplier"]}
        self.assertEqual({"SUP-PET-A": 0, "SUP-PET-B": 0, "SUP-MB-A": 1, "SUP-NY-A": 1, "SUP-NY-B": 2, "SUP-ADD-A": 3}, delay)

    def test_actual_usage_is_above_standard(self):
        for r in self.g["fact_usage_factor"]:
            self.assertGreater(r["actual_kg_per_kg"], r["std_kg_per_kg"], r["usage_factor_key"])
            self.assertLess(r["loss_pct"], 5)

    def test_v1_current_plan_keeps_every_bunker_above_safety(self):
        self.assertEqual(0, sum(r["below_safety"] for r in self.g["fact_balance"]))
        self.assertEqual(0, sum(r["over_capacity"] for r in self.g["fact_balance"]))
        self.assertTrue(all(r["on_time"] for r in self.g["fact_order_fulfillment"]))

    def test_v2_urgent_order_hits_l3_pet_sd_only(self):
        below = [r for r in self.e["fact_bunker_summary"] if r["below_safety_days"]]
        self.assertEqual(["BNK-L3-2"], [r["bunker_id"] for r in below])
        r = below[0]
        self.assertEqual((D("2026-10-06"), D("2026-10-07")), (r["first_below_safety_date"], r["first_shortage_date"]))
        self.assertEqual((-23630, D("2026-11-26"), 35630), (r["min_closing_kg"], r["min_closing_date"], r["required_topup_kg"]))
        urgent = self.e["fact_sales_order"][0]
        self.assertEqual(("SO-10322", "C-1004", "P-L3-05", 100000, D("2026-10-08"), True),
                         (urgent["sales_order_id"], urgent["customer_id"], urgent["product_id"], urgent["order_qty_kg"], urgent["due_date"], urgent["is_urgent"]))

    def test_v3_moved_production_keeps_every_order_on_time(self):
        moved = [r for r in self.e["fact_plan"] if r["change_type"] == "moved"]
        self.assertEqual(6, len(moved))
        self.assertTrue(all(r["plan_date"] - r["original_plan_date"] == timedelta(days=2) for r in moved))
        self.assertEqual(["SO-10108", "SO-10109", "SO-10110"], sorted({r["sales_order_id"] for r in moved}))
        customers = {o["sales_order_id"]: o["customer_id"] for o in self.s["sales_order"]}
        self.assertEqual(["C-1004", "C-1009", "C-1001"], [customers[so] for so in ("SO-10108", "SO-10109", "SO-10110")])
        fulfillment = {r["sales_order_id"]: r for r in self.e["fact_order_fulfillment"]}
        self.assertTrue(all(r["on_time"] for r in fulfillment.values()))
        self.assertEqual((D("2026-10-06"), 2), (fulfillment["SO-10322"]["finish_date"], fulfillment["SO-10322"]["slack_days"]))

    def test_v4_transfer_source_stays_above_safety(self):
        opt2 = next(o for o in self.e["fact_response_option"] if o["option_id"] == "OPT-2")
        self.assertEqual(("BNK-L1-2", "R-01", 40000, D("2026-10-03")), (opt2["source_bunker_id"], opt2["route_id"], opt2["qty_kg"], opt2["first_arrival_date"]))
        donor = [r for r in self.e["fact_option_balance"] if r["option_id"] == "OPT-2" and r["bunker_id"] == "BNK-L1-2"]
        self.assertEqual(92, len(donor))
        self.assertGreaterEqual(min(r["closing_kg"] for r in donor), 6000)

    def test_v5_next_pet_sd_receipt(self):
        key = self.e["fact_risk_event"][0]["next_inbound_key"]
        inbound = next(r for r in self.g["fact_inbound"] if r["inbound_key"] == key)
        self.assertEqual(("4500010294", "00020", "SUP-PET-B", D("2026-10-09"), 25000),
                         (inbound["purchase_order_id"], inbound["po_line_no"], inbound["supplier_id"], inbound["expected_date"], inbound["quantity_kg"]))

    def test_v6_options_and_recommendation(self):
        result = {o["option_id"]: (o["c1_safety_pass"], o["c2_capacity_pass"], o["c3_due_date_pass"], o["c4_route_limit_pass"], o["rank"], o["added_cost_krw"])
                  for o in self.e["fact_response_option"]}
        self.assertEqual({
            "OPT-1": (False, True, True, True, None, 500000),
            "OPT-2": (True, True, True, True, 1, 1000000),
            "OPT-3": (True, True, True, True, 2, 3750000),
            "OPT-4": (False, True, False, True, None, 0),
        }, result)
        risk = self.e["fact_risk_event"][0]
        self.assertEqual(("EVT-20261001-001", "SO-10322", "BNK-L3-2", "OPT-2", "open"),
                         (risk["event_id"], risk["sales_order_id"], risk["bunker_id"], risk["recommended_option_id"], risk["status"]))


if __name__ == "__main__":
    unittest.main()
