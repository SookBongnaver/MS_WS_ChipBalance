# Databricks notebook source
# MAGIC %md
# MAGIC # 05. 긴급 오더 비교와 대응안
# MAGIC 9월 5일 FILM-A 생산량을 100kg에서 120kg으로 늘리는 긴급 오더가 들어왔습니다.
# MAGIC 기준 계획은 그대로 두고, 긴급 오더 시나리오를 따로 계산해 비교합니다.
# MAGIC
# MAGIC 이 Notebook은 의사결정의 **1. 현재 계산**과 **2. 판단 기준**을 담당합니다.
# MAGIC **3. Agent 제안**과 **4. 사람 승인**은 Fabric에서 진행합니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 긴급 오더 입력
# MAGIC 날짜·제품·증가율을 바꿔 다른 긴급 오더도 계산할 수 있습니다. 바꾸면 아래 예상 결과도 달라집니다.

# COMMAND ----------
emergency = scenario("emergency_v1", "긴급 오더: 9/5 FILM-A 20% 증산",
                     change_date="2026-09-05", product_id="FILM-A", increase_pct=20)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 두 시나리오 계산
# MAGIC 같은 Silver와 같은 함수로 기준 계획과 긴급 오더를 각각 계산합니다. 입고예정은 두 시나리오가 같습니다.
# MAGIC
# MAGIC **예상 결과:** 긴급 오더의 9/5 FILM-A 생산량 120kg, CHIP-A 소요량 120kg

