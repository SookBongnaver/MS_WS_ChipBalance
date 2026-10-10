"""Reference calculation for the Chip Balance workshop.

Plain-Python version of the Silver, Gold and emergency-order notebooks. The notebooks must
return the same numbers. The tests generate the source files into a temporary folder and
check these results.

Run: python tools/reference_pipeline.py <source_dir>
"""
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

PLAN_START = date(2026, 10, 1)
PLAN_END = date(2026, 12, 31)
TODAY = date(2026, 10, 1)
OPENING_TS = datetime(2026, 9, 30, 23)
URGENT = {
    "customer_id": "C-1004", "customer_name": "누리전자소재", "product_id": "P-L3-05", "line_id": "L3",
    "order_qty_kg": 100000, "order_date": date(2026, 10, 1), "due_date": date(2026, 10, 8), "priority": "high",
    "production": [(date(2026, 10, 5), 50000), (date(2026, 10, 6), 50000)],
}
MOVE_FROM, MOVE_TO, MOVE_DAYS = date(2026, 10, 5), date(2026, 10, 10), 2
TRANSFER_STEP_KG = 5000
FACTOR_PLACES = Decimal("0.000001")

SOURCE = {
    "material": "sap_material",
    "supplier": "sap_supplier",
    "purchase_receipt": "sap_purchase_receipt_2025-10_2026-09",
    "purchase_order_open": "sap_purchase_order_open_2026Q4",
    "sales_order": "sap_sales_order_open_2026Q4",
    "line": "fpims_line",
    "bunker": "fpims_bunker",
    "product": "fpims_product",
    "recipe": "fpims_recipe",
    "transfer_route": "fpims_bunker_transfer_route",
    "production_lot": "fpims_production_lot_2025-10_2026-09",
    "material_consumption": "fpims_material_consumption_2025-10_2026-09",
    "production_plan": "fpims_production_plan_2026Q4",
    "bunker_level": "pvss_bunker_level_2026-09",
}


def q_half_up(value, places=Decimal("1")):
    return Decimal(value).quantize(places, rounding=ROUND_HALF_UP)


def d8(text):
    return datetime.strptime(text, "%Y%m%d").date()


