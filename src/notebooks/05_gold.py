# Databricks notebook source
# MAGIC %md
# MAGIC # 05. Gold: Chip Balance 계산과 OneLake 저장
# MAGIC Silver 테이블로 Bunker별·날짜별 원료 Balance를 계산해 Gold 테이블을 만들고, Fabric Lakehouse(OneLake)에 바로 저장합니다.
# MAGIC Gold는 Unity Catalog에 만들지 않습니다. OneLake에만 있고, Databricks와 Fabric이 같은 Gold를 씁니다.
# MAGIC
# MAGIC | 순서 | 계산 | Gold 테이블 |
# MAGIC |---|---|---|
# MAGIC | 1 | 기준 정보 정리 (라인, Bunker, 원료, 제품, 공급사, 고객, 이송 경로, 날짜) | `gold_dim_*` |
# MAGIC | 2 | 1년 실적으로 제품별 실제 원료 소요량 | `gold_fact_usage_factor` |
# MAGIC | 3 | 공급사별 평균 입고 지연 → 입고 예정일 | `gold_dim_supplier`, `gold_fact_inbound` |
# MAGIC | 4 | 9월 30일 23시 센서 값 → 시작 재고 | `gold_fact_opening_stock` |
# MAGIC | 5 | 생산계획 × 실제 소요량 → 날짜별 Bunker 사용량, 날짜별 재고 | `gold_fact_balance` |
# MAGIC | 6 | Bunker별 위험 요약, 판매오더 납기 | `gold_fact_bunker_summary`, `gold_fact_order_fulfillment` |
# MAGIC
# MAGIC 이 Notebook은 **현재 계획**(`baseline`)만 계산합니다. 긴급 오더는 06장에서 같은 방식으로 다시 계산합니다.
# MAGIC
# MAGIC 1. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 2. 마지막 셀까지 확인하면 교재 05장으로 돌아가 Fabric에서 결과를 확인합니다.
# MAGIC
# MAGIC Gold 셀은 결과를 OneLake에 저장하고, 저장된 Gold를 같은 이름(`gold_…`)의 임시 뷰로 등록합니다. 다음 셀이 이 뷰를 이어서 씁니다.
# MAGIC OneLake에 저장하느라 셀마다 몇 초 더 걸립니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정 불러오기
# MAGIC **예상 결과:** 01에서 본 결과가 다시 표시되고, `연결 확인 완료`가 나옵니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 기준 정보 (Dimension)
# MAGIC 보고서와 Ontology에서 이름과 속성을 보여 줄 기준 정보 테이블입니다.
# MAGIC 원료의 공급사는 입고 실적에서 찾습니다. 날짜는 4분기(10월 1일~12월 31일) 92일입니다.
# MAGIC
# MAGIC **예상 결과:** 결과 없이 끝납니다.

# COMMAND ----------
dimension_tables = {
    "gold_dim_line": """
        SELECT line_id, plant_id, line_family, default_daily_output_kg FROM silver_line""",
    "gold_dim_bunker": """
        SELECT bunker_id, concat(line_id, ' ', material_id) AS bunker_name, line_id, material_id, capacity_kg, safety_stock_kg
        FROM silver_bunker""",
    "gold_dim_material": """
        SELECT m.material_id, m.material_name, m.description, m.unit_price_krw_per_kg, s.supplier_id
        FROM silver_material m
        LEFT JOIN (SELECT DISTINCT material_id, supplier_id FROM silver_purchase_receipt) s ON s.material_id = m.material_id""",
    "gold_dim_product": """
        SELECT product_id, product_name, line_id, film_family FROM silver_product""",
    "gold_dim_customer": """
        SELECT DISTINCT customer_id, customer_name FROM silver_sales_order""",
    "gold_dim_route": """
        SELECT route_id, from_bunker_id, to_bunker_id, material_id, max_kg_per_day, lead_time_days, cost_krw_per_kg
        FROM silver_transfer_route""",
    "gold_dim_date": """
        SELECT date_key, date_format(date_key, 'yyyyMM') AS yyyymm, weekday(date_key) + 1 AS day_of_week,
               element_at(array('월', '화', '수', '목', '금', '토', '일'), weekday(date_key) + 1) AS weekday_name
        FROM (SELECT explode(sequence(DATE'2026-10-01', DATE'2026-12-31')) AS date_key)""",
    "gold_dim_scenario": """
        SELECT 'baseline' AS scenario_id, '현재 계획' AS scenario_name, '2026년 4분기 생산계획과 입고 예정' AS description""",
}
for table, query in dimension_tables.items():
    publish_gold(table.removeprefix("gold_"), spark.sql(query))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 실제 원료 소요량
