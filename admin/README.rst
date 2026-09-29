관리자 준비 가이드
==========================

`목차 <../README.rst>`_

Workshop 환경을 준비하고 정리하는 관리자용 문서입니다. 참가자는 이 문서를 보지 않아도 됩니다.
예시는 참가자 ``p001`` 기준입니다. 참가자마다 ``pNNN`` 부분을 바꿔 반복합니다.

준비할 리소스
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 리소스
     - 이 Workshop에서 쓰는 값
   * - Azure Databricks
     - Premium workspace, Unity Catalog 사용
   * - Unity Catalog
     - 카탈로그 ``lab_factory``, 참가자별 스키마 ``lab_pNNN``, 스키마 안의 Volume ``raw``
   * - Compute
     - 참가자별 Classic Compute (Dedicated), DBR 16.4 LTS, 20분 자동 종료
   * - Microsoft Fabric
     - F 용량, 작업 영역 ``factory-pNNN``, Lakehouse ``lh_factory_pNNN``, 스키마 ``gold``
   * - 서비스 주체
     - Databricks가 OneLake에 Gold 테이블을 저장할 때 사용
   * - Secret scope
     - 서비스 주체 인증 정보 ``tenant-id``, ``client-id``, ``client-secret``

1. Azure Databricks
----------------------

#. Pricing tier를 **Premium**\ 으로 선택해 Azure Databricks workspace를 만들고, Unity Catalog 메타스토어에 연결합니다.
#. 참가자의 Microsoft Entra ID 계정을 workspace에 추가합니다.
#. SQL editor나 Notebook에서 카탈로그, 스키마, Volume을 만들고 참가자에게 권한을 줍니다.

.. code-block:: sql

   CREATE CATALOG IF NOT EXISTS lab_factory;
   CREATE SCHEMA IF NOT EXISTS lab_factory.lab_p001;
   CREATE VOLUME IF NOT EXISTS lab_factory.lab_p001.raw;

   GRANT USE CATALOG ON CATALOG lab_factory TO `p001@contoso.com`;
   GRANT USE SCHEMA, CREATE TABLE ON SCHEMA lab_factory.lab_p001 TO `p001@contoso.com`;
   GRANT READ VOLUME, WRITE VOLUME ON VOLUME lab_factory.lab_p001.raw TO `p001@contoso.com`;

* 메타스토어에 기본 저장소가 없으면 ``CREATE CATALOG``\ 에 ``MANAGED LOCATION``\ 을 지정합니다.
* 참가자는 본인 스키마에만 권한을 받습니다. Bronze·Silver 테이블은 참가자가 03 Notebook에서 만듭니다.

참가자마다 Classic Compute를 하나씩 만듭니다. Serverless는 사용하지 않습니다.

* Access mode: **Dedicated** (single user), 해당 참가자 한 명
* Databricks Runtime: **16.4 LTS**
* Worker 1대, 자동 크기 조정 끔 (이 환경: Standard_D4as_v5)
* 자동 종료: 20분
* 권한: 해당 참가자에게 **Can Restart** (자동 종료된 Compute를 다시 시작할 수 있음)

2. Microsoft Fabric
----------------------

#. Fabric 용량을 만듭니다. F2 이상이면 됩니다. 이 환경은 F2로 준비했고 최대 F64까지 늘릴 수 있습니다.
#. 참가자마다 작업 영역 ``factory-p001``\ 을 만들고 위 용량에 할당합니다.
#. 작업 영역의 **Manage access**\ 에서 참가자를 **Contributor**\ 로 추가합니다.
#. **New item** > **Lakehouse**\ 에서 ``lh_factory_p001``\ 을 만듭니다. **Lakehouse schemas** 옵션을 켭니다.
#. Lakehouse에서 **Tables** 옆 **…** > **New schema**\ 로 ``gold`` 스키마를 만듭니다.
   테이블은 미리 만들지 않습니다. 참가자가 04 Notebook을 실행하면 Databricks가 만듭니다.

참가자는 Power BI 보고서를 만들므로 Power BI 사용자 라이선스(Pro 등)가 필요합니다.

**Admin portal** > **Tenant settings**\ 에서 아래 설정을 켭니다. 위쪽 검색 창에서 키워드로 찾으면 빠릅니다.

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - 설정
     - 필요한 이유
   * - Users can access data stored in OneLake with apps external to Fabric (기본값: 켜짐)
     - Databricks가 OneLake에 Gold 테이블 저장
   * - Ontology (preview) 항목 만들기
     - Fabric IQ Ontology
   * - Users can use Copilot and other features powered by Azure OpenAI
     - Data agent 등 AI 기능
   * - Data agent 항목 만들기와 공유
     - 긴급 오더 대응안 제안
   * - Azure OpenAI 데이터의 지역 간 처리 (cross-geo processing)
     - 용량이 미국·EU 밖에 있을 때만

