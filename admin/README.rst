관리자 준비 가이드
==========================

`목차 <../README.rst>`_

Workshop 환경을 준비하고 정리하는 관리자용 문서입니다. 참가자는 이 문서를 보지 않아도 됩니다.
예시는 참가자 ``p001`` 기준입니다. 참가자마다 ``pNNN`` 부분을 바꿔 반복합니다.
데이터 구조와 예상 결과는 `데이터 설계 <data-design.rst>`_\ 에 있습니다.

준비할 리소스
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 리소스
     - 값
   * - Azure Databricks
     - Premium workspace, Unity Catalog 사용
   * - Unity Catalog
     - 카탈로그 ``lab_factory``, 참가자별 스키마 ``chipbalance_pNNN``, 스키마 안의 Volume ``raw``
   * - Compute
     - 참가자별 Classic Compute (Dedicated), DBR 16.4 LTS, 20분 자동 종료, 라이브러리 ``deltalake==1.6.6``
   * - SQL warehouse
     - Pro SQL warehouse ``chipbalance-pro`` (2X-Small, 15분 자동 종료). 07장 Genie Agent가 사용
   * - 관리 ID
     - Access Connector for Azure Databricks ``ac-chipbalance-onelake``, Unity Catalog service credential ``chipbalance_onelake``
   * - Microsoft Fabric
     - F 용량, 작업 영역 ``chipbalance-pNNN``, Lakehouse ``lh_chipbalance_pNNN`` (Lakehouse schemas 켬)
   * - Microsoft Teams
     - 참가자 계정에 Teams 라이선스, Teams 앱 **Fabric Operations Agent** 허용 (11장)
   * - Microsoft Foundry
     - 참가자가 Foundry 리소스·프로젝트를 만들 Azure 리소스 그룹 (12장)

예상 비용
------------

실습 하루(약 7시간) 기준입니다. 참가자는 최대 10명이고, 강사 1명이 참가자 5명을 맡습니다.
Sweden Central 종량제 소매가(USD, 2026년 9월 Azure 가격표) 기준이며, 계약 할인과 Microsoft 365·Power BI 라이선스 비용은 뺐습니다.

.. list-table::
   :header-rows: 1
   :widths: 40 30 15 15

   * - 항목
     - 계산
     - 참가자 5명 (강사 1명)
     - 참가자 10명 (강사 2명)
   * - Microsoft Fabric 용량
     - 참가자마다 F16 하루(24시간): 16 CU × $0.19 × 24 = $72.96
     - $364.80
     - $729.60
   * - Databricks Classic Compute (DBU, VM, 디스크)
     - 참가자 1명이 02~07장을 실행한 날의 실제 비용 약 $20
     - $100
     - $200
   * - Databricks SQL warehouse ``chipbalance-pro``
     - 07장 Genie에서만 켜짐, 2X-Small Pro, 15분 자동 종료. 1명 실행한 날 약 $3.3
     - $5
     - $10
   * - Microsoft Foundry (``gpt-5`` 토큰)
     - 12장 질문 몇 개, 참가자당 $1 미만
     - $5
     - $10
   * - Storage (Unity Catalog, OneLake)
     - GB·월당 약 $0.02
     - $1 미만
     - $1 미만
   * - **하루 합계**
     -
     - **약 $475**
     - **약 $950**

* Fabric 용량이 합계의 약 77%입니다. 실습이 끝나면 바로 일시 중지합니다. 일시 중지한 동안에는 용량 비용이 나오지 않습니다. 8시간만 켜면 F16 한 개가 $24.32이므로 참가자 10명의 하루 합계는 약 $460입니다.
* 강사 환경은 참가자 환경 하나를 함께 보는 것으로 보고 따로 더하지 않았습니다. 강사도 용량을 따로 쓰면 강사 1명당 약 $95를 더합니다.
* 한국 중부(Korea Central)는 CU·시간당 $0.21이라 F16 하루가 $80.64입니다.
* Databricks 비용은 02~07장을 여러 번 다시 실행한 날의 값이라 넉넉하게 잡은 값입니다. Microsoft Defender for Cloud처럼 구독 설정에 따라 붙는 비용은 넣지 않았습니다.

