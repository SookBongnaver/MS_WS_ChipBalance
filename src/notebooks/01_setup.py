# Databricks notebook source
# MAGIC %md
# MAGIC # 01. 설정과 연결 확인
# MAGIC 다른 Notebook은 첫 코드 셀 `%run ./01_setup`으로 이 Notebook을 불러옵니다.
# MAGIC
# MAGIC 1. **2. 설정값** 셀에서 `participant`만 본인 참가자 번호로 바꿉니다.
# MAGIC 2. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 3. 마지막 셀에 `연결 확인 완료`가 나오면 `02_source_data`를 엽니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Serverless 준비
# MAGIC 이 Workshop은 별도 Compute를 만들지 않고 Serverless에서 실행합니다.
# MAGIC OneLake에 Delta 형식으로 저장할 때 필요한 `deltalake`를 Notebook 범위에 설치합니다.
# MAGIC
# MAGIC **예상 결과:** 설치가 완료되거나 `Requirement already satisfied`가 표시됩니다.

# COMMAND ----------
# MAGIC %pip install deltalake==1.6.6

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 설정값 — 참가자 번호만 바꿉니다
# MAGIC `participant`에 관리자에게 받은 참가자 번호(예: `p001`)를 넣습니다.
# MAGIC 나머지 이름은 참가자 번호로 정해지므로 바꾸지 않습니다.
# MAGIC
# MAGIC | 이름 | 값 (`p001`일 때) | 용도 |
# MAGIC |---|---|---|
# MAGIC | `catalog`, `schema` | `lab_factory_p001`, `chipbalance_p001` | Bronze·Silver·Gold 테이블을 저장하는 Unity Catalog 위치 |
# MAGIC | `raw_volume` | `/Volumes/lab_factory_p001/chipbalance_p001/raw` | 02에서 SAP·FPIMS·PVSS 원천 파일을 만드는 Volume |
# MAGIC | `fabric_workspace`, `fabric_lakehouse` | `chipbalance-p001`, `lh_chipbalance_p001` | Gold를 저장하는 Fabric 작업 영역과 Lakehouse |
# MAGIC | `service_credential` | `chipbalance_onelake_hyosung` | OneLake에 저장할 때 쓰는 Managed Identity |

# COMMAND ----------
import re

participant = "p001"

catalog = f"lab_factory_{participant}"
schema = f"chipbalance_{participant}"
raw_volume = f"/Volumes/{catalog}/{schema}/raw"
fabric_workspace = f"chipbalance-{participant}"
fabric_lakehouse = f"lh_chipbalance_{participant}"
service_credential = "chipbalance_onelake_hyosung"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Unity Catalog 확인
# MAGIC 설정값을 확인한 뒤 Catalog, 본인 스키마, 원천 파일 Volume이 없으면 준비합니다.
# MAGIC 이후 SQL이 본인 스키마를 기본으로 쓰도록 지정합니다.
# MAGIC 시간대는 한국 시간(Asia/Seoul)으로 맞춥니다.
# MAGIC
# MAGIC **예상 결과:** 스키마 이름과 Volume 경로가 표시됩니다.

# COMMAND ----------
if not re.fullmatch(r"p\d{3}", participant):
    raise ValueError("participant는 p001처럼 p와 숫자 세 자리로 입력합니다.")

spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`raw`")
spark.sql(f"USE CATALOG `{catalog}`")
spark.sql(f"USE SCHEMA `{schema}`")
spark.conf.set("spark.sql.session.timeZone", "Asia/Seoul")
dbutils.fs.ls(raw_volume)
print("Unity Catalog 스키마:", f"{catalog}.{schema}")
print("원천 파일 Volume:", raw_volume)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. OneLake 저장 함수
# MAGIC Gold는 Fabric Lakehouse의 `Tables/gold` 폴더에 Delta 테이블로 저장합니다. Fabric은 이 폴더의 테이블을 자동으로 인식합니다.
# MAGIC
# MAGIC 인증에는 Managed Identity를 씁니다. 관리자가 Access Connector의 Managed Identity를
# MAGIC Unity Catalog service credential `chipbalance_onelake_hyosung`로 등록하고, Fabric 작업 영역에 Contributor 권한을 주었습니다.
# MAGIC Notebook에는 비밀번호나 키를 넣지 않습니다. 저장할 때마다 service credential에서 토큰을 받아 씁니다.
# MAGIC
# MAGIC | 함수 | 하는 일 |
# MAGIC |---|---|
# MAGIC | `onelake_options` | Managed Identity 토큰을 받아 OneLake 접속 옵션을 만듭니다. |
# MAGIC | `write_delta` | Spark DataFrame을 OneLake 경로에 Delta 형식으로 덮어써서 저장하고, 저장된 행 수를 돌려줍니다. |
# MAGIC | `write_gold` | `Tables/gold/<테이블 이름>`에 저장합니다. 소수(`DECIMAL`) 열은 `DOUBLE`로 바꿔 저장합니다. Fabric Ontology가 `DECIMAL`을 읽지 못하기 때문입니다. |
# MAGIC | `publish_gold` | Gold를 `write_gold`로 OneLake에 저장한 뒤 `read_gold`로 다시 읽어 임시 뷰 `gold_<테이블 이름>`으로 등록합니다. Gold는 Unity Catalog에 만들지 않고 OneLake에만 있으며, 뷰는 OneLake에 저장된 Gold와 같습니다. `05_gold`와 `06_emergency_order`에서 씁니다. |
# MAGIC | `read_gold` | OneLake의 Gold를 읽어 임시 뷰 `gold_<테이블 이름>`으로 등록합니다. `DOUBLE`로 저장한 소수 열은 `DECIMAL`로 되돌립니다. `06_emergency_order`가 05의 Gold를 불러올 때 씁니다. |
# MAGIC | `onelake_gold_rows` | OneLake에 저장된 Gold 테이블의 행 수를 돌려줍니다. |
# MAGIC
# MAGIC 임시 뷰는 이 Notebook 세션 안에서만 보입니다. 세션이 끊겨도 OneLake의 Gold는 그대로 남습니다.

# COMMAND ----------
from zoneinfo import ZoneInfo

import pyarrow as pa
from pyspark.sql import functions as F
from pyspark.sql import types as T

try:
    from deltalake import DeltaTable, write_deltalake
except ImportError as error:
    raise RuntimeError("deltalake 설치에 실패했습니다. 1. Serverless 준비 셀의 오류 메시지를 관리자에게 알립니다.") from error

ONELAKE_ROOT = f"abfss://{fabric_workspace}@onelake.dfs.fabric.microsoft.com/{fabric_lakehouse}.lakehouse"
ARROW_TYPES = {T.StringType: pa.string(), T.LongType: pa.int64(), T.IntegerType: pa.int32(),
               T.DoubleType: pa.float64(), T.BooleanType: pa.bool_(), T.DateType: pa.date32(),
               T.TimestampType: pa.timestamp("us", tz="UTC")}


def onelake_options():
    try:
        credential = dbutils.credentials.getServiceCredentialsProvider(service_credential)
        token = credential.get_token("https://storage.azure.com/.default").token
    except Exception as error:
        raise RuntimeError(f"service credential '{service_credential}' 사용 권한을 확인합니다. 오류 메시지를 관리자에게 알립니다.\n원본 오류: {type(error).__name__}: {error}") from error
    return {"bearer_token": token, "use_fabric_endpoint": "true"}


def to_arrow(df):
    fields = df.schema.fields
    unsupported = [f"{f.name} {f.dataType.simpleString()}" for f in fields if type(f.dataType) not in ARROW_TYPES]
    if unsupported:
        raise TypeError("OneLake에 저장할 수 없는 형식입니다: " + ", ".join(unsupported))
    zone = ZoneInfo(spark.conf.get("spark.sql.session.timeZone"))
    rows = [row.asDict() for row in df.collect()]
    for field in fields:
        if isinstance(field.dataType, T.TimestampType):
            for row in rows:
                if row[field.name] is not None:
                    row[field.name] = row[field.name].replace(tzinfo=zone)
    schema = pa.schema([pa.field(f.name, ARROW_TYPES[type(f.dataType)]) for f in fields])
    return pa.Table.from_pylist(rows, schema=schema)


