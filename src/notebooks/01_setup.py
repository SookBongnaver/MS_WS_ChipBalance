# Databricks notebook source
# MAGIC %md
# MAGIC # 01. 설정과 연결 확인
# MAGIC 02~05 Notebook은 첫 코드 셀 `%run ./01_setup`으로 이 Notebook을 불러옵니다.
# MAGIC
# MAGIC 1. **2. 설정값** 셀에서 `participant`만 본인 참가자 번호로 바꿉니다.
# MAGIC 2. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 3. 마지막 셀에 `연결 확인 완료`가 나오면 `02_source_data`를 엽니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Compute 확인
# MAGIC 관리자가 배정한 Classic Compute에서 실행합니다. Serverless는 사용하지 않습니다.
# MAGIC
# MAGIC **예상 결과:** 배정받은 Compute 이름과 Runtime `16.4.x`가 표시됩니다.

# COMMAND ----------
import re


def cluster_tag(name):
    try:
        return spark.conf.get(f"spark.databricks.clusterUsageTags.{name}", "")
    except Exception:
        return ""


if not re.fullmatch(r"\d{4}-\d{6}-[A-Za-z0-9]+", cluster_tag("clusterId")):
    raise RuntimeError("오른쪽 위 Compute 목록에서 배정받은 Classic Compute를 선택한 뒤 다시 실행하세요.")
print("Compute:", cluster_tag("clusterName"))
print("Runtime:", cluster_tag("sparkVersion"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 설정값 — 참가자 번호만 바꿉니다
# MAGIC `participant`에 관리자에게 받은 참가자 번호(예: `p001`)를 넣습니다.
# MAGIC 나머지 이름은 참가자 번호로 정해지므로 바꾸지 않습니다.
# MAGIC
# MAGIC | 이름 | 값 (`p001`일 때) | 용도 |
# MAGIC |---|---|---|
# MAGIC | `catalog`, `schema` | `lab_factory`, `chipbalance_p001` | Bronze·Silver 테이블을 저장하는 Unity Catalog 위치 |
# MAGIC | `raw_volume` | `/Volumes/lab_factory/chipbalance_p001/raw` | SAP·FPIMS·PVSS 원천 파일을 올리는 Volume |
# MAGIC | `fabric_workspace`, `fabric_lakehouse` | `chipbalance-p001`, `lh_chipbalance_p001` | Gold를 저장하는 Fabric 작업 영역과 Lakehouse |
# MAGIC | `service_credential` | `chipbalance_onelake` | OneLake에 저장할 때 쓰는 관리 ID |

# COMMAND ----------
participant = "p001"

catalog = "lab_factory"
schema = f"chipbalance_{participant}"
raw_volume = f"/Volumes/{catalog}/{schema}/raw"
fabric_workspace = f"chipbalance-{participant}"
fabric_lakehouse = f"lh_chipbalance_{participant}"
service_credential = "chipbalance_onelake"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Unity Catalog 확인
# MAGIC 본인 스키마와 원천 파일 Volume을 확인하고, 이후 SQL이 본인 스키마를 기본으로 쓰도록 지정합니다.
# MAGIC 시간대는 한국 시간(Asia/Seoul)으로 맞춥니다.
# MAGIC
# MAGIC **예상 결과:** 스키마 이름과 Volume 경로가 표시됩니다. 원천 파일은 02에서 올리므로 처음에는 0개입니다.

# COMMAND ----------
if not re.fullmatch(r"p\d{3}", participant):
    raise ValueError("participant는 p001처럼 p와 숫자 세 자리로 입력합니다.")

spark.sql(f"USE CATALOG `{catalog}`")
spark.sql(f"USE SCHEMA `{schema}`")
spark.conf.set("spark.sql.session.timeZone", "Asia/Seoul")
raw_files = [f.name for f in dbutils.fs.ls(raw_volume) if not f.name.endswith("/")]
print("Unity Catalog 스키마:", f"{catalog}.{schema}")
print("원천 파일 Volume:", raw_volume, f"(파일 {len(raw_files)}개)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. OneLake 저장 함수
# MAGIC Gold는 Fabric Lakehouse의 `Tables/gold` 폴더에 Delta 테이블로 저장합니다. Fabric은 이 폴더의 테이블을 자동으로 인식합니다.
# MAGIC
# MAGIC 인증에는 관리 ID(Managed Identity)를 씁니다. 관리자가 Access Connector의 관리 ID를
# MAGIC Unity Catalog service credential `chipbalance_onelake`로 등록하고, Fabric 작업 영역에 Contributor 권한을 주었습니다.
# MAGIC Notebook에는 비밀번호나 키를 넣지 않습니다. 저장할 때마다 service credential에서 토큰을 받아 씁니다.
# MAGIC
# MAGIC | 함수 | 하는 일 |
# MAGIC |---|---|
# MAGIC | `onelake_options` | 관리 ID 토큰을 받아 OneLake 접속 옵션을 만듭니다. |
# MAGIC | `write_delta` | Spark DataFrame을 OneLake 경로에 Delta 형식으로 덮어써서 저장하고, 저장된 행 수를 돌려줍니다. |
# MAGIC | `write_gold` | `Tables/gold/<테이블 이름>`에 저장합니다. 04·05 Notebook에서 씁니다. |

# COMMAND ----------
from zoneinfo import ZoneInfo

import pyarrow as pa
from pyspark.sql import types as T

try:
    from deltalake import DeltaTable, write_deltalake
except ImportError as error:
    raise RuntimeError("Compute에 deltalake 라이브러리가 없습니다. 관리자에게 알립니다.") from error

ONELAKE_ROOT = f"abfss://{fabric_workspace}@onelake.dfs.fabric.microsoft.com/{fabric_lakehouse}.lakehouse"
ARROW_TYPES = {T.StringType: pa.string(), T.LongType: pa.int64(), T.IntegerType: pa.int32(),
               T.DoubleType: pa.float64(), T.BooleanType: pa.bool_(), T.DateType: pa.date32(),
               T.TimestampType: pa.timestamp("us", tz="UTC")}


def onelake_options():
    try:
        credential = dbutils.credentials.getServiceCredentialsProvider(service_credential)
        token = credential.get_token("https://storage.azure.com/.default").token
    except Exception as error:
        raise RuntimeError(f"service credential '{service_credential}' 사용 권한을 확인합니다. 오류 메시지를 관리자에게 알립니다.") from error
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
    return write_delta(df, f"{ONELAKE_ROOT}/Tables/gold/{table}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. OneLake 연결 확인
# MAGIC 관리 ID로 토큰을 받아 Lakehouse의 `Files/chipbalance/connection_check`에 확인용 Delta 테이블을 쓰고 다시 읽습니다.
# MAGIC Gold 테이블과 섞이지 않도록 `Files` 폴더에 저장합니다.
# MAGIC
# MAGIC **예상 결과:** `연결 확인 완료`, OneLake 경로, `쓰기·읽기: 1행`이 표시됩니다.

# COMMAND ----------
check = spark.sql(f"SELECT '{participant}' AS participant, current_timestamp() AS checked_at")
check_rows = write_delta(check, f"{ONELAKE_ROOT}/Files/chipbalance/connection_check")
print("연결 확인 완료")
print("OneLake 경로:", ONELAKE_ROOT)
print("관리 ID(service credential):", service_credential)
print("쓰기·읽기:", f"{check_rows}행")