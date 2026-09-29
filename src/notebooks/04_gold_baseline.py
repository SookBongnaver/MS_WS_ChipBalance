# Databricks notebook source
# MAGIC %md
# MAGIC # 04. 기준 계획 Gold → OneLake
# MAGIC Silver 데이터로 9월 한 달의 날짜별 원료 Balance를 계산하고, 결과(Gold)를 Fabric OneLake에 저장합니다.
# MAGIC
# MAGIC ```
# MAGIC 생산계획(제품 kg) × 제품 1kg당 Chip kg = 날짜별 Chip 소요량
# MAGIC 전일 마감 재고 + 당일 입고 - 당일 소요량 = 당일 마감 재고
# MAGIC ```

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Silver 읽기
# MAGIC 03에서 저장한 Silver 테이블 6개를 읽습니다.
# MAGIC
# MAGIC **예상 결과:** materials 2, bunkers 2, opening 2, recipes 2, plans 60, receipts 3

# COMMAND ----------
silver = read_silver()
display(spark.createDataFrame([(name, df.count()) for name, df in silver.items()],
                              "silver_table STRING, row_count BIGINT"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 날짜별 Chip 소요량
# MAGIC 생산계획과 소요량 기준을 제품 ID로 연결하고 곱합니다.
# MAGIC
# MAGIC **예상 결과 (9월 1일):** FILM-A 100kg × 1.0 = CHIP-A 100kg, FILM-B 40kg × 1.25 = CHIP-B 50kg

# COMMAND ----------
plan = add_required_qty(silver["plans"], silver["recipes"], BASELINE)
display(plan.filter("business_date = '2026-09-01'")
        .select("business_date", "product_id", "planned_output_kg", "kg_per_kg",
                "material_id", "bunker_id", "required_qty_kg"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 날짜별 예상 재고
# MAGIC Bunker마다 9월 1일~30일 달력을 만들고, 입고와 소요량을 날짜별로 누적합니다.
# MAGIC 입고가 없는 날도 빠지지 않도록 달력을 기준으로 연결합니다.
# MAGIC * `below_safety`: 마감 재고 < 안전재고(200kg)
# MAGIC * `shortage`: 마감 재고 < 0kg — 계획대로 생산하면 모자라는 양입니다.
# MAGIC
# MAGIC **예상 결과 (CHIP-A):** 9/8 200kg → 9/9 100kg(안전재고 미만) → 9/10 0kg → 9/11 -100kg(부족) → 9/12 800kg(1,000kg 입고)

# COMMAND ----------
balance = project_balance(plan, silver["receipts"], silver["bunkers"], silver["opening"], "baseline")
display(balance.filter("material_id = 'CHIP-A' AND business_date BETWEEN '2026-09-07' AND '2026-09-13'")
        .select("business_date", "material_id", "received_qty_kg", "required_qty_kg", "closing_qty_kg",
                "below_safety", "shortage")
        .orderBy("business_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 원료별 요약
# MAGIC `required_topup_kg`는 9월 내내 안전재고를 지키려면 월초에 더 있어야 했던 양입니다. (안전재고 - 최저 재고)
# MAGIC
# MAGIC | 원료 | 첫 안전재고 미만 | 첫 부족 | 9월 소요량 | 월말 재고 | 최저 재고 | 추가 확보량 |
# MAGIC |---|---|---|---|---|---|---|
# MAGIC | CHIP-A | 9/9 | 9/11 | 3,000kg | 0kg | -100kg | 300kg |
# MAGIC | CHIP-B | 없음 | 없음 | 1,500kg | 500kg | 300kg | 0kg |

# COMMAND ----------
display(summarize(balance).select("material_id", "first_below_safety_date", "first_shortage_date",
                                  "total_required_kg", "ending_qty_kg", "min_closing_qty_kg",
                                  "required_topup_kg").orderBy("material_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. OneLake에 Gold 저장
# MAGIC 계산 결과를 Gold 테이블 9개로 만들어 Fabric Lakehouse의 `gold` 스키마에 저장합니다.
# MAGIC 비교·대응안 테이블은 05 Notebook에서 채우므로 지금은 0행입니다.
# MAGIC
# MAGIC **예상 결과:** material 2, bunker 2, date 30, scenario 1, plan 60, balance 60, summary 2, comparison 0, response_option 0

# COMMAND ----------
display(write_gold(build_gold(silver, BASELINE)))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 다음 단계
# MAGIC Fabric에서 Lakehouse를 열어 방금 저장한 `gold` 테이블을 확인합니다. (문서 04)
