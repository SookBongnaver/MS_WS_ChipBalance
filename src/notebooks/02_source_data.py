# Databricks notebook source
# MAGIC %md
# MAGIC # 02. 원천 데이터 만들기
# MAGIC SAP·FPIMS·PVSS에서 추출한 것과 같은 형식의 파일 14개를 `raw` Volume에 만들고, 내용과 관계를 확인합니다.
# MAGIC 이 파일이 메달리온 아키텍처의 시작점입니다. 03 Bronze가 이 파일을 그대로 읽습니다.
# MAGIC
# MAGIC 1. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 2. 마지막 셀까지 확인하면 `03_bronze`를 엽니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정과 생성기 불러오기
# MAGIC `01_setup`의 설정값과 `source_systems`의 데이터 생성 함수를 불러옵니다.
# MAGIC
# MAGIC **예상 결과:** 01에서 본 결과가 다시 표시되고, 다음 셀은 결과 없이 끝납니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
# MAGIC %run ./source_systems

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 원천 파일 만들기
# MAGIC `raw` Volume 아래 `sap`, `fpims`, `pvss` 폴더에 파일을 만듭니다. 다시 실행하면 같은 내용으로 새로 만듭니다.
# MAGIC
# MAGIC | 시스템 | 하는 일 | 파일 |
# MAGIC |---|---|---|
# MAGIC | SAP | 구매·판매 | 원료, 공급사, 입고 실적, 입고 예정 발주, 판매오더 |
# MAGIC | FPIMS | 생산 관리 | 라인, Bunker, 제품, 레시피, 이송 경로, 생산 Lot, 원료 사용, 생산계획 |
# MAGIC | PVSS | 설비 센서 | Bunker 레벨 (1시간 간격, JSON) |
# MAGIC
# MAGIC **예상 결과:** 표 14행, 합계 `43,410행` (1분 안쪽)

# COMMAND ----------
import shutil

from pyspark.sql import functions as F

for folder in ("sap", "fpims", "pvss"):
    shutil.rmtree(f"{raw_volume}/{folder}", ignore_errors=True)
counts = generate_all(raw_volume)

descriptions = {
    "sap_material": "원료 Chip과 단가",
    "sap_supplier": "공급사 리드타임, 발주 단위, 긴급 비용",
    "sap_purchase_receipt_2025-10_2026-09": "1년 입고 실적",
    "sap_purchase_order_open_2026Q4": "4분기 입고 예정 (미결 발주)",
    "sap_sales_order_open_2026Q4": "4분기 판매오더",
    "fpims_line": "생산 라인",
    "fpims_bunker": "Bunker 용량, 안전재고, 보관 원료",
    "fpims_product": "제품",
    "fpims_recipe": "제품별 원료 표준 소요량",
    "fpims_bunker_transfer_route": "Bunker 간 이송 경로",
    "fpims_production_lot_2025-10_2026-09": "1년 생산 Lot 실적",
    "fpims_material_consumption_2025-10_2026-09": "Lot별 원료 사용 실적",
    "fpims_production_plan_2026Q4": "4분기 생산계획",
    "pvss_bunker_level_2026-09": "9월 Bunker 레벨 센서",
}
files = [(path.split("/")[0].upper(), path, descriptions[path.split("/")[1].rsplit(".", 1)[0]], rows) for path, rows in counts.items()]
display(spark.createDataFrame(files, "`시스템` string, `파일` string, `내용` string, `행 수` long"))
print(f"합계: {sum(counts.values()):,}행")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 파일 사이의 관계
# MAGIC Chip Balance는 Bunker마다 날짜별로 **시작 재고 + 입고 예정 − 생산계획이 쓸 원료**를 계산합니다.
# MAGIC 이 계산에 필요한 파일은 아래 키로 이어집니다.
# MAGIC
# MAGIC | 연결 | 키 | 의미 |
# MAGIC |---|---|---|
# MAGIC | 라인 → Bunker | `line_id` | 라인마다 Bunker 4개. Bunker 하나에는 원료 한 종류만 보관합니다. |
# MAGIC | 원료 → Bunker | `material_id` | 같은 원료를 여러 라인의 Bunker가 보관합니다. |
# MAGIC | 제품 → 레시피 → 원료 | `product_id`, `material_id` | 제품 1kg에 드는 원료 kg |
# MAGIC | 생산계획 → 라인·제품 | `line_id`, `product_id` | 날짜별 생산량 × 레시피 = 그날 Bunker에서 빠질 원료 |
# MAGIC | 생산계획 → 판매오더 | `sales_order_id` | 그 생산이 어느 고객 주문을 채우는지 |
# MAGIC | 발주 → Bunker | `bunker_id` | 입고 예정 원료가 들어갈 Bunker |
# MAGIC | 센서 → Bunker | `bunker_id` | 9월 30일 23시 레벨 = 10월 1일 시작 재고 |
# MAGIC | 생산 Lot → 원료 사용 | `lot_id` | 실제 사용량으로 실제 소요량(손실 포함)을 구합니다. |
# MAGIC
# MAGIC 아래 셀에서 파일을 읽는 함수를 만듭니다. 원본 그대로 보기 위해 모든 열을 문자로 읽습니다.
# MAGIC
# MAGIC **예상 결과:** 결과 없이 끝납니다.