1. Unity Catalog와 Compute
-----------------------------

#. Pricing tier가 **Premium**\ 인 Azure Databricks workspace를 Unity Catalog 메타스토어에 연결합니다.
#. 참가자의 Microsoft Entra ID 계정을 workspace에 추가합니다.
#. SQL editor에서 스키마와 Volume을 만들고 참가자에게 권한을 줍니다.

.. code-block:: sql

   CREATE CATALOG IF NOT EXISTS lab_factory;
   CREATE SCHEMA IF NOT EXISTS lab_factory.chipbalance_p001
     COMMENT '원료 칩 수급 Workshop 참가자 p001: 원천 파일 Volume raw와 Bronze·Silver·Gold 테이블';
   CREATE VOLUME IF NOT EXISTS lab_factory.chipbalance_p001.raw;

   GRANT USE CATALOG ON CATALOG lab_factory TO `p001@contoso.com`;
   GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA lab_factory.chipbalance_p001 TO `p001@contoso.com`;
   GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory.chipbalance_p001.raw TO `p001@contoso.com`;

* 메타스토어에 기본 저장소가 없으면 ``CREATE CATALOG``\ 에 ``MANAGED LOCATION``\ 을 지정합니다.
* Bronze·Silver·Gold 테이블은 참가자가 03~06 Notebook에서 만듭니다. 07장에서 Genie Code가 Gold 테이블에 설명을 넣으므로 참가자가 테이블 소유자이거나 ``MODIFY`` 권한이 있어야 합니다.

참가자마다 Classic Compute를 하나씩 만듭니다. Serverless는 사용하지 않습니다.

* Access mode: **Dedicated** (single user), 해당 참가자 한 명
* Databricks Runtime: **16.4 LTS**
* Worker 1대, 자동 크기 조정 끔 (이 환경: Standard_D4as_v5)
* 자동 종료: 20분
* **Libraries** > **Install new** > **PyPI**\ 에서 ``deltalake==1.6.6``\ 을 설치합니다. Gold를 OneLake에 쓸 때 사용합니다.
* 권한: 해당 참가자에게 **Can Restart** (자동 종료된 Compute를 다시 시작할 수 있음)

SQL warehouse를 하나 만들어 모든 참가자가 함께 씁니다. 07장 Genie Agent가 이 warehouse로 SQL을 실행합니다.

* **SQL Warehouses** > **Create SQL warehouse**: 이름 ``chipbalance-pro``, Type **Pro**, Cluster size **2X-Small**, Auto stop 15분
* **Permissions**\ 에서 참가자에게 **Can use**\ 를 줍니다.
* Unity Catalog 저장소를 private endpoint로 연결한 환경에서는 Serverless warehouse가 저장소에 접근하지 못합니다. Pro 또는 Classic warehouse를 씁니다.
* Genie Code와 Genie Agent는 **Partner-powered AI features**\ 가 켜져 있어야 합니다(계정 콘솔 **Settings** > **Feature enablement**).
  데이터 처리 지역 제한(**Enforce data processing within workspace Geography for AI features**)이 켜져 있으면 Genie Code를 쓸 수 없는 지역이 있습니다.
  참가자에게는 Databricks SQL 사용 권한(**Databricks SQL access** entitlement)이 필요합니다.

2. 관리 ID와 service credential
----------------------------------

Databricks는 관리 ID로 OneLake에 Gold를 씁니다. 비밀번호나 client secret을 만들지 않습니다.

#. Azure portal에서 **Access Connector for Azure Databricks**\ 를 만듭니다.

   * 이름: ``ac-chipbalance-onelake``, 지역: Databricks workspace와 같은 지역
   * **Managed identity**: System-assigned (기본값)

