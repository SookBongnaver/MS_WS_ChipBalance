00. 시나리오와 실습 순서
==================================

`목차 <../README.rst>`_ | 다음: `01. Databricks 접속과 설정 <01-connect.rst>`_

업무 상황
------------

필름 공장 한 곳에 BOPET 라인 4개(L1~L4)와 BOPA 라인 2개(L5·L6)가 있습니다.
라인마다 Bunker 4개에 원료 Chip을 보관하고, 생산계획에 맞춰 Chip을 투입합니다.
생산 담당자는 4분기(2026년 10월 1일~12월 31일) 동안 Bunker별 Chip 재고가 안전재고 아래로 내려가지 않도록 관리합니다.

10월 1일, L3 라인 제품 ``P-L3-05`` 100,000kg 긴급 오더가 접수되었습니다. 납기는 10월 8일입니다.
``P-L3-05``\ 는 제품 1kg에 PET-SD Chip 0.6kg을 쓰며, L3의 다른 제품보다 PET-SD를 4배 이상 많이 씁니다.
담당자는 PET-SD가 언제부터 부족해지는지 계산하고 대응안을 정해야 합니다.

확인할 질문은 세 가지입니다.

#. 기준 계획에서 모든 Bunker의 재고가 4분기 내내 안전재고 이상인가?
#. 긴급 오더를 반영하면 어느 Bunker가 언제부터 안전재고 아래로 내려가고, 얼마나 부족한가?
#. 입고 앞당김, Bunker 간 이송, 추가 구매, 생산 순서 조정 가운데 어떤 대응안이 판단 기준을 만족하는가?

원천 데이터 (가상)
------------------

SAP, FPIMS, PVSS에서 추출한 파일 14개를 씁니다. 모두 41,412행입니다.

.. list-table::
   :header-rows: 1
   :widths: 14 56 16 14

   * - 시스템
     - 데이터
     - 기간
     - 행 수
   * - SAP
     - 원료 Chip 12종과 단가, 공급사 6곳(리드타임, 발주 단위)
     - 기준정보
     - 18
   * - SAP
     - 원료 입고 실적 (약속일, 실제 입고일)
     - 2025-10 ~ 2026-09
     - 1,900
   * - SAP
     - 미결 발주 = 4분기 입고예정 (Bunker별)
     - 2026-10 ~ 12
     - 735
   * - SAP
     - 판매오더 (제품, 수량, 납기)
     - 2026-10 ~ 12
     - 360
   * - FPIMS
     - 라인 6개, Bunker 24개(용량, 안전재고), 제품 30개, 제품별 원료 소요량 기준, Bunker 간 이송 경로
     - 기준정보
     - 190
   * - FPIMS
     - 생산 Lot 실적과 Lot별 원료 투입 실적
     - 2025-10 ~ 2026-09
     - 20,384
   * - FPIMS
     - 생산계획 (라인·일자별 제품과 생산량)
     - 2026-10 ~ 12
     - 547
   * - PVSS
     - Bunker 레벨 센서 (1시간 간격)
     - 2026-09
     - 17,278

데이터와 관계
----------------

.. code-block:: text

   라인 ──보유──▶ Bunker ──보관──▶ 원료 Chip ◀──공급── 공급사
   제품 ──소요량 기준──▶ 원료 Chip
   판매오더 ──▶ 생산계획(라인·일자·제품) ──원료 소요──▶ Bunker
   미결 발주(입고예정) ──입고──▶ Bunker
   Bunker ──이송 경로──▶ 같은 원료를 보관하는 다른 라인의 Bunker
   생산 Lot ──원료 투입 실적──▶ Bunker
   레벨 센서 ──시간별 재고──▶ Bunker

과거 실적으로 계획에 쓸 값을 먼저 구합니다.

* **실제 소요량 기준:** 1년 동안의 원료 투입 실적 ÷ 생산 실적 (제품·원료별). 표준 소요량보다 1~4% 많습니다.
* **10월 1일 시작 재고:** 9월 30일 마지막 정상 센서값
* **입고 예정일:** 발주 약속일 + 공급사의 평균 입고 지연일

그다음 4분기 92일 동안 Bunker별 재고를 날짜마다 계산합니다.