def ts(text):
    return datetime.fromisoformat(text).replace(tzinfo=None)


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def ceil_to(value, step):
    return -(-value // step) * step


def read_source(source_dir):
    source_dir = Path(source_dir)
    tables = {}
    for path in sorted(source_dir.glob("*/*.csv")):
        with path.open(encoding="utf-8", newline="") as f:
            tables[path.stem] = list(csv.DictReader(f))
    for path in sorted(source_dir.glob("*/*.json")):
        with path.open(encoding="utf-8") as f:
            tables[path.stem] = [json.loads(line) for line in f if line.strip()]
    return tables


# ---------------------------------------------------------------- Silver

def silver_tables(src):
    s = {}
    get = lambda name: src[SOURCE[name]]
    s["material"] = [{"material_id": r["material_id"], "material_name": r["material_name"], "description": r["description"],
                      "unit_price_krw_per_kg": int(r["unit_price_krw_per_kg"]), "base_uom": r["base_uom"]} for r in get("material")]
    s["supplier"] = [{"supplier_id": r["supplier_id"], "supplier_name": r["supplier_name"],
                      **{k: int(r[k]) for k in ("standard_lead_time_days", "max_pull_in_days", "order_unit_kg", "pull_in_fee_krw_per_kg", "spot_premium_pct")}}
                     for r in get("supplier")]
    s["purchase_receipt"] = [{"receipt_id": r["receipt_id"], "purchase_order_id": r["purchase_order_id"], "supplier_id": r["supplier_id"],
                              "material_id": r["material_id"], "bunker_id": r["bunker_id"], "promised_date": d8(r["promised_date"]),
                              "received_date": d8(r["received_date"]), "quantity_kg": int(r["quantity"])} for r in get("purchase_receipt")]
    s["sales_order"] = [{"sales_order_id": r["sales_order_id"], "order_date": d8(r["order_date"]), "customer_id": r["customer_id"],
                         "customer_name": r["customer_name"], "product_id": r["product_id"], "order_qty_kg": int(r["order_qty_kg"]),
                         "due_date": d8(r["due_date"]), "priority": r["priority"]} for r in get("sales_order")]
    s["line"] = [{"line_id": r["line_id"], "plant_id": r["plant_id"], "line_family": r["line_family"],
                  "default_daily_output_kg": int(r["default_daily_output_kg"])} for r in get("line")]
    s["bunker"] = [{"bunker_id": r["bunker_id"], "line_id": r["line_id"], "material_id": r["material_id"],
                    "capacity_kg": int(r["capacity_kg"]), "safety_stock_kg": int(r["safety_stock_kg"])} for r in get("bunker")]
    s["product"] = [{"product_id": r["product_id"], "line_id": r["line_id"], "product_name": r["product_name"], "film_family": r["film_family"],
                     "default_daily_output_kg": int(r["default_daily_output_kg"])} for r in get("product")]
    s["recipe"] = [{"product_id": r["product_id"], "line_id": r["line_id"], "material_id": r["material_id"],
                    "std_kg_per_kg": Decimal(r["std_kg_per_kg"])} for r in get("recipe")]
    s["transfer_route"] = [{"route_id": r["route_id"], "from_bunker_id": r["from_bunker_id"], "to_bunker_id": r["to_bunker_id"],
                            "material_id": r["material_id"], "max_kg_per_day": int(r["max_kg_per_day"]),
                            "lead_time_days": int(r["lead_time_days"]), "cost_krw_per_kg": int(r["cost_krw_per_kg"])} for r in get("transfer_route")]
    s["production_lot"] = [{"lot_id": r["lot_id"], "line_id": r["line_id"], "product_id": r["product_id"], "start_ts": ts(r["start_ts"]),
                            "end_ts": ts(r["end_ts"]), "output_kg": int(r["output_kg"])} for r in get("production_lot")]
    s["material_consumption"] = [{"consumption_id": r["consumption_id"], "lot_id": r["lot_id"], "line_id": r["line_id"],
                                  "bunker_id": r["bunker_id"], "material_id": r["material_id"], "consumed_kg": int(r["consumed_kg"])}
                                 for r in get("material_consumption")]
    s["production_plan"] = [{"plan_id": r["plan_id"], "plan_date": d8(r["plan_date"]), "line_id": r["line_id"], "product_id": r["product_id"],
                             "planned_output_kg": int(r["planned_output_kg"]), "sales_order_id": r["sales_order_id"]} for r in get("production_plan")]

    quarantine = []

    def reject(table, row_number, key, reason, raw):
        quarantine.append({"source_table": table, "source_row_number": row_number, "record_key": key, "reason": reason,
                           "raw_record": json.dumps(raw, ensure_ascii=False, sort_keys=True)})

    materials = {r["material_id"] for r in s["material"]}
    seen, open_po, converted = set(), [], 0
    for i, r in enumerate(get("purchase_order_open"), 1):
        key = (r["purchase_order_id"], r["po_line_no"])
        reason = ("unknown_material" if r["material_id"] not in materials else
                  "blank_quantity" if r["quantity"] == "" else
                  "duplicate_line" if key in seen else None)
        if reason:
            reject("purchase_order_open", i, "|".join(key), reason, r)
            continue
        seen.add(key)
        qty = int(r["quantity"])
        converted += r["unit"] == "TO"
        open_po.append({"purchase_order_id": r["purchase_order_id"], "po_line_no": r["po_line_no"], "supplier_id": r["supplier_id"],
                        "material_id": r["material_id"], "bunker_id": r["bunker_id"], "promised_date": d8(r["promised_date"]),
                        "source_quantity": qty, "source_unit": r["unit"], "quantity_kg": qty * 1000 if r["unit"] == "TO" else qty})
    s["purchase_order_open"] = open_po

    capacity = {b["bunker_id"]: b["capacity_kg"] for b in s["bunker"]}
    seen, levels, observed = set(), [], set()
    for i, r in enumerate(get("bunker_level"), 1):
        key = (r["bunker_id"], r["timestamp"])
        observed.add(key)
        level = int(r["level_kg"])
        reason = ("out_of_range" if level < 0 or level > capacity[r["bunker_id"]] else
                  "duplicate_reading" if key in seen else None)
        if reason:
            reject("bunker_level", i, "|".join(key), reason, r)
            continue
        seen.add(key)
        levels.append({"bunker_id": r["bunker_id"], "reading_ts": ts(r["timestamp"]), "level_kg": level})
    s["bunker_level"] = levels
    s["quarantine"] = quarantine

    count = lambda reason: sum(1 for q in quarantine if q["reason"] == reason)
    metrics = {
        "open_po_unit_converted": converted,
        "open_po_duplicate_line": count("duplicate_line"),
        "open_po_blank_quantity": count("blank_quantity"),
        "open_po_unknown_material": count("unknown_material"),
        "sensor_out_of_range": count("out_of_range"),
        "sensor_duplicate_reading": count("duplicate_reading"),
        "sensor_missing_hour": len(capacity) * 30 * 24 - len(observed),
        "quarantine_rows": len(quarantine),
    }
    return s, metrics


# ---------------------------------------------------------------- Gold (current plan)

def usage_factors(s):
    product_of = {l["lot_id"]: l["product_id"] for l in s["production_lot"]}
    output = defaultdict(int)
    for l in s["production_lot"]:
        output[l["product_id"]] += l["output_kg"]
    used = defaultdict(int)
    for c in s["material_consumption"]:
        used[(product_of[c["lot_id"]], c["material_id"])] += c["consumed_kg"]
    std = {(r["product_id"], r["material_id"]): r["std_kg_per_kg"] for r in s["recipe"]}
    rows, factors = [], {}
    for (pid, mat), kg in sorted(used.items()):
        factor = q_half_up(Decimal(kg) / Decimal(output[pid]), FACTOR_PLACES)
        factors[(pid, mat)] = factor
        rows.append({"usage_factor_key": f"{pid}|{mat}", "product_id": pid, "material_id": mat, "std_kg_per_kg": std[(pid, mat)],
                     "actual_kg_per_kg": factor, "loss_pct": q_half_up((factor / std[(pid, mat)] - 1) * 100, Decimal("0.01")),
                     "consumed_kg": kg, "output_kg": output[pid]})
    return rows, factors


def monthly_usage(s):
    month_of = {l["lot_id"]: l["start_ts"].strftime("%Y-%m") for l in s["production_lot"]}
    kg, material = defaultdict(int), {}
    for c in s["material_consumption"]:
        kg[(month_of[c["lot_id"]], c["bunker_id"])] += c["consumed_kg"]
        material[c["bunker_id"]] = c["material_id"]
    return [{"monthly_usage_key": f"{m}|{b}", "usage_month": m, "bunker_id": b, "material_id": material[b], "consumed_kg": v}
            for (m, b), v in sorted(kg.items())]


def supplier_delay(s):
    total, count = defaultdict(int), defaultdict(int)
    for r in s["purchase_receipt"]:
        total[r["supplier_id"]] += (r["received_date"] - r["promised_date"]).days
        count[r["supplier_id"]] += 1
    return {sid: {"receipt_count": count[sid], "avg_delay_days": q_half_up(Decimal(total[sid]) / count[sid], Decimal("0.01")),
                  "planning_delay_days": int(q_half_up(Decimal(total[sid]) / count[sid]))} for sid in count}


def opening_stock(s):
    latest = {}
    for r in s["bunker_level"]:
        if r["reading_ts"] <= OPENING_TS and (r["bunker_id"] not in latest or r["reading_ts"] > latest[r["bunker_id"]]["reading_ts"]):
            latest[r["bunker_id"]] = r
    return [{"bunker_id": b, "as_of_date": PLAN_START, "reading_ts": r["reading_ts"], "opening_kg": r["level_kg"]} for b, r in sorted(latest.items())]


def inbound_lines(s, delay):
    rows = []
    for r in s["purchase_order_open"]:
        rows.append({"inbound_key": f"{r['purchase_order_id']}|{r['po_line_no']}", "purchase_order_id": r["purchase_order_id"],
                     "po_line_no": r["po_line_no"], "supplier_id": r["supplier_id"], "material_id": r["material_id"], "bunker_id": r["bunker_id"],
                     "promised_date": r["promised_date"], "expected_date": r["promised_date"] + timedelta(days=delay[r["supplier_id"]]["planning_delay_days"]),
                     "quantity_kg": r["quantity_kg"], "source_quantity": r["source_quantity"], "source_unit": r["source_unit"]})
    return sorted(rows, key=lambda r: (r["expected_date"], r["bunker_id"], r["inbound_key"]))


def requirements(plan, bunkers, factors):
    bunker_of = {(b["line_id"], b["material_id"]): b["bunker_id"] for b in bunkers}
    by_product = defaultdict(list)
    for (pid, mat), factor in factors.items():
        by_product[pid].append((mat, factor))
    req = defaultdict(int)
    for r in plan:
        for mat, factor in by_product[r["product_id"]]:
            bid = bunker_of.get((r["line_id"], mat))
            if bid:
                req[(bid, r["plan_date"])] += int(q_half_up(Decimal(r["planned_output_kg"]) * factor))
    return req


def balance(scenario_id, plan, inbound, opening, bunkers, factors, transfers=(), extra_receipts=()):
    req = requirements(plan, bunkers, factors)
    receipts = defaultdict(int)
    for r in inbound:
        receipts[(r["bunker_id"], r["expected_date"])] += r["quantity_kg"]
    for bid, d, qty in extra_receipts:
        receipts[(bid, d)] += qty
    t_in, t_out = defaultdict(int), defaultdict(int)
    for t in transfers:
        t_out[(t["from_bunker_id"], t["ship_date"])] += t["qty_kg"]
        t_in[(t["to_bunker_id"], t["arrival_date"])] += t["qty_kg"]
    start = {r["bunker_id"]: r["opening_kg"] for r in opening}
    rows = []
    for b in sorted(bunkers, key=lambda x: x["bunker_id"]):
        bid, level = b["bunker_id"], start[b["bunker_id"]]
        for d in daterange(PLAN_START, PLAN_END):
            available = level + receipts[(bid, d)] + t_in[(bid, d)]
            closing = available - t_out[(bid, d)] - req[(bid, d)]
            rows.append({"balance_key": f"{scenario_id}|{bid}|{d.isoformat()}", "scenario_id": scenario_id, "bunker_id": bid, "balance_date": d,
                         "opening_kg": level, "receipt_kg": receipts[(bid, d)], "transfer_in_kg": t_in[(bid, d)], "transfer_out_kg": t_out[(bid, d)],
                         "requirement_kg": req[(bid, d)], "closing_kg": closing, "safety_stock_kg": b["safety_stock_kg"], "capacity_kg": b["capacity_kg"],
                         "below_safety": closing < b["safety_stock_kg"], "shortage": closing < 0, "over_capacity": available > b["capacity_kg"]})
            level = closing
    return rows


def summarize(scenario_id, rows, bunkers):
    by_bunker = defaultdict(list)
    for r in rows:
        by_bunker[r["bunker_id"]].append(r)
    info = {b["bunker_id"]: b for b in bunkers}
    out = []
    for bid in sorted(by_bunker):
        br = by_bunker[bid]
        low = min(br, key=lambda r: (r["closing_kg"], r["balance_date"]))
        out.append({"summary_key": f"{scenario_id}|{bid}", "scenario_id": scenario_id, "bunker_id": bid, "line_id": info[bid]["line_id"],
                    "material_id": info[bid]["material_id"], "below_safety_days": sum(r["below_safety"] for r in br),
                    "first_below_safety_date": next((r["balance_date"] for r in br if r["below_safety"]), None),
                    "first_shortage_date": next((r["balance_date"] for r in br if r["shortage"]), None),
                    "min_closing_kg": low["closing_kg"], "min_closing_date": low["balance_date"],
                    "required_topup_kg": max(0, info[bid]["safety_stock_kg"] - low["closing_kg"])})
    return out


def plan_rows(scenario_id, plan):
    return [{"plan_key": f"{scenario_id}|{r['plan_id']}", "scenario_id": scenario_id, **r,
             "original_plan_date": r.get("original_plan_date", r["plan_date"]), "change_type": r.get("change_type", "none")} for r in plan]


def fulfillment(scenario_id, plan, orders, products):
    finish = {}
    for r in plan:
        finish[r["sales_order_id"]] = max(finish.get(r["sales_order_id"], r["plan_date"]), r["plan_date"])
    line_of = {p["product_id"]: p["line_id"] for p in products}
    rows = []
    for o in orders:
        done = finish[o["sales_order_id"]]
        rows.append({"fulfillment_key": f"{scenario_id}|{o['sales_order_id']}", "scenario_id": scenario_id, "sales_order_id": o["sales_order_id"],
                     "customer_id": o["customer_id"], "product_id": o["product_id"], "line_id": line_of[o["product_id"]], "due_date": o["due_date"],
                     "finish_date": done, "slack_days": (o["due_date"] - done).days, "on_time": done <= o["due_date"]})
    return rows


def gold_current(s):
    delay = supplier_delay(s)
    usage_rows, factors = usage_factors(s)
    opening = opening_stock(s)
    inbound = inbound_lines(s, delay)
    supplier_of = {}
    for r in s["purchase_receipt"]:
        supplier_of[r["material_id"]] = r["supplier_id"]
    orders = s["sales_order"]
    line_of = {p["product_id"]: p["line_id"] for p in s["product"]}
    plan = s["production_plan"]
    bal = balance("baseline", plan, inbound, opening, s["bunker"], factors)
    weekday = "월화수목금토일"
    gold = {
        "dim_line": [dict(r) for r in s["line"]],
        "dim_bunker": [{"bunker_id": b["bunker_id"], "bunker_name": f"{b['line_id']} {b['material_id']}", **{k: b[k] for k in ("line_id", "material_id", "capacity_kg", "safety_stock_kg")}}
                            for b in s["bunker"]],
        "dim_material": [{**{k: m[k] for k in ("material_id", "material_name", "description", "unit_price_krw_per_kg")}, "supplier_id": supplier_of[m["material_id"]]}
                              for m in s["material"]],
        "dim_product": [{k: p[k] for k in ("product_id", "product_name", "line_id", "film_family")} for p in s["product"]],
        "dim_supplier": [{**sup, **delay[sup["supplier_id"]]} for sup in s["supplier"]],
        "dim_customer": sorted({(o["customer_id"], o["customer_name"]) for o in orders}),
        "dim_route": [dict(r) for r in s["transfer_route"]],
        "dim_date": [{"date_key": d, "yyyymm": d.strftime("%Y%m"), "day_of_week": d.isoweekday(), "weekday_name": weekday[d.weekday()]}
                          for d in daterange(PLAN_START, PLAN_END)],
        "dim_scenario": [{"scenario_id": "baseline", "scenario_name": "현재 계획", "description": "2026년 4분기 생산계획과 입고 예정"}],
        "fact_usage_factor": usage_rows,
        "fact_monthly_usage": monthly_usage(s),
        "fact_opening_stock": opening,
        "fact_inbound": inbound,
        "fact_sales_order": [{**{k: o[k] for k in ("sales_order_id", "order_date", "customer_id", "product_id")}, "line_id": line_of[o["product_id"]],
                                   **{k: o[k] for k in ("order_qty_kg", "due_date", "priority")}, "is_urgent": False} for o in orders],
        "fact_plan": plan_rows("baseline", plan),
        "fact_order_fulfillment": fulfillment("baseline", plan, orders, s["product"]),
        "fact_balance": bal,
        "fact_bunker_summary": summarize("baseline", bal, s["bunker"]),
    }
    gold["dim_customer"] = [{"customer_id": c, "customer_name": n} for c, n in gold["dim_customer"]]
    context = {"delay": delay, "factors": factors, "opening": opening, "inbound": inbound, "plan": plan, "orders": orders}
    return gold, context


# ---------------------------------------------------------------- Emergency order

def urgent_order_id(orders):
    return f"SO-{max(int(o['sales_order_id'][3:]) for o in orders) + 1}"


def emergency_plan(plan, so_id):
    rows = []
    for r in plan:
        moved = r["line_id"] == URGENT["line_id"] and MOVE_FROM <= r["plan_date"] <= MOVE_TO
        rows.append({**r, "plan_date": r["plan_date"] + timedelta(days=MOVE_DAYS) if moved else r["plan_date"],
                     "original_plan_date": r["plan_date"], "change_type": "moved" if moved else "none"})
    for d, qty in URGENT["production"]:
        rows.append({"plan_id": f"PP-{d:%Y%m%d}-{URGENT['line_id']}-U", "plan_date": d, "line_id": URGENT["line_id"], "product_id": URGENT["product_id"],
                     "planned_output_kg": qty, "sales_order_id": so_id, "original_plan_date": d, "change_type": "urgent"})
    return sorted(rows, key=lambda r: (r["plan_date"], r["line_id"], r["plan_id"]))


def check_options(s, ctx, affected, orders, emg_plan):
    """Build and test the four responses. Only the passing responses get a rank, cheapest first."""
    bunkers = {b["bunker_id"]: b for b in s["bunker"]}
    target = affected["bunker_id"]
    material = bunkers[target]["material_id"]
    supplier_id = next(r["supplier_id"] for r in s["purchase_receipt"] if r["material_id"] == material)
    sup = next(x for x in s["supplier"] if x["supplier_id"] == supplier_id)
    delay = ctx["delay"][supplier_id]["planning_delay_days"]
    price = next(m["unit_price_krw_per_kg"] for m in s["material"] if m["material_id"] == material)
    topup = affected["required_topup_kg"]
    first_below = affected["first_below_safety_date"]
    inbound = ctx["inbound"]

    next_in = min((r for r in inbound if r["bunker_id"] == target and r["expected_date"] > first_below),
                  key=lambda r: (r["expected_date"], r["inbound_key"]))
    pulled_promised = max(next_in["promised_date"] - timedelta(days=sup["max_pull_in_days"]), TODAY + timedelta(days=1))
    pulled = [dict(r, expected_date=pulled_promised + timedelta(days=delay)) if r is next_in else r for r in inbound]

    route = min((r for r in s["transfer_route"] if r["to_bunker_id"] == target and r["material_id"] == material),
                key=lambda r: (r["cost_krw_per_kg"], r["route_id"]))
    transfer_qty = ceil_to(topup, TRANSFER_STEP_KG)
    transfers, left, ship = [], transfer_qty, TODAY + timedelta(days=1)
    while left > 0:
        qty = min(left, route["max_kg_per_day"])
        transfers.append({"route_id": route["route_id"], "from_bunker_id": route["from_bunker_id"], "to_bunker_id": target, "qty_kg": qty,
                          "ship_date": ship, "arrival_date": ship + timedelta(days=route["lead_time_days"])})
        left -= qty
        ship += timedelta(days=1)

    spot_qty = ceil_to(topup, sup["order_unit_kg"])
    spot_arrival = TODAY + timedelta(days=sup["standard_lead_time_days"] + delay)

    urgent_rows = [r for r in emg_plan if r["change_type"] == "urgent"]
    free_days = [d for d in daterange(next_in["expected_date"] + timedelta(days=1), PLAN_END)
                 if not any(r["line_id"] == URGENT["line_id"] and r["plan_date"] == d for r in ctx["plan"])][:len(urgent_rows)]
    resched = [dict(r, original_plan_date=r["plan_date"], change_type="none") for r in ctx["plan"]]
    resched += [dict(r, plan_date=d, change_type="urgent") for r, d in zip(urgent_rows, free_days)]

    options = [
        {"option_id": "OPT-1", "option_name": "입고 앞당김", "plan": emg_plan, "inbound": pulled, "transfers": [], "extra": [],
         "added_cost_krw": next_in["quantity_kg"] * sup["pull_in_fee_krw_per_kg"], "qty_kg": next_in["quantity_kg"],
         "source_bunker_id": None, "route_id": None, "purchase_order_id": next_in["purchase_order_id"], "supplier_id": supplier_id,
         "first_arrival_date": pulled_promised + timedelta(days=delay),
         "action_detail": f"{next_in['purchase_order_id']}-{next_in['po_line_no']} 입고일을 {next_in['expected_date']:%m/%d}에서 {pulled_promised + timedelta(days=delay):%m/%d}로 앞당김"},
        {"option_id": "OPT-2", "option_name": "Bunker 간 이송", "plan": emg_plan, "inbound": inbound, "transfers": transfers, "extra": [],
         "added_cost_krw": transfer_qty * route["cost_krw_per_kg"], "qty_kg": transfer_qty,
         "source_bunker_id": route["from_bunker_id"], "route_id": route["route_id"], "purchase_order_id": None, "supplier_id": None,
         "first_arrival_date": transfers[0]["arrival_date"],
         "action_detail": f"{route['from_bunker_id']}에서 {target}로 {material} {transfer_qty:,} kg 이송 ({route['route_id']}, {transfers[0]['ship_date']:%m/%d} 출고, {transfers[-1]['arrival_date']:%m/%d} 도착)"},
        {"option_id": "OPT-3", "option_name": "추가 구매", "plan": emg_plan, "inbound": inbound, "transfers": [], "extra": [(target, spot_arrival, spot_qty)],
         "added_cost_krw": int(q_half_up(Decimal(spot_qty * price * sup["spot_premium_pct"]) / 100)), "qty_kg": spot_qty,
         "source_bunker_id": None, "route_id": None, "purchase_order_id": None, "supplier_id": supplier_id, "first_arrival_date": spot_arrival,
         "action_detail": f"{sup['supplier_name']}({supplier_id})에 {material} {spot_qty:,} kg 긴급 구매 ({spot_arrival:%m/%d} 입고)"},
        {"option_id": "OPT-4", "option_name": "생산 순서 조정", "plan": resched, "inbound": inbound, "transfers": [], "extra": [],
         "added_cost_krw": 0, "qty_kg": URGENT["order_qty_kg"], "source_bunker_id": None, "route_id": None, "purchase_order_id": None,
         "supplier_id": None, "first_arrival_date": None,
         "action_detail": f"긴급 생산을 다음 입고({next_in['expected_date']:%m/%d}) 뒤 {free_days[0]:%m/%d}–{free_days[-1]:%m/%d}로 이동"},
    ]
    due = {o["sales_order_id"]: o["due_date"] for o in orders}
    route_limit = {(r["from_bunker_id"], r["to_bunker_id"]): r["max_kg_per_day"] for r in s["transfer_route"]}
    option_rows, option_balance = [], []
    for opt in options:
        rows = balance(opt["option_id"], opt["plan"], opt["inbound"], ctx["opening"], s["bunker"], ctx["factors"], opt["transfers"], opt["extra"])
        touched = {target} | {t["from_bunker_id"] for t in opt["transfers"]}
        option_balance += [{"option_balance_key": r["balance_key"], "option_id": opt["option_id"], **{k: v for k, v in r.items() if k not in ("balance_key", "scenario_id")}}
                           for r in rows if r["bunker_id"] in touched]
        below = [r for r in rows if r["below_safety"]]
        over = [r for r in rows if r["over_capacity"]]
        finish = {}
        for r in opt["plan"]:
            finish[r["sales_order_id"]] = max(finish.get(r["sales_order_id"], r["plan_date"]), r["plan_date"])
        late = sorted((so for so, d in finish.items() if d > due[so]), key=lambda so: finish[so])
        bad_route = [t for t in opt["transfers"] if t["qty_kg"] > route_limit.get((t["from_bunker_id"], t["to_bunker_id"]), 0)]
        c1, c2, c3, c4 = not below, not over, not late, not bad_route
        reasons = []
        if not c1:
            first = min(below, key=lambda r: (r["balance_date"], r["bunker_id"]))
            reasons.append(f"C1 안전재고: {first['bunker_id']} {first['balance_date']:%m/%d}부터 미달")
        if not c2:
            first = min(over, key=lambda r: (r["balance_date"], r["bunker_id"]))
            reasons.append(f"C2 용량: {first['bunker_id']} {first['balance_date']:%m/%d} 초과")
        if not c3:
            reasons.append(f"C3 납기: {late[0]} 완료 {finish[late[0]]:%m/%d}, 납기 {due[late[0]]:%m/%d}")
        if not c4:
            reasons.append(f"C4 이송 한도: {bad_route[0]['route_id']} 하루 한도 초과")
        option_rows.append({"option_id": opt["option_id"], "option_name": opt["option_name"], "scenario_id": "emergency", "target_bunker_id": target,
                            "source_bunker_id": opt["source_bunker_id"], "route_id": opt["route_id"], "purchase_order_id": opt["purchase_order_id"],
                            "supplier_id": opt["supplier_id"], "qty_kg": opt["qty_kg"], "first_arrival_date": opt["first_arrival_date"],
                            "added_cost_krw": opt["added_cost_krw"], "c1_safety_pass": c1, "c2_capacity_pass": c2, "c3_due_date_pass": c3,
                            "c4_route_limit_pass": c4, "meets_all": c1 and c2 and c3 and c4, "below_safety_days": len(below),
                            "late_order_count": len(late), "recommendation_rank": None, "action_detail": opt["action_detail"], "result_note": "; ".join(reasons) or "모든 기준 충족"})
    passing = sorted((r for r in option_rows if r["meets_all"]), key=lambda r: (r["added_cost_krw"], r["option_id"]))
    for i, r in enumerate(passing, 1):
        r["recommendation_rank"] = i
    return option_rows, option_balance, next_in


def gold_emergency(s, gold, ctx, detected_at=None):
    so_id = urgent_order_id(ctx["orders"])
    urgent = {"sales_order_id": so_id, "order_date": URGENT["order_date"], "customer_id": URGENT["customer_id"], "customer_name": URGENT["customer_name"],
              "product_id": URGENT["product_id"], "order_qty_kg": URGENT["order_qty_kg"], "due_date": URGENT["due_date"], "priority": URGENT["priority"]}
    orders = ctx["orders"] + [urgent]
    plan = emergency_plan(ctx["plan"], so_id)
    bal = balance("emergency", plan, ctx["inbound"], ctx["opening"], s["bunker"], ctx["factors"])
    summary = summarize("emergency", bal, s["bunker"])
    base_below = {r["bunker_id"] for r in gold["fact_bunker_summary"] if r["below_safety_days"]}
    newly = sorted((r for r in summary if r["below_safety_days"] and r["bunker_id"] not in base_below),
                   key=lambda r: (r["first_below_safety_date"], r["bunker_id"]))
    affected = newly[0]
    options, option_balance, next_in = check_options(s, ctx, affected, orders, plan)
    best = next(r for r in options if r["recommendation_rank"] == 1)
    risk = {"event_id": f"EVT-{TODAY:%Y%m%d}-001", "detected_at": detected_at, "scenario_id": "emergency", "sales_order_id": so_id,
            "bunker_id": affected["bunker_id"], "line_id": affected["line_id"], "material_id": affected["material_id"],
            "first_below_safety_date": affected["first_below_safety_date"], "first_shortage_date": affected["first_shortage_date"],
            "min_closing_kg": affected["min_closing_kg"], "min_closing_date": affected["min_closing_date"],
            "required_topup_kg": affected["required_topup_kg"], "next_inbound_key": next_in["inbound_key"],
            "recommended_option_id": best["option_id"], "recommended_action": best["action_detail"], "status": "open"}
    return {
        "dim_scenario": [{"scenario_id": "emergency", "scenario_name": "긴급 오더 반영",
                               "description": f"{URGENT['order_date']:%Y-%m-%d} 접수 {so_id} ({URGENT['customer_name']}, {URGENT['product_id']} {URGENT['order_qty_kg']:,} kg)"}],
        "fact_sales_order": [{**{k: urgent[k] for k in ("sales_order_id", "order_date", "customer_id", "product_id")}, "line_id": URGENT["line_id"],
                                   **{k: urgent[k] for k in ("order_qty_kg", "due_date", "priority")}, "is_urgent": True}],
        "fact_plan": plan_rows("emergency", plan),
        "fact_order_fulfillment": fulfillment("emergency", plan, orders, s["product"]),
        "fact_balance": bal,
        "fact_bunker_summary": summary,
        "fact_response_option": options,
        "fact_option_balance": option_balance,
        "fact_risk_event": [risk],
    }


def build(source_dir):
    src = read_source(source_dir)
    s, metrics = silver_tables(src)
    gold, ctx = gold_current(s)
    emergency = gold_emergency(s, gold, ctx)
    return {"source": src, "silver": s, "quarantine_metrics": metrics, "gold": gold, "emergency": emergency, "context": ctx}


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python tools/reference_pipeline.py <source_dir>")
    res = build(sys.argv[1])
    print("SOURCE", {k: len(v) for k, v in res["source"].items()}, "total", sum(len(v) for v in res["source"].values()))
    print("SILVER", res["quarantine_metrics"])
    print("GOLD", {k: len(v) for k, v in res["gold"].items()})
    print("EMERGENCY", {k: len(v) for k, v in res["emergency"].items()})
    for r in res["emergency"]["fact_bunker_summary"]:
        if r["below_safety_days"]:
            print("BELOW", r)
    for r in res["emergency"]["fact_response_option"]:
        print("OPTION", r)
    print("RISK", res["emergency"]["fact_risk_event"][0])


if __name__ == "__main__":
    main()
