from __future__ import annotations

import csv
import json
import random
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 20261001
KST = timezone(timedelta(hours=9))
START_ACTUAL = date(2025, 10, 1)
END_ACTUAL = date(2026, 9, 30)
PLAN_START = date(2026, 10, 1)
PLAN_END = date(2026, 12, 31)
SENSOR_START = datetime(2026, 9, 1, 0, 0, tzinfo=KST)

MATERIALS = [
    ("PET-BR", "Bright PET chip", "BOPET main bright polyester", 1180),
    ("PET-SD", "Semi-dull PET chip", "BOPET semi-dull polyester", 1250),
    ("PET-RC", "Recycled PET chip", "Recycled polyester blend", 980),
    ("PET-CO", "Copolyester chip", "Copolyester sealant grade", 1420),
    ("MB-AB", "Anti-block masterbatch", "Silica anti-block MB", 2850),
    ("MB-SL", "Slip masterbatch", "Slip additive MB", 3120),
    ("MB-WH", "White masterbatch", "TiO2 white MB", 3350),
    ("MB-UV", "UV masterbatch", "UV stabilizer MB", 3680),
    ("NY6-F", "Nylon 6 film chip", "BOPA film grade nylon 6", 2180),
    ("NY6-H", "High-viscosity nylon 6", "High IV nylon 6", 2380),
    ("MB-NA", "Nylon anti-block MB", "BOPA anti-block MB", 3260),
    ("MB-NS", "Nylon slip MB", "BOPA slip MB", 3480),
]
SUPPLIERS = [
    ("SUP-PET-A", "한빛케미칼", 7, 2, 25000),
    ("SUP-PET-B", "세미폴리머", 4, 2, 25000),
    ("SUP-MB-A", "첨단마스터", 6, 1, 5000),
    ("SUP-NY-A", "나일론소재", 9, 2, 25000),
    ("SUP-NY-B", "고점도케미칼", 10, 2, 25000),
    ("SUP-ADD-A", "기능성첨가", 5, 1, 1000),
]
SUP_BY_MAT = {
    "PET-BR": "SUP-PET-A", "PET-SD": "SUP-PET-B", "PET-RC": "SUP-PET-A", "PET-CO": "SUP-PET-B",
    "MB-AB": "SUP-MB-A", "MB-SL": "SUP-MB-A", "MB-WH": "SUP-ADD-A", "MB-UV": "SUP-ADD-A",
    "NY6-F": "SUP-NY-A", "NY6-H": "SUP-NY-B", "MB-NA": "SUP-ADD-A", "MB-NS": "SUP-ADD-A",
}
LINES = [
    ("L1", "BOPET", 52000), ("L2", "BOPET", 50000), ("L3", "BOPET", 50000),
    ("L4", "BOPET", 47000), ("L5", "BOPA", 28000), ("L6", "BOPA", 26000),
]
BUNKER_ASSIGN = {
    "L1": ["PET-BR", "PET-SD", "MB-AB", "MB-SL"],
    "L2": ["PET-BR", "PET-RC", "MB-AB", "MB-WH"],
    "L3": ["PET-BR", "PET-SD", "MB-SL", "MB-UV"],
    "L4": ["PET-BR", "PET-CO", "MB-WH", "MB-UV"],
    "L5": ["NY6-F", "NY6-H", "MB-NA", "MB-NS"],
    "L6": ["NY6-F", "NY6-H", "MB-NA", "MB-NS"],
}
CAPACITY = {"PET-BR": 250000, "PET-SD": 250000, "PET-RC": 150000, "PET-CO": 150000,
            "NY6-F": 170000, "NY6-H": 150000,
            "MB-AB": 20000, "MB-SL": 18000, "MB-WH": 18000, "MB-UV": 16000, "MB-NA": 16000, "MB-NS": 16000}
SAFETY = {"PET-BR": 45000, "PET-SD": 12000, "PET-RC": 35000, "PET-CO": 32000,
          "NY6-F": 35000, "NY6-H": 18000,
          "MB-AB": 2500, "MB-SL": 2200, "MB-WH": 2200, "MB-UV": 1000, "MB-NA": 1800, "MB-NS": 1800}