.. code-block:: text

   당일 마감 재고 = 전일 마감 재고 + 입고 + 이송 입고 − 이송 출고 − 원료 소요량
   원료 소요량 = 생산계획(kg) × 실제 소요량 기준

* **안전재고 미만:** 마감 재고가 Bunker의 안전재고보다 적은 날입니다.
* **부족:** 마감 재고가 0kg보다 적은 날입니다. 음수는 계획대로 생산하면 모자라는 양입니다.
* **필요 보충량:** 4분기 내내 안전재고를 지키려면 더 있어야 하는 양입니다. (안전재고 − 최저 마감 재고)

데이터 흐름
--------------

.. image:: ../assets/architecture.svg
   :alt: 전체 구성. Azure Databricks가 원천 파일을 Bronze, Silver로 정제하고 Gold를 계산해 OneLake에 저장합니다. Microsoft Fabric은 같은 Gold로 Semantic model과 Power BI 보고서, Ontology를 만들고, Data agent와 Operations agent가 Ontology를 근거로 동작합니다. 담당자는 Microsoft Teams에서 Operations agent의 제안을 승인하고, Microsoft 365 Copilot 채팅으로 Data agent에 질문합니다.
   :width: 1000

* **Azure Databricks** — 원천 파일을 Bronze → Silver로 정제하고, 재고와 대응안을 계산해 Gold 17개를 OneLake에 저장합니다.
* **Microsoft Fabric** — Gold로 Power BI 보고서와 Ontology를 만들어 원료 수급 현황과 부족 지점을 파악합니다. Operations agent는 대응안을 제안하고, Data agent는 질문에 답합니다.
* **Microsoft 365** — 담당자가 Teams에서 Operations agent의 제안을 받고 승인합니다. Microsoft 365 Copilot 채팅으로 Data agent에 질문합니다.

의사결정 흐름
----------------

#. **현재 계산** — Databricks에서 기준 계획과 긴급 오더의 날짜별 재고를 계산하고 Power BI로 비교합니다.
#. **판단 기준** — 대응안마다 모든 Bunker의 안전재고, Bunker 용량, 판매오더 납기, 이송 한도를 확인합니다.
#. **Agent 제안** — Operations agent가 판단 기준을 만족한 대응안을 Teams로 보냅니다.
#. **사람 승인** — 담당자가 Teams에서 승인하면 승인 내역이 저장됩니다. 발주와 이송 지시는 기존 절차로 진행합니다.

실습 순서
------------

전체 약 6시간 15분입니다.

* 00\. 시나리오와 실습 순서 — 15분 (이 문서)
* `01. Databricks 접속과 설정 <01-connect.rst>`_ — Databricks, 30분
* `02. 원천 데이터 올리기 <02-source-data.rst>`_ — Databricks, 30분
* `03. Bronze와 Silver <03-bronze-silver.rst>`_ — Databricks, 45분
* `04. Gold 계산과 OneLake 저장 <04-gold-onelake.rst>`_ — Databricks → Fabric, 45분
* `05. Power BI 보고서 <05-power-bi.rst>`_ — Fabric, 60분
* `06. Ontology와 Data agent <06-ontology.rst>`_ — Fabric → Microsoft 365, 60분
* `07. 긴급 오더와 Operations agent <07-emergency-decision.rst>`_ — Databricks → Fabric → Teams, 60분
* `08. 마무리 <08-finish.rst>`_ — 15분

실습 파일 내려받기
---------------------

#. 브라우저에서 GitHub 저장소를 엽니다: https://github.com/SookBongnaver/MS_WS_ChipBalance

   비공개 저장소이므로 접근 권한이 있는 GitHub 계정으로 로그인합니다.

#. 파일 목록 위의 **Code** > **Download ZIP**\ 을 누릅니다.
#. 내려받은 ZIP 파일의 압축을 풉니다.

**예상 결과:** 압축을 푼 폴더에 아래 두 가지가 있습니다.

* ``notebooks\ChipBalance.zip`` — 01장에서 Databricks로 가져오는 Notebook 5개
* ``data`` 폴더 — 02장에서 Databricks Volume에 올리는 원천 파일 14개

다음 단계
------------

`01. Databricks 접속과 설정 <01-connect.rst>`_