# COMMAND ----------
silver = read_silver()
base = build_gold(silver, BASELINE)
emer = build_gold(silver, emergency)
display(emer["chip_fact_plan"].filter("business_date = '2026-09-05'")
        .select("scenario_id", "business_date", "product_id", "planned_output_kg", "material_id", "required_qty_kg"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 기준 계획과 비교 — 현재 계산
# MAGIC
# MAGIC **예상 결과 (CHIP-A):** 안전재고 미만 9/9 → 9/8, 부족 9/11 → 9/10, 9월 소요량 3,000 → 3,020kg, 추가 확보량 300 → 320kg.
# MAGIC CHIP-B는 변화가 없습니다.

# COMMAND ----------
comparison = compare_scenarios(base["chip_scenario_summary"], emer["chip_scenario_summary"])
display(comparison.selectExpr(
    "material_id",
    "stack(4, '첫 안전재고 미만', string(baseline_first_below_safety_date), string(scenario_first_below_safety_date),"
    " '첫 부족', string(baseline_first_shortage_date), string(scenario_first_shortage_date),"
    " '9월 소요량(kg)', string(baseline_total_required_kg), string(scenario_total_required_kg),"
    " '추가 확보량(kg)', string(baseline_required_topup_kg), string(scenario_required_topup_kg))"
    " AS (item, baseline, emergency_v1)").orderBy("material_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 판단 기준과 대응안
# MAGIC **판단 기준**
# MAGIC 1. 9월 모든 날의 마감 재고가 안전재고(200kg) 이상이어야 합니다.
# MAGIC 2. 입고 직후 Bunker 재고가 용량(3,000kg)을 넘으면 안 됩니다.
# MAGIC
# MAGIC **대응안 (CHIP-A / BNK-A)** — 긴급 오더 계획에 입고만 바꿔 같은 함수로 다시 계산합니다.
# MAGIC
# MAGIC | 대응안 | 내용 | 추가 구매 |
# MAGIC |---|---|---|
# MAGIC | OPT-1 입고 앞당김 | R-A-12를 9/12→9/8, R-A-22를 9/22→9/18 | 0kg |
# MAGIC | OPT-2 추가 입고 | 9/8에 320kg 추가 입고 | 320kg |
# MAGIC | OPT-3 앞당김 + 추가 입고 | OPT-1 + 9/28에 220kg 추가 입고 | 220kg |
# MAGIC
# MAGIC **예상 결과:** OPT-1은 9/28 안전재고 미만·9/30 부족으로 기준 미충족, OPT-2·OPT-3은 기준 충족입니다.
# MAGIC 다른 Bunker에서 옮기는 재배분안은 계산하지 않습니다. 이 데이터에는 같은 Chip을 가진 다른 Bunker가 없기 때문입니다.

# COMMAND ----------
OPTIONS = [
    ("OPT-1", "입고 앞당김", "R-A-12 9/12→9/8, R-A-22 9/22→9/18",
     {"R-A-12": "2026-09-08", "R-A-22": "2026-09-18"}, None),
    ("OPT-2", "추가 입고", "9/8 CHIP-A 320kg 추가 입고", {}, ("2026-09-08", 320)),
    ("OPT-3", "입고 앞당김 + 추가 입고", "OPT-1 + 9/28 CHIP-A 220kg 추가 입고",
     {"R-A-12": "2026-09-08", "R-A-22": "2026-09-18"}, ("2026-09-28", 220)),
]
emergency_plan = add_required_qty(silver["plans"], silver["recipes"], emergency)
capacity = silver["bunkers"].select("bunker_id", "capacity_kg")


def evaluate_option(option_id, option_name, detail, moved_receipts, extra_receipt):
    receipts = silver["receipts"]
    for receipt_id, new_date in moved_receipts.items():
        receipts = receipts.withColumn("business_date", F.when(
            F.col("receipt_id") == receipt_id, F.lit(date.fromisoformat(new_date))).otherwise(F.col("business_date")))
    extra_kg = 0
    if extra_receipt:
        extra_date, extra_kg = extra_receipt
        receipts = receipts.unionByName(spark.createDataFrame(
            [(f"{option_id}-EXTRA", "CHIP-A", "BNK-A", date.fromisoformat(extra_date), Decimal(extra_kg))],
            receipts.schema))
    balance = project_balance(emergency_plan, receipts, silver["bunkers"], silver["opening"],
                              emergency["scenario_id"]).filter("bunker_id = 'BNK-A'")
    peak = (balance.join(capacity, "bunker_id")
            .groupBy("bunker_id").agg(F.max(F.greatest(F.col("opening_qty_kg"), F.lit(0)) + F.col("received_qty_kg")
                                            - F.col("capacity_kg")).alias("over_capacity_kg")))
    return (summarize(balance).join(peak, "bunker_id")
            .withColumn("option_id", F.lit(option_id))
            .withColumn("option_name", F.lit(option_name))
            .withColumn("action_detail", F.lit(detail))
            .withColumn("extra_receipt_kg", F.lit(extra_kg))
            .withColumn("within_capacity", F.col("over_capacity_kg") <= 0)
            .withColumn("meets_safety_rule",
                        (F.col("min_closing_qty_kg") >= F.col("safety_stock_kg")) & F.col("within_capacity"))
            .withColumn("option_key", make_key("scenario_id", "option_id")))


options = None
for option in OPTIONS:
    result = evaluate_option(*option)
    options = result if options is None else options.unionByName(result)
options = to_gold(options, "chip_response_option")
display(options.select("option_id", "option_name", "extra_receipt_kg", "first_below_safety_date",
                       "first_shortage_date", "min_closing_qty_kg", "meets_safety_rule").orderBy("option_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. OneLake에 저장
# MAGIC 기준 계획과 긴급 오더를 함께 저장합니다. 비교 결과와 대응안도 저장합니다.
# MAGIC
# MAGIC **예상 결과:** material 2, bunker 2, date 30, scenario 2, plan 120, balance 120, summary 4, comparison 2, response_option 3

# COMMAND ----------
frames = {}
for name in GOLD_SCHEMA:
    if name in ("chip_dim_material", "chip_dim_bunker", "chip_dim_date"):
        frames[name] = base[name]
    elif name == "chip_scenario_comparison":
        frames[name] = comparison
    elif name == "chip_response_option":
        frames[name] = options
    else:
        frames[name] = base[name].unionByName(emer[name])
display(write_gold(frames))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 다음 단계
# MAGIC Fabric에서 Power BI 보고서로 두 시나리오를 비교하고, Agent 제안과 사람 승인을 진행합니다. (문서 07)
