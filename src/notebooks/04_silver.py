# Databricks notebook source
# MAGIC %md
# MAGIC # 04. Silver: 형식을 맞추고 문제 행 정리
# MAGIC Bronze 테이블을 계산에 쓸 수 있는 Silver 테이블로 바꿉니다.
# MAGIC
# MAGIC | 작업 | 예 |
# MAGIC |---|---|
# MAGIC | 형식 맞추기 | 문자 `20261002` → 날짜 `2026-10-02`, 문자 `50000` → 숫자 |
# MAGIC | 단위 통일 | 발주 수량 `50` `TO`(톤) → `50000` kg |
# MAGIC | 격리 | 중복, 수량 공란, 미등록 원료 코드, 범위를 벗어난 센서 값 → `silver_quarantine` |
# MAGIC
# MAGIC 격리한 행은 지우지 않고 이유와 원본 행 번호를 함께 남깁니다.
# MAGIC
# MAGIC 1. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 2. 마지막 셀까지 확인하면 `05_gold`를 엽니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정 불러오기
# MAGIC **예상 결과:** 01에서 본 결과가 다시 표시됩니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 기준 정보와 실적: 형식 맞추기
# MAGIC 문제 행이 없는 테이블 12개는 형식만 바꿉니다. 날짜는 `DATE`, 시각은 한국 시간 `TIMESTAMP`, 수량은 `BIGINT`, 소요량은 소수 6자리 `DECIMAL`입니다.
# MAGIC
# MAGIC **예상 결과:** 표 12행. 행 수가 Bronze와 같습니다.

# COMMAND ----------
from pyspark.sql import functions as F

typed_tables = {
    "silver_material": """
        SELECT material_id, material_name, description, CAST(unit_price_krw_per_kg AS INT) AS unit_price_krw_per_kg, base_uom
        FROM bronze_sap_material""",
    "silver_supplier": """
        SELECT supplier_id, supplier_name, CAST(standard_lead_time_days AS INT) AS standard_lead_time_days,
               CAST(max_pull_in_days AS INT) AS max_pull_in_days, CAST(order_unit_kg AS BIGINT) AS order_unit_kg,
               CAST(pull_in_fee_krw_per_kg AS INT) AS pull_in_fee_krw_per_kg, CAST(spot_premium_pct AS INT) AS spot_premium_pct
        FROM bronze_sap_supplier""",
    "silver_purchase_receipt": """
        SELECT receipt_id, purchase_order_id, supplier_id, material_id, bunker_id,
               to_date(promised_date, 'yyyyMMdd') AS promised_date, to_date(received_date, 'yyyyMMdd') AS received_date,
               CAST(quantity AS BIGINT) AS quantity_kg
        FROM bronze_sap_purchase_receipt""",
    "silver_sales_order": """
        SELECT sales_order_id, to_date(order_date, 'yyyyMMdd') AS order_date, customer_id, customer_name, product_id,
               CAST(order_qty_kg AS BIGINT) AS order_qty_kg, to_date(due_date, 'yyyyMMdd') AS due_date, priority
        FROM bronze_sap_sales_order""",
    "silver_line": """
        SELECT line_id, plant_id, line_family, CAST(default_daily_output_kg AS BIGINT) AS default_daily_output_kg
        FROM bronze_fpims_line""",
    "silver_bunker": """
        SELECT bunker_id, line_id, material_id, CAST(capacity_kg AS BIGINT) AS capacity_kg, CAST(safety_stock_kg AS BIGINT) AS safety_stock_kg
        FROM bronze_fpims_bunker""",
    "silver_product": """
        SELECT product_id, line_id, product_name, film_family, CAST(default_daily_output_kg AS BIGINT) AS default_daily_output_kg
        FROM bronze_fpims_product""",
    "silver_recipe": """
        SELECT product_id, line_id, material_id, CAST(std_kg_per_kg AS DECIMAL(10,6)) AS std_kg_per_kg
        FROM bronze_fpims_recipe""",
    "silver_transfer_route": """
        SELECT route_id, from_bunker_id, to_bunker_id, material_id, CAST(max_kg_per_day AS BIGINT) AS max_kg_per_day,
               CAST(lead_time_days AS INT) AS lead_time_days, CAST(cost_krw_per_kg AS INT) AS cost_krw_per_kg
        FROM bronze_fpims_transfer_route""",
    "silver_production_lot": """
        SELECT lot_id, line_id, product_id, CAST(start_ts AS TIMESTAMP) AS start_ts, CAST(end_ts AS TIMESTAMP) AS end_ts,
               CAST(output_kg AS BIGINT) AS output_kg
        FROM bronze_fpims_production_lot""",
    "silver_material_consumption": """
        SELECT consumption_id, lot_id, line_id, bunker_id, material_id, CAST(consumed_kg AS BIGINT) AS consumed_kg
        FROM bronze_fpims_material_consumption""",
    "silver_production_plan": """
        SELECT plan_id, to_date(plan_date, 'yyyyMMdd') AS plan_date, line_id, product_id,
               CAST(planned_output_kg AS BIGINT) AS planned_output_kg, sales_order_id
        FROM bronze_fpims_production_plan""",
}

