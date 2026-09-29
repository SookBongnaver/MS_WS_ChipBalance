# Databricks notebook source
# MAGIC %md
# MAGIC # 03. Bronze와 Silver
# MAGIC * **Bronze:** 원본 파일을 그대로 테이블에 넣고 파일 경로·적재 시각을 붙입니다.
# MAGIC * **Silver:** 중복을 지우고 결측 행을 격리한 뒤 날짜·수량 형식을 바꿉니다.
# MAGIC
# MAGIC 테이블은 모두 본인 스키마(`lab_factory.lab_p001`)에 저장됩니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Bronze 적재
# MAGIC 02에서 저장한 JSON 파일을 읽어 `chip_bronze_*` 테이블 6개로 저장합니다.
# MAGIC `_source_file`은 원본 파일 경로, `_ingested_at`은 적재 시각입니다.
# MAGIC
# MAGIC **예상 결과:** 테이블별 행 수 2·2·2·2·60·5와 입고예정 5행이 표시됩니다. 중복·결측은 아직 그대로입니다.

# COMMAND ----------
bronze_counts = []
for name, columns in RAW_COLUMNS.items():
    schema_ddl = ", ".join(f"{c} STRING" for c in columns)
    bronze = (spark.read.schema(schema_ddl).json(f"{raw_dir}/{name}")
              .select("*", F.col("_metadata.file_path").alias("_source_file"))
              .withColumn("_ingested_at", F.current_timestamp()))
    bronze_counts.append((f"chip_bronze_{name}", save_uc_table(bronze, f"chip_bronze_{name}")))
display(spark.createDataFrame(bronze_counts, "table_name STRING, row_count BIGINT"))
display(spark.table(uc_table("chip_bronze_receipts")).orderBy("receipt_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 입고예정 정리
# MAGIC 1. 모든 열이 같은 행은 하나만 남깁니다. → `R-A-12` 중복 1행 제거
# MAGIC 2. 수량이 비었거나 숫자가 아닌 행은 격리 테이블로 보냅니다. → `R-A-08` 1행 격리
# MAGIC
# MAGIC **예상 결과:** 제거한 중복 1행, 격리 1행(`R-A-08`), 유효 입고 3행이 표시됩니다.

# COMMAND ----------
receipts_bronze = spark.table(uc_table("chip_bronze_receipts")).select(*RAW_COLUMNS["receipts"])
receipts_unique = receipts_bronze.dropDuplicates()
duplicates_removed = receipts_bronze.count() - receipts_unique.count()

qty = F.expr(f"try_cast(received_qty_kg AS {QTY})")
receipts_bad = (receipts_unique.filter(qty.isNull() | (qty < 0))
                .withColumn("reason", F.lit("수량이 비었거나 올바른 숫자가 아님")))
receipts_ok = receipts_unique.filter(qty.isNotNull() & (qty >= 0))

print("제거한 중복 행:", duplicates_removed)
display(receipts_bad)
display(receipts_ok.orderBy("business_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 형식 바꾸기
# MAGIC 문자열을 계산할 수 있는 형식으로 바꿉니다.
# MAGIC * 날짜 → DATE
# MAGIC * 수량(kg) → DECIMAL(18,3)
# MAGIC * 제품 1kg당 Chip 소요량 → DECIMAL(18,6)
# MAGIC
# MAGIC **예상 결과:** 입고예정의 열 형식이 표시됩니다. `business_date`는 date, `received_qty_kg`는 decimal(18,3)입니다.

# COMMAND ----------
def typed(df):
    columns = []
    for column in df.columns:
        if column == "business_date":
            columns.append(F.to_date(column).alias(column))
        elif column == "kg_per_kg":
            columns.append(F.col(column).cast("DECIMAL(18,6)").alias(column))
        elif column.endswith("_kg"):
            columns.append(F.col(column).cast(QTY).alias(column))
        else:
            columns.append(F.col(column))
    return df.select(*columns)


silver = {name: typed(spark.table(uc_table(f"chip_bronze_{name}")).select(*RAW_COLUMNS[name]))
          for name in RAW_COLUMNS if name != "receipts"}
silver["receipts"] = typed(receipts_ok)
silver["receipts"].printSchema()

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 기준 정보 확인
# MAGIC 계산 전에 연결 관계를 확인합니다. 문제가 있으면 여기서 멈춥니다.
# MAGIC * 모든 Bunker의 원료가 원료 목록에 있어야 합니다.
# MAGIC * 모든 제품에 소요량 기준이 있어야 합니다.
# MAGIC * 입고예정의 원료·Bunker 조합이 Bunker 목록과 맞아야 합니다.
# MAGIC
# MAGIC **예상 결과:** `기준 정보 확인 완료`

# COMMAND ----------
checks = {
    "Bunker 원료가 원료 목록에 없음": silver["bunkers"].join(silver["materials"], "material_id", "left_anti"),
    "소요량 기준이 없는 제품": silver["plans"].join(silver["recipes"], "product_id", "left_anti"),
    "Bunker와 맞지 않는 입고": silver["receipts"].join(
        silver["bunkers"].select("material_id", "bunker_id"), ["material_id", "bunker_id"], "left_anti"),
}
for message, bad_rows in checks.items():
    if bad_rows.count() > 0:
        display(bad_rows)
        raise ValueError(message)
print("기준 정보 확인 완료")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Silver 저장
# MAGIC 정리한 여섯 테이블과 격리 테이블을 `chip_silver_*`로 저장합니다. 다시 실행하면 같은 결과로 덮어씁니다.
# MAGIC
# MAGIC **예상 결과:** materials 2, bunkers 2, opening 2, recipes 2, plans 60, receipts 3, quarantine 1

# COMMAND ----------
silver_counts = [(f"chip_silver_{name}", save_uc_table(df, f"chip_silver_{name}")) for name, df in silver.items()]
silver_counts.append(("chip_silver_quarantine", save_uc_table(receipts_bad, "chip_silver_quarantine")))
display(spark.createDataFrame(silver_counts, "table_name STRING, row_count BIGINT"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 다음 단계
# MAGIC `04_gold_baseline`을 엽니다. Silver로 날짜별 원료 Balance를 계산해 Fabric OneLake에 저장합니다.
