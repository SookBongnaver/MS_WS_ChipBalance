# 관리자 준비 가이드

[목차](../README.md)

Workshop 환경을 준비하고 정리하는 관리자용 문서입니다. 참가자는 보지 않아도 됩니다. 예시는 `p001` 기준이며 참가자마다 `pNNN`을 바꿔 반복합니다. 체크리스트는 [admin_checklist.rst](admin_checklist.rst), 데이터 구조는 [데이터 설계](data-design.md)를 봅니다.

## 준비할 리소스

| 리소스 | 값 |
|----|----|
| Azure Databricks | Premium workspace, Unity Catalog 사용 |
| Unity Catalog | 참가자별 카탈로그 `lab_factory_pNNN`, 스키마 `chipbalance_pNNN`, Volume `raw` |
| 공유 실습 원본 | **Workspace → Shared → ChipBalance**에 Notebook 8개, **Workspace → Shared → fabric**에 Fabric 파일 3개 |
| SQL warehouse (선택) | `chipbalance-pro`, Serverless 또는 Pro 2X-Small. 07장 Genie용 |
| Managed Identity | Access Connector `ac-chipbalance-onelake`, service credential `chipbalance_onelake_hyosung` |
| Microsoft Fabric | F 용량, 작업 영역 `chipbalance-pNNN`, Lakehouse `lh_chipbalance_pNNN`(schemas 켬) |
| Fabric Data agent | 참가자가 09장에서 `da_chipbalance`를 만들고 `ont_chipbalance` 연결 |
| Microsoft Teams | Teams 라이선스, 앱 **Fabric Operations Agent** 허용 (11장) |
| Microsoft Foundry | Foundry 리소스·프로젝트를 만들 Azure 리소스 그룹 (12장) |

## 1. Unity Catalog

1.  Premium workspace를 Unity Catalog 메타스토어에 연결합니다.
2.  참가자 Entra ID 계정을 workspace에 추가하고 **Workspace access** entitlement를 줍니다.
3.  참가자마다 Catalog·스키마·Volume을 미리 만들고 사용 권한만 줍니다(권장). `01_setup`은 `IF NOT EXISTS`라 이미 있으면 그대로 넘어갑니다.

``` sql
CREATE CATALOG IF NOT EXISTS lab_factory_p001;
CREATE SCHEMA IF NOT EXISTS lab_factory_p001.chipbalance_p001;
CREATE VOLUME IF NOT EXISTS lab_factory_p001.chipbalance_p001.raw;

GRANT USE CATALOG ON CATALOG lab_factory_p001 TO `p001@contoso.com`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory_p001.chipbalance_p001 TO `p001@contoso.com`;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory_p001.chipbalance_p001.raw TO `p001@contoso.com`;
```

참가자에게 생성 권한을 주고 Notebook이 직접 만들게 하려면 메타스토어 `CREATE CATALOG`(또는 `MANAGED LOCATION` 지정 후 관리자가 Catalog만 생성), Catalog의 `USE CATALOG`·`CREATE SCHEMA`, 스키마의 `USE SCHEMA`·`CREATE VOLUME`이 필요합니다.

Bronze·Silver는 03–04 Notebook이 Unity Catalog에 만듭니다. Gold는 05–06 Notebook이 Fabric Lakehouse(OneLake)에만 저장합니다.

Databricks 쪽 준비(service credential 등록, Catalog·스키마·Volume과 권한)는 `admin/00_admin_setup.ipynb`로 한 번에 처리할 수 있습니다. **Notebook Serverless** 또는 **Runtime 18.0 이상 / Standard access mode**에서 0단계(SDK 확인·재시작) 후 1–5단계를 순서대로 실행합니다. 6단계(Genie Federation)는 05장 이후 선택 실행입니다.

### 공유 Notebook과 Fabric 파일 원본

Shared 아래에 Notebook 원본 ``ChipBalance``와 파일 원본 ``fabric``을 각각 준비합니다. 참가자는 01장에서 ``ChipBalance``를 본인 Home에 **Clone**하고, ``fabric``의 파일은 PC로 내려받습니다.