#. Databricks **Catalog** > **External data** > **Credentials** > **Create credential**\ 을 누릅니다.

   * Credential type: **Service credential**
   * Credential name: ``chipbalance_onelake``
   * Access connector ID: Access Connector의 Resource ID (``/subscriptions/…/providers/Microsoft.Databricks/accessConnectors/ac-chipbalance-onelake``)

   **예상 결과:** ``chipbalance_onelake``\ 의 **Overview**\ 에 Credential Type **Managed Identity**, Purpose **SERVICE**\ 와 Access Connector의 Resource ID가 보입니다.

   .. image:: ../assets/screenshots/admin-service-credential.png
      :alt: Catalog Explorer > Credentials > chipbalance_onelake 화면. Credential Type은 Managed Identity, Purpose는 SERVICE, Connector Id는 ac-chipbalance-onelake Access Connector의 Resource ID입니다.
      :width: 800

#. 참가자에게 service credential 사용 권한을 줍니다.

   .. code-block:: sql

      GRANT ACCESS ON SERVICE CREDENTIAL `chipbalance_onelake` TO `p001@contoso.com`;

   credential을 만든 소유자는 GRANT 없이 쓸 수 있습니다. 부여한 권한은 **Permissions** 탭에서 확인합니다.

#. Fabric 작업 영역의 **Manage access**\ 에서 ``ac-chipbalance-onelake``\ 를 검색해 **Contributor**\ 로 추가합니다.
   Access Connector의 관리 ID가 이 이름으로 보입니다.

   **예상 결과:** 목록에 ``ac-chipbalance-onelake`` (Service Principal)가 **Contributor**\ 로 보입니다.

   .. image:: ../assets/screenshots/admin-fabric-access.png
      :alt: chipbalance-p001 작업 영역의 Manage access 창. MOD Administrator는 Admin, ac-chipbalance-onelake (Service Principal)는 Contributor입니다.
      :width: 340

* service credential 하나를 모든 참가자가 함께 쓰면, 이 관리 ID가 Contributor로 추가된 모든 작업 영역에 쓸 수 있습니다.
  참가자별로 권한을 나누려면 참가자마다 Access Connector와 service credential을 따로 만듭니다.
* Notebook은 ``dbutils.credentials.getServiceCredentialsProvider("chipbalance_onelake")``\ 로 토큰을 받습니다.
  Databricks Runtime 16.2 이상이 필요합니다.

3. Microsoft Fabric
----------------------

#. Fabric 용량을 만듭니다. 참가자마다 F16 하나를 기준으로 합니다(위 "예상 비용"). F2 이상이면 실습할 수 있습니다.
#. 참가자마다 작업 영역 ``chipbalance-p001``\ 을 만들고 위 용량에 할당합니다.
#. 작업 영역의 **Manage access**\ 에서 참가자를 **Contributor**\ 로 추가합니다.
#. **New item** > **Lakehouse**\ 에서 ``lh_chipbalance_p001``\ 을 만듭니다. **Lakehouse schemas** 옵션을 켭니다.

참가자는 Power BI 보고서를 만들므로 Power BI 사용자 라이선스(Pro 등)가 필요합니다.

**Admin portal** > **Tenant settings**\ 에서 아래 설정을 켭니다. 위쪽 검색 창에서 키워드로 찾으면 빠릅니다.

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - 설정
     - 필요한 이유
   * - Users can access data stored in OneLake with apps external to Fabric
     - Databricks가 OneLake에 Gold 저장
   * - Service principals can call Fabric public APIs
     - 관리 ID가 Fabric 작업 영역 권한으로 접근
   * - Users can create Ontology items
     - Fabric IQ Ontology
   * - Users can use Copilot, AI Agents and other AI experiences powered by Azure OpenAI
     - Ontology agent, Operations agent
   * - Data sent to Azure OpenAI can be processed / stored outside your capacity's geographic region
     - 용량이 미국·EU 밖에 있을 때 Operations agent 사용

Teams 관리 센터의 **Teams 앱** > **앱 관리**\ 에서 **Fabric Operations Agent**\ 가 차단되어 있지 않은지 확인합니다.
Operations agent는 이 앱의 **Fabric operations agent** 채팅으로 참가자에게 제안을 보냅니다.

4. Microsoft Foundry
-----------------------

