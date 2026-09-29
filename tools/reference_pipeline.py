from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.generate_source_data import PLAN_START, PLAN_END, SAFETY, CAPACITY, SUP_BY_MAT, q_half_up

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TODAY = date(2026, 10, 1)
URGENT_ORDER = {
    "sales_order_id": "URG-20261001-L3-001",
    "product_id": "P-L3-05",
    "line_id": "L3",
    "qty_kg": 100000,
    "due_date": date(2026, 10, 8),
    "production_dates": [date(2026, 10, d) for d in range(5, 7)],
}
SPARE_DATES = [date(2026, 10, d) for d in range(11, 16)]
AFFECTED_BUNKER = "BNK-L3-2"
DETECTED_AT_PLACEHOLDER = "<current_timestamp>"


def d8(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()


def ymd(d: date | None) -> str:
    return "" if d is None else d.isoformat()


def ceil_to_unit(value: int, unit: int) -> int:
    return ((value + unit - 1) // unit) * unit


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def source_tables(data_dir: Path = DATA_DIR) -> dict[str, list[dict]]:
    tables = {}
    for path in sorted(data_dir.glob("*.csv")):
        tables[path.name] = read_csv(path)
    for path in sorted(data_dir.glob("*.json")):
        tables[path.name] = read_jsonl(path)
    return tables


def cleanse(data_dir: Path = DATA_DIR):
    src = source_tables(data_dir)
    qrows: list[dict] = []
    silver = {k: deepcopy(v) for k, v in src.items()}

    materials = {r["material_id"] for r in src["sap_material.csv"]}
    bunkers = {r["bunker_id"]: r for r in src["fpims_bunker.csv"]}

    clean_po = []
    seen_po_keys = set()
    for idx, r in enumerate(src["sap_purchase_order_open_2026Q4.csv"], 1):
        key = (r["purchase_order_id"], r["po_line_no"])
        reason = None
        if r["material_id"] not in materials:
            reason = "unknown_material"
        elif r["quantity"] == "":
            reason = "null_quantity"
        elif key in seen_po_keys:
            reason = "duplicate_open_po"
        if reason:
            bad = dict(r)
            bad.update({"source_table": "sap_purchase_order_open_2026Q4", "source_row_number": idx, "reason": reason})
            qrows.append(bad)
            continue
        seen_po_keys.add(key)
        nr = dict(r)
        qty = Decimal(nr["quantity"])
        if nr["unit"] == "TO":
            qty *= Decimal(1000)
            nr["unit"] = "KG"
        nr["quantity_kg"] = str(q_half_up(qty))
        clean_po.append(nr)
    silver["sap_purchase_order_open_2026Q4"] = clean_po

    clean_sensor = []
    seen_sensor = set()
    capacities = {bid: int(b["capacity_kg"]) for bid, b in bunkers.items()}
    observed_unique = set()
    for idx, r in enumerate(src["pvss_bunker_level_2026-09.json"], 1):
        key = (r["bunker_id"], r["timestamp"])
        observed_unique.add(key)
        level = int(r["level_kg"])
        reason = None
        if level < 0 or level > capacities[r["bunker_id"]]:
            reason = "sensor_spike_out_of_capacity"
        elif key in seen_sensor:
            reason = "duplicate_sensor_timestamp"
        if reason:
            bad = dict(r)
            bad.update({"source_table": "pvss_bunker_level_2026-09", "source_row_number": idx, "reason": reason})
            qrows.append(bad)
            continue
        seen_sensor.add(key)
        clean_sensor.append({"bunker_id": r["bunker_id"], "timestamp": r["timestamp"], "level_kg": str(level)})
    silver["pvss_bunker_level_2026-09"] = clean_sensor

    expected_sensor_keys = 24 * 30 * 24
    metrics = {
        "open_po_duplicate": sum(1 for r in qrows if r["reason"] == "duplicate_open_po"),
        "open_po_null_quantity": sum(1 for r in qrows if r["reason"] == "null_quantity"),
        "open_po_unknown_material": sum(1 for r in qrows if r["reason"] == "unknown_material"),
        "open_po_to_converted": sum(1 for r in clean_po if r.get("unit") == "KG" and Decimal(r["quantity"]) < Decimal(r["quantity_kg"])),
        "sensor_spike": sum(1 for r in qrows if r["reason"] == "sensor_spike_out_of_capacity"),
        "sensor_duplicate": sum(1 for r in qrows if r["reason"] == "duplicate_sensor_timestamp"),
        "sensor_missing_hour": expected_sensor_keys - len(observed_unique),
        "total_quarantine_rows": len(qrows),
    }
    return src, silver, qrows, metrics


def supplier_delay(receipts: list[dict]) -> tuple[list[dict], dict[str, int]]:
    sums = defaultdict(int)
    counts = defaultdict(int)
    for r in receipts:
        delay = (d8(r["received_date"]) - d8(r["promised_date"])).days
        sums[r["supplier_id"]] += delay
        counts[r["supplier_id"]] += 1
    rows = []
    rounded = {}
    for sid in sorted(counts):
        avg = Decimal(sums[sid]) / Decimal(counts[sid])
        rd = q_half_up(avg)
        rounded[sid] = rd
        rows.append({"supplier_id": sid, "receipt_count": str(counts[sid]), "avg_delay_days": f"{avg:.6f}", "rounded_delay_days": str(rd)})
    return rows, rounded


def usage_factors(lots: list[dict], consumption: list[dict], recipes: list[dict]):
    lot_prod = {r["lot_id"]: r["product_id"] for r in lots}
    output_by_prod = defaultdict(int)
    for r in lots:
        output_by_prod[r["product_id"]] += int(r["output_kg"])
    cons_by_prod_mat = defaultdict(int)
    monthly_by_bunker = defaultdict(int)
    lot_month = {r["lot_id"]: r["start_ts"][:7] for r in lots}
    for r in consumption:
        pid = lot_prod[r["lot_id"]]
        kg = int(r["consumed_kg"])
        cons_by_prod_mat[(pid, r["material_id"])] += kg
        monthly_by_bunker[(lot_month[r["lot_id"]], r["bunker_id"])] += kg
    std = {(r["product_id"], r["material_id"]): Decimal(r["std_kg_per_kg"]) for r in recipes}
    uf_rows = []
    factors: dict[tuple[str, str], Decimal] = {}
    for key in sorted(cons_by_prod_mat):
        pid, mat = key
        factor = Decimal(cons_by_prod_mat[key]) / Decimal(output_by_prod[pid])
        factors[key] = factor
        uf_rows.append({
            "usage_factor_key": f"{pid}|{mat}", "product_id": pid, "material_id": mat,
            "actual_kg_per_kg": f"{factor:.6f}", "std_kg_per_kg": f"{std[key]:.6f}",
            "variance_kg_per_kg": f"{(factor - std[key]):.6f}",
            "total_consumed_kg": str(cons_by_prod_mat[key]), "total_output_kg": str(output_by_prod[pid]),
        })
    monthly_rows = []
    for (month, bid), kg in sorted(monthly_by_bunker.items()):
        monthly_rows.append({"monthly_usage_key": f"{month}|{bid}", "month": month, "bunker_id": bid, "consumed_kg": str(kg)})
    return uf_rows, factors, monthly_rows


def opening_stock(clean_sensor: list[dict]) -> list[dict]:
    latest = {}
    cutoff = "2026-09-30T23:00:00+09:00"
    for r in clean_sensor:
        if r["timestamp"] <= cutoff and (r["bunker_id"] not in latest or r["timestamp"] > latest[r["bunker_id"]]["timestamp"]):
            latest[r["bunker_id"]] = r
    rows = []
    for bid in sorted(latest):
        r = latest[bid]
        rows.append({"opening_stock_key": f"2026-10-01|{bid}", "as_of_date": "2026-10-01", "bunker_id": bid, "source_timestamp": r["timestamp"], "opening_kg": r["level_kg"]})
    return rows


def plan_rows(baseline_src: list[dict], scenario: str) -> list[dict]:
    rows = deepcopy(baseline_src)
    if scenario == "emergency":
        displaced = []
        for r in rows:
            pd = d8(r["plan_date"])
            if r["line_id"] == "L3" and pd in URGENT_ORDER["production_dates"]:
                displaced.append(dict(r))
                r["product_id"] = URGENT_ORDER["product_id"]
                r["planned_output_kg"] = "50000"
                r["sales_order_id"] = URGENT_ORDER["sales_order_id"]
        for moved, spare_date in zip(displaced, SPARE_DATES):
            nr = dict(moved)
            nr["plan_id"] = f"EMG-MOVE-{spare_date.strftime('%Y%m%d')}"
            nr["plan_date"] = spare_date.strftime("%Y%m%d")
            rows.append(nr)
    elif scenario == "opt4_postpone":
        for i, spare_date in enumerate(SPARE_DATES[:len(URGENT_ORDER["production_dates"])], 1):
            rows.append({
                "plan_id": f"OPT4-URG-{i:02d}",
                "plan_date": spare_date.strftime("%Y%m%d"),
                "line_id": "L3",
                "product_id": URGENT_ORDER["product_id"],
                "planned_output_kg": "50000",
                "sales_order_id": URGENT_ORDER["sales_order_id"],
            })
    return sorted(rows, key=lambda r: (r["plan_date"], r["line_id"], r["plan_id"]))


def requirement_by_bunker(plan: list[dict], bunkers: list[dict], factors: dict[tuple[str, str], Decimal]):
    b_by_line_mat = {(b["line_id"], b["material_id"]): b["bunker_id"] for b in bunkers}
    req = defaultdict(int)
    for r in plan:
        pd = d8(r["plan_date"])
        pid = r["product_id"]
        for (p, mat), factor in factors.items():
            if p != pid:
                continue
            bid = b_by_line_mat.get((r["line_id"], mat))
            if bid:
                req[(bid, pd)] += q_half_up(Decimal(r["planned_output_kg"]) * factor)
    return req


def expected_receipts(open_po: list[dict], delay_by_supplier: dict[str, int], pullin: dict[tuple[str, str], int] | None = None, extra_pos: list[dict] | None = None):
    rows = deepcopy(open_po) + deepcopy(extra_pos or [])
    pullin = pullin or {}
    rec = defaultdict(int)
    receipt_rows = []
    for r in rows:
        promised = d8(r["promised_date"])
        key = (r["purchase_order_id"], r["po_line_no"])
        if key in pullin:
            promised = pullin[key] if isinstance(pullin[key], date) else promised - timedelta(days=pullin[key])
        ed = promised + timedelta(days=delay_by_supplier.get(r["supplier_id"], 0))
        qty = int(r["quantity_kg"])
        rec[(r["bunker_id"], ed)] += qty
        receipt_rows.append((r, ed, qty))
    return rec, receipt_rows


def balance(plan: list[dict], open_po: list[dict], delay_by_supplier: dict[str, int], opening: list[dict], bunkers: list[dict], factors, scenario_id: str, transfers=None, pullin=None, extra_pos=None):
    transfers = transfers or []
    opening_by_b = {r["bunker_id"]: int(r["opening_kg"]) for r in opening}
    binfo = {b["bunker_id"]: b for b in bunkers}
    req = requirement_by_bunker(plan, bunkers, factors)
    rec, _ = expected_receipts(open_po, delay_by_supplier, pullin, extra_pos)
    tin = defaultdict(int); tout = defaultdict(int)
    for t in transfers:
        out_d = t["date"]
        in_d = out_d + timedelta(days=t["lead_time_days"])
        tout[(t["from_bunker_id"], out_d)] += t["qty_kg"]
        tin[(t["to_bunker_id"], in_d)] += t["qty_kg"]
    rows = []
    dates = list(_daterange(PLAN_START, PLAN_END))
    for bid in sorted(binfo):
        prev = opening_by_b[bid]
        for d in dates:
            receipts = rec[(bid, d)]
            transfers_in = tin[(bid, d)]
            transfers_out = tout[(bid, d)]
            requirement = req[(bid, d)]
            close = prev + receipts + transfers_in - transfers_out - requirement
            cap = int(binfo[bid]["capacity_kg"])
            safety = int(binfo[bid]["safety_stock_kg"])
            rows.append({
                "balance_key": f"{scenario_id}|{bid}|{d.isoformat()}", "scenario_id": scenario_id, "bunker_id": bid,
                "line_id": binfo[bid]["line_id"], "material_id": binfo[bid]["material_id"], "balance_date": d.isoformat(),
                "opening_kg": str(prev), "receipt_kg": str(receipts), "transfer_in_kg": str(transfers_in), "transfer_out_kg": str(transfers_out),
                "requirement_kg": str(requirement), "closing_kg": str(close), "safety_stock_kg": str(safety), "capacity_kg": str(cap),
                "below_safety": str(close < safety).lower(), "shortage": str(close < 0).lower(), "over_capacity": str(prev + receipts + transfers_in > cap).lower(),
            })
            prev = close
    return rows


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def summarize_balance(rows: list[dict], scenario_id: str) -> list[dict]:
    by_b = defaultdict(list)
    for r in rows:
        by_b[r["bunker_id"]].append(r)
    out = []
    for bid in sorted(by_b):
        br = by_b[bid]
        first_below = next((r["balance_date"] for r in br if r["below_safety"] == "true"), "")
        first_short = next((r["balance_date"] for r in br if r["shortage"] == "true"), "")
        min_row = min(br, key=lambda r: (int(r["closing_kg"]), r["balance_date"]))
        ending = br[-1]
        safety = int(br[0]["safety_stock_kg"])
        min_close = int(min_row["closing_kg"])
        out.append({"summary_key": f"{scenario_id}|{bid}", "scenario_id": scenario_id, "bunker_id": bid, "line_id": br[0]["line_id"], "material_id": br[0]["material_id"],
                    "first_below_safety_date": first_below, "first_shortage_date": first_short, "min_closing_kg": str(min_close),
                    "min_closing_date": min_row["balance_date"], "ending_closing_kg": ending["closing_kg"], "required_topup_kg": str(max(0, safety - min_close))})
    return out


def sales_due_dates(sales_rows: list[dict]) -> dict[str, date]:
    due = {r["sales_order_id"]: d8(r["due_date"]) for r in sales_rows}
    due[URGENT_ORDER["sales_order_id"]] = URGENT_ORDER["due_date"]
    return due


def sales_finish_dates(plan: list[dict]) -> dict[str, date]:
    finish = {}
    for r in plan:
        so = r["sales_order_id"]
        pd = d8(r["plan_date"])
        if so not in finish or pd > finish[so]:
            finish[so] = pd
    return finish


def late_order_count(plan: list[dict], due_dates: dict[str, date]) -> int:
    return sum(1 for so, finish in sales_finish_dates(plan).items() if finish > due_dates[so])


def earliest_below_date(rows: list[dict]) -> str:
    return min((r["balance_date"] for r in rows if r["below_safety"] == "true"), default="")


def below_safety_breakdown(rows: list[dict]) -> dict[str, int]:
    counts = defaultdict(int)
    for r in rows:
        if r["below_safety"] == "true":
            counts[r["bunker_id"]] += 1
    return dict(counts)


def bunker_margin_table(balance_rows: list[dict]) -> list[dict]:
    by_b = defaultdict(list)
    for r in balance_rows:
        by_b[r["bunker_id"]].append(r)
    out = []
    for bid in sorted(by_b):
        rows = by_b[bid]
        avg_use = sum(int(r["requirement_kg"]) for r in rows) / len(rows)
        safety = int(rows[0]["safety_stock_kg"])
        min_closing = min(int(r["closing_kg"]) for r in rows)
        out.append({
            "bunker_id": bid,
            "safety_stock_kg": str(safety),
            "avg_daily_use_kg": f"{avg_use:.1f}",
            "baseline_min_closing_kg": str(min_closing),
            "min_safety_ratio": f"{(min_closing / safety if safety else 0):.2f}",
        })
    return out


def option_evaluations(base_plan, clean_po, delay_by_supplier, opening, bunkers, factors, routes, material_prices, supplier_rows, emergency_summary, sales_rows):
    affected = next(r for r in emergency_summary if r["bunker_id"] == AFFECTED_BUNKER)
    required_topup = int(affected["required_topup_kg"])
    first_below = date.fromisoformat(affected["first_below_safety_date"])
    binfo = {b["bunker_id"]: b for b in bunkers}
    affected_material = binfo[AFFECTED_BUNKER]["material_id"]
    supplier = next(s for s in supplier_rows if s["supplier_id"] == SUP_BY_MAT[affected_material])
    max_pull = int(supplier["max_pull_in_days"])
    order_unit = int(supplier["order_unit_kg"])
    lead = int(supplier["standard_lead_time_days"])
    price = int(material_prices[affected_material])
    due_dates = sales_due_dates(sales_rows)

    _, receipt_detail = expected_receipts(clean_po, delay_by_supplier)
    affected_receipts = sorted(
        [(r, expected, qty) for r, expected, qty in receipt_detail if r["bunker_id"] == AFFECTED_BUNKER and expected > first_below],
        key=lambda x: (x[1], x[0]["purchase_order_id"], x[0]["po_line_no"]),
    )
    first_po, first_expected, _ = affected_receipts[0]
    pulled_promised = max(d8(first_po["promised_date"]) - timedelta(days=max_pull), TODAY + timedelta(days=1))
    pullin = {(first_po["purchase_order_id"], first_po["po_line_no"]): pulled_promised}

    candidate_routes = sorted(
        [r for r in routes if r["to_bunker_id"] == AFFECTED_BUNKER and r["material_id"] == affected_material],
        key=lambda r: (int(r["cost_krw_per_kg"]), r["from_bunker_id"]),
    )
    route = candidate_routes[0]
    transfer_qty = ceil_to_unit(required_topup, 5000)
    transfers = []
    remaining = transfer_qty
    ship_date = TODAY + timedelta(days=1)
    while remaining > 0:
        qty = min(remaining, int(route["max_kg_per_day"]))
        transfers.append({"date": ship_date, "from_bunker_id": route["from_bunker_id"], "to_bunker_id": AFFECTED_BUNKER, "qty_kg": qty, "lead_time_days": int(route["lead_time_days"])})
        remaining -= qty
        ship_date += timedelta(days=1)
    first_transfer_arrival = transfers[0]["date"] + timedelta(days=transfers[0]["lead_time_days"])

    purchase_qty = ceil_to_unit(required_topup, order_unit)
    promised = TODAY + timedelta(days=lead)
    expected_new = promised + timedelta(days=delay_by_supplier.get(supplier["supplier_id"], 0))
    extra_po = {"purchase_order_id": "PO-EMER-001", "po_line_no": "10", "supplier_id": supplier["supplier_id"], "material_id": affected_material, "bunker_id": AFFECTED_BUNKER,
                "promised_date": promised.strftime("%Y%m%d"), "quantity_kg": str(purchase_qty), "unit": "KG"}

    opt4_plan = plan_rows(base_plan, "opt4_postpone")
    displaced_rows = sorted([r for r in base_plan if r["line_id"] == "L3" and r["plan_id"].startswith("EMG-MOVE-")], key=lambda r: r["plan_date"])
    opt4_plan = [dict(r) for r in base_plan if r["sales_order_id"] != URGENT_ORDER["sales_order_id"] and not r["plan_id"].startswith("EMG-MOVE-")]
    for moved, original_date in zip(displaced_rows, URGENT_ORDER["production_dates"]):
        nr = dict(moved)
        nr["plan_id"] = f"OPT4-RESTORE-{original_date.strftime('%Y%m%d')}"
        nr["plan_date"] = original_date.strftime("%Y%m%d")
        opt4_plan.append(nr)
    opt4_dates = [d for d in SPARE_DATES if d > first_expected][:len(URGENT_ORDER["production_dates"])]
    if len(opt4_dates) < len(URGENT_ORDER["production_dates"]):
        opt4_dates = SPARE_DATES[-len(URGENT_ORDER["production_dates"]):]
    for i, spare_date in enumerate(opt4_dates, 1):
        opt4_plan.append({"plan_id": f"OPT4-URG-{i:02d}", "plan_date": spare_date.strftime("%Y%m%d"), "line_id": "L3",
                          "product_id": URGENT_ORDER["product_id"], "planned_output_kg": "50000", "sales_order_id": URGENT_ORDER["sales_order_id"]})
    opt4_plan = sorted(opt4_plan, key=lambda r: (r["plan_date"], r["line_id"], r["plan_id"]))
    options = [
        {"option_id": "OPT-1", "option_name": "입고 앞당김", "plan": base_plan, "pullin": pullin, "transfers": [], "extra_pos": [], "added_cost_krw": 0,
         "action_detail": f"{first_po['purchase_order_id']} 납기 {max_pull}일 앞당김", "source_bunker_id": "", "target_bunker_id": AFFECTED_BUNKER,
         "qty_kg": first_po["quantity_kg"], "first_arrival_date": (pulled_promised + timedelta(days=delay_by_supplier.get(first_po["supplier_id"], 0))).isoformat()},
        {"option_id": "OPT-2", "option_name": "Bunker 간 이송", "plan": base_plan, "pullin": {}, "transfers": transfers, "extra_pos": [], "added_cost_krw": transfer_qty * int(route["cost_krw_per_kg"]),
         "action_detail": f"{route['from_bunker_id']}에서 {AFFECTED_BUNKER}로 {affected_material} {transfer_qty:,}kg 이송", "source_bunker_id": route["from_bunker_id"],
         "target_bunker_id": AFFECTED_BUNKER, "qty_kg": str(transfer_qty), "first_arrival_date": first_transfer_arrival.isoformat()},
        {"option_id": "OPT-3", "option_name": "추가 구매", "plan": base_plan, "pullin": {}, "transfers": [], "extra_pos": [extra_po], "added_cost_krw": purchase_qty * price,
         "action_detail": f"{supplier['supplier_id']}에 {affected_material} {purchase_qty:,}kg 추가 구매", "source_bunker_id": "", "target_bunker_id": AFFECTED_BUNKER,
         "qty_kg": str(purchase_qty), "first_arrival_date": expected_new.isoformat()},
        {"option_id": "OPT-4", "option_name": "생산 순서 조정", "plan": opt4_plan, "pullin": {}, "transfers": [], "extra_pos": [], "added_cost_krw": 0,
         "action_detail": f"긴급 생산을 다음 예상 입고일 {first_expected.isoformat()} 이후 예비일로 이동", "source_bunker_id": "", "target_bunker_id": AFFECTED_BUNKER,
         "qty_kg": str(URGENT_ORDER["qty_kg"]), "first_arrival_date": opt4_dates[0].isoformat()},
    ]
    option_rows = []
    option_balance = []
    for opt in options:
        br = balance(opt["plan"], clean_po, delay_by_supplier, opening, bunkers, factors, opt["option_id"], opt["transfers"], opt["pullin"], opt["extra_pos"])
        changed = {AFFECTED_BUNKER}
        if opt["option_id"] == "OPT-2":
            changed.add("BNK-L1-2")
        for r in br:
            if r["bunker_id"] in changed:
                nr = dict(r)
                nr["option_id"] = opt["option_id"]
                nr["option_balance_key"] = f"{opt['option_id']}|{r['bunker_id']}|{r['balance_date']}"
                option_balance.append(nr)
        c1 = all(r["below_safety"] == "false" for r in br)
        c2 = all(r["over_capacity"] == "false" for r in br)
        c3 = late_order_count(opt["plan"], due_dates) == 0
        route_keys = {(r["from_bunker_id"], r["to_bunker_id"]) for r in routes}
        c4 = all(t["qty_kg"] <= int(route["max_kg_per_day"]) and (t["from_bunker_id"], t["to_bunker_id"]) in route_keys for t in opt["transfers"])
        meets = c1 and c2 and c3 and c4
        below_breakdown = below_safety_breakdown(br)
        below_days = sum(below_breakdown.values())
        first_below_any = earliest_below_date(br)
        late_count = late_order_count(opt["plan"], due_dates)
        option_rows.append({"option_id": opt["option_id"], "option_name": opt["option_name"], "c1_safety_pass": str(c1).lower(), "c2_capacity_pass": str(c2).lower(),
                            "c3_due_date_pass": str(c3).lower(), "c4_route_limit_pass": str(c4).lower(), "added_cost_krw": str(opt["added_cost_krw"]),
                            "below_safety_days": str(below_days), "first_below_safety_date": first_below_any, "late_order_count": str(late_count),
                            "action_detail": opt["action_detail"], "source_bunker_id": opt["source_bunker_id"], "target_bunker_id": opt["target_bunker_id"],
                            "qty_kg": str(opt["qty_kg"]), "first_arrival_date": opt["first_arrival_date"],
                            "below_safety_breakdown": "; ".join(f"{k}:{v}" for k, v in sorted(below_breakdown.items())),
                            "meets_all": str(meets).lower(), "rank": ""})
    passing = sorted([r for r in option_rows if r["meets_all"] == "true"], key=lambda r: (int(r["added_cost_krw"]), r["option_id"]))
    for i, r in enumerate(passing, 1):
        r["rank"] = str(i)
    return option_rows, option_balance


def build_gold(data_dir: Path = DATA_DIR):
    src, silver, quarantine, qmetrics = cleanse(data_dir)
    materials = silver["sap_material.csv"]
    suppliers = silver["sap_supplier.csv"]
    lines = silver["fpims_line.csv"]
    bunkers = silver["fpims_bunker.csv"]
    products = silver["fpims_product.csv"]
    recipes = silver["fpims_recipe.csv"]
    clean_po = silver["sap_purchase_order_open_2026Q4"]
    clean_sensor = silver["pvss_bunker_level_2026-09"]
    delay_rows, delay_by_supplier = supplier_delay(silver["sap_purchase_receipt_2025-10_2026-09.csv"])
    uf_rows, factors, monthly_rows = usage_factors(silver["fpims_production_lot_2025-10_2026-09.csv"], silver["fpims_material_consumption_2025-10_2026-09.csv"], recipes)
    opening = opening_stock(clean_sensor)
    baseline_plan = plan_rows(silver["fpims_production_plan_2026Q4.csv"], "baseline")
    emergency_plan = plan_rows(silver["fpims_production_plan_2026Q4.csv"], "emergency")
    baseline_bal = balance(baseline_plan, clean_po, delay_by_supplier, opening, bunkers, factors, "baseline")
    emergency_bal = balance(emergency_plan, clean_po, delay_by_supplier, opening, bunkers, factors, "emergency")
    baseline_sum = summarize_balance(baseline_bal, "baseline")
    emergency_sum = summarize_balance(emergency_bal, "emergency")
    material_prices = {r["material_id"]: r["unit_price_krw_per_kg"] for r in materials}
    opt_rows, opt_bal = option_evaluations(emergency_plan, clean_po, delay_by_supplier, opening, bunkers, factors, silver["fpims_bunker_transfer_route.csv"], material_prices, suppliers, emergency_sum, silver["sap_sales_order_open_2026Q4.csv"])
    rec = next(r for r in opt_rows if r["rank"] == "1")
    aff_sum = next(r for r in emergency_sum if r["bunker_id"] == AFFECTED_BUNKER)
    risk = [{"event_id": "EVT-20261001-001", "detected_at": DETECTED_AT_PLACEHOLDER, "scenario_id": "emergency", "bunker_id": AFFECTED_BUNKER,
             "material_id": aff_sum["material_id"], "line_id": aff_sum["line_id"], "first_below_safety_date": aff_sum["first_below_safety_date"],
             "first_shortage_date": aff_sum["first_shortage_date"], "min_closing_kg": aff_sum["min_closing_kg"], "required_topup_kg": aff_sum["required_topup_kg"],
             "recommended_option_id": rec["option_id"], "recommended_action": rec["action_detail"], "status": "open"}]
    date_dim = [{"date_key": d.isoformat(), "calendar_date": d.isoformat(), "yyyymm": d.strftime("%Y%m"), "day_of_week": str(d.isoweekday())} for d in _daterange(PLAN_START, PLAN_END)]
    dim_scenario = [{"scenario_id": "baseline", "scenario_name": "현재 계산", "description": "Q4 기준 생산계획"}, {"scenario_id": "emergency", "scenario_name": "긴급 오더 반영", "description": "2026-10-01 접수 긴급 오더 반영"}]
    fact_plan = []
    for sid, rows in (("baseline", baseline_plan), ("emergency", emergency_plan)):
        for r in rows:
            nr = dict(r); nr["scenario_id"] = sid; nr["plan_key"] = f"{sid}|{r['plan_date']}|{r['line_id']}"; fact_plan.append(nr)
    gold = {
        "chip_dim_line": lines, "chip_dim_bunker": bunkers, "chip_dim_material": materials, "chip_dim_product": products, "chip_dim_supplier": suppliers,
        "chip_dim_date": date_dim, "chip_dim_scenario": dim_scenario, "chip_fact_usage_factor": uf_rows, "chip_fact_monthly_usage": monthly_rows,
        "chip_fact_supplier_delay": delay_rows, "chip_fact_opening_stock": opening, "chip_fact_plan": fact_plan,
        "chip_fact_balance": baseline_bal + emergency_bal, "chip_scenario_summary": baseline_sum + emergency_sum,
        "chip_response_option": opt_rows, "chip_option_balance": opt_bal, "chip_risk_event": risk,
    }
    return {"source": src, "silver": silver, "quarantine": quarantine, "quarantine_metrics": qmetrics, "gold": gold,
            "key": {"baseline_affected": next(r for r in baseline_sum if r["bunker_id"] == AFFECTED_BUNKER), "emergency_affected": aff_sum,
                    "options": opt_rows, "risk_event": risk[0], "urgent_order": URGENT_ORDER, "spare_dates": [d.isoformat() for d in SPARE_DATES],
                    "bunker_margin": bunker_margin_table(baseline_bal)}}


def main():
    res = build_gold(DATA_DIR)
    print("SOURCE ROW COUNTS")
    for name in sorted(res["source"]):
        print(f"{name}: {len(res['source'][name])}")
    print(f"source_total: {sum(len(v) for v in res['source'].values())}")
    print("SILVER QUARANTINE COUNTS")
    for k in sorted(res["quarantine_metrics"]):
        print(f"{k}: {res['quarantine_metrics'][k]}")
    print("GOLD ROW COUNTS")
    for name in sorted(res["gold"]):
        print(f"{name}: {len(res['gold'][name])}")
    print(f"gold_total: {sum(len(v) for v in res['gold'].values())}")
    print("AFFECTED BUNKER")
    print("baseline", res["key"]["baseline_affected"])
    print("emergency", res["key"]["emergency_affected"])
    print("OPTIONS")
    for r in res["key"]["options"]:
        print(r)
    print("BUNKER MARGIN TABLE")
    for r in res["key"]["bunker_margin"]:
        print(r)
    print("OPTION BELOW-SAFETY BREAKDOWN")
    for r in res["key"]["options"]:
        print(r["option_id"], r.get("below_safety_breakdown", ""))
    print("RISK EVENT")
    print(res["key"]["risk_event"])


if __name__ == "__main__":
    main()
