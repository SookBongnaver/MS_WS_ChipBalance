# Databricks notebook source
# MAGIC %md
# MAGIC # 03. Bronze: 원천 파일 그대로 적재
# MAGIC 02에서 만든 파일 14개를 Unity Catalog의 Bronze 테이블 14개로 옮깁니다.
# MAGIC
# MAGIC Bronze는 원본을 바꾸지 않습니다. 값은 모두 문자로 두고, 어느 파일의 몇 번째 행인지와 적재 시각만 붙입니다.
# MAGIC Silver나 Gold 결과가 이상하면 Bronze에서 원본 행을 찾아 비교합니다.
# MAGIC
# MAGIC 1. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 2. 마지막 셀까지 확인하면 `04_silver`를 엽니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정 불러오기
# MAGIC **예상 결과:** 01에서 본 결과가 다시 표시됩니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 파일과 Bronze 테이블
# MAGIC 파일 하나가 Bronze 테이블 하나가 됩니다. 테이블 이름은 `bronze_<시스템>_<내용>`입니다.
# MAGIC
# MAGIC | 추가 열 | 내용 |
# MAGIC |---|---|
# MAGIC | `_source_file` | 원천 파일 경로 |
# MAGIC | `_source_row` | 파일 안의 행 번호 (머리글 제외, 1부터) |
# MAGIC | `_ingested_at` | 적재 시각 |
# MAGIC
# MAGIC **예상 결과:** 결과 없이 끝납니다.

# COMMAND ----------
from pyspark.sql import Window
from pyspark.sql import functions as F

bronze_tables = {
    "sap/sap_material.csv": "bronze_sap_material",
    "sap/sap_supplier.csv": "bronze_sap_supplier",
    "sap/sap_purchase_receipt_2025-10_2026-09.csv": "bronze_sap_purchase_receipt",
    "sap/sap_purchase_order_open_2026Q4.csv": "bronze_sap_purchase_order_open",
    "sap/sap_sales_order_open_2026Q4.csv": "bronze_sap_sales_order",
    "fpims/fpims_line.csv": "bronze_fpims_line",
    "fpims/fpims_bunker.csv": "bronze_fpims_bunker",
    "fpims/fpims_product.csv": "bronze_fpims_product",
    "fpims/fpims_recipe.csv": "bronze_fpims_recipe",
    "fpims/fpims_bunker_transfer_route.csv": "bronze_fpims_transfer_route",
    "fpims/fpims_production_lot_2025-10_2026-09.csv": "bronze_fpims_production_lot",
    "fpims/fpims_material_consumption_2025-10_2026-09.csv": "bronze_fpims_material_consumption",
    "fpims/fpims_production_plan_2026Q4.csv": "bronze_fpims_production_plan",
    "pvss/pvss_bunker_level_2026-09.json": "bronze_pvss_bunker_level",
}


def read_raw(path):
    full_path = f"{raw_volume}/{path}"
    if path.endswith(".json"):
        df = spark.read.schema("bunker_id string, timestamp string, level_kg string").json(full_path)
    else:
        df = spark.read.option("header", True).csv(full_path)
    return (df.withColumn("_source_file", F.col("_metadata.file_path"))
              .withColumn("_order", F.monotonically_increasing_id())
              .withColumn("_source_row", F.row_number().over(Window.orderBy("_order")))
              .drop("_order")
              .withColumn("_ingested_at", F.current_timestamp()))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Bronze 테이블 만들기
# MAGIC 파일마다 Delta 테이블로 저장합니다. 다시 실행하면 테이블을 덮어씁니다.
# MAGIC
# MAGIC **예상 결과:** 표 14행, 합계 `43,410행`. 02에서 만든 파일의 행 수와 같습니다. (1~2분)

# COMMAND ----------
loaded = []
for path, table in bronze_tables.items():
    df = read_raw(path)
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(table)
    loaded.append((table, path, spark.table(table).count()))

display(spark.createDataFrame(loaded, "`Bronze 테이블` string, `원천 파일` string, `행 수` long"))
print(f"합계: {sum(rows for _, _, rows in loaded):,}행")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 원본 그대로인지 확인
# MAGIC `bronze_sap_purchase_order_open`에서 `BNK-L3-2`의 10월 입고 예정을 봅니다. 02에서 본 파일 내용과 같아야 합니다.
# MAGIC
# MAGIC **예상 결과:** 6행. 10월 2일 줄은 여전히 `50` `TO`이고, 10월 9일 `00020` 줄이 두 번 있습니다.
# MAGIC `_source_row`로 원천 파일의 몇 번째 행인지 알 수 있습니다.

# COMMAND ----------
display(spark.table("bronze_sap_purchase_order_open")
        .filter("bunker_id = 'BNK-L3-2' AND promised_date < '20261101'")
        .select("purchase_order_id", "po_line_no", "promised_date", "quantity", "unit", "_source_row", "_ingested_at")
        .orderBy("_source_row"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. 열 형식 확인
# MAGIC Bronze는 형식을 바꾸지 않으므로 날짜와 수량도 문자(`string`)입니다. 04 Silver에서 날짜·숫자 형식으로 바꿉니다.
# MAGIC
# MAGIC **예상 결과:** 9행. `plan_date`, `planned_output_kg`가 `string`입니다.

# COMMAND ----------
display(spark.sql("DESCRIBE TABLE bronze_fpims_production_plan"))
