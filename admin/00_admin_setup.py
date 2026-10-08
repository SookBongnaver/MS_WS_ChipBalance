# Databricks notebook source
# MAGIC %md
# MAGIC # 00. 관리자 준비 (Databricks)
# MAGIC 참가자가 실습을 시작하기 전에 **관리자가 한 번** 실행합니다. 참가자용 `ChipBalance.zip`에는 들어 있지 않습니다.
# MAGIC
# MAGIC | 단계 | 하는 일 |
# MAGIC |---|---|
# MAGIC | 2 | Access Connector의 Managed Identity를 service credential `chipbalance_onelake_hyosung`로 등록 |
# MAGIC | 3 | 참가자별 Catalog·스키마·Volume 만들기 |
# MAGIC | 4 | 참가자에게 service credential, Catalog, 스키마, Volume 권한 주기 |
# MAGIC
# MAGIC **먼저 Azure portal에서 해야 하는 일:** Access Connector for Azure Databricks 만들기(System-assigned). Resource ID를 아래 설정값에 넣습니다.
# MAGIC
# MAGIC **이 Notebook으로 할 수 없는 일 (Fabric):** 작업 영역 `chipbalance-pNNN`, Lakehouse `lh_chipbalance_pNNN`(Lakehouse schemas 켬) 만들기, 그리고 작업 영역 **Manage access**에서 Access Connector와 참가자를 **Contributor**로 추가하기.
# MAGIC
# MAGIC 필요한 권한: 메타스토어의 `CREATE SERVICE CREDENTIAL`, `CREATE CATALOG`. 메타스토어 관리자로 실행합니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정값
# MAGIC `access_connector_id`와 `participants`(참가자 번호: 로그인 계정)를 채웁니다.

# COMMAND ----------
access_connector_id = "/subscriptions/<구독 ID>/resourceGroups/<리소스 그룹>/providers/Microsoft.Databricks/accessConnectors/ac-chipbalance-onelake"
service_credential = "chipbalance_onelake_hyosung"

participants = {
    "p101": "user@contoso.com",
}

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. service credential 등록
# MAGIC 같은 이름이 이미 있으면 새로 만들지 않고, 연결된 Access Connector가 같은지만 확인합니다.
# MAGIC credential 이름은 메타스토어 안에서 유일합니다. 다른 작업 영역이 같은 이름을 쓰고 있으면 Access Connector가 달라 경고가 나옵니다.

# COMMAND ----------
import re

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.catalog import AzureManagedIdentity, CredentialPurpose

if "<" in access_connector_id:
    raise ValueError("1. 설정값의 access_connector_id에 Access Connector의 Resource ID를 넣습니다.")
for number, email in participants.items():
    if not re.fullmatch(r"p\d{3}", number):
        raise ValueError(f"참가자 번호 '{number}'는 p001처럼 p와 숫자 세 자리로 입력합니다.")

w = WorkspaceClient()

try:
    existing = w.credentials.get_credential(service_credential)
    current = existing.azure_managed_identity.access_connector_id if existing.azure_managed_identity else None
    if (current or "").lower() == access_connector_id.lower():
        print("이미 있음:", service_credential)
    else:
        print("경고: 같은 이름의 credential이 다른 Access Connector를 가리킵니다.")
        print("  기존:", current)
        print("  설정:", access_connector_id)
except NotFound:
    w.credentials.create_credential(
        name=service_credential,
        purpose=CredentialPurpose.SERVICE,
        azure_managed_identity=AzureManagedIdentity(access_connector_id=access_connector_id),
        comment="Workshop: Databricks에서 Fabric OneLake로 Gold 저장 (Managed Identity)",
    )
    print("만듦:", service_credential)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 참가자별 Catalog·스키마·Volume
# MAGIC `lab_factory_pNNN` > `chipbalance_pNNN` > Volume `raw`를 만듭니다. 메타스토어에 기본 저장소가 없으면 `CREATE CATALOG`에 `MANAGED LOCATION`을 지정해야 합니다.

# COMMAND ----------
for number in participants:
    catalog, schema = f"lab_factory_{number}", f"chipbalance_{number}"
    spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
    spark.sql(f"""CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`
        COMMENT '원료 칩 수급 Workshop 참가자 {number}: 원천 파일 Volume raw와 Bronze·Silver·Gold 테이블'""")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`raw`")
    print("준비:", f"{catalog}.{schema}.raw")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. 권한 주기
# MAGIC 참가자에게 service credential 사용 권한과 본인 Catalog·스키마·Volume 권한을 줍니다. 권한은 `SHOW GRANTS`로 확인합니다.

# COMMAND ----------
for number, email in participants.items():
    catalog, schema = f"lab_factory_{number}", f"chipbalance_{number}"
    spark.sql(f"GRANT ACCESS ON SERVICE CREDENTIAL `{service_credential}` TO `{email}`")
    spark.sql(f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{email}`")
    spark.sql(f"GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA `{catalog}`.`{schema}` TO `{email}`")
    spark.sql(f"GRANT READ VOLUME, WRITE VOLUME ON VOLUME `{catalog}`.`{schema}`.`raw` TO `{email}`")
    print("권한:", number, email)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. 확인
# MAGIC 아래 결과에 참가자 계정이 보이면 됩니다. 이어서 Fabric 작업 영역과 Lakehouse를 준비하고, 참가자가 `01_setup`의 마지막 셀에서 `연결 확인 완료`를 확인합니다.

# COMMAND ----------
display(spark.sql(f"SHOW GRANTS ON SERVICE CREDENTIAL `{service_credential}`"))