12장에서 참가자가 Foundry 프로젝트 ``chipbalance-pNNN``\ 과 에이전트 ``fa-chipbalance``\ 를 만들고, Fabric IQ 도구로 Ontology ``ont_chipbalance``\ 를 연결합니다.

#. Fabric 용량과 같은 지역(이 환경: Sweden Central)에 리소스 그룹을 준비합니다. 이 환경은 Fabric 용량과 같은 ``rg-factory-onelake-lab-0922``\ 를 씁니다.
#. 참가자에게 리소스 그룹의 **Contributor** 역할을 줍니다. 참가자가 Foundry 리소스 ``fdy-chipbalance-pNNN``\ 과 프로젝트를 직접 만듭니다.
   관리자가 프로젝트를 미리 만들어 두려면 참가자에게 프로젝트의 **Foundry User**\ 와 **Foundry Project Manager** 역할을 줍니다. Fabric IQ 연결을 만들 때 **Foundry Project Manager**\ 가 필요합니다.
#. 구독에 ``gpt-5`` 글로벌 표준 배포 할당량이 있는지 확인합니다. 에이전트를 만들면 ``gpt-5``\ 가 자동으로 배포됩니다.

* Fabric IQ 도구는 로그인한 참가자의 Fabric 권한으로 Ontology를 읽습니다. 참가자는 작업 영역 ``chipbalance-pNNN``\ 의 **Contributor**\ 이면 됩니다.
* 이 환경에서 Fabric IQ 도구가 Ontology(새 Ontology 환경)에 주는 기능은 ``list_ontology_entities``, ``list_ontology_rules``\ 입니다. 에이전트는 엔터티 정의와 업무 규칙 설명으로 답하고, 날짜별 값은 09장 Ontology agent에서 확인합니다.
  Ontology 엔드포인트의 도구 목록은 ``https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/<작업 영역 ID>/items/<Ontology ID>/ontologyEndpoint``\ 에 MCP ``tools/list``\ 를 보내 확인할 수 있습니다.
* 비용은 모델 토큰 사용량만큼 나옵니다. 프로젝트를 만들 때 권장 리소스(App Insights)를 끄므로 추적 저장 비용은 없습니다.
* Work IQ 도구(Teams, Mail 등)는 Microsoft 365 Copilot 라이선스가 있는 사용자만 조회할 수 있습니다. 라이선스가 없으면 도구 호출이 ``WorkIQ license check failed``\ 로 실패하므로, 12장에서는 붙이는 화면만 보여 줍니다.

5. 네트워크
--------------

Databricks Compute에서 아래 주소로 HTTPS(443) 연결이 되어야 합니다. 방화벽이나 프록시를 쓰면 허용합니다.

* ``onelake.dfs.fabric.microsoft.com``: Gold 저장
* ``pypi.org``, ``files.pythonhosted.org``: Compute 시작 시 ``deltalake`` 설치

Unity Catalog 저장소를 private endpoint로 연결했다면, Compute에서 저장소 주소가 사설 IP로 해석되도록 private DNS를 구성합니다.

6. 참가자에게 알려 줄 값
---------------------------

