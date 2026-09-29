# Databricks notebook source
# MAGIC %md
# MAGIC # 02. 원천 데이터 확인
# MAGIC `raw` Volume에 올린 SAP·FPIMS·PVSS 파일 14개를 읽어 내용과 관계를 확인합니다. 테이블은 만들지 않습니다.
# MAGIC
# MAGIC 1. 02장 2단계에서 파일 14개를 올렸는지 확인합니다.
# MAGIC 2. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 3. 마지막 셀까지 확인하면 `03_bronze_silver`를 엽니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정 불러오기
# MAGIC `01_setup`의 설정값과 함수를 불러옵니다.
# MAGIC
# MAGIC **예상 결과:** 01에서 본 결과가 다시 표시되고, `원천 파일 Volume` 뒤에 `(파일 14개)`가 나옵니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 파일 14개 확인
# MAGIC 파일마다 행 수를 세어 추출할 때의 행 수와 비교합니다.
# MAGIC
# MAGIC **예상 결과:** 표 14행, `확인` 열이 모두 `OK`, 합계 `41,412행`

# COMMAND ----------
from pyspark.sql import functions as F

source_files = [
    ("SAP", "sap_material.csv", "원료 Chip과 단가", 12),
    ("SAP", "sap_supplier.csv", "공급사 (리드타임, 발주 단위)", 6),
    ("SAP", "sap_purchase_receipt_2025-10_2026-09.csv", "원료 입고 실적 (약속일, 실제 입고일)", 1900),
    ("SAP", "sap_purchase_order_open_2026Q4.csv", "미결 발주 = 4분기 입고 예정", 735),
    ("SAP", "sap_sales_order_open_2026Q4.csv", "판매오더 (제품, 수량, 납기)", 360),
    ("FPIMS", "fpims_line.csv", "생산 라인", 6),
    ("FPIMS", "fpims_bunker.csv", "Bunker (용량, 안전재고, 보관 원료)", 24),
    ("FPIMS", "fpims_product.csv", "제품", 30),
    ("FPIMS", "fpims_recipe.csv", "제품별 원료 소요량 기준", 118),
    ("FPIMS", "fpims_bunker_transfer_route.csv", "Bunker 간 이송 경로", 12),
    ("FPIMS", "fpims_production_lot_2025-10_2026-09.csv", "생산 Lot 실적", 4132),
    ("FPIMS", "fpims_material_consumption_2025-10_2026-09.csv", "Lot별 원료 투입 실적", 16252),
    ("FPIMS", "fpims_production_plan_2026Q4.csv", "4분기 생산계획", 547),
    ("PVSS", "pvss_bunker_level_2026-09.json", "Bunker 레벨 센서 (1시간 간격)", 17278),
]


def read_source(name):
    path = f"{raw_volume}/{name}"
    if name.endswith(".json"):
        return spark.read.json(path)
    return spark.read.option("header", True).csv(path)


uploaded = {f.name for f in dbutils.fs.ls(raw_volume)}
missing = [name for _, name, _, _ in source_files if name not in uploaded]
if missing:
    raise FileNotFoundError("Volume에 없는 파일: " + ", ".join(missing) + " — 02장 2단계에서 다시 올립니다.")

checks = [(system, name, description, read_source(name).count(), expected)
          for system, name, description, expected in source_files]
display(spark.createDataFrame(checks, "`시스템` string, `파일` string, `내용` string, `행 수` long, `추출 행 수` long")
        .withColumn("확인", F.when(F.col("행 수") == F.col("추출 행 수"), "OK").otherwise("다름")))
print(f"합계: {sum(rows for _, _, _, rows, _ in checks):,}행")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 라인과 Bunker
# MAGIC 원천: FPIMS `fpims_bunker`
# MAGIC
# MAGIC 라인마다 Bunker가 4개 있고, Bunker 하나에는 원료 Chip 한 종류만 보관합니다.
# MAGIC 같은 원료를 보관하는 Bunker끼리는 이송 경로가 있으면 원료를 옮길 수 있습니다.
# MAGIC
# MAGIC **예상 결과:** 6행. L1과 L3의 Bunker 2(`BNK-L1-2`, `BNK-L3-2`)가 모두 `PET-SD`를 보관합니다.