1.  `notebooks\ChipBalance.zip`을 **Workspace → Shared**에 **Import**합니다(ZIP은 풀지 않음). `ChipBalance` 폴더에 Notebook 8개가 생깁니다.
2.  **Workspace → Shared**에 별도 `fabric` 폴더를 만들고 `sm_chipbalance.tmdl`, `chipbalance-theme.json`, `nb_record_decision.ipynb`를 올립니다.
3.  참가자에게 읽기·복제·파일 내려받기 권한을 주고, Clone과 파일 내려받기가 되는지 확인합니다. `nb_record_decision`은 Notebook을 연 뒤 **오른쪽 위 ⋮ → File → Export... → IPython Notebook**으로 내려받습니다([01장 상세 절차](../docs/01-connect.md#fabric-파일-3개-내려받기)).

원본 변경은 관리자만 합니다. 원본을 갱신해도 참가자 복제본은 자동으로 갱신되지 않습니다.

**참가자 PC에서 Fabric 로컬 파일 업로드가 차단된 경우:** Shared에서 파일을 내려받아도 Fabric의 **From this computer** Import는 사용할 수 없습니다. 관리자가 업로드 가능한 PC에서 참가자별 작업 영역 `chipbalance-pNNN`에 `fabric\nb_record_decision.ipynb`를 미리 Import하고 이름이 `nb_record_decision`인지 확인합니다. Notebook은 실행하지 않으며, 참가자는 11장에서 기존 Notebook을 열어 본인의 `lh_chipbalance_pNNN`을 기본 Lakehouse로 연결합니다.

- `sm_chipbalance.tmdl`은 파일 Import가 아니라 내용을 TMDL View에 붙여 넣으므로 진행할 수 있습니다.
- `chipbalance-theme.json`은 Power BI의 로컬 파일 Import가 필요합니다. 업로드가 차단된 환경에서는 10장의 사용자 지정 테마 단계를 건너뛰거나, 보고서 생성 뒤 관리자가 테마를 적용합니다.
- `nb_record_decision.ipynb`만 참가자별 작업 영역에 사전 Import하면 11장의 로컬 Notebook 업로드 단계를 건너뛸 수 있습니다.

### (선택) Genie 확장

- SQL warehouse `chipbalance-pro`(Serverless 또는 Pro, 2X-Small, Auto stop 15분)를 만들고 참가자에게 **Can use**를 줍니다.
- 계정 콘솔에서 **Partner-powered AI features**를 켭니다.
- OneLake를 **Foreign catalog** `fabric_chipbalance_pNNN`으로 연결합니다(읽기 전용, `00_admin_setup` 6단계). Fabric 테넌트 설정 **Service principals can call Fabric public APIs**, **Users can access data stored in OneLake with apps external to Fabric**, **Use short-lived user-delegated SAS tokens**를 켜고, 작업 영역 OneLake settings에서 SAS 토큰 인증을 켭니다.
- OneLake Federation용 SQL warehouse는 **SQL 버전 2025.40 이상**이 필요합니다([요구 사항](https://learn.microsoft.com/azure/databricks/query-federation/onelake)).

## 2. Managed Identity와 service credential

1.  Azure portal에서 **Access Connector for Azure Databricks** `ac-chipbalance-onelake`를 만듭니다(System-assigned identity).
2.  Databricks **Catalog → Connect → Credentials**에서 **Create credential**: Service credential, 이름 `chipbalance_onelake_hyosung`, Access connector ID는 위 Resource ID.
3.  참가자에게 사용 권한을 줍니다.

    ``` sql
    GRANT ACCESS ON SERVICE CREDENTIAL `chipbalance_onelake_hyosung` TO `p001@contoso.com`;
    ```

4.  Fabric 작업 영역 **Manage access**에서 `ac-chipbalance-onelake`를 **Contributor**로 추가합니다.

Notebook은 `dbutils.credentials.getServiceCredentialsProvider("chipbalance_onelake_hyosung")`로 토큰을 받습니다(Runtime 16.2 이상 필요).

## 3. Microsoft Fabric

1.  활성 유료 Fabric 용량을 만듭니다(최소 SKU F2, 동시 참가자 수에 맞춰 조정).
2.  참가자마다 작업 영역 `chipbalance-pNNN`을 만들어 용량에 할당하고 참가자를 **Contributor**로 추가합니다.
3.  **Lakehouse schemas**를 켠 `lh_chipbalance_pNNN`을 만듭니다.
4.  참가자에게 Power BI 사용자 라이선스(Pro 등)를 줍니다.

**Admin portal → Tenant settings**에서 켤 항목:

| 설정 | 필요한 이유 |
|----|----|
| Users can access data stored in OneLake with apps external to Fabric | Databricks가 OneLake에 Gold 저장 |
| Service principals can call Fabric public APIs | Managed Identity의 작업 영역 접근 |
| Users can create Fabric items / Ontology items | Ontology 환경 생성 |
| Users can use Copilot, AI Agents and other AI experiences | Ontology(08), Data agent(09), Power BI Copilot(10), Operations agent(11) |
| Data sent to Azure OpenAI can be processed/stored outside your capacity's region | 조직 정책에 따라 필요 시 승인 |

Teams 관리 센터에서 **Fabric Operations Agent** 앱 차단 여부를 확인합니다.

**Data agent 확인:** 참가자 계정으로 **New item → Data agent → Add ontology**에서 `ont_chipbalance`를 선택하고 09장의 지침을 저장해 Gold 값을 조회할 수 있는지 확인합니다.

## 4. Microsoft Foundry

12장에서 참가자가 Foundry 프로젝트 `chipbalance-pNNN`과 에이전트 `fa-chipbalance`를 만들고 Fabric IQ로 `ont_chipbalance`를 연결합니다.

1.  Agent Service·모델을 지원하는 지역에 Azure 구독·리소스 그룹을 준비합니다.
2.  참가자에게 리소스 그룹 **Contributor**를 주고, 프로젝트 생성 후 **Foundry User**·**Foundry Project Manager** 역할을 부여합니다([Foundry RBAC](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry#minimum-role-assignments-to-get-started)).
3.  `gpt-5` 등 Fabric IQ/MCP 지원 모델의 배포·할당량을 확인합니다.
4.  Fabric IQ 도구의 **managed OAuth** 또는 **BYO Microsoft Entra** 인증을 준비합니다([요구 사항](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/fabric-iq#authentication-and-security)).

참가자는 작업 영역 `chipbalance-pNNN`의 **Contributor**면 Fabric IQ로 Ontology를 읽을 수 있습니다. Fabric 쿼리·AI 사용량은 Fabric 용량을 소비합니다.

## 5. 네트워크

Databricks Serverless에서 HTTPS(443) 연결 필요:

- `onelake.dfs.fabric.microsoft.com` — Gold 저장
- `pypi.org`, `files.pythonhosted.org` — `deltalake` 설치
- `login.microsoftonline.com` — Microsoft Entra 토큰

Private endpoint 사용 시 Network Connectivity Configuration을 구성합니다.

## 6. 참가자에게 알려 줄 값

- Databricks 주소, 참가자 번호(예: `p001`)
- Shared `ChipBalance` 복제 권한, Shared `fabric` 파일 내려받기 방법
- Foundry 구독·리소스 그룹(12장)

전체 진행 전 참가자 계정으로 `01_setup` 실행, OneLake 연결, 06장 Gold, 09장 Data agent 연결, 10장 모델 작성, 11장 Notebook 실행, 12장 OAuth 동의를 확인합니다.

## 7. 종료 후 정리

1.  SQL warehouse `chipbalance-pro` **Stop**.
2.  참가자별 Operations agent `oa_chipbalance` **Stop** 확인.
3.  (선택) 실습 데이터 삭제: Unity Catalog `lab_factory_pNNN`, Fabric 작업 영역의 `oa_chipbalance`·`nb_record_decision`·`eh_chipbalance`·`rpt_chipbalance`·`sm_chipbalance`·`da_chipbalance`·`ont_chipbalance`(연관 Eventhouse·Graph 포함), Foundry 리소스 `fdy-chipbalance-pNNN`.
4.  Fabric 용량 **Pause**.
5.  더 쓰지 않으면 `ac-chipbalance-onelake` 권한, 공용 credential을 의존성 확인 후 삭제.

## 8. 유지보수

- Notebook은 `src/notebooks/*.py`에서 고치고, 아래로 재생성·검사합니다.

``` powershell
python tools/generate_source_data.py
python tools/build_notebooks.py
python -m unittest discover tests
```

- 구성도는 `python tools/build_architecture.py`로 재생성합니다([아이콘 출처](../assets/icon-attribution.md)).
- 화면이 바뀌면 `assets/screenshots`의 같은 이름 파일을 교체합니다.