OPENING = {
    "BNK-L1-1": 190000, "BNK-L1-2": 245000, "BNK-L1-3": 12000, "BNK-L1-4": 11000,
    "BNK-L2-1": 190000, "BNK-L2-2": 110000, "BNK-L2-3": 11500, "BNK-L2-4": 10500,
    "BNK-L3-1": 190000, "BNK-L3-2": 106000, "BNK-L3-3": 11000, "BNK-L3-4": 10000,
    "BNK-L4-1": 185000, "BNK-L4-2": 105000, "BNK-L4-3": 10500, "BNK-L4-4": 9500,
    "BNK-L5-1": 130000, "BNK-L5-2": 95000, "BNK-L5-3": 9000, "BNK-L5-4": 9000,
    "BNK-L6-1": 125000, "BNK-L6-2": 90000, "BNK-L6-3": 8500, "BNK-L6-4": 8500,
}
# Base recipes. Sums are 1.02 to 1.04 kg chip per kg product before deterministic loss.
RECIPE_BY_PRODUCT = {
    "L1": [
        [("PET-BR", "0.965"), ("PET-SD", "0.040"), ("MB-AB", "0.015"), ("MB-SL", "0.010")],
        [("PET-BR", "0.965"), ("PET-SD", "0.030"), ("MB-AB", "0.020"), ("MB-SL", "0.010")],
        [("PET-BR", "0.955"), ("PET-SD", "0.050"), ("MB-AB", "0.015"), ("MB-SL", "0.010")],
        [("PET-BR", "0.965"), ("PET-SD", "0.030"), ("MB-AB", "0.020"), ("MB-SL", "0.015")],
        [("PET-BR", "0.955"), ("PET-SD", "0.050"), ("MB-AB", "0.015"), ("MB-SL", "0.010")],
    ],
    "L2": [
        [("PET-BR", "0.840"), ("PET-RC", "0.165"), ("MB-AB", "0.015"), ("MB-WH", "0.010")],
        [("PET-BR", "0.800"), ("PET-RC", "0.205"), ("MB-AB", "0.015"), ("MB-WH", "0.010")],
        [("PET-BR", "0.780"), ("PET-RC", "0.225"), ("MB-AB", "0.015"), ("MB-WH", "0.010")],
        [("PET-BR", "0.865"), ("PET-RC", "0.135"), ("MB-AB", "0.020"), ("MB-WH", "0.010")],
        [("PET-BR", "0.820"), ("PET-RC", "0.180"), ("MB-AB", "0.015"), ("MB-WH", "0.015")],
    ],
    "L3": [
        [("PET-BR", "0.875"), ("PET-SD", "0.120"), ("MB-SL", "0.020"), ("MB-UV", "0.010")],
        [("PET-BR", "0.895"), ("PET-SD", "0.100"), ("MB-SL", "0.020"), ("MB-UV", "0.010")],
        [("PET-BR", "0.845"), ("PET-SD", "0.150"), ("MB-SL", "0.020"), ("MB-UV", "0.010")],
        [("PET-BR", "0.900"), ("PET-SD", "0.095"), ("MB-SL", "0.020"), ("MB-UV", "0.015")],
        [("PET-BR", "0.420"), ("PET-SD", "0.600"), ("MB-SL", "0.000"), ("MB-UV", "0.000")],
    ],
    "L4": [
        [("PET-BR", "0.830"), ("PET-CO", "0.175"), ("MB-WH", "0.015"), ("MB-UV", "0.010")],
        [("PET-BR", "0.800"), ("PET-CO", "0.200"), ("MB-WH", "0.020"), ("MB-UV", "0.010")],
        [("PET-BR", "0.855"), ("PET-CO", "0.145"), ("MB-WH", "0.020"), ("MB-UV", "0.010")],
        [("PET-BR", "0.820"), ("PET-CO", "0.180"), ("MB-WH", "0.015"), ("MB-UV", "0.015")],
        [("PET-BR", "0.780"), ("PET-CO", "0.220"), ("MB-WH", "0.020"), ("MB-UV", "0.010")],
    ],
    "L5": [
        [("NY6-F", "0.820"), ("NY6-H", "0.185"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
        [("NY6-F", "0.785"), ("NY6-H", "0.220"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
        [("NY6-F", "0.850"), ("NY6-H", "0.150"), ("MB-NA", "0.020"), ("MB-NS", "0.010")],
        [("NY6-F", "0.810"), ("NY6-H", "0.190"), ("MB-NA", "0.015"), ("MB-NS", "0.015")],
        [("NY6-F", "0.790"), ("NY6-H", "0.210"), ("MB-NA", "0.020"), ("MB-NS", "0.010")],
    ],
    "L6": [
        [("NY6-F", "0.830"), ("NY6-H", "0.175"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
        [("NY6-F", "0.800"), ("NY6-H", "0.205"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
        [("NY6-F", "0.855"), ("NY6-H", "0.145"), ("MB-NA", "0.020"), ("MB-NS", "0.010")],
        [("NY6-F", "0.815"), ("NY6-H", "0.185"), ("MB-NA", "0.015"), ("MB-NS", "0.015")],
        [("NY6-F", "0.790"), ("NY6-H", "0.210"), ("MB-NA", "0.020"), ("MB-NS", "0.010")],
    ],
}
HIDDEN_LOSS_BY_PRODUCT_MATERIAL = {}
for _line_id, _recipes in RECIPE_BY_PRODUCT.items():
    for _idx, _comps in enumerate(_recipes, 1):
        for _j, (_mat, _std) in enumerate(_comps):
            HIDDEN_LOSS_BY_PRODUCT_MATERIAL[(f"P-{_line_id}-{_idx:02d}", _mat)] = Decimal("0.010") + Decimal((_idx + _j) % 4) / Decimal(100)


def q_half_up(value: Decimal | str | int | float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def product_rows():
    rows = []
    for line_id, family, default_kg in LINES:
        for idx in range(1, 6):
            product_id = f"P-{line_id}-{idx:02d}"
            rows.append({
                "product_id": product_id,
                "line_id": line_id,
                "product_name": f"{family} Film Grade {line_id}-{idx}",
                "film_family": family,
                "default_daily_output_kg": str(default_kg if idx != 5 or line_id != "L3" else 50000),
            })
    return rows


def recipe_rows():
    rows = []
    for line_id in RECIPE_BY_PRODUCT:
        for idx, comps in enumerate(RECIPE_BY_PRODUCT[line_id], 1):
            product_id = f"P-{line_id}-{idx:02d}"
            for mat, std in comps:
                if Decimal(std) == 0:
                    continue
                rows.append({
                    "product_id": product_id,
                    "line_id": line_id,
                    "material_id": mat,
                    "std_kg_per_kg": std,
                })
    return rows


def generate_all(output_dir: str | Path | None = None) -> Path:
    root = Path(__file__).resolve().parents[1]
    out = Path(output_dir) if output_dir else root / "data"
    if out.exists():
        for child in sorted(out.iterdir(), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(SEED)

    mats = [{"material_id": a, "material_name": b, "description": c, "unit_price_krw_per_kg": str(p), "base_uom": "KG"} for a, b, c, p in MATERIALS]
    write_csv(out / "sap_material.csv", mats, list(mats[0].keys()))
    sups = [{"supplier_id": a, "supplier_name": b, "standard_lead_time_days": str(c), "max_pull_in_days": str(d), "order_unit_kg": str(e)} for a, b, c, d, e in SUPPLIERS]
    write_csv(out / "sap_supplier.csv", sups, list(sups[0].keys()))

    line_rows = [{"line_id": l, "plant_id": "P001", "line_family": fam, "default_daily_output_kg": str(kg)} for l, fam, kg in LINES]
    write_csv(out / "fpims_line.csv", line_rows, list(line_rows[0].keys()))

    bunkers = []
    for line_id, chips in BUNKER_ASSIGN.items():
        for i, mat in enumerate(chips, 1):
            bid = f"BNK-{line_id}-{i}"
            bunkers.append({"bunker_id": bid, "line_id": line_id, "material_id": mat, "capacity_kg": str(CAPACITY[mat]), "safety_stock_kg": str(SAFETY[mat])})
    write_csv(out / "fpims_bunker.csv", bunkers, list(bunkers[0].keys()))

    products = product_rows()
    write_csv(out / "fpims_product.csv", products, list(products[0].keys()))
    recipes = recipe_rows()
    write_csv(out / "fpims_recipe.csv", recipes, list(recipes[0].keys()))

    route_defs = [
        ("BNK-L1-2", "BNK-L3-2", 40000, 1, 25), ("BNK-L3-2", "BNK-L1-2", 35000, 1, 25),
        ("BNK-L1-1", "BNK-L2-1", 50000, 1, 18), ("BNK-L2-1", "BNK-L3-1", 50000, 1, 18),
        ("BNK-L3-1", "BNK-L4-1", 45000, 1, 18), ("BNK-L2-3", "BNK-L1-3", 8000, 1, 40),
        ("BNK-L1-4", "BNK-L3-3", 7000, 1, 40), ("BNK-L3-4", "BNK-L4-4", 6000, 1, 45),
        ("BNK-L5-1", "BNK-L6-1", 35000, 1, 22), ("BNK-L6-1", "BNK-L5-1", 35000, 1, 22),
        ("BNK-L5-2", "BNK-L6-2", 25000, 1, 24), ("BNK-L6-4", "BNK-L5-4", 5000, 1, 42),
    ]
    routes = []
    bmat = {b["bunker_id"]: b["material_id"] for b in bunkers}
    for i, (src, dst, maxkg, lead, cost) in enumerate(route_defs, 1):
        routes.append({"route_id": f"R-{i:02d}", "from_bunker_id": src, "to_bunker_id": dst, "material_id": bmat[src], "max_kg_per_day": str(maxkg), "lead_time_days": str(lead), "cost_krw_per_kg": str(cost)})
    write_csv(out / "fpims_bunker_transfer_route.csv", routes, list(routes[0].keys()))

    # Actual production lots and chip consumption.
    recipe_by_pid = {}
    for r in recipes:
        recipe_by_pid.setdefault(r["product_id"], []).append(r)
    lots, cons = [], []
    lot_no = 1
    for d in daterange(START_ACTUAL, END_ACTUAL):
        day_idx = (d - START_ACTUAL).days
        for line_id, fam, default_kg in LINES:
            # one deterministic maintenance day per line and quarter, no production lot
            if (day_idx + int(line_id[1:]) * 17) % 18 == 0:
                continue
            product_index = (day_idx + int(line_id[1:])) % 5 + 1
            pid = f"P-{line_id}-{product_index:02d}"
            daily_kg = default_kg + ((day_idx % 7) - 3) * (350 if fam == "BOPET" else 180)
            for shift in (1, 2):
                output = q_half_up(Decimal(daily_kg) / Decimal(2) + (shift - 1) * Decimal(120))
                lot_id = f"LOT-{lot_no:05d}"
                lots.append({"lot_id": lot_id, "line_id": line_id, "product_id": pid, "start_ts": f"{d.isoformat()}T{8 if shift == 1 else 20:02d}:00:00+09:00", "end_ts": f"{d.isoformat()}T{16 if shift == 1 else 23:02d}:30:00+09:00", "output_kg": str(output)})
                for rr in recipe_by_pid[pid]:
                    mat = rr["material_id"]
                    bunker_id = next(b["bunker_id"] for b in bunkers if b["line_id"] == line_id and b["material_id"] == mat)
                    hidden_loss = HIDDEN_LOSS_BY_PRODUCT_MATERIAL[(pid, mat)]
                    noise = Decimal(((lot_no + len(mat)) % 11) - 5) / Decimal(1000)
                    factor = Decimal(rr["std_kg_per_kg"]) * (Decimal("1") + hidden_loss + noise)
                    cons.append({"consumption_id": f"CON-{len(cons)+1:06d}", "lot_id": lot_id, "line_id": line_id, "bunker_id": bunker_id, "material_id": mat, "consumed_kg": str(q_half_up(Decimal(output) * factor))})
                lot_no += 1
    write_csv(out / "fpims_production_lot_2025-10_2026-09.csv", lots, list(lots[0].keys()))
    write_csv(out / "fpims_material_consumption_2025-10_2026-09.csv", cons, list(cons[0].keys()))

    # Actual purchase receipts.
    delay_patterns = {
        "SUP-PET-A": [-1, 0, 0, 0, 0, 1, 1, 0, 2, 0],
        "SUP-PET-B": [-1, 0, 0, 0, 1, 0, 0, 2],
        "SUP-MB-A": [-1, 0, 1, 1, 1, 2, 2, 3, 0, 4],
        "SUP-NY-A": [0, 0, 1, 1, 1, 2, 2, 3, -1, 3],
        "SUP-NY-B": [0, 1, 2, 2, 2, 3, 3, 4, 5, 0],
        "SUP-ADD-A": [1, 2, 2, 3, 3, 3, 4, 4, 5, 0],
    }
    recs = []
    supplier_receipt_index = defaultdict(int)
    mat_ids = [m[0] for m in MATERIALS]
    for i in range(1900):
        mat = mat_ids[i % len(mat_ids)]
        sup = SUP_BY_MAT[mat]
        promised = START_ACTUAL + timedelta(days=(i * 7) % 365)
        delay = delay_patterns[sup][supplier_receipt_index[sup] % len(delay_patterns[sup])]
        supplier_receipt_index[sup] += 1
        qty = 5000 + (i % 37) * 700
        recs.append({"receipt_id": f"GR-{i+1:05d}", "purchase_order_id": f"POH-{i//3+1:05d}", "supplier_id": sup, "material_id": mat, "promised_date": ymd(promised), "received_date": ymd(promised + timedelta(days=delay)), "quantity": str(qty), "unit": "KG"})
    recs.sort(key=lambda r: r["receipt_id"])
    write_csv(out / "sap_purchase_receipt_2025-10_2026-09.csv", recs, list(recs[0].keys()))

    # Sales orders and production plan. L3 spare days are left empty for emergency displacement.
    sales = []
    pids = [p["product_id"] for p in products]
    for i in range(360):
        pid = pids[i % len(pids)]
        sales.append({"sales_order_id": f"SO-{i+1:04d}", "customer_segment": f"SEG-{i % 9 + 1}", "product_id": pid, "order_qty_kg": str(18000 + (i % 11) * 2000), "due_date": ymd(PLAN_END), "priority": "normal"})
    write_csv(out / "sap_sales_order_open_2026Q4.csv", sales, list(sales[0].keys()))

    plan = []
    so_idx = 0
    spare_dates = {date(2026, 10, d) for d in range(11, 16)}
    for d in daterange(PLAN_START, PLAN_END):
        day_idx = (d - PLAN_START).days
        for line_id, fam, default_kg in LINES:
            if line_id == "L3" and d in spare_dates:
                continue
            if line_id == "L3" and date(2026, 10, 3) <= d <= date(2026, 10, 7):
                product_index = 1
            else:
                product_index = (day_idx + int(line_id[1:])) % 5 + 1
            pid = f"P-{line_id}-{product_index:02d}"
            qty = default_kg + ((day_idx % 5) - 2) * (400 if fam == "BOPET" else 180)
            plan.append({"plan_id": f"PLAN-{len(plan)+1:04d}", "plan_date": ymd(d), "line_id": line_id, "product_id": pid, "planned_output_kg": str(qty), "sales_order_id": sales[so_idx % len(sales)]["sales_order_id"]})
            so_idx += 1
    write_csv(out / "fpims_production_plan_2026Q4.csv", plan, list(plan[0].keys()))

    # Open PO lines for Q4 are generated by a deterministic reorder rule per bunker.
    delay_days = {"SUP-PET-A": 0, "SUP-PET-B": 0, "SUP-MB-A": 1, "SUP-NY-A": 1, "SUP-NY-B": 2, "SUP-ADD-A": 2}
    recipe_lookup = {}
    for r in recipes:
        recipe_lookup.setdefault(r["product_id"], []).append(r)
    b_by_line_mat = {(b["line_id"], b["material_id"]): b["bunker_id"] for b in bunkers}
    req_by_bunker_day = {(b["bunker_id"], d): 0 for b in bunkers for d in daterange(PLAN_START, PLAN_END)}
    for pr in plan:
        pd = datetime.strptime(pr["plan_date"], "%Y%m%d").date()
        for rr in recipe_lookup[pr["product_id"]]:
            mat = rr["material_id"]
            bid = b_by_line_mat.get((pr["line_id"], mat))
            if bid:
                loss = HIDDEN_LOSS_BY_PRODUCT_MATERIAL[(pr["product_id"], mat)]
                factor = Decimal(rr["std_kg_per_kg"]) * (Decimal("1") + loss)
                req_by_bunker_day[(bid, pd)] += q_half_up(Decimal(pr["planned_output_kg"]) * factor)
    emergency_req_by_bunker_day = {(b["bunker_id"], d): 0 for b in bunkers for d in daterange(PLAN_START, PLAN_END)}
    displaced = []
    for pr in plan:
        er = dict(pr)
        pd = datetime.strptime(pr["plan_date"], "%Y%m%d").date()
        if er["line_id"] == "L3" and date(2026, 10, 3) <= pd <= date(2026, 10, 7):
            displaced.append(dict(pr))
            er["product_id"] = "P-L3-05"
            er["planned_output_kg"] = "50000"
        for rr in recipe_lookup[er["product_id"]]:
            mat = rr["material_id"]
            bid = b_by_line_mat.get((er["line_id"], mat))
            if bid:
                loss = HIDDEN_LOSS_BY_PRODUCT_MATERIAL[(er["product_id"], mat)]
                factor = Decimal(rr["std_kg_per_kg"]) * (Decimal("1") + loss)
                emergency_req_by_bunker_day[(bid, pd)] += q_half_up(Decimal(er["planned_output_kg"]) * factor)
    for moved, spare_d in zip(displaced, sorted(spare_dates)):
        for rr in recipe_lookup[moved["product_id"]]:
            mat = rr["material_id"]
            bid = b_by_line_mat.get((moved["line_id"], mat))
            if bid:
                loss = HIDDEN_LOSS_BY_PRODUCT_MATERIAL[(moved["product_id"], mat)]
                factor = Decimal(rr["std_kg_per_kg"]) * (Decimal("1") + loss)
                emergency_req_by_bunker_day[(bid, spare_d)] += q_half_up(Decimal(moved["planned_output_kg"]) * factor)
    for key, val in emergency_req_by_bunker_day.items():
        if False and key[0] != "BNK-L3-2":
            req_by_bunker_day[key] = val
    valid_pos = []
    po_no = 1
    for b in bunkers:
        bid, mat = b["bunker_id"], b["material_id"]
        cap = int(b["capacity_kg"])
        safety = int(b["safety_stock_kg"])
        supplier = SUP_BY_MAT[mat]
        order_unit = next(e for a, _name, _lead, _pull, e in SUPPLIERS if a == supplier)
        current = OPENING[bid]
        avg_req = q_half_up(Decimal(sum(req_by_bunker_day[(bid, x)] for x in daterange(PLAN_START, PLAN_END))) / Decimal(92))
        lower = safety + avg_req * 3
        for d in daterange(PLAN_START, PLAN_END):
            req = req_by_bunker_day[(bid, d)]
            if current - req < lower:
                target = min(cap, lower + max(avg_req * 3, order_unit))
                needed = max(0, target - current)
                qty = ((needed + order_unit - 1) // order_unit) * order_unit
                qty = min(qty, max(0, cap - current - 1000))
                if qty > 0:
                    promised = d - timedelta(days=delay_days[supplier])
                    valid_pos.append({"purchase_order_id": f"POQ4-{po_no:04d}", "po_line_no": "10", "supplier_id": supplier, "material_id": mat, "bunker_id": bid, "promised_date": ymd(promised), "quantity": str(qty), "unit": "KG"})
                    po_no += 1
                    current += qty
            current -= req
    for _po in valid_pos:
        if _po["bunker_id"] == "BNK-L4-1" and _po["promised_date"] == "20261130":
            _po["quantity"] = str(max(1, int(_po["quantity"]) - 1000))
            break
    for _po in valid_pos:
        if _po["bunker_id"] == "BNK-L3-1" and _po["promised_date"] <= "20261007":
            _po["quantity"] = str(max(1, int(_po["quantity"]) - 15000))
    valid_pos.append({"purchase_order_id": f"POQ4-{po_no:04d}", "po_line_no": "10", "supplier_id": SUP_BY_MAT["MB-UV"], "material_id": "MB-UV", "bunker_id": "BNK-L3-4", "promised_date": ymd(date(2026, 10, 20)), "quantity": "5000", "unit": "KG"})
    po_no += 1
    # Keep source scale by adding small late-December top-off lines that do not affect criteria.
    extra_idx = 0
    while len(valid_pos) < 596:
        b = bunkers[extra_idx % len(bunkers)]
        mat = b["material_id"]
        valid_pos.append({"purchase_order_id": f"POQ4-{po_no:04d}", "po_line_no": "10", "supplier_id": SUP_BY_MAT[mat], "material_id": mat, "bunker_id": b["bunker_id"], "promised_date": ymd(date(2026, 12, 31)), "quantity": "1", "unit": "KG"})
        po_no += 1
        extra_idx += 1
    for idx in [31, 77, 123, 199, 251, 333, 441, 509]:
        valid_pos[idx]["unit"] = "TO"
        valid_pos[idx]["quantity"] = str(max(1, int(valid_pos[idx]["quantity"]) // 1000))
    open_po = list(valid_pos)
    for idx in [5, 25, 125, 225, 425]:
        open_po.append(dict(valid_pos[idx]))
    for j in range(4):
        b = bunkers[(j * 5) % len(bunkers)]
        open_po.append({"purchase_order_id": f"POQ4-BADN-{j+1}", "po_line_no": "10", "supplier_id": SUP_BY_MAT[b["material_id"]], "material_id": b["material_id"], "bunker_id": b["bunker_id"], "promised_date": ymd(date(2026, 10, 15 + j)), "quantity": "", "unit": "KG"})
    for j in range(3):
        b = bunkers[(j * 7) % len(bunkers)]
        open_po.append({"purchase_order_id": f"POQ4-BADU-{j+1}", "po_line_no": "10", "supplier_id": "SUP-PET-A", "material_id": f"UNK-{j+1}", "bunker_id": b["bunker_id"], "promised_date": ymd(date(2026, 11, 5 + j)), "quantity": "12000", "unit": "KG"})
    write_csv(out / "sap_purchase_order_open_2026Q4.csv", open_po, list(open_po[0].keys()))

    # PVSS sensor levels for September; 7 missing hours, 6 spikes, 5 duplicate timestamp rows.
    missing = {("BNK-L1-1", "2026-09-03T02:00:00+09:00"), ("BNK-L2-2", "2026-09-05T11:00:00+09:00"), ("BNK-L3-2", "2026-09-07T18:00:00+09:00"),
               ("BNK-L4-4", "2026-09-10T09:00:00+09:00"), ("BNK-L5-1", "2026-09-13T22:00:00+09:00"), ("BNK-L6-2", "2026-09-18T04:00:00+09:00"), ("BNK-L3-4", "2026-09-28T16:00:00+09:00")}
    spikes = {("BNK-L1-2", "2026-09-04T05:00:00+09:00"): -100, ("BNK-L2-1", "2026-09-08T14:00:00+09:00"): CAPACITY["PET-BR"] + 5000,
              ("BNK-L3-2", "2026-09-12T03:00:00+09:00"): -50, ("BNK-L4-2", "2026-09-15T19:00:00+09:00"): CAPACITY["PET-CO"] + 1200,
              ("BNK-L5-3", "2026-09-21T08:00:00+09:00"): -20, ("BNK-L6-4", "2026-09-24T17:00:00+09:00"): CAPACITY["MB-NS"] + 1000}
    dup_keys = [("BNK-L1-3", "2026-09-06T06:00:00+09:00"), ("BNK-L2-4", "2026-09-09T12:00:00+09:00"), ("BNK-L3-1", "2026-09-16T20:00:00+09:00"), ("BNK-L4-3", "2026-09-20T01:00:00+09:00"), ("BNK-L6-1", "2026-09-26T13:00:00+09:00")]
    sensor_rows = []
    total_hours = 30 * 24
    b_by_id = {b["bunker_id"]: b for b in bunkers}
    for b in bunkers:
        bid, mat = b["bunker_id"], b["material_id"]
        cap = CAPACITY[mat]
        for h in range(total_hours):
            ts = SENSOR_START + timedelta(hours=h)
            ts_s = ts.isoformat(timespec="seconds")
            key = (bid, ts_s)
            if key in missing:
                continue
            if key in spikes:
                level = spikes[key]
            elif h == total_hours - 1:
                level = OPENING[bid]
            else:
                wave = ((h * 17 + len(bid) * 13) % 61) - 30
                level = max(100, min(cap - 100, OPENING[bid] + wave * 45 + (total_hours - h) // 12))
            sensor_rows.append({"bunker_id": bid, "timestamp": ts_s, "level_kg": level})
    for bid, ts_s in dup_keys:
        base = next(r for r in sensor_rows if r["bunker_id"] == bid and r["timestamp"] == ts_s)
        sensor_rows.append({"bunker_id": bid, "timestamp": ts_s, "level_kg": base["level_kg"]})
    sensor_rows.sort(key=lambda r: (r["bunker_id"], r["timestamp"], str(r["level_kg"])))
    with (out / "pvss_bunker_level_2026-09.json").open("w", encoding="utf-8", newline="") as f:
        for r in sensor_rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    return out


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    p = generate_all(target)
    print(f"generated {p}")


















