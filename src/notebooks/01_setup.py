# Databricks notebook source
# MAGIC %md
# MAGIC # 01. 실습 설정
# MAGIC 02~05 Notebook은 맨 처음 `%run ./01_setup`으로 이 Notebook을 불러옵니다.
# MAGIC 여기에는 **설정값**과 **공통 함수**가 들어 있습니다.
# MAGIC
# MAGIC 1. 2번 셀의 설정값 네 개를 본인 값으로 바꿉니다.
# MAGIC 2. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 3. 마지막 셀에 `설정 확인 완료`가 나오면 `02_source_data`를 엽니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Compute 확인
# MAGIC 이 실습은 관리자가 배정한 **Classic Compute**에서 실행합니다.
# MAGIC 화면 오른쪽 위 Compute 선택 목록에 Serverless가 선택되어 있으면 배정받은 Compute로 바꿉니다.
# MAGIC
# MAGIC **예상 결과:** `Compute:` 뒤에 배정받은 Compute 이름이 표시됩니다.

# COMMAND ----------
import re

try:
    cluster_id = spark.conf.get("spark.databricks.clusterUsageTags.clusterId", "")
except Exception:
    cluster_id = ""
if not re.fullmatch(r"\d{4}-\d{6}-[A-Za-z0-9]+", cluster_id or ""):
    raise RuntimeError("오른쪽 위 Compute 목록에서 배정받은 Classic Compute를 선택한 뒤 다시 실행하세요.")
print("Compute:", spark.conf.get("spark.databricks.clusterUsageTags.clusterName", cluster_id))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 설정값 — 이 셀만 바꿉니다
# MAGIC | 변수 | 넣을 값 | 찾는 곳 |
# MAGIC |---|---|---|
# MAGIC | `participant` | 참가자 번호 (예: `p001`) | 관리자 안내 |
# MAGIC | `fabric_workspace_id` | Fabric 작업 영역 ID | Lakehouse 주소의 `groups/` 뒤 값 |
# MAGIC | `fabric_lakehouse_id` | Lakehouse ID | Lakehouse 주소의 `lakehouses/` 뒤 값 |
# MAGIC | `secret_scope` | OneLake 저장용 secret scope 이름 | 관리자 안내 |
# MAGIC
# MAGIC `catalog`는 관리자가 만든 Unity Catalog 이름이므로 바꾸지 않습니다.

# COMMAND ----------
participant = "p001"
fabric_workspace_id = "00000000-0000-0000-0000-000000000000"
fabric_lakehouse_id = "00000000-0000-0000-0000-000000000000"
secret_scope = "관리자에게-받은-이름"

catalog = "lab_factory"
schema = f"lab_{participant}"
raw_dir = f"/Volumes/{catalog}/{schema}/raw/chip_balance"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 설정값 검사
# MAGIC 빈 값이나 형식이 틀린 값이 있으면 무엇을 고칠지 알려 줍니다.
# MAGIC 이상이 없으면 이후 SQL이 본인 스키마(`lab_factory.lab_p001`)를 기본으로 사용하도록 지정합니다.

# COMMAND ----------
from uuid import UUID


def is_guid(value):
    try:
        return UUID(str(value)).int != 0
    except ValueError:
        return False


problems = []
if not re.fullmatch(r"p\d{3}", participant):
    problems.append("participant는 p001처럼 p와 숫자 세 자리입니다.")
if not is_guid(fabric_workspace_id):
    problems.append("fabric_workspace_id에 Fabric 작업 영역 ID를 넣으세요.")
if not is_guid(fabric_lakehouse_id):
    problems.append("fabric_lakehouse_id에 Lakehouse ID를 넣으세요.")
if not re.fullmatch(r"[A-Za-z0-9._-]+", secret_scope):
    problems.append("secret_scope에 관리자가 알려 준 이름을 넣으세요.")
if problems:
    raise ValueError("설정값을 확인하세요.\n" + "\n".join(problems))