3. 서비스 주체와 secret scope
--------------------------------

Databricks는 서비스 주체로 인증해 OneLake에 Gold 테이블을 씁니다.

#. **Microsoft Entra ID** > **App registrations** > **New registration**\ 에서 앱을 만듭니다.
#. 앱의 **Overview**\ 에서 Directory (tenant) ID와 Application (client) ID를 확인합니다.
#. **Certificates & secrets** > **New client secret**\ 에서 유효 기간을 짧게 정해 secret을 만들고 **Value**\ 를 복사합니다.
   **Secret ID**\ 는 인증에 쓰지 않습니다.
#. Fabric 작업 영역 ``factory-p001``\ 의 **Manage access**\ 에서 이 서비스 주체를 **Contributor**\ 로 추가합니다.
#. Databricks CLI로 secret scope를 만들고 세 값을 넣습니다. ``put-secret``\ 을 실행하면 값을 입력하는 프롬프트가 나옵니다.

.. code-block:: powershell

   databricks secrets create-scope <scope-name>
   databricks secrets put-secret <scope-name> tenant-id
   databricks secrets put-secret <scope-name> client-id
   databricks secrets put-secret <scope-name> client-secret
   databricks secrets put-acl <scope-name> <participant-email> READ

``tenant-id``\ 에는 Directory (tenant) ID, ``client-id``\ 에는 Application (client) ID,
``client-secret``\ 에는 client secret의 **Value**\ 를 넣습니다.

* secret 값은 Notebook, Git, 메일, 채팅에 넣지 않습니다. 참가자에게는 scope 이름만 알려 줍니다.
* Contributor는 작업 영역 전체에 쓸 수 있는 권한입니다. 참가자마다 서비스 주체와 scope를 따로 만들면,
  한 참가자의 인증 정보로 다른 참가자의 작업 영역에 쓸 수 없습니다.
* client secret은 Workshop이 끝나면 삭제합니다.

4. 네트워크
--------------

* Databricks Compute에서 아래 두 주소로 HTTPS(443) 연결이 되어야 합니다. 방화벽이나 프록시를 쓰면 허용합니다.

  - ``onelake.dfs.fabric.microsoft.com`` (Gold 저장)
  - ``login.microsoftonline.com`` (서비스 주체 인증)

* Unity Catalog 저장소를 private endpoint로 연결했다면, Compute에서 저장소 주소가 사설 IP로 해석되도록 private DNS를 구성합니다.

5. 참가자에게 알려 줄 값
---------------------------

* Databricks 주소 (예: ``https://adb-<번호>.<번호>.azuredatabricks.net``)
* 참가자 번호(예: ``p001``)와 배정한 Compute 이름
* Fabric 작업 영역과 Lakehouse 이름 (예: ``factory-p001``, ``lh_factory_p001``). ID는 참가자가 주소 창에서 복사합니다.
* secret scope 이름. 값은 알려 주지 않습니다.
* 실습 파일: GitHub 저장소 접근 권한 또는 ZIP 파일

6. 종료 후 정리
------------------

#. 참가자 Compute를 모두 **Terminate**\ 합니다.
#. 서비스 주체의 client secret을 삭제하고, ``databricks secrets delete-scope <scope-name>``\ 으로 scope를 삭제합니다.
#. (선택) 실습 데이터를 지웁니다. Fabric 항목은 용량을 일시 중지하기 전에 지웁니다.

   - Unity Catalog ``lab_factory.lab_pNNN``: ``chip_bronze_*`` 테이블 6개, ``chip_silver_*`` 테이블 7개
   - Volume: ``/Volumes/lab_factory/lab_pNNN/raw/chip_balance`` 폴더
   - Lakehouse ``lh_factory_pNNN``: ``gold.chip_*`` 테이블 9개
   - 작업 영역 ``factory-pNNN``: 참가자가 만든 rpt·sm·ont·da 항목 (보고서, 시맨틱 모델, Ontology, Data agent)

#. Azure portal에서 Fabric 용량을 **Pause**\ 합니다.

7. 교재 유지보수
-------------------

* Notebook 내용은 ``src/notebooks/*.py``\ 에서 고칩니다. ``notebooks/*.ipynb``\ 는 직접 고치지 않습니다.
* 고친 뒤 저장소 루트에서 아래 명령으로 .ipynb를 다시 만들고 검사합니다.

.. code-block:: powershell

   python tools/build_notebooks.py
   python -m unittest discover tests

* ``tests/test_expected_numbers.py``\ 는 계산 예상값을, ``tests/test_docs.py``\ 는 문서 링크·이미지와 Notebook 파일을 검사합니다.
* 화면이 바뀌면 ``assets/screenshots``\ 의 같은 이름 파일을 교체합니다.