# COMMAND ----------
def read_raw(path):
    full_path = f"{raw_volume}/{path}"
    if path.endswith(".json"):
        return spark.read.schema("bunker_id string, timestamp string, level_kg string").json(full_path)
    return spark.read.option("header", True).csv(full_path)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 라인과 Bunker
# MAGIC 원천: FPIMS `fpims_bunker`
# MAGIC
# MAGIC 라인 6개에 Bunker가 4개씩 있습니다. L1–L4는 BOPET 필름, L5–L6은 BOPA(나일론) 필름 라인입니다.
# MAGIC
# MAGIC **예상 결과:** 6행. L1과 L3의 Bunker 2(`BNK-L1-2`, `BNK-L3-2`)가 모두 `PET-SD`를 보관합니다.

# COMMAND ----------
display(read_raw("fpims/fpims_bunker.csv")
        .withColumn("slot", F.concat(F.lit("Bunker "), F.substring("bunker_id", -1, 1)))
        .groupBy("line_id").pivot("slot").agg(F.first("material_id"))
        .orderBy("line_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. L3 제품의 레시피
# MAGIC 원천: FPIMS `fpims_recipe` (단위 kg/kg)
# MAGIC
# MAGIC 제품 1kg을 만들 때 드는 원료 Chip의 표준량입니다.
# MAGIC
# MAGIC **예상 결과:** 5행. `P-L3-05`(반광택 75μm 후막)는 PET-SD가 `0.450`으로 다른 L3 제품(0.095–0.150)보다 3배 이상 많고,
# MAGIC MB-SL·MB-UV를 쓰지 않아 `null`로 보입니다.

# COMMAND ----------
display(read_raw("fpims/fpims_recipe.csv")
        .filter("line_id = 'L3'")
        .groupBy("product_id").pivot("material_id", ["PET-BR", "PET-SD", "MB-SL", "MB-UV"]).agg(F.first("std_kg_per_kg"))
        .orderBy("product_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. 생산 실적: Lot과 원료 사용
# MAGIC 원천: FPIMS `fpims_production_lot`, `fpims_material_consumption`
# MAGIC
# MAGIC 라인은 주간(08–20시)과 야간(20–08시) Lot으로 생산합니다. Lot마다 Bunker에서 원료를 꺼내 쓴 양이 기록됩니다.
# MAGIC 9월 30일 L3 주간 Lot `L3-260930-D`를 봅니다.
# MAGIC
# MAGIC **예상 결과:** 4행. 제품 `P-L3-01`을 24,564kg 생산하면서 PET-SD를 3,031kg 썼습니다.
# MAGIC 레시피 기준(24,564 × 0.120 = 2,948kg)보다 조금 많습니다. 이 차이가 실제 손실이며 05 Gold에서 계산합니다.

# COMMAND ----------
lot = read_raw("fpims/fpims_production_lot_2025-10_2026-09.csv").filter("lot_id = 'L3-260930-D'")
display(read_raw("fpims/fpims_material_consumption_2025-10_2026-09.csv")
        .join(lot.select("lot_id", "product_id", "start_ts", "end_ts", "output_kg"), "lot_id")
        .select("lot_id", "product_id", "start_ts", "end_ts", "output_kg", "bunker_id", "material_id", "consumed_kg")
        .orderBy("bunker_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. L3 생산계획과 판매오더
# MAGIC 원천: FPIMS `fpims_production_plan_2026Q4`, SAP `sap_sales_order_open_2026Q4`
# MAGIC
# MAGIC 10월 1–16일 L3 생산계획에 판매오더의 고객과 납기를 붙여 봅니다. 같은 제품을 며칠씩 이어서 생산하고, 판매오더 하나를 1–3일에 나눠 채웁니다.
# MAGIC
# MAGIC **예상 결과:** 11행. 10월 10일 다음 계획이 10월 16일입니다. 10월 11–15일은 계획이 없는 예비일입니다.
# MAGIC 모든 행에서 생산일이 납기(`due_date`)보다 앞섭니다.

# COMMAND ----------
display(read_raw("fpims/fpims_production_plan_2026Q4.csv")
        .filter("line_id = 'L3' AND plan_date BETWEEN '20261001' AND '20261016'")
        .join(read_raw("sap/sap_sales_order_open_2026Q4.csv").drop("product_id"), "sales_order_id")
        .select("plan_date", "product_id", "planned_output_kg", "sales_order_id", "customer_name", "order_qty_kg", "due_date")
        .orderBy("plan_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. BNK-L3-2 입고 예정
# MAGIC 원천: SAP `sap_purchase_order_open_2026Q4`
# MAGIC
# MAGIC 10월에 `BNK-L3-2`로 들어올 PET-SD 발주입니다. 공급사 세미폴리머(`SUP-PET-B`)는 금요일마다 납품합니다.
# MAGIC
# MAGIC **예상 결과:** 6행. 10월 2일 줄은 수량이 `50`, 단위가 `TO`(톤)입니다.
# MAGIC 10월 9일 `4500010294`-`00020` 줄은 두 번 나옵니다. 04 Silver에서 톤은 kg으로 바꾸고, 중복은 한 줄만 남깁니다.

# COMMAND ----------
display(read_raw("sap/sap_purchase_order_open_2026Q4.csv")
        .filter("bunker_id = 'BNK-L3-2' AND promised_date < '20261101'")
        .orderBy("promised_date", "po_line_no"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. Bunker 간 이송 경로
# MAGIC 원천: FPIMS `fpims_bunker_transfer_route`
# MAGIC
# MAGIC 같은 원료를 보관하는 Bunker 사이에는 원료를 옮기는 경로가 있습니다.
# MAGIC
# MAGIC **예상 결과:** 2행. `R-01`은 `BNK-L1-2`에서 `BNK-L3-2`로 하루 40,000kg까지 1일 걸려 옮기고, 비용은 kg당 25원입니다.

# COMMAND ----------
display(read_raw("fpims/fpims_bunker_transfer_route.csv")
        .filter("material_id = 'PET-SD'")
        .orderBy("route_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 10. 레벨 센서와 시작 재고
# MAGIC 원천: PVSS `pvss_bunker_level_2026-09` (JSON Lines, 한국 시간)
# MAGIC
# MAGIC PVSS 센서는 Bunker 재고(kg)를 1시간마다 기록합니다. 9월 30일 23시 값이 10월 1일 시작 재고입니다.
# MAGIC
# MAGIC **예상 결과:** 6행. `BNK-L3-2`의 9월 30일 23시 값은 `30370`kg입니다.

# COMMAND ----------
display(read_raw("pvss/pvss_bunker_level_2026-09.json")
        .filter("bunker_id = 'BNK-L3-2' AND timestamp >= '2026-09-30T18:00'")
        .orderBy("timestamp"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 11. 정리가 필요한 행
# MAGIC 원천 파일에는 그대로 계산하면 결과가 틀어지는 행이 있습니다. 04 Silver에서 고치거나 따로 격리합니다.
# MAGIC
# MAGIC **예상 결과:** 7행. 단위 TO 8, 발주 중복 5, 수량 공란 4, 미등록 원료 3, 센서 범위 벗어남 6, 센서 중복 5, 센서 누락 7

# COMMAND ----------
open_po = read_raw("sap/sap_purchase_order_open_2026Q4.csv")
sensor = read_raw("pvss/pvss_bunker_level_2026-09.json")
materials = read_raw("sap/sap_material.csv")
bunkers = read_raw("fpims/fpims_bunker.csv")


def extra_rows(df, keys):
    return df.groupBy(*keys).count().filter("count > 1").agg(F.sum(F.col("count") - 1)).first()[0] or 0


expected_readings = bunkers.count() * 30 * 24
issues = [
    ("SAP 발주", "단위 TO(톤)", open_po.filter("unit = 'TO'").count(), "kg으로 바꿈"),
    ("SAP 발주", "발주 번호·항목 중복", extra_rows(open_po, ["purchase_order_id", "po_line_no"]), "중복 격리"),
    ("SAP 발주", "수량 공란", open_po.filter("quantity IS NULL").count(), "격리"),
    ("SAP 발주", "미등록 원료 코드", open_po.join(materials, "material_id", "left_anti").count(), "격리"),
    ("PVSS 센서", "0 미만 또는 용량 초과", sensor.join(bunkers.select("bunker_id", "capacity_kg"), "bunker_id")
        .filter("CAST(level_kg AS BIGINT) < 0 OR CAST(level_kg AS BIGINT) > CAST(capacity_kg AS BIGINT)").count(), "격리"),
    ("PVSS 센서", "Bunker·시각 중복", extra_rows(sensor, ["bunker_id", "timestamp"]), "중복 격리"),
    ("PVSS 센서", "기록 누락 시각", expected_readings - sensor.select("bunker_id", "timestamp").distinct().count(), "건수 기록"),
]
display(spark.createDataFrame(issues, "`원천` string, `문제` string, `건수` long, `04 Silver 처리` string"))