spark.sql(f"USE CATALOG `{catalog}`")
spark.sql(f"USE SCHEMA `{schema}`")
spark.conf.set("spark.sql.session.timeZone", "Asia/Seoul")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 공통 값과 테이블 함수
# MAGIC * 계획 기간은 2026년 9월 1일~30일, 수량 단위는 kg입니다.
# MAGIC * `RAW_COLUMNS`: 원본 6종의 열 이름입니다.
# MAGIC * `save_uc_table`: Unity Catalog 테이블에 덮어써서 저장합니다. 다시 실행해도 결과가 같습니다.

# COMMAND ----------
from datetime import date
from decimal import Decimal
from pyspark.sql import Window
from pyspark.sql import functions as F

START_DATE = date(2026, 9, 1)
END_DATE = date(2026, 9, 30)
QTY = "DECIMAL(18,3)"

RAW_COLUMNS = {
    "materials": ["material_id", "material_name", "unit"],
    "bunkers": ["bunker_id", "bunker_name", "material_id", "capacity_kg", "safety_stock_kg"],
    "opening": ["material_id", "bunker_id", "business_date", "opening_qty_kg"],
    "recipes": ["product_id", "material_id", "bunker_id", "kg_per_kg"],
    "plans": ["plan_id", "product_id", "business_date", "planned_output_kg"],
    "receipts": ["receipt_id", "material_id", "bunker_id", "business_date", "received_qty_kg"],
}


def uc_table(name):
    return f"`{catalog}`.`{schema}`.`{name}`"


def save_uc_table(df, name):
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(uc_table(name))
    return spark.table(uc_table(name)).count()


def read_silver():
    return {name: spark.table(uc_table(f"chip_silver_{name}")) for name in RAW_COLUMNS}

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Gold 테이블 형식
# MAGIC Fabric Lakehouse에 저장할 Gold 테이블 9개의 열입니다.
# MAGIC 계산은 Silver의 DECIMAL로 정확하게 하고, 저장할 때 수량을 DOUBLE로 바꿉니다.
# MAGIC Fabric IQ Ontology의 그래프가 DECIMAL 형식을 지원하지 않기 때문입니다.

# COMMAND ----------
GOLD_SCHEMA = {
    "chip_dim_material": "material_id STRING, material_name STRING, unit STRING",
    "chip_dim_bunker": ("bunker_id STRING, bunker_name STRING, material_id STRING, "
                        "capacity_kg DOUBLE, safety_stock_kg DOUBLE"),
    "chip_dim_date": "business_date DATE",
    "chip_dim_scenario": ("scenario_id STRING, scenario_name STRING, change_date DATE, "
                          "product_id STRING, increase_pct DOUBLE"),
    "chip_fact_plan": ("plan_key STRING, scenario_id STRING, business_date DATE, product_id STRING, "
                       "material_id STRING, bunker_id STRING, planned_output_kg DOUBLE, required_qty_kg DOUBLE"),
    "chip_fact_balance": ("balance_key STRING, scenario_id STRING, business_date DATE, material_id STRING, "
                          "bunker_id STRING, opening_qty_kg DOUBLE, received_qty_kg DOUBLE, "
                          "required_qty_kg DOUBLE, closing_qty_kg DOUBLE, safety_stock_kg DOUBLE, "
                          "below_safety BOOLEAN, shortage BOOLEAN"),
    "chip_scenario_summary": ("summary_key STRING, scenario_id STRING, material_id STRING, bunker_id STRING, "
                              "first_below_safety_date DATE, first_shortage_date DATE, total_required_kg DOUBLE, "
                              "ending_qty_kg DOUBLE, min_closing_qty_kg DOUBLE, required_topup_kg DOUBLE"),
    "chip_scenario_comparison": ("comparison_key STRING, scenario_id STRING, material_id STRING, "
                                 "bunker_id STRING, baseline_first_below_safety_date DATE, "
                                 "scenario_first_below_safety_date DATE, baseline_first_shortage_date DATE, "
                                 "scenario_first_shortage_date DATE, baseline_total_required_kg DOUBLE, "
                                 "scenario_total_required_kg DOUBLE, extra_required_kg DOUBLE, "
                                 "baseline_required_topup_kg DOUBLE, scenario_required_topup_kg DOUBLE, "
                                 "extra_topup_kg DOUBLE"),
    "chip_response_option": ("option_key STRING, scenario_id STRING, option_id STRING, option_name STRING, "
                             "material_id STRING, bunker_id STRING, action_detail STRING, "
                             "extra_receipt_kg DOUBLE, first_below_safety_date DATE, first_shortage_date DATE, "
                             "min_closing_qty_kg DOUBLE, ending_qty_kg DOUBLE, within_capacity BOOLEAN, "
                             "meets_safety_rule BOOLEAN"),
}


