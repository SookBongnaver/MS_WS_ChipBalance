# Databricks notebook source
# MAGIC %md
# MAGIC # 원천 시스템 데이터 생성
# MAGIC `02_source_data`가 `%run ./source_systems`로 이 Notebook을 불러옵니다. 직접 실행하거나 고치지 않습니다.
# MAGIC
# MAGIC 공장 한 곳의 운영을 시간 순서대로 계산해 SAP·FPIMS·PVSS 추출 파일을 만듭니다.
# MAGIC 모든 파일이 같은 운영 흐름에서 나오므로 생산량, 원료 사용량, 입고량, Bunker 레벨이 서로 맞습니다.
# MAGIC
# MAGIC | 순서 | 계산 | 결과 파일 |
# MAGIC |---|---|---|
# MAGIC | 1 | 라인마다 같은 제품을 3–7일씩 연속 생산하고, 주간(08–20시)·야간(20–08시) Lot을 기록합니다. | FPIMS 생산 Lot |
# MAGIC | 2 | Lot마다 레시피 기준량에 실제 손실(1–4%)을 더해 원료를 씁니다. | FPIMS 원료 사용 |
# MAGIC | 3 | Bunker 레벨이 기준 아래로 내려가면 공급사가 정해진 요일에 납품합니다. | SAP 입고, PVSS Bunker 레벨 |
# MAGIC | 4 | 4분기 생산계획과 판매오더를 만들고, 계획에 맞춰 발주를 잡습니다. | FPIMS 생산계획, SAP 판매오더·발주 |
# MAGIC | 5 | 실제 추출 파일에서 자주 보이는 오류(톤 단위, 중복, 수량 공란, 미등록 코드, 센서 누락·튐)를 넣습니다. | SAP 발주, PVSS Bunker 레벨 |

# COMMAND ----------
import csv
import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 20261001
ACTUAL_START = date(2025, 10, 1)
ACTUAL_END = date(2026, 9, 30)
PLAN_START = date(2026, 10, 1)
PLAN_END = date(2026, 12, 31)
HISTORY_START = datetime(2025, 10, 1, 0)
SENSOR_START = datetime(2026, 9, 1, 0)
LAST_READING = datetime(2026, 9, 30, 23)
DELIVERY_HOUR = 10
TZ = "+09:00"

MATERIALS = [
    ("PET-BR", "Bright PET chip", "BOPET 주원료 (Bright)", 1180),
    ("PET-SD", "Semi-dull PET chip", "BOPET 반광택 원료 (Semi-dull)", 1250),
    ("PET-RC", "Recycled PET chip", "재생 PET 원료", 980),
    ("PET-CO", "Copolyester chip", "실링용 공중합 PET", 1420),
    ("MB-AB", "Anti-block masterbatch", "Anti-block 마스터배치", 2850),
    ("MB-SL", "Slip masterbatch", "Slip 마스터배치", 3120),
    ("MB-WH", "White masterbatch", "백색 마스터배치", 3350),
    ("MB-UV", "UV masterbatch", "UV 차단 마스터배치", 3680),
    ("NY6-F", "Nylon 6 film chip", "BOPA 주원료 (Nylon 6)", 2180),
    ("NY6-H", "High-viscosity nylon 6", "고점도 Nylon 6", 2380),
    ("MB-NA", "Nylon anti-block MB", "BOPA Anti-block 마스터배치", 3260),
    ("MB-NS", "Nylon slip MB", "BOPA Slip 마스터배치", 3480),
]
# supplier, name, standard lead time days, max pull-in days, order unit kg, pull-in fee KRW/kg, spot premium %
SUPPLIERS = [
    ("SUP-PET-A", "한빛케미칼", 7, 2, 25000, 20, 5),
    ("SUP-PET-B", "세미폴리머", 4, 2, 25000, 20, 6),
    ("SUP-MB-A", "첨단마스터", 6, 1, 5000, 40, 8),
    ("SUP-NY-A", "나일론소재", 9, 2, 25000, 25, 6),
    ("SUP-NY-B", "고점도케미칼", 10, 2, 25000, 25, 7),
    ("SUP-ADD-A", "기능성첨가", 5, 1, 1000, 50, 10),
]
SUP_BY_MAT = {
    "PET-BR": "SUP-PET-A", "PET-SD": "SUP-PET-B", "PET-RC": "SUP-PET-A", "PET-CO": "SUP-PET-B",
    "MB-AB": "SUP-MB-A", "MB-SL": "SUP-MB-A", "MB-WH": "SUP-ADD-A", "MB-UV": "SUP-ADD-A",
    "NY6-F": "SUP-NY-A", "NY6-H": "SUP-NY-B", "MB-NA": "SUP-ADD-A", "MB-NS": "SUP-ADD-A",
}
# received date minus promised date, repeated per supplier in receipt order
DELAY_PATTERNS = {
    "SUP-PET-A": [-1, 0, 0, 0, 0, 1, 1, 0, 2, 0],
    "SUP-PET-B": [-1, 0, 0, 0, 1, 0, 0, 2],
    "SUP-MB-A": [-1, 0, 1, 1, 1, 2, 2, 3, 0, 4],
    "SUP-NY-A": [0, 0, 1, 1, 1, 2, 2, 3, -1, 3],
    "SUP-NY-B": [0, 1, 2, 2, 2, 3, 3, 4, 5, 0],
    "SUP-ADD-A": [1, 2, 2, 3, 3, 3, 4, 4, 5, 0],
}
LINES = [("L1", "BOPET", 52000), ("L2", "BOPET", 50000), ("L3", "BOPET", 50000),
         ("L4", "BOPET", 47000), ("L5", "BOPA", 28000), ("L6", "BOPA", 26000)]