# MAGIC 제품 1kg을 만들 때 실제로 쓴 원료(kg)를 1년 실적으로 구합니다.
# MAGIC
# MAGIC `실제 소요량 = 원료 사용량 합계 ÷ 생산량 합계` (소수 6자리 반올림)
# MAGIC
# MAGIC 레시피 기준보다 실제 소요량이 1~4% 많습니다. 공정 손실이 있기 때문입니다. Balance는 실제 소요량으로 계산합니다.
# MAGIC 아래 결과는 L3 제품의 PET-SD만 보여 줍니다. 테이블에는 제품·원료 118개 조합이 모두 들어 있습니다.
# MAGIC
# MAGIC **예상 결과:** 5행. `P-L3-05`의 PET-SD 실제 소요량은 `0.463237`로 레시피 기준 `0.450000`보다 2.94% 많습니다.

# COMMAND ----------
publish_gold("fact_usage_factor", spark.sql("""
WITH output AS (
    SELECT product_id, SUM(output_kg) AS output_kg FROM silver_production_lot GROUP BY product_id
), used AS (
    SELECT l.product_id, c.material_id, SUM(c.consumed_kg) AS consumed_kg
    FROM silver_material_consumption c JOIN silver_production_lot l ON l.lot_id = c.lot_id
    GROUP BY l.product_id, c.material_id
), factor AS (
    SELECT u.product_id, u.material_id, r.std_kg_per_kg, u.consumed_kg, o.output_kg,
           CAST(ROUND(CAST(u.consumed_kg AS DECIMAL(20,0)) / o.output_kg, 6) AS DECIMAL(10,6)) AS actual_kg_per_kg
    FROM used u
    JOIN output o ON o.product_id = u.product_id
    JOIN silver_recipe r ON r.product_id = u.product_id AND r.material_id = u.material_id
)
SELECT concat(product_id, '|', material_id) AS usage_factor_key, product_id, material_id, std_kg_per_kg, actual_kg_per_kg,
       CAST(ROUND((actual_kg_per_kg / std_kg_per_kg - 1) * 100, 2) AS DECIMAL(6,2)) AS loss_pct, consumed_kg, output_kg
FROM factor
"""))
publish_gold("fact_monthly_usage", spark.sql("""
SELECT concat(date_format(l.start_ts, 'yyyy-MM'), '|', c.bunker_id) AS monthly_usage_key, date_format(l.start_ts, 'yyyy-MM') AS usage_month,
       c.bunker_id, c.material_id, SUM(c.consumed_kg) AS consumed_kg
FROM silver_material_consumption c JOIN silver_production_lot l ON l.lot_id = c.lot_id
GROUP BY ALL
"""))
display(spark.table("gold_fact_usage_factor")
        .filter("product_id LIKE 'P-L3-%' AND material_id = 'PET-SD'")
        .select("product_id", "material_id", "std_kg_per_kg", "actual_kg_per_kg", "loss_pct", "consumed_kg", "output_kg")
        .orderBy("product_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 공급사 입고 지연과 입고 예정일
# MAGIC 1년 입고 실적에서 공급사마다 `실제 입고일 − 약속일`의 평균을 구합니다. 이 평균을 반올림한 일수를 **계획 지연일**로 씁니다.
# MAGIC
# MAGIC `입고 예정일 = 발주 약속일 + 계획 지연일`
# MAGIC
# MAGIC **예상 결과:** 6행. 계획 지연일은 `SUP-PET-A` 0, `SUP-PET-B` 0, `SUP-MB-A` 1, `SUP-NY-A` 1, `SUP-NY-B` 2, `SUP-ADD-A` 3일입니다.

# COMMAND ----------
publish_gold("dim_supplier", spark.sql("""
WITH delay AS (
    SELECT supplier_id, COUNT(*) AS receipt_count,
           CAST(SUM(datediff(received_date, promised_date)) AS DECIMAL(20,0)) / COUNT(*) AS avg_delay
    FROM silver_purchase_receipt GROUP BY supplier_id
)
SELECT s.*, d.receipt_count, CAST(ROUND(d.avg_delay, 2) AS DECIMAL(6,2)) AS avg_delay_days,
       CAST(ROUND(d.avg_delay, 0) AS INT) AS planning_delay_days
FROM silver_supplier s JOIN delay d ON d.supplier_id = s.supplier_id
"""))
publish_gold("fact_inbound", spark.sql("""
SELECT concat(p.purchase_order_id, '|', p.po_line_no) AS inbound_key, p.purchase_order_id, p.po_line_no, p.supplier_id, p.material_id,
       p.bunker_id, p.promised_date, date_add(p.promised_date, s.planning_delay_days) AS expected_date,
       p.quantity_kg, p.source_quantity, p.source_unit
FROM silver_purchase_order_open p JOIN gold_dim_supplier s ON s.supplier_id = p.supplier_id
"""))
display(spark.table("gold_dim_supplier")
        .select("supplier_id", "supplier_name", "receipt_count", "avg_delay_days", "planning_delay_days")
        .orderBy("supplier_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. 시작 재고
# MAGIC Bunker마다 9월 30일 23시까지의 마지막 센서 값을 10월 1일 시작 재고로 씁니다.
# MAGIC
# MAGIC **예상 결과:** 24행. `BNK-L3-2`는 `30370`kg입니다.

# COMMAND ----------
publish_gold("fact_opening_stock", spark.sql("""
SELECT bunker_id, DATE'2026-10-01' AS as_of_date, reading_ts, level_kg AS opening_kg
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY bunker_id ORDER BY reading_ts DESC) AS rn
    FROM silver_bunker_level WHERE reading_ts <= TIMESTAMP'2026-09-30 23:00:00'
) WHERE rn = 1
"""))
display(spark.table("gold_fact_opening_stock").orderBy("bunker_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. 판매오더와 생산계획
# MAGIC 판매오더에 생산 라인을 붙이고, 생산계획에 시나리오(`baseline`)를 붙입니다.
# MAGIC 판매오더의 생산 완료일은 그 오더를 채우는 마지막 생산일입니다. 완료일이 납기보다 늦지 않으면 `on_time`이 `true`입니다.
# MAGIC
# MAGIC **예상 결과:** 321행 가운데 `on_time`이 `false`인 오더는 0개입니다.

# COMMAND ----------
publish_gold("fact_sales_order", spark.sql("""
SELECT o.sales_order_id, o.order_date, o.customer_id, o.product_id, p.line_id, o.order_qty_kg, o.due_date, o.priority, false AS is_urgent
FROM silver_sales_order o JOIN silver_product p ON p.product_id = o.product_id
"""))
publish_gold("fact_plan", spark.sql("""
SELECT concat('baseline|', plan_id) AS plan_key, 'baseline' AS scenario_id, plan_id, plan_date, line_id, product_id,
       planned_output_kg, sales_order_id, plan_date AS original_plan_date, 'none' AS change_type
FROM silver_production_plan
"""))
publish_gold("fact_order_fulfillment", spark.sql("""
SELECT concat(p.scenario_id, '|', o.sales_order_id) AS fulfillment_key, p.scenario_id, o.sales_order_id, o.customer_id, o.product_id,
       o.line_id, o.due_date, MAX(p.plan_date) AS finish_date, datediff(o.due_date, MAX(p.plan_date)) AS slack_days,
       MAX(p.plan_date) <= o.due_date AS on_time
FROM gold_fact_sales_order o JOIN gold_fact_plan p ON p.sales_order_id = o.sales_order_id
GROUP BY p.scenario_id, o.sales_order_id, o.customer_id, o.product_id, o.line_id, o.due_date
"""))
display(spark.sql("SELECT scenario_id, COUNT(*) AS orders, COUNT_IF(NOT on_time) AS late_orders FROM gold_fact_order_fulfillment GROUP BY scenario_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. 날짜별 Bunker Balance
# MAGIC Bunker마다 10월 1일부터 12월 31일까지 하루씩 재고를 계산합니다.
# MAGIC
# MAGIC | 항목 | 계산 |
# MAGIC |---|---|
# MAGIC | 사용량 `requirement_kg` | 그날 생산계획의 생산량 × 제품의 실제 소요량 (계획 행마다 kg 단위 반올림), 같은 라인의 해당 원료 Bunker에서 빠짐 |
# MAGIC | 입고 `receipt_kg` | 입고 예정일이 그날인 발주 수량 |
# MAGIC | 이송 `transfer_in_kg`, `transfer_out_kg` | 현재 계획에는 없음 (긴급 오더 대응안에서 사용) |
# MAGIC | 기말 재고 `closing_kg` | 기초 재고 + 입고 + 이송 입고 − 이송 출고 − 사용량. 다음 날 기초 재고가 됩니다. |
# MAGIC | 판정 | `below_safety`: 기말 재고 < 안전재고, `shortage`: 기말 재고 < 0, `over_capacity`: 기초 재고 + 입고 + 이송 입고 > 용량 |
# MAGIC
# MAGIC **예상 결과:** `BNK-L3-2`의 10월 1~10일 10행. 10월 2일과 9일에 입고가 있고, `below_safety`는 모두 `false`입니다.

# COMMAND ----------
publish_gold("fact_balance", spark.sql("""
WITH requirement AS (
    SELECT b.bunker_id, p.plan_date AS balance_date,
           SUM(CAST(ROUND(p.planned_output_kg * f.actual_kg_per_kg, 0) AS BIGINT)) AS requirement_kg
    FROM gold_fact_plan p
    JOIN gold_fact_usage_factor f ON f.product_id = p.product_id
    JOIN gold_dim_bunker b ON b.line_id = p.line_id AND b.material_id = f.material_id
    WHERE p.scenario_id = 'baseline'
    GROUP BY b.bunker_id, p.plan_date
), receipt AS (
    SELECT bunker_id, expected_date AS balance_date, SUM(quantity_kg) AS receipt_kg
    FROM gold_fact_inbound GROUP BY bunker_id, expected_date
), flow AS (
    SELECT b.bunker_id, d.date_key AS balance_date, s.opening_kg AS start_kg, b.safety_stock_kg, b.capacity_kg,
           COALESCE(r.receipt_kg, 0) AS receipt_kg, CAST(0 AS BIGINT) AS transfer_in_kg, CAST(0 AS BIGINT) AS transfer_out_kg,
           COALESCE(q.requirement_kg, 0) AS requirement_kg
    FROM gold_dim_bunker b
    CROSS JOIN gold_dim_date d
    JOIN gold_fact_opening_stock s ON s.bunker_id = b.bunker_id
    LEFT JOIN receipt r ON r.bunker_id = b.bunker_id AND r.balance_date = d.date_key
    LEFT JOIN requirement q ON q.bunker_id = b.bunker_id AND q.balance_date = d.date_key
), balance AS (
    SELECT *, start_kg + SUM(receipt_kg + transfer_in_kg - transfer_out_kg - requirement_kg)
                  OVER (PARTITION BY bunker_id ORDER BY balance_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS closing_kg
    FROM flow
)
SELECT concat('baseline|', bunker_id, '|', balance_date) AS balance_key, 'baseline' AS scenario_id, bunker_id, balance_date,
       closing_kg + requirement_kg + transfer_out_kg - transfer_in_kg - receipt_kg AS opening_kg,
       receipt_kg, transfer_in_kg, transfer_out_kg, requirement_kg, closing_kg, safety_stock_kg, capacity_kg,
       closing_kg < safety_stock_kg AS below_safety, closing_kg < 0 AS shortage,
       closing_kg + requirement_kg + transfer_out_kg > capacity_kg AS over_capacity
FROM balance
"""))
display(spark.table("gold_fact_balance")
        .filter("bunker_id = 'BNK-L3-2' AND balance_date <= '2026-10-10'")
        .select("balance_date", "opening_kg", "receipt_kg", "requirement_kg", "closing_kg", "safety_stock_kg", "below_safety")
        .orderBy("balance_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. Bunker 위험 요약
# MAGIC Bunker마다 4분기 동안 안전재고 아래로 내려가는 날이 있는지 요약합니다.
# MAGIC `required_topup_kg`는 가장 낮은 재고를 안전재고까지 올리는 데 필요한 양입니다.
# MAGIC 아래 결과는 가장 낮은 재고와 안전재고의 차이(`margin_kg`)가 작은 Bunker부터 보여 줍니다.
# MAGIC
# MAGIC **예상 결과:** 24행. 여유가 가장 작은 `BNK-L5-4`도 안전재고보다 1,002kg 많습니다.
# MAGIC 모든 Bunker의 `below_safety_days`와 `required_topup_kg`가 0입니다. 현재 계획으로는 모든 Bunker가 안전재고를 지킵니다.

# COMMAND ----------
publish_gold("fact_bunker_summary", spark.sql("""
SELECT concat(f.scenario_id, '|', f.bunker_id) AS summary_key, f.scenario_id, f.bunker_id, b.line_id, b.material_id,
       COUNT_IF(f.below_safety) AS below_safety_days,
       MIN(CASE WHEN f.below_safety THEN f.balance_date END) AS first_below_safety_date,
       MIN(CASE WHEN f.shortage THEN f.balance_date END) AS first_shortage_date,
       MIN(f.closing_kg) AS min_closing_kg,
       MIN_BY(f.balance_date, struct(f.closing_kg, f.balance_date)) AS min_closing_date,
       GREATEST(0, MAX(f.safety_stock_kg) - MIN(f.closing_kg)) AS required_topup_kg
FROM gold_fact_balance f JOIN gold_dim_bunker b ON b.bunker_id = f.bunker_id
GROUP BY f.scenario_id, f.bunker_id, b.line_id, b.material_id
"""))
display(spark.sql("""
SELECT s.bunker_id, s.material_id, s.below_safety_days, s.min_closing_kg, b.safety_stock_kg,
       s.min_closing_kg - b.safety_stock_kg AS margin_kg, s.min_closing_date, s.required_topup_kg
FROM gold_fact_bunker_summary s JOIN gold_dim_bunker b ON b.bunker_id = s.bunker_id
ORDER BY margin_kg, s.bunker_id
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. OneLake의 Gold 확인
# MAGIC Gold 테이블 18개가 Fabric Lakehouse `lh_chipbalance_<참가자 번호>`의 `gold` 스키마에 저장되었는지 확인합니다.
# MAGIC 이름에서 `gold_`를 뺍니다. 예를 들어 `gold_fact_balance`는 Lakehouse의 `gold.fact_balance`입니다.
# MAGIC Managed Identity로 저장했고, 다시 실행하면 덮어씁니다. 소수 열(`actual_kg_per_kg` 등)은 `DOUBLE`로 저장됩니다.
# MAGIC
# MAGIC **예상 결과:** 18행. `gold_fact_balance`는 2,208행 (Bunker 24개 × 92일)입니다.

# COMMAND ----------
check = [(f"gold_{t}", f"gold.{t}", onelake_gold_rows(t)) for t in GOLD_TABLES]
display(spark.createDataFrame(check, "`Notebook의 Gold` string, `OneLake 테이블` string, `OneLake 행 수` long"))
print("OneLake 경로:", f"{ONELAKE_ROOT}/Tables/gold")