def to_gold(df, name):
    fields = spark.createDataFrame([], GOLD_SCHEMA[name]).schema.fields
    return df.select(*[F.col(f.name).cast(f.dataType).alias(f.name) for f in fields])


def make_key(*columns):
    return F.concat_ws("|", *[F.col(c).cast("string") for c in columns])


def september_days():
    return spark.range(1).select(
        F.explode(F.sequence(F.lit(START_DATE), F.lit(END_DATE))).alias("business_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Balance 계산 함수
# MAGIC 04와 05 Notebook이 같은 함수로 계산합니다.
# MAGIC
# MAGIC | 함수 | 하는 일 |
# MAGIC |---|---|
# MAGIC | `scenario` | 시나리오(기준 계획, 긴급 오더)를 정의합니다. |
# MAGIC | `add_required_qty` | 생산계획(제품 kg) × 제품 1kg당 Chip 소요량 = Chip 소요량(kg) |
# MAGIC | `project_balance` | Bunker별로 9월 30일 치 달력을 만들고 날짜마다 `마감 = 전일 마감 + 입고 - 소요`를 누적합니다. |
# MAGIC | `summarize` | 처음 안전재고 미만이 되는 날, 처음 0 미만이 되는 날, 월말·최저 재고, 필요한 추가 확보량을 구합니다. |
# MAGIC | `build_gold` | 위 결과를 Gold 테이블 9개 형식으로 만듭니다. |
# MAGIC
# MAGIC 그날 들어온 입고는 그날 생산에 바로 씁니다. 마감 재고가 음수이면 계획대로 생산할 때 모자라는 양입니다.

# COMMAND ----------
def scenario(scenario_id, scenario_name, change_date=None, product_id=None, increase_pct=0):
    return {"scenario_id": scenario_id, "scenario_name": scenario_name,
            "change_date": date.fromisoformat(change_date) if change_date else None,
            "product_id": product_id, "increase_pct": Decimal(str(increase_pct))}


BASELINE = scenario("baseline", "기준 계획")


def add_required_qty(plans, recipes, scen):
    output = F.col("planned_output_kg")
    if scen["change_date"] is not None:
        factor = Decimal(1) + scen["increase_pct"] / Decimal(100)
        changed = (F.col("product_id") == scen["product_id"]) & (F.col("business_date") == F.lit(scen["change_date"]))
        output = F.when(changed, output * F.lit(factor)).otherwise(output)
    return (plans.join(recipes, "product_id")
            .withColumn("planned_output_kg", output.cast(QTY))
            .withColumn("required_qty_kg", (F.col("planned_output_kg") * F.col("kg_per_kg")).cast(QTY))
            .withColumn("scenario_id", F.lit(scen["scenario_id"])))


def project_balance(plan, receipts, bunkers, opening, scenario_id):
    keys = ["material_id", "bunker_id", "business_date"]
    need = plan.groupBy(*keys).agg(F.sum("required_qty_kg").alias("required_qty_kg"))
    incoming = receipts.groupBy(*keys).agg(F.sum("received_qty_kg").alias("received_qty_kg"))
    start = opening.select("material_id", "bunker_id", F.col("opening_qty_kg").alias("start_qty_kg"))
    daily = (bunkers.select("material_id", "bunker_id", "safety_stock_kg")
             .crossJoin(september_days())
             .join(start, ["material_id", "bunker_id"])
             .join(need, keys, "left")
             .join(incoming, keys, "left")
             .fillna(0, ["required_qty_kg", "received_qty_kg"]))
    by_day = Window.partitionBy("material_id", "bunker_id").orderBy("business_date")
    until_today = by_day.rowsBetween(Window.unboundedPreceding, Window.currentRow)
    change = F.col("received_qty_kg") - F.col("required_qty_kg")
    return (daily
            .withColumn("closing_qty_kg", (F.col("start_qty_kg") + F.sum(change).over(until_today)).cast(QTY))
            .withColumn("opening_qty_kg", F.coalesce(F.lag("closing_qty_kg").over(by_day), F.col("start_qty_kg")))
            .withColumn("below_safety", F.col("closing_qty_kg") < F.col("safety_stock_kg"))
            .withColumn("shortage", F.col("closing_qty_kg") < 0)
            .withColumn("scenario_id", F.lit(scenario_id))
            .select("scenario_id", "business_date", "material_id", "bunker_id", "opening_qty_kg",
                    "received_qty_kg", "required_qty_kg", "closing_qty_kg", "safety_stock_kg",
                    "below_safety", "shortage"))


def summarize(balance):
    last_day = F.col("business_date") == F.lit(END_DATE)
    return (balance.groupBy("scenario_id", "material_id", "bunker_id").agg(
                F.min(F.when(F.col("below_safety"), F.col("business_date"))).alias("first_below_safety_date"),
                F.min(F.when(F.col("shortage"), F.col("business_date"))).alias("first_shortage_date"),
                F.sum("required_qty_kg").alias("total_required_kg"),
                F.max(F.when(last_day, F.col("closing_qty_kg"))).alias("ending_qty_kg"),
                F.min("closing_qty_kg").alias("min_closing_qty_kg"),
                F.max("safety_stock_kg").alias("safety_stock_kg"))
            .withColumn("required_topup_kg", F.greatest(
                F.lit(0).cast(QTY), (F.col("safety_stock_kg") - F.col("min_closing_qty_kg")).cast(QTY))))


def build_gold(silver, scen):
    plan = add_required_qty(silver["plans"], silver["recipes"], scen)
    balance = project_balance(plan, silver["receipts"], silver["bunkers"], silver["opening"], scen["scenario_id"])
    scenario_row = [(scen["scenario_id"], scen["scenario_name"], scen["change_date"],
                     scen["product_id"], float(scen["increase_pct"]))]
    frames = {
        "chip_dim_material": silver["materials"],
        "chip_dim_bunker": silver["bunkers"],
        "chip_dim_date": september_days(),
        "chip_dim_scenario": spark.createDataFrame(scenario_row, GOLD_SCHEMA["chip_dim_scenario"]),
        "chip_fact_plan": plan.withColumn("plan_key", make_key("scenario_id", "business_date", "product_id")),
        "chip_fact_balance": balance.withColumn("balance_key", make_key("scenario_id", "business_date", "bunker_id")),
        "chip_scenario_summary": summarize(balance).withColumn("summary_key", make_key("scenario_id", "bunker_id")),
        "chip_scenario_comparison": spark.createDataFrame([], GOLD_SCHEMA["chip_scenario_comparison"]),
        "chip_response_option": spark.createDataFrame([], GOLD_SCHEMA["chip_response_option"]),
    }
    return {name: to_gold(df, name) for name, df in frames.items()}


def compare_scenarios(base_summary, new_summary):
    b, s = base_summary.alias("b"), new_summary.alias("s")
    compared = s.join(b, ["material_id", "bunker_id"]).select(
        F.col("s.scenario_id").alias("scenario_id"), "material_id", "bunker_id",
        F.col("b.first_below_safety_date").alias("baseline_first_below_safety_date"),
        F.col("s.first_below_safety_date").alias("scenario_first_below_safety_date"),
        F.col("b.first_shortage_date").alias("baseline_first_shortage_date"),
        F.col("s.first_shortage_date").alias("scenario_first_shortage_date"),
        F.col("b.total_required_kg").alias("baseline_total_required_kg"),
        F.col("s.total_required_kg").alias("scenario_total_required_kg"),
        (F.col("s.total_required_kg") - F.col("b.total_required_kg")).alias("extra_required_kg"),
        F.col("b.required_topup_kg").alias("baseline_required_topup_kg"),
        F.col("s.required_topup_kg").alias("scenario_required_topup_kg"),
        (F.col("s.required_topup_kg") - F.col("b.required_topup_kg")).alias("extra_topup_kg"))
    return to_gold(compared.withColumn("comparison_key", make_key("scenario_id", "bunker_id")),
                   "chip_scenario_comparison")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. OneLake 저장 함수
# MAGIC Databricks가 Fabric Lakehouse의 `Tables/gold` 폴더에 Delta 테이블을 직접 저장합니다.
# MAGIC Fabric은 이 폴더의 Delta 테이블을 자동으로 인식하므로 Fabric에서 따로 만들 필요가 없습니다.
# MAGIC 인증 정보는 secret scope에서 읽으며 화면에 표시하지 않습니다.
# MAGIC Fabric의 SQL·Power BI·Ontology가 모두 읽을 수 있도록 기본 Delta 기능(삭제 벡터 끔)으로 저장합니다.

# COMMAND ----------
def connect_onelake():
    host = "onelake.dfs.fabric.microsoft.com"
    defaults = "spark.databricks.delta.properties.defaults"
    spark.conf.set(f"{defaults}.enableDeletionVectors", "false")
    spark.conf.set(f"{defaults}.columnMapping.mode", "none")
    spark.conf.set(f"{defaults}.enableRowTracking", "false")
    spark.conf.set(f"{defaults}.checkpointPolicy", "classic")
    tenant_id = dbutils.secrets.get(secret_scope, "tenant-id")
    spark.conf.set(f"fs.azure.account.auth.type.{host}", "OAuth")
    spark.conf.set(f"fs.azure.account.oauth.provider.type.{host}",
                   "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
    spark.conf.set(f"fs.azure.account.oauth2.client.id.{host}", dbutils.secrets.get(secret_scope, "client-id"))
    spark.conf.set(f"fs.azure.account.oauth2.client.secret.{host}",
                   dbutils.secrets.get(secret_scope, "client-secret"))
    spark.conf.set(f"fs.azure.account.oauth2.client.endpoint.{host}",
                   f"https://login.microsoftonline.com/{tenant_id}/oauth2/token")


def onelake_path(name):
    return (f"abfss://{fabric_workspace_id}@onelake.dfs.fabric.microsoft.com/"
            f"{fabric_lakehouse_id}/Tables/gold/{name}")


def write_gold(frames):
    connect_onelake()
    counts = []
    for name in GOLD_SCHEMA:
        (frames[name].write.format("delta").mode("overwrite")
         .option("overwriteSchema", "true").save(onelake_path(name)))
        counts.append((name, spark.read.format("delta").load(onelake_path(name)).count()))
    return spark.createDataFrame(counts, "table_name STRING, row_count BIGINT")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. 설정 확인
# MAGIC 본인 스키마와 원본 파일용 Volume(`raw`)이 있는지 확인합니다.
# MAGIC
# MAGIC **예상 결과:** `설정 확인 완료`와 스키마·폴더 이름이 표시됩니다. 오류가 나면 관리자에게 스키마 권한을 확인합니다.

# COMMAND ----------
dbutils.fs.ls(f"/Volumes/{catalog}/{schema}/raw")
print("설정 확인 완료")
print("Unity Catalog 스키마:", f"{catalog}.{schema}")
print("원본 파일 폴더:", raw_dir)
