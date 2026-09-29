# Databricks notebook source
# MAGIC %md
# MAGIC # 02. 원본 데이터 만들기
# MAGIC 실제 FPIMS·PVSS·SAP에 연결하지 않고, 이 Notebook에서 2026년 9월 교육용 데이터를 만듭니다.
# MAGIC 만든 데이터는 Unity Catalog Volume에 JSON 파일로 저장하고, 다음 `03_bronze_silver`에서 읽습니다.
# MAGIC
# MAGIC | 원본 | 내용 | 행 수 |
# MAGIC |---|---|---|
# MAGIC | materials | 원료 Chip | 2 |
# MAGIC | bunkers | 원료를 보관하는 Bunker, 용량·안전재고 | 2 |
# MAGIC | opening | 9월 1일 시작 재고 | 2 |
# MAGIC | recipes | 제품 1kg 생산에 필요한 Chip kg | 2 |
# MAGIC | plans | 일별 제품 생산계획 | 60 |
# MAGIC | receipts | 원료 입고예정 (정제 연습용 오류 포함) | 5 |

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 원료·Bunker·시작 재고·소요량 기준
# MAGIC * CHIP-A는 BNK-A에, CHIP-B는 BNK-B에 보관합니다. 두 Bunker 모두 용량 3,000kg, 안전재고 200kg입니다.
# MAGIC * FILM-A 1kg에는 CHIP-A 1kg, FILM-B 1kg에는 CHIP-B 1.25kg이 들어갑니다.
# MAGIC
# MAGIC **예상 결과:** 표 네 개가 차례로 표시됩니다.

# COMMAND ----------
materials = [
    {"material_id": "CHIP-A", "material_name": "Chip A", "unit": "kg"},
    {"material_id": "CHIP-B", "material_name": "Chip B", "unit": "kg"},
]
bunkers = [
    {"bunker_id": "BNK-A", "bunker_name": "Bunker A", "material_id": "CHIP-A",
     "capacity_kg": "3000", "safety_stock_kg": "200"},
    {"bunker_id": "BNK-B", "bunker_name": "Bunker B", "material_id": "CHIP-B",
     "capacity_kg": "3000", "safety_stock_kg": "200"},
]
opening = [
    {"material_id": "CHIP-A", "bunker_id": "BNK-A", "business_date": "2026-09-01", "opening_qty_kg": "1000"},
    {"material_id": "CHIP-B", "bunker_id": "BNK-B", "business_date": "2026-09-01", "opening_qty_kg": "1000"},
]
recipes = [
    {"product_id": "FILM-A", "material_id": "CHIP-A", "bunker_id": "BNK-A", "kg_per_kg": "1.0"},
    {"product_id": "FILM-B", "material_id": "CHIP-B", "bunker_id": "BNK-B", "kg_per_kg": "1.25"},
]
for rows in (materials, bunkers, opening, recipes):
    display(spark.createDataFrame(rows))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 생산계획
# MAGIC 9월 1일~30일 매일 FILM-A 100kg, FILM-B 40kg을 생산합니다. 30일 × 제품 2개 = 60행입니다.
# MAGIC
# MAGIC **예상 결과:** 9월 1일과 5일의 계획 4행이 표시됩니다.

# COMMAND ----------
from datetime import timedelta

plans = []
for day in range(30):
    business_date = (START_DATE + timedelta(days=day)).isoformat()
    for product_id, qty in (("FILM-A", "100"), ("FILM-B", "40")):
        plans.append({"plan_id": f"P-{product_id}-{business_date}", "product_id": product_id,
                      "business_date": business_date, "planned_output_kg": qty})
print("생산계획 행 수:", len(plans))
display(spark.createDataFrame(plans).filter("business_date IN ('2026-09-01', '2026-09-05')"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 입고예정 — 오류 두 건 포함
# MAGIC 정상 입고는 CHIP-A 9/12·9/22, CHIP-B 9/15에 각각 1,000kg입니다.
# MAGIC 실제 시스템 데이터처럼 오류 두 건을 넣었습니다. 03 Notebook에서 정리합니다.
# MAGIC * `R-A-12`가 두 번 들어 있습니다. (중복)
# MAGIC * `R-A-08`은 수량이 비어 있습니다. (결측)
# MAGIC
# MAGIC **예상 결과:** 입고예정 5행이 표시됩니다.

# COMMAND ----------
receipts = [
    {"receipt_id": "R-A-12", "material_id": "CHIP-A", "bunker_id": "BNK-A",
     "business_date": "2026-09-12", "received_qty_kg": "1000"},
    {"receipt_id": "R-A-22", "material_id": "CHIP-A", "bunker_id": "BNK-A",
     "business_date": "2026-09-22", "received_qty_kg": "1000"},
    {"receipt_id": "R-B-15", "material_id": "CHIP-B", "bunker_id": "BNK-B",
     "business_date": "2026-09-15", "received_qty_kg": "1000"},
    {"receipt_id": "R-A-12", "material_id": "CHIP-A", "bunker_id": "BNK-A",
     "business_date": "2026-09-12", "received_qty_kg": "1000"},
    {"receipt_id": "R-A-08", "material_id": "CHIP-A", "bunker_id": "BNK-A",
     "business_date": "2026-09-08", "received_qty_kg": None},
]
display(spark.createDataFrame(receipts, ", ".join(f"{c} STRING" for c in RAW_COLUMNS["receipts"])))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Volume에 원본 파일 저장
# MAGIC 여섯 원본을 모두 문자열로 저장합니다. 실제 시스템에서 받은 파일처럼 형식 변환은 아직 하지 않습니다.
# MAGIC 다시 실행하면 같은 내용으로 덮어씁니다.
# MAGIC
# MAGIC **예상 결과:** 원본별 저장 경로와 행 수(2·2·2·2·60·5)가 표시됩니다.

# COMMAND ----------
sources = {"materials": materials, "bunkers": bunkers, "opening": opening,
           "recipes": recipes, "plans": plans, "receipts": receipts}
saved = []
for name, rows in sources.items():
    schema_ddl = ", ".join(f"{c} STRING" for c in RAW_COLUMNS[name])
    path = f"{raw_dir}/{name}"
    spark.createDataFrame(rows, schema_ddl).coalesce(1).write.mode("overwrite").json(path)
    saved.append((name, path, spark.read.schema(schema_ddl).json(path).count()))
display(spark.createDataFrame(saved, "source STRING, path STRING, row_count BIGINT"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 다음 단계
# MAGIC `03_bronze_silver`를 엽니다. 저장한 파일을 Bronze로 읽고, 중복·결측을 정리해 Silver를 만듭니다.