* Databricks 주소 (예: ``https://adb-<번호>.<번호>.azuredatabricks.net``)
* 참가자 번호(예: ``p001``)와 배정한 Compute 이름
* GitHub 저장소 접근 권한 또는 저장소 ZIP 파일
* Foundry 프로젝트를 만들 구독과 리소스 그룹 (12장)

Unity Catalog 스키마, Fabric 작업 영역·Lakehouse, service credential 이름은 참가자 번호로 정해지므로 따로 알려 주지 않습니다.

7. 종료 후 정리
------------------

#. 참가자 Compute를 모두 **Terminate**\ 하고, SQL warehouse ``chipbalance-pro``\ 를 **Stop**\ 합니다.
#. 참가자마다 Operations agent ``oa_chipbalance``\ 가 **Stop** 상태인지 확인합니다. 시작 상태면 5분마다 조회하며 용량을 씁니다.
#. (선택) 실습 데이터를 지웁니다. Fabric 항목은 용량을 일시 중지하기 전에 지웁니다.

   - Unity Catalog 스키마 ``lab_factory.chipbalance_pNNN``\ 과 Volume ``raw``
   - Fabric 작업 영역 ``chipbalance-pNNN``: ``oa_chipbalance``, ``nb_record_decision``, ``eh_chipbalance``, ``rpt_chipbalance``, ``sm_chipbalance``, ``ont_chipbalance``\ (자동으로 만들어진 ``ont_chipbalance_eh_…``, ``ont_chipbalance_graph_…`` 포함), ``lh_chipbalance_pNNN``. 작업 영역을 지우면 한 번에 지워집니다.
   - Foundry: Azure portal의 리소스 그룹에서 Foundry 리소스 ``fdy-chipbalance-pNNN``\ 을 삭제합니다. 프로젝트, 에이전트 ``fa-chipbalance``, 모델 배포, Fabric IQ 연결이 함께 지워집니다.
     같은 이름으로 다시 만들려면 Azure portal에서 삭제된 Foundry 리소스를 제거(purge)합니다.

#. Azure portal에서 Fabric 용량을 **Pause**\ 합니다. Azure CLI로는 아래 명령을 씁니다.

   .. code-block:: powershell

      az resource invoke-action --action suspend --ids /subscriptions/<구독 ID>/resourceGroups/rg-factory-onelake-lab-0922/providers/Microsoft.Fabric/capacities/<용량 이름>

#. Workshop 환경을 더 쓰지 않으면 Fabric 작업 영역 권한에서 ``ac-chipbalance-onelake``\ 를 빼고,
   service credential ``chipbalance_onelake``\ 와 Access Connector를 삭제합니다.

8. 유지보수
--------------

* Notebook 내용은 ``src/notebooks/*.py``\ 에서 고칩니다. ``notebooks/*.ipynb``\ 와 ``notebooks/ChipBalance.zip``\ 은 직접 고치지 않습니다.
* 원천 데이터는 ``tools/generate_source_data.py``\ 가 만들고, 예상 결과는 ``tools/reference_pipeline.py``\ 가 계산합니다.
* 고친 뒤 저장소 루트에서 아래 명령으로 다시 만들고 검사합니다.

.. code-block:: powershell

   python tools/generate_source_data.py
   python tools/build_notebooks.py
   python -m unittest discover tests

* 화면이 바뀌면 ``assets/screenshots``\ 의 같은 이름 파일을 교체합니다.
* 구성도는 ``python tools/build_architecture.py``\ 로 다시 만듭니다. 아이콘 출처는 `구성도 아이콘 출처 <../assets/icon-attribution.rst>`_\ 에 있습니다.
* Ontology 연결 확인: 새 Ontology 환경의 ``ont_chipbalance``\ 를 Operations agent, Data agent, Foundry agent가 데이터 값까지 읽을 수 있게 되면 아래를 Ontology 기준으로 고칩니다.

  - 09장: Ontology agent 대신 Data agent를 만들고 데이터 원본으로 ``ont_chipbalance``\ 를 연결합니다.
  - 11장: ``oa_chipbalance``\ 의 **Knowledge**\ 를 ``eh_chipbalance``\ 에서 ``ont_chipbalance``\ 로 바꾸고, 위험 이벤트(RiskEvent)를 Ontology에서 감시합니다. Eventhouse 만들기 단계를 지우고 ``nb_record_decision``\ 은 Lakehouse에만 기록하게 고칩니다.
  - 12장: 5절 질문을 ``OPT-2``\ 를 반영한 BNK-L1-2의 최저 기말재고(16,763 kg)처럼 값을 묻는 질문으로 바꾸고, note를 지웁니다.
  - 구성도: Eventhouse 카드를 지우고, Ontology에서 Operations agent와 Data agent로 바로 잇습니다.

  확인 방법: Operations agent에서 **Knowledge**\ 를 ``ont_chipbalance``\ 로 두고 **Generate playbook**\ 이 성공하는지, Ontology 엔드포인트의 MCP ``tools/list``\ 에 값을 조회하는 도구(예: ``ask_ontology``)가 있고 호출이 성공하는지 봅니다.