results = []
for table, query in typed_tables.items():
    spark.sql(f"CREATE OR REPLACE TABLE {table} AS {query}")
    source = query.split("FROM")[-1].strip()
    results.append((source, table, spark.table(source).count(), spark.table(table).count()))
display(spark.createDataFrame(results, "`Bronze` string, `Silver` string, `Bronze 행 수` long, `Silver 행 수` long"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 입고 예정 발주 정리
# MAGIC 원천: `bronze_sap_purchase_order_open`
# MAGIC
# MAGIC 행마다 아래 순서로 확인합니다. 해당하면 격리하고, 통과한 행만 Silver에 넣습니다.
# MAGIC
# MAGIC | 순서 | 확인 | 처리 |
# MAGIC |---|---|---|
# MAGIC | 1 | 원료 코드가 `silver_material`에 없음 | `unknown_material`로 격리 |
# MAGIC | 2 | 수량이 공란 | `blank_quantity`로 격리 |
# MAGIC | 3 | 발주 번호·항목이 앞 행과 같음 | `duplicate_line`으로 격리 (먼저 나온 행만 남김) |
# MAGIC | 4 | 단위가 `TO` | 수량 × 1000 → kg. 원래 수량과 단위는 `source_quantity`, `source_unit`에 남김 |
# MAGIC
# MAGIC **예상 결과:** 결과 없이 끝납니다.

# COMMAND ----------
spark.sql("""
CREATE OR REPLACE TEMP VIEW purchase_order_checked AS
SELECT b.*,
       CASE WHEN m.material_id IS NULL THEN 'unknown_material'
            WHEN b.quantity IS NULL THEN 'blank_quantity'
            WHEN ROW_NUMBER() OVER (PARTITION BY b.purchase_order_id, b.po_line_no ORDER BY b._source_row) > 1 THEN 'duplicate_line'
       END AS reason
FROM bronze_sap_purchase_order_open b
LEFT JOIN silver_material m ON m.material_id = b.material_id
""")

spark.sql("""
CREATE OR REPLACE TABLE silver_purchase_order_open AS
SELECT purchase_order_id, po_line_no, supplier_id, material_id, bunker_id,
       to_date(promised_date, 'yyyyMMdd') AS promised_date,
       CAST(quantity AS BIGINT) AS source_quantity, unit AS source_unit,
       CAST(quantity AS BIGINT) * CASE WHEN unit = 'TO' THEN 1000 ELSE 1 END AS quantity_kg
FROM purchase_order_checked
WHERE reason IS NULL
""")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 발주 정리 결과
# MAGIC 02에서 본 `BNK-L3-2`의 10월 입고 예정을 다시 봅니다.
# MAGIC
# MAGIC **예상 결과:** 5행. 10월 2일 줄은 `quantity_kg`가 `50000`이고, 원래 값 `50` `TO`가 옆에 남습니다. 10월 9일 줄은 한 번만 나옵니다.

# COMMAND ----------
display(spark.table("silver_purchase_order_open")
        .filter("bunker_id = 'BNK-L3-2' AND promised_date < '2026-11-01'")
        .orderBy("promised_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. 센서 값 정리
# MAGIC 원천: `bronze_pvss_bunker_level`
# MAGIC
# MAGIC | 확인 | 처리 |
# MAGIC |---|---|
# MAGIC | 값이 0 미만이거나 Bunker 용량보다 큼 | `out_of_range`로 격리 |
# MAGIC | 같은 Bunker·시각이 앞 행과 같음 | `duplicate_reading`으로 격리 (먼저 나온 행만 남김) |
# MAGIC
# MAGIC 기록이 빠진 시각은 채우지 않습니다. 시작 재고에는 9월 30일 23시 값만 쓰기 때문입니다.
# MAGIC
# MAGIC **예상 결과:** 결과 없이 끝납니다.

# COMMAND ----------
spark.sql("""
CREATE OR REPLACE TEMP VIEW bunker_level_checked AS
SELECT b.*,
       CASE WHEN CAST(b.level_kg AS BIGINT) < 0 OR CAST(b.level_kg AS BIGINT) > s.capacity_kg THEN 'out_of_range'
            WHEN ROW_NUMBER() OVER (PARTITION BY b.bunker_id, b.timestamp ORDER BY b._source_row) > 1 THEN 'duplicate_reading'
       END AS reason
FROM bronze_pvss_bunker_level b
JOIN silver_bunker s ON s.bunker_id = b.bunker_id
""")

spark.sql("""
CREATE OR REPLACE TABLE silver_bunker_level AS
SELECT bunker_id, CAST(timestamp AS TIMESTAMP) AS reading_ts, CAST(level_kg AS BIGINT) AS level_kg
FROM bunker_level_checked
WHERE reason IS NULL
""")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. 격리 테이블 만들기
# MAGIC 격리한 행을 `silver_quarantine`에 모읍니다. `raw_record`에는 Bronze 원본 행을 JSON으로 남깁니다.
# MAGIC
# MAGIC **예상 결과:** 5행, 합계 23행. `unknown_material` 3, `blank_quantity` 4, `duplicate_line` 5, `out_of_range` 6, `duplicate_reading` 5

# COMMAND ----------
spark.sql("""
CREATE OR REPLACE TABLE silver_quarantine AS
SELECT 'bronze_sap_purchase_order_open' AS source_table, _source_row AS source_row_number,
       concat(purchase_order_id, '|', po_line_no) AS record_key, reason,
       to_json(struct(purchase_order_id, po_line_no, supplier_id, material_id, bunker_id, promised_date, quantity, unit)) AS raw_record
FROM purchase_order_checked WHERE reason IS NOT NULL
UNION ALL
SELECT 'bronze_pvss_bunker_level', _source_row, concat(bunker_id, '|', timestamp), reason,
       to_json(struct(bunker_id, timestamp, level_kg))
FROM bunker_level_checked WHERE reason IS NOT NULL
""")

display(spark.sql("""
SELECT source_table, reason, COUNT(*) AS rows
FROM silver_quarantine
GROUP BY source_table, reason
ORDER BY source_table DESC, reason DESC
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. 격리한 행 보기
# MAGIC 미등록 원료 코드와 범위를 벗어난 센서 값을 봅니다. `source_row_number`로 Bronze 원본 행을 찾을 수 있습니다.
# MAGIC
# MAGIC **예상 결과:** 9행. 원료 코드 `PET-HV`, `MB-AS`, `NY6-R`와, `-100`처럼 0보다 작거나 용량보다 큰 센서 값이 보입니다.

# COMMAND ----------
display(spark.table("silver_quarantine")
        .filter("reason IN ('unknown_material', 'out_of_range')")
        .orderBy("source_table", "source_row_number"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. 센서 기록이 빠진 시각
# MAGIC 9월 한 달은 Bunker 24개 × 720시간 = 17,280개 기록이 있어야 합니다. 빠진 시각을 찾습니다.
# MAGIC
# MAGIC **예상 결과:** 7행

# COMMAND ----------
display(spark.sql("""
WITH hours AS (
    SELECT explode(sequence(TIMESTAMP'2026-09-01 00:00:00', TIMESTAMP'2026-09-30 23:00:00', INTERVAL 1 HOUR)) AS reading_ts
)
SELECT b.bunker_id, h.reading_ts
FROM silver_bunker b CROSS JOIN hours h
LEFT ANTI JOIN (SELECT DISTINCT bunker_id, CAST(timestamp AS TIMESTAMP) AS reading_ts FROM bronze_pvss_bunker_level) r
    ON r.bunker_id = b.bunker_id AND r.reading_ts = h.reading_ts
ORDER BY h.reading_ts
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. Silver 정리 결과
# MAGIC Silver 테이블 15개의 행 수입니다.
# MAGIC
# MAGIC **예상 결과:** 15행. `silver_purchase_order_open` 719행 (Bronze 731행 − 격리 12행), `silver_bunker_level` 17,267행 (Bronze 17,278행 − 격리 11행), `silver_quarantine` 23행

# COMMAND ----------
silver_tables = [*typed_tables, "silver_purchase_order_open", "silver_bunker_level", "silver_quarantine"]
display(spark.createDataFrame([(t, spark.table(t).count()) for t in silver_tables], "`Silver 테이블` string, `행 수` long"))