# COMMAND ----------
bunkers = read_source("fpims_bunker.csv")
display(bunkers
        .withColumn("slot", F.concat(F.lit("Bunker "), F.substring("bunker_id", -1, 1)))
        .groupBy("line_id").pivot("slot").agg(F.first("material_id"))
        .orderBy("line_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 제품별 원료 소요량 기준
# MAGIC 원천: FPIMS `fpims_recipe` (단위 kg/kg)
# MAGIC
# MAGIC 제품 1kg을 만들 때 원료 Chip이 몇 kg 드는지 FPIMS에 등록된 표준값입니다.
# MAGIC 04장에서는 1년 동안의 실제 투입 실적으로 실제 소요량 기준을 다시 구합니다.
# MAGIC
# MAGIC **예상 결과:** L3 제품 5행. 긴급 오더 제품 `P-L3-05`는 PET-SD가 `0.600`으로, 다른 L3 제품(0.095~0.150)보다 4배 이상 많습니다.
# MAGIC `P-L3-05`는 MB-SL·MB-UV를 쓰지 않아 `null`로 보입니다.

# COMMAND ----------
recipes = read_source("fpims_recipe.csv")
display(recipes.filter("line_id = 'L3'")
        .groupBy("product_id").pivot("material_id").agg(F.first("std_kg_per_kg"))
        .orderBy("product_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. L3 생산계획과 PET-SD 소요량
# MAGIC 원천: FPIMS `fpims_production_plan_2026Q4`
# MAGIC
# MAGIC 10월 1~16일 L3 생산계획입니다.
# MAGIC `pet_sd_std_kg`는 생산량 × PET-SD 표준 소요량으로, 그날 `BNK-L3-2`에서 빠져나갈 PET-SD 양입니다.
# MAGIC
# MAGIC **예상 결과:** 11행. 10월 2일은 `P-L3-05`를 생산해 PET-SD를 29,760kg 씁니다.
# MAGIC 10월 10일 다음 날짜가 10월 16일입니다. 10월 11~15일은 계획이 없는 예비일이며, 07장에서 긴급 오더 때문에 밀린 생산을 이 날짜로 옮깁니다.

# COMMAND ----------
pet_sd = recipes.filter("material_id = 'PET-SD'").select("product_id", F.col("std_kg_per_kg").cast("double").alias("pet_sd_kg_per_kg"))
display(read_source("fpims_production_plan_2026Q4.csv")
        .filter("line_id = 'L3' AND plan_date BETWEEN '20261001' AND '20261016'")
        .join(pet_sd, "product_id")
        .select("plan_date", "product_id", F.col("planned_output_kg").cast("long").alias("planned_output_kg"), "sales_order_id",
                F.round(F.col("planned_output_kg") * F.col("pet_sd_kg_per_kg")).cast("long").alias("pet_sd_std_kg"))
        .orderBy("plan_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. BNK-L3-2 입고 예정
# MAGIC 원천: SAP `sap_purchase_order_open_2026Q4`
# MAGIC
# MAGIC SAP 미결 발주 가운데 10월에 `BNK-L3-2`로 들어올 PET-SD입니다.
# MAGIC 실제 입고일은 약속일(`promised_date`)에 공급사의 평균 입고 지연일을 더해 04장에서 계산합니다.
# MAGIC
# MAGIC **예상 결과:** 6행. 첫 입고는 10월 7일 `POQ4-0339` 50,000kg (`SUP-PET-B`)입니다.

# COMMAND ----------
display(read_source("sap_purchase_order_open_2026Q4.csv")
        .filter("bunker_id = 'BNK-L3-2' AND promised_date < '20261101'")
        .orderBy("promised_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Bunker 간 이송 경로
# MAGIC 원천: FPIMS `fpims_bunker_transfer_route`
# MAGIC
# MAGIC 같은 원료를 보관하는 Bunker 사이에 원료를 옮길 수 있는 경로와 하루 한도입니다.
# MAGIC
# MAGIC **예상 결과:** 2행. `R-01`은 `BNK-L1-2`에서 `BNK-L3-2`로 하루 40,000kg까지, 1일 걸려, kg당 25원에 옮깁니다.

# COMMAND ----------
display(read_source("fpims_bunker_transfer_route.csv")
        .filter("material_id = 'PET-SD'")
        .orderBy("route_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. 레벨 센서와 시작 재고
# MAGIC 원천: PVSS `pvss_bunker_level_2026-09` (JSON Lines, 한국 시간)
# MAGIC
# MAGIC PVSS 센서는 Bunker 재고(kg)를 1시간마다 기록합니다.
# MAGIC 9월 30일 마지막 정상값을 10월 1일 시작 재고로 씁니다.
# MAGIC
# MAGIC **예상 결과:** 6행. `BNK-L3-2`의 9월 30일 23시 값은 106,000kg입니다.

# COMMAND ----------
display(read_source("pvss_bunker_level_2026-09.json")
        .filter("bunker_id = 'BNK-L3-2' AND timestamp >= '2026-09-30T18:00'")
        .select("bunker_id", F.substring("timestamp", 1, 19).alias("timestamp"), "level_kg")
        .orderBy("timestamp"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. 품질 이슈 미리 보기
# MAGIC 원천 파일에는 그대로 계산하면 결과가 틀어지는 행이 있습니다.
# MAGIC 03장에서 Silver를 만들 때 이 행을 고치거나 따로 격리합니다.
# MAGIC
# MAGIC **예상 결과:** 7행. 발주 중복 5, 수량 없음 4, 단위 TO 8, 미등록 원료 3, 센서 범위 초과 6, 센서 중복 5, 센서 누락 7

# COMMAND ----------
open_po = read_source("sap_purchase_order_open_2026Q4.csv")
sensor = read_source("pvss_bunker_level_2026-09.json")
materials = read_source("sap_material.csv")


def extra_rows(df, keys):
    return df.groupBy(*keys).count().filter("count > 1").agg(F.sum(F.col("count") - 1)).first()[0] or 0


expected_hours = bunkers.count() * 30 * 24
issues = [
    ("SAP 미결 발주", "발주 번호·항목 중복", extra_rows(open_po, ["purchase_order_id", "po_line_no"]), "중복분 격리"),
    ("SAP 미결 발주", "수량 없음", open_po.filter("quantity IS NULL").count(), "격리"),
    ("SAP 미결 발주", "단위 TO(톤)", open_po.filter("unit = 'TO'").count(), "kg으로 환산"),
    ("SAP 미결 발주", "미등록 원료", open_po.join(materials, "material_id", "left_anti").count(), "격리"),
    ("PVSS 센서", "범위 초과 (0 미만, 용량 초과)", sensor.join(bunkers.select("bunker_id", "capacity_kg"), "bunker_id")
        .filter("level_kg < 0 OR level_kg > CAST(capacity_kg AS BIGINT)").count(), "격리"),
    ("PVSS 센서", "Bunker·시각 중복", extra_rows(sensor, ["bunker_id", "timestamp"]), "중복분 격리"),
    ("PVSS 센서", "기록 누락 시간", expected_hours - sensor.select("bunker_id", "timestamp").distinct().count(), "품질 지표로 기록"),
]
display(spark.createDataFrame(issues, "`원천` string, `이슈` string, `건수` long, `03장 처리` string"))