def write_delta(df, path):
    write_deltalake(path, to_arrow(df), mode="overwrite", schema_mode="overwrite", storage_options=onelake_options())
    return DeltaTable(path, storage_options=onelake_options()).to_pyarrow_table().num_rows


def write_gold(df, table):
    df = df.select([F.col(f.name).cast("double") if isinstance(f.dataType, T.DecimalType) else F.col(f.name)
                    for f in df.schema.fields])
    return write_delta(df, f"{ONELAKE_ROOT}/Tables/gold/{table}")


GOLD_TABLES = [
    "dim_line", "dim_bunker", "dim_material", "dim_product", "dim_supplier", "dim_customer", "dim_route", "dim_date", "dim_scenario",
    "fact_usage_factor", "fact_monthly_usage", "fact_opening_stock", "fact_inbound", "fact_sales_order", "fact_plan",
    "fact_order_fulfillment", "fact_balance", "fact_bunker_summary",
]
EMERGENCY_GOLD_TABLES = ["fact_response_option", "fact_option_balance", "fact_risk_event"]
GOLD_DECIMALS = {"std_kg_per_kg": "decimal(10,6)", "actual_kg_per_kg": "decimal(10,6)",
                 "loss_pct": "decimal(6,2)", "avg_delay_days": "decimal(6,2)"}


def publish_gold(table, df):
    write_gold(df, table)
    read_gold(table)


def spark_type(arrow_type):
    if pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
        return T.StringType()
    if pa.types.is_int64(arrow_type):
        return T.LongType()
    if pa.types.is_int32(arrow_type):
        return T.IntegerType()
    if pa.types.is_floating(arrow_type):
        return T.DoubleType()
    if pa.types.is_boolean(arrow_type):
        return T.BooleanType()
    if pa.types.is_date32(arrow_type):
        return T.DateType()
    if pa.types.is_timestamp(arrow_type):
        return T.TimestampType()
    raise TypeError(f"OneLake에서 읽을 수 없는 형식입니다: {arrow_type}")


def onelake_gold_table(table):
    return DeltaTable(f"{ONELAKE_ROOT}/Tables/gold/{table}", storage_options=onelake_options()).to_pyarrow_table()


def read_gold(table):
    data = onelake_gold_table(table)
    schema = T.StructType([T.StructField(f.name, spark_type(f.type), True) for f in data.schema])
    df = spark.createDataFrame([tuple(row.values()) for row in data.to_pylist()], schema)
    for column, decimal_type in GOLD_DECIMALS.items():
        if column in df.columns:
            df = df.withColumn(column, F.col(column).cast(decimal_type))
    df.createOrReplaceTempView(f"gold_{table}")


def onelake_gold_rows(table):
    return onelake_gold_table(table).num_rows

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. OneLake 연결 확인
# MAGIC Managed Identity로 토큰을 받아 Lakehouse의 `Files/chipbalance/connection_check`에 확인용 Delta 테이블을 쓰고 다시 읽습니다.
# MAGIC Gold 테이블과 섞이지 않도록 `Files` 폴더에 저장합니다.
# MAGIC
# MAGIC **예상 결과:** `연결 확인 완료`, OneLake 경로, `쓰기·읽기: 1행`이 표시됩니다.

# COMMAND ----------
check = spark.sql(f"SELECT '{participant}' AS participant, current_timestamp() AS checked_at")
check_rows = write_delta(check, f"{ONELAKE_ROOT}/Files/chipbalance/connection_check")
print("연결 확인 완료")
print("OneLake 경로:", ONELAKE_ROOT)
print("Managed Identity(service credential):", service_credential)
print("쓰기·읽기:", f"{check_rows}행")