BUNKER_MATERIALS = {
    "L1": ["PET-BR", "PET-SD", "MB-AB", "MB-SL"],
    "L2": ["PET-BR", "PET-RC", "MB-AB", "MB-WH"],
    "L3": ["PET-BR", "PET-SD", "MB-SL", "MB-UV"],
    "L4": ["PET-BR", "PET-CO", "MB-WH", "MB-UV"],
    "L5": ["NY6-F", "NY6-H", "MB-NA", "MB-NS"],
    "L6": ["NY6-F", "NY6-H", "MB-NA", "MB-NS"],
}
PRODUCT_NAMES = {
    "L1": ["12μm 포장용", "16μm 인쇄용", "19μm 증착용", "23μm 라벨용", "36μm 공업용"],
    "L2": ["재생 12μm 포장용", "재생 16μm 인쇄용", "백색 25μm 라벨용", "백색 38μm 카드용", "재생 50μm 공업용"],
    "L3": ["반광택 16μm 포장용", "반광택 23μm 인쇄용", "반광택 36μm 라미용", "UV차단 50μm 창호용", "반광택 75μm 후막"],
    "L4": ["실링 12μm 포장용", "실링 20μm 레토르트용", "백색 실링 25μm", "UV차단 실링 30μm", "실링 38μm 공업용"],
    "L5": ["15μm 식품포장용", "15μm 레토르트용", "20μm 진공포장용", "25μm 고강도", "30μm 공업용"],
    "L6": ["15μm 식품포장용", "15μm 레토르트용", "20μm 진공포장용", "25μm 고강도", "30μm 공업용"],
}
# standard kg of chip per kg of film; zero entries are not registered as recipe lines
RECIPES = {
    "L1": [[("PET-BR", "0.965"), ("PET-SD", "0.040"), ("MB-AB", "0.015"), ("MB-SL", "0.010")],
           [("PET-BR", "0.965"), ("PET-SD", "0.030"), ("MB-AB", "0.020"), ("MB-SL", "0.010")],
           [("PET-BR", "0.955"), ("PET-SD", "0.050"), ("MB-AB", "0.015"), ("MB-SL", "0.010")],
           [("PET-BR", "0.965"), ("PET-SD", "0.030"), ("MB-AB", "0.020"), ("MB-SL", "0.015")],
           [("PET-BR", "0.955"), ("PET-SD", "0.050"), ("MB-AB", "0.015"), ("MB-SL", "0.010")]],
    "L2": [[("PET-BR", "0.840"), ("PET-RC", "0.165"), ("MB-AB", "0.015"), ("MB-WH", "0.010")],
           [("PET-BR", "0.800"), ("PET-RC", "0.205"), ("MB-AB", "0.015"), ("MB-WH", "0.010")],
           [("PET-BR", "0.780"), ("PET-RC", "0.225"), ("MB-AB", "0.015"), ("MB-WH", "0.010")],
           [("PET-BR", "0.865"), ("PET-RC", "0.135"), ("MB-AB", "0.020"), ("MB-WH", "0.010")],
           [("PET-BR", "0.820"), ("PET-RC", "0.180"), ("MB-AB", "0.015"), ("MB-WH", "0.015")]],
    "L3": [[("PET-BR", "0.875"), ("PET-SD", "0.120"), ("MB-SL", "0.020"), ("MB-UV", "0.010")],
           [("PET-BR", "0.895"), ("PET-SD", "0.100"), ("MB-SL", "0.020"), ("MB-UV", "0.010")],
           [("PET-BR", "0.845"), ("PET-SD", "0.150"), ("MB-SL", "0.020"), ("MB-UV", "0.010")],
           [("PET-BR", "0.900"), ("PET-SD", "0.095"), ("MB-SL", "0.020"), ("MB-UV", "0.015")],
           [("PET-BR", "0.575"), ("PET-SD", "0.450"), ("MB-SL", "0.000"), ("MB-UV", "0.000")]],
    "L4": [[("PET-BR", "0.830"), ("PET-CO", "0.175"), ("MB-WH", "0.015"), ("MB-UV", "0.010")],
           [("PET-BR", "0.800"), ("PET-CO", "0.200"), ("MB-WH", "0.020"), ("MB-UV", "0.010")],
           [("PET-BR", "0.855"), ("PET-CO", "0.145"), ("MB-WH", "0.020"), ("MB-UV", "0.010")],
           [("PET-BR", "0.820"), ("PET-CO", "0.180"), ("MB-WH", "0.015"), ("MB-UV", "0.015")],
           [("PET-BR", "0.780"), ("PET-CO", "0.220"), ("MB-WH", "0.020"), ("MB-UV", "0.010")]],
    "L5": [[("NY6-F", "0.820"), ("NY6-H", "0.185"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
           [("NY6-F", "0.785"), ("NY6-H", "0.220"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
           [("NY6-F", "0.850"), ("NY6-H", "0.150"), ("MB-NA", "0.020"), ("MB-NS", "0.010")],
           [("NY6-F", "0.810"), ("NY6-H", "0.190"), ("MB-NA", "0.015"), ("MB-NS", "0.015")],
           [("NY6-F", "0.790"), ("NY6-H", "0.210"), ("MB-NA", "0.020"), ("MB-NS", "0.010")]],
    "L6": [[("NY6-F", "0.830"), ("NY6-H", "0.175"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
           [("NY6-F", "0.800"), ("NY6-H", "0.205"), ("MB-NA", "0.015"), ("MB-NS", "0.010")],
           [("NY6-F", "0.855"), ("NY6-H", "0.145"), ("MB-NA", "0.020"), ("MB-NS", "0.010")],
           [("NY6-F", "0.815"), ("NY6-H", "0.185"), ("MB-NA", "0.015"), ("MB-NS", "0.015")],
           [("NY6-F", "0.790"), ("NY6-H", "0.210"), ("MB-NA", "0.020"), ("MB-NS", "0.010")]],
}
# material: capacity kg, safety stock kg, delivery weekdays (Mon=0), level kept before a delivery,
#           max order units per delivery, planning floor used for the Q4 delivery schedule
BUNKER_POLICY = {
    "PET-BR": (250000, 45000, (0, 1, 2, 3, 4, 5), 95000, 4, 95000),
    "PET-RC": (150000, 20000, (0, 3), 35000, 3, 35000),
    "PET-CO": (150000, 20000, (1, 4), 35000, 3, 35000),
    "NY6-F": (170000, 35000, (0, 1, 2, 3, 4, 5), 55000, 3, 55000),
    "NY6-H": (150000, 12000, (1, 4), 22000, 2, 22000),
    "MB-AB": (20000, 2500, (2,), 4500, 2, 3500),
    "MB-SL": (18000, 2200, (2,), 4200, 2, 3200),
    "MB-WH": (18000, 2200, (2,), 4200, 8, 3200),
    "MB-UV": (16000, 1500, (2,), 3500, 8, 2500),
    "MB-NA": (16000, 1800, (2,), 3800, 8, 2800),
    "MB-NS": (16000, 1800, (2,), 3800, 8, 2800),
}
BUNKER_POLICY_OVERRIDE = {
    # L3 PET-BR keeps a larger buffer for the PET-BR-heavy thick film
    "BNK-L3-1": (250000, 45000, (0, 1, 2, 3, 4, 5), 95000, 4, 115000),
    # L1 PET-SD is the shared PET-SD buffer for L1 and L3 (route R-01), delivered on Mondays
    "BNK-L1-2": (150000, 6000, (0,), 60000, 2, 55000),
    # L3 PET-SD is called off once a week and delivered on Fridays
    "BNK-L3-2": (150000, 12000, (4,), 22000, 5, 20000),
}
OPENING = {  # level read by PVSS at 2026-09-30 23:00
    "BNK-L1-1": 152340, "BNK-L1-2": 71860, "BNK-L1-3": 10470, "BNK-L1-4": 7530,
    "BNK-L2-1": 140720, "BNK-L2-2": 61290, "BNK-L2-3": 9460, "BNK-L2-4": 7180,
    "BNK-L3-1": 146410, "BNK-L3-2": 30370, "BNK-L3-3": 10830, "BNK-L3-4": 6470,
    "BNK-L4-1": 135860, "BNK-L4-2": 56240, "BNK-L4-3": 10190, "BNK-L4-4": 6320,
    "BNK-L5-1": 91270, "BNK-L5-2": 35830, "BNK-L5-3": 6280, "BNK-L5-4": 5410,
    "BNK-L6-1": 86140, "BNK-L6-2": 34260, "BNK-L6-3": 6130, "BNK-L6-4": 5290,
}
ROUTES = [  # from bunker, to bunker, max kg per day, lead time days, cost KRW per kg
    ("BNK-L1-2", "BNK-L3-2", 40000, 1, 25), ("BNK-L3-2", "BNK-L1-2", 35000, 1, 25),
    ("BNK-L1-1", "BNK-L2-1", 50000, 1, 18), ("BNK-L2-1", "BNK-L3-1", 50000, 1, 18),
    ("BNK-L3-1", "BNK-L4-1", 45000, 1, 18), ("BNK-L2-3", "BNK-L1-3", 8000, 1, 40),
    ("BNK-L1-4", "BNK-L3-3", 7000, 1, 40), ("BNK-L3-4", "BNK-L4-4", 6000, 1, 45),
    ("BNK-L5-1", "BNK-L6-1", 35000, 1, 22), ("BNK-L6-1", "BNK-L5-1", 35000, 1, 22),
    ("BNK-L5-2", "BNK-L6-2", 25000, 1, 24), ("BNK-L6-4", "BNK-L5-4", 5000, 1, 42),
]
CUSTOMERS = [
    ("C-1001", "한결패키징", "BOPET"), ("C-1002", "대원라벨", "BOPET"), ("C-1003", "선진포장", "BOPET"),
    ("C-1004", "누리전자소재", "BOPET"), ("C-1005", "새빛인쇄", "BOPET"), ("C-1006", "청우산업", "BOPET"),
    ("C-1007", "금강포장재", "BOPET"), ("C-1008", "미르코팅", "BOPET"), ("C-1009", "하늘테이프", "BOPET"),
    ("C-1010", "동해식품포장", "BOPA"), ("C-1011", "온누리팩", "BOPA"), ("C-1012", "태양라미", "BOPA"),
]
# L3 plan around the urgent order: two campaigns, five open days, and a thick-film campaign in November
L3_FIXED = {**{date(2026, 10, d): 3 for d in range(1, 5)}, **{date(2026, 10, d): 1 for d in range(5, 11)},
            date(2026, 11, 18): 5, date(2026, 11, 19): 5}
L3_SPARE = [date(2026, 10, d) for d in range(11, 16)]
# PVSS data issues (bunker, hour) and extract issues in the open purchase-order lines
SENSOR_MISSING = [("BNK-L1-1", datetime(2026, 9, 3, 2)), ("BNK-L2-2", datetime(2026, 9, 5, 11)),
                  ("BNK-L3-2", datetime(2026, 9, 7, 18)), ("BNK-L4-4", datetime(2026, 9, 10, 9)),
                  ("BNK-L5-1", datetime(2026, 9, 13, 22)), ("BNK-L6-2", datetime(2026, 9, 18, 4)),
                  ("BNK-L3-4", datetime(2026, 9, 28, 16))]
SENSOR_SPIKES = [("BNK-L1-2", datetime(2026, 9, 4, 5), -100), ("BNK-L2-1", datetime(2026, 9, 8, 14), 255000),
                 ("BNK-L3-2", datetime(2026, 9, 12, 3), -50), ("BNK-L4-2", datetime(2026, 9, 15, 19), 151200),
                 ("BNK-L5-3", datetime(2026, 9, 21, 8), -20), ("BNK-L6-4", datetime(2026, 9, 24, 17), 17000)]
SENSOR_DUPLICATES = [("BNK-L1-3", datetime(2026, 9, 6, 6)), ("BNK-L2-4", datetime(2026, 9, 9, 12)),
                     ("BNK-L3-1", datetime(2026, 9, 16, 20)), ("BNK-L4-3", datetime(2026, 9, 20, 1)),
                     ("BNK-L6-1", datetime(2026, 9, 26, 13))]
UNREGISTERED_MATERIALS = [("PET-HV", "BNK-L1-1", "SUP-PET-A", 25000), ("MB-AS", "BNK-L2-3", "SUP-MB-A", 5000),
                          ("NY6-R", "BNK-L5-1", "SUP-NY-A", 25000)]

# COMMAND ----------
def q_half_up(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def ymd(d):
    return d.strftime("%Y%m%d")


def iso(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%S") + TZ


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def hidden_loss(product_index, component_index):
    """Process loss above the standard recipe, 1-4% per product and material."""
    return Decimal("0.010") + Decimal((product_index + component_index) % 4) / Decimal(100)


def policy(bunker_id, material_id):
    if bunker_id in BUNKER_POLICY_OVERRIDE:
        return BUNKER_POLICY_OVERRIDE[bunker_id]
    return BUNKER_POLICY[material_id]


def master_data():
    materials = [{"material_id": m, "material_name": n, "description": d, "unit_price_krw_per_kg": str(p), "base_uom": "KG"}
                 for m, n, d, p in MATERIALS]
    suppliers = [{"supplier_id": s, "supplier_name": n, "standard_lead_time_days": str(lt), "max_pull_in_days": str(pi),
                  "order_unit_kg": str(u), "pull_in_fee_krw_per_kg": str(fee), "spot_premium_pct": str(prem)}
                 for s, n, lt, pi, u, fee, prem in SUPPLIERS]
    lines = [{"line_id": l, "plant_id": "P001", "line_family": fam, "default_daily_output_kg": str(kg)} for l, fam, kg in LINES]
    bunkers, products, recipes = [], [], []
    for line_id, fam, kg in LINES:
        for slot, mat in enumerate(BUNKER_MATERIALS[line_id], 1):
            cap, safety = policy(f"BNK-{line_id}-{slot}", mat)[:2]
            bunkers.append({"bunker_id": f"BNK-{line_id}-{slot}", "line_id": line_id, "material_id": mat,
                            "capacity_kg": str(cap), "safety_stock_kg": str(safety)})
        for idx, name in enumerate(PRODUCT_NAMES[line_id], 1):
            pid = f"P-{line_id}-{idx:02d}"
            products.append({"product_id": pid, "line_id": line_id, "product_name": f"{fam} {name}", "film_family": fam,
                             "default_daily_output_kg": str(kg)})
            for mat, std in RECIPES[line_id][idx - 1]:
                if Decimal(std) > 0:
                    recipes.append({"product_id": pid, "line_id": line_id, "material_id": mat, "std_kg_per_kg": std})
    routes = [{"route_id": f"R-{i:02d}", "from_bunker_id": a, "to_bunker_id": b, "material_id": next(x["material_id"] for x in bunkers if x["bunker_id"] == a),
               "max_kg_per_day": str(mx), "lead_time_days": str(lt), "cost_krw_per_kg": str(c)} for i, (a, b, mx, lt, c) in enumerate(ROUTES, 1)]
    return materials, suppliers, lines, bunkers, products, recipes, routes

# COMMAND ----------
def pick_product(rng, last, line_id):
    weights = [0.24, 0.24, 0.22, 0.22, 0.08]
    while True:
        idx = rng.choices(range(1, 6), weights=weights)[0]
        if idx != last:
            return idx


def campaign_length(rng, line_id, idx):
    if idx == 5:
        return 2 if line_id == "L3" else rng.randint(2, 3)
    return rng.randint(3, 7)


def history_schedule(rng, line_id):
    """Product per day for the past year; None marks a one-day maintenance stop."""
    days = list(daterange(ACTUAL_START, ACTUAL_END))
    schedule, i, last = {}, 0, None
    next_stop = rng.randint(35, 60)
    while i < len(days):
        if i >= next_stop:
            schedule[days[i]] = None
            next_stop = i + rng.randint(40, 70)
            i += 1
            continue
        idx = pick_product(rng, last, line_id)
        for _ in range(campaign_length(rng, line_id, idx)):
            if i >= len(days) or i >= next_stop:
                break
            schedule[days[i]] = idx
            i += 1
        last = idx
    return schedule


def plan_schedule(rng, line_id):
    """Product per day for Q4. L3 keeps the fixed campaigns and the open days before 16 October."""
    days = list(daterange(PLAN_START, PLAN_END))
    schedule, i, last = {}, 0, None
    while i < len(days):
        d = days[i]
        if line_id == "L3" and d in L3_SPARE:
            i += 1
            continue
        if line_id == "L3" and d in L3_FIXED:
            schedule[d] = last = L3_FIXED[d]
            i += 1
            continue
        idx = pick_product(rng, last, line_id)
        for _ in range(campaign_length(rng, line_id, idx)):
            if i >= len(days) or (line_id == "L3" and (days[i] in L3_FIXED or days[i] in L3_SPARE)):
                break
            schedule[days[i]] = idx
            i += 1
        last = idx
    return schedule


def production_actuals(rng, bunkers, recipes):
    recipe_by_product = defaultdict(list)
    for r in recipes:
        recipe_by_product[r["product_id"]].append(r)
    bunker_of = {(b["line_id"], b["material_id"]): b["bunker_id"] for b in bunkers}
    lots, consumption = [], []
    for line_id, fam, default_kg in LINES:
        schedule = history_schedule(rng, line_id)
        previous = None
        for d in daterange(ACTUAL_START, ACTUAL_END):
            idx = schedule[d]
            if idx is None:
                previous = None
                continue
            pid = f"P-{line_id}-{idx:02d}"
            target = default_kg * rng.uniform(0.965, 1.01)
            for shift, start_hour in (("D", 8), ("N", 20)):
                output = target / 2 * rng.uniform(0.98, 1.02)
                if shift == "D" and idx != previous:
                    output *= 0.9  # changeover to a new product
                output = int(round(output))
                start = datetime(d.year, d.month, d.day, start_hour)
                lot_id = f"{line_id}-{d.strftime('%y%m%d')}-{shift}"
                lots.append({"lot_id": lot_id, "line_id": line_id, "product_id": pid, "start_ts": iso(start),
                             "end_ts": iso(start + timedelta(hours=12)), "output_kg": str(output)})
                for j, rr in enumerate(recipe_by_product[pid]):
                    comp_index = [m for m, _ in RECIPES[line_id][idx - 1]].index(rr["material_id"])
                    factor = Decimal(rr["std_kg_per_kg"]) * (1 + hidden_loss(idx, comp_index)) * Decimal(str(round(rng.uniform(0.995, 1.005), 4)))
                    consumption.append({"consumption_id": f"MC{len(consumption) + 1:07d}", "lot_id": lot_id, "line_id": line_id,
                                        "bunker_id": bunker_of[(line_id, rr["material_id"])], "material_id": rr["material_id"],
                                        "consumed_kg": str(q_half_up(Decimal(output) * factor))})
            previous = idx
    return lots, consumption

# COMMAND ----------
def hour_index(ts):
    return int((ts - HISTORY_START).total_seconds() // 3600)


def bunker_history(bunkers, lots, consumption):
    """Hourly bunker levels for the past year, built backwards from the 30 September 23:00 reading."""
    hours = hour_index(LAST_READING) + 1
    lot_start = {l["lot_id"]: datetime.fromisoformat(l["start_ts"][:19]) for l in lots}
    usage = {b["bunker_id"]: [0.0] * hours for b in bunkers}
    for c in consumption:
        start = hour_index(lot_start[c["lot_id"]])
        per_hour = int(c["consumed_kg"]) / 12
        for h in range(start, min(start + 12, hours)):
            usage[c["bunker_id"]][h] += per_hour
    unit_of = {s[0]: s[4] for s in SUPPLIERS}
    levels, deliveries = {}, []
    for b in bunkers:
        bid, mat = b["bunker_id"], b["material_id"]
        cap, safety, weekdays, keep, max_units, _floor = policy(bid, mat)
        unit = unit_of[SUP_BY_MAT[mat]]
        level = [0.0] * hours
        level[hours - 1] = OPENING[bid]
        for h in range(hours - 2, -1, -1):
            after_receipt = level[h + 1] + usage[bid][h]
            ts = HISTORY_START + timedelta(hours=h)
            received = 0
            if ts.hour == DELIVERY_HOUR and ts.weekday() in weekdays:
                units = min(max_units, int((after_receipt - keep) // unit))
                if units >= 1:
                    received = units * unit
                    deliveries.append((ts, bid, mat, received))
            if after_receipt > cap:
                raise ValueError(f"{bid} exceeds capacity at {ts}: {after_receipt:.0f}")
            level[h] = after_receipt - received
        levels[bid] = level
    deliveries.sort(key=lambda x: (x[0], x[1]))
    return levels, deliveries


def goods_receipts(deliveries):
    delay_index = defaultdict(int)
    po_numbers, receipts = {}, []
    for ts, bid, mat, qty in deliveries:
        sup = SUP_BY_MAT[mat]
        pattern = DELAY_PATTERNS[sup]
        delay = pattern[delay_index[sup] % len(pattern)]
        delay_index[sup] += 1
        key = (bid, ts.strftime("%Y%m"))
        po_numbers.setdefault(key, f"45000{10001 + len(po_numbers)}")
        receipts.append({"receipt_id": f"50000{10001 + len(receipts)}", "purchase_order_id": po_numbers[key], "supplier_id": sup,
                         "material_id": mat, "bunker_id": bid, "promised_date": ymd(ts.date() - timedelta(days=delay)),
                         "received_date": ymd(ts.date()), "quantity": str(qty), "unit": "KG"})
    return receipts, len(po_numbers)


def sensor_readings(rng, bunkers, levels):
    missing = set(SENSOR_MISSING)
    spikes = {(b, ts): v for b, ts, v in SENSOR_SPIKES}
    first = hour_index(SENSOR_START)
    last = hour_index(LAST_READING)
    rows = []
    for b in bunkers:
        bid = b["bunker_id"]
        noise = int(b["capacity_kg"]) * 0.002
        for h in range(first, last + 1):
            ts = HISTORY_START + timedelta(hours=h)
            if (bid, ts) in missing:
                continue
            value = spikes.get((bid, ts))
            if value is None:
                value = OPENING[bid] if h == last else int(round(levels[bid][h] + rng.uniform(-noise, noise)))
            rows.append({"bunker_id": bid, "timestamp": iso(ts), "level_kg": value})
    for bid, ts in SENSOR_DUPLICATES:
        rows.append(dict(next(r for r in rows if r["bunker_id"] == bid and r["timestamp"] == iso(ts))))
    rows.sort(key=lambda r: (r["bunker_id"], r["timestamp"]))
    return rows

# COMMAND ----------
def usage_factors(lots, consumption):
    output = defaultdict(int)
    product_of = {}
    for l in lots:
        output[l["product_id"]] += int(l["output_kg"])
        product_of[l["lot_id"]] = l["product_id"]
    used = defaultdict(int)
    for c in consumption:
        used[(product_of[c["lot_id"]], c["material_id"])] += int(c["consumed_kg"])
    return {k: (Decimal(v) / Decimal(output[k[0]])).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP) for k, v in used.items()}


def rounded_delays(receipts):
    total, count = defaultdict(int), defaultdict(int)
    for r in receipts:
        total[r["supplier_id"]] += (datetime.strptime(r["received_date"], "%Y%m%d") - datetime.strptime(r["promised_date"], "%Y%m%d")).days
        count[r["supplier_id"]] += 1
    return {s: q_half_up(Decimal(total[s]) / Decimal(count[s])) for s in count}


def production_plan_and_orders(rng):
    plan, orders = [], []
    customers = {fam: [c for c in CUSTOMERS if c[2] == fam] for fam in ("BOPET", "BOPA")}
    for line_id, fam, default_kg in LINES:
        schedule = plan_schedule(rng, line_id)
        days = sorted(schedule)
        rows = []
        for d in days:
            qty = int(round(default_kg * rng.uniform(0.98, 1.02) / 100)) * 100
            rows.append({"plan_id": f"PP-{ymd(d)}-{line_id}", "plan_date": ymd(d), "line_id": line_id,
                         "product_id": f"P-{line_id}-{schedule[d]:02d}", "planned_output_kg": str(qty), "sales_order_id": ""})
        i = 0
        while i < len(rows):
            j = i
            while j + 1 < len(rows) and rows[j + 1]["product_id"] == rows[i]["product_id"] and j + 1 - i < rng.randint(1, 3) \
                    and (datetime.strptime(rows[j + 1]["plan_date"], "%Y%m%d") - datetime.strptime(rows[j]["plan_date"], "%Y%m%d")).days == 1:
                j += 1
            chunk = rows[i:j + 1]
            first_day = datetime.strptime(chunk[0]["plan_date"], "%Y%m%d").date()
            last_day = datetime.strptime(chunk[-1]["plan_date"], "%Y%m%d").date()
            customer = rng.choice(customers[fam])
            so_id = f"SO-{10001 + len(orders)}"
            orders.append({"sales_order_id": so_id, "order_date": ymd(first_day - timedelta(days=rng.randint(14, 35))),
                           "customer_id": customer[0], "customer_name": customer[1], "product_id": chunk[0]["product_id"],
                           "order_qty_kg": str(int(sum(int(r["planned_output_kg"]) for r in chunk) * rng.uniform(0.96, 0.99) / 1000) * 1000),
                           "due_date": ymd(last_day + timedelta(days=rng.randint(4, 12))),
                           "priority": "high" if rng.random() < 0.12 else "normal"})
            for r in chunk:
                r["sales_order_id"] = so_id
            i = j + 1
        plan.extend(rows)
    plan.sort(key=lambda r: (r["plan_date"], r["line_id"]))
    orders.sort(key=lambda r: r["sales_order_id"])
    return plan, orders


def planned_requirements(plan, bunkers, factors):
    bunker_of = {(b["line_id"], b["material_id"]): b["bunker_id"] for b in bunkers}
    req = defaultdict(int)
    for r in plan:
        d = datetime.strptime(r["plan_date"], "%Y%m%d").date()
        for (pid, mat), factor in factors.items():
            if pid == r["product_id"] and (r["line_id"], mat) in bunker_of:
                req[(bunker_of[(r["line_id"], mat)], d)] += q_half_up(Decimal(r["planned_output_kg"]) * factor)
    return req


def delivery_schedule(bunkers, req):
    """Q4 deliveries per bunker: on delivery days, order full units so the level stays above the planning floor."""
    unit_of = {s[0]: s[4] for s in SUPPLIERS}
    days = list(daterange(PLAN_START, PLAN_END))
    arrivals = []
    for b in bunkers:
        bid, mat = b["bunker_id"], b["material_id"]
        cap, safety, weekdays, _keep, _max_units, floor = policy(bid, mat)
        unit = unit_of[SUP_BY_MAT[mat]]
        slots = [d for d in days if d.weekday() in weekdays]
        level = OPENING[bid]
        for d in days:
            if d in slots:
                later = [s for s in slots if s > d]
                until = later[0] if later else PLAN_END + timedelta(days=1)
                projected = level - sum(req[(bid, x)] for x in daterange(d, until - timedelta(days=1)))
                if projected < floor:
                    units = min(-(-(floor - projected) // unit), (cap - level) // unit)
                    if units > 0:
                        arrivals.append((d, bid, mat, units * unit))
                        level += units * unit
            level -= req[(bid, d)]
            if level < safety:
                raise ValueError(f"{bid} below safety stock on {d}: {level}")
    arrivals.sort(key=lambda x: (x[0], x[1]))
    return arrivals


def open_purchase_orders(arrivals, delays, first_po_number):
    po_numbers, lines = {}, []
    item_count = defaultdict(int)
    for d, bid, mat, qty in arrivals:
        sup = SUP_BY_MAT[mat]
        key = (bid, d.strftime("%Y%m"))
        po_numbers.setdefault(key, f"45000{first_po_number + len(po_numbers)}")
        item_count[po_numbers[key]] += 10
        lines.append({"purchase_order_id": po_numbers[key], "po_line_no": f"{item_count[po_numbers[key]]:05d}", "supplier_id": sup,
                      "material_id": mat, "bunker_id": bid, "promised_date": ymd(d - timedelta(days=delays[sup])), "quantity": str(qty), "unit": "KG"})
    return lines, po_numbers, item_count


def add_extract_issues(rng, lines, po_numbers, item_count):
    """Problems found in real ERP extracts: tons instead of kg, repeated lines, blank quantities, unregistered codes."""
    by_key = {(l["bunker_id"], l["promised_date"]): l for l in lines}
    to_lines = [by_key[("BNK-L3-2", "20261002")]]
    big = [l for l in lines if l["material_id"] in ("PET-BR", "NY6-F") and l not in to_lines]
    to_lines += [big[i] for i in sorted(rng.sample(range(len(big)), 7))]
    for l in to_lines:
        l["unit"] = "TO"
        l["quantity"] = str(int(l["quantity"]) // 1000)
    repeated = [by_key[("BNK-L3-2", "20261009")]]
    others = [l for l in lines if l not in repeated and l not in to_lines]
    repeated += [others[i] for i in sorted(rng.sample(range(len(others)), 4))]
    extra = [dict(l) for l in repeated]
    for po in sorted(rng.sample(sorted(set(l["purchase_order_id"] for l in lines)), 4)):
        base = next(l for l in lines if l["purchase_order_id"] == po)
        item_count[po] += 10
        extra.append({**base, "po_line_no": f"{item_count[po]:05d}", "quantity": ""})
    next_po = int(max(po_numbers.values())) + 1
    for k, (mat, bid, sup, qty) in enumerate(UNREGISTERED_MATERIALS):
        extra.append({"purchase_order_id": str(next_po + k), "po_line_no": "00010", "supplier_id": sup, "material_id": mat,
                      "bunker_id": bid, "promised_date": ymd(date(2026, 11, 4 + 7 * k)), "quantity": str(qty), "unit": "KG"})
    rows = lines + extra
    rows.sort(key=lambda l: (l["purchase_order_id"], l["po_line_no"]))
    return rows

# COMMAND ----------
def generate_all(output_dir):
    out = Path(output_dir)
    rng = random.Random(SEED)
    materials, suppliers, lines, bunkers, products, recipes, routes = master_data()
    lots, consumption = production_actuals(rng, bunkers, recipes)
    levels, deliveries = bunker_history(bunkers, lots, consumption)
    receipts, po_count = goods_receipts(deliveries)
    sensor = sensor_readings(rng, bunkers, levels)
    factors = usage_factors(lots, consumption)
    delays = rounded_delays(receipts)
    plan, orders = production_plan_and_orders(rng)
    arrivals = delivery_schedule(bunkers, planned_requirements(plan, bunkers, factors))
    open_lines, po_numbers, item_count = open_purchase_orders(arrivals, delays, 10001 + po_count)
    open_po = add_extract_issues(rng, open_lines, po_numbers, item_count)

    files = {
        "sap/sap_material.csv": materials,
        "sap/sap_supplier.csv": suppliers,
        "sap/sap_purchase_receipt_2025-10_2026-09.csv": receipts,
        "sap/sap_purchase_order_open_2026Q4.csv": open_po,
        "sap/sap_sales_order_open_2026Q4.csv": orders,
        "fpims/fpims_line.csv": lines,
        "fpims/fpims_bunker.csv": bunkers,
        "fpims/fpims_product.csv": products,
        "fpims/fpims_recipe.csv": recipes,
        "fpims/fpims_bunker_transfer_route.csv": routes,
        "fpims/fpims_production_lot_2025-10_2026-09.csv": lots,
        "fpims/fpims_material_consumption_2025-10_2026-09.csv": consumption,
        "fpims/fpims_production_plan_2026Q4.csv": plan,
    }
    counts = {}
    for name, rows in files.items():
        write_csv(out / name, rows)
        counts[name] = len(rows)
    sensor_path = out / "pvss" / "pvss_bunker_level_2026-09.json"
    sensor_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sensor_path, "w", encoding="utf-8", newline="\n") as f:
        for r in sensor:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    counts["pvss/pvss_bunker_level_2026-09.json"] = len(sensor)
    return counts
