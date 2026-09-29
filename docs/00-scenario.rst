00. 시나리오와 실습 순서
==================================

`목차 <../README.rst>`_ | 다음: `01. Databricks 접속과 설정 <01-connect.rst>`_

업무 상황
------------

필름 생산 담당자는 9월 생산계획에 맞춰 원료 Chip이 날짜별로 충분한지 관리합니다.
9월 5일 FILM-A 생산량을 100kg에서 120kg으로 늘리는 긴급 오더가 접수되었습니다.
담당자는 원료가 언제부터 부족해지는지 다시 계산하고, 대응안을 정해야 합니다.

확인할 질문은 세 가지입니다.

#. 기준 계획대로 생산하면 Chip 재고는 언제 안전재고 아래로 내려가는가?
#. 긴급 오더를 반영하면 부족해지는 날과 추가로 확보할 양은 어떻게 달라지는가?
#. 어떤 대응안이 판단 기준을 만족하는가?

데이터와 관계
----------------

원료 Chip은 Bunker에 보관합니다. 제품을 만들 때는 제품 1kg당 정해진 양의 Chip을 씁니다.
수량 단위는 kg이고, 기간은 2026년 9월 1일~30일입니다.

.. code-block:: text

   원료 Chip ──보관──▶ Bunker ──공급──▶ 생산계획
   제품 ──소요량 기준──▶ 원료 Chip
   입고예정 ──입고──▶ Bunker

.. list-table::
   :header-rows: 1
   :widths: 34 33 33

   * - 항목
     - CHIP-A / BNK-A
     - CHIP-B / BNK-B
   * - Bunker 용량
     - 3,000kg
     - 3,000kg
   * - 안전재고
     - 200kg
     - 200kg
   * - 9월 1일 시작 재고
     - 1,000kg
     - 1,000kg
   * - 이 Chip을 쓰는 제품
     - FILM-A
     - FILM-B
   * - 제품 1kg당 Chip 소요량
     - 1.0kg
     - 1.25kg
   * - 일별 생산계획 (9/1~9/30)
     - FILM-A 100kg
     - FILM-B 40kg
   * - 일별 Chip 소요량
     - 100kg
     - 50kg
   * - 입고예정
     - 9/12 1,000kg (R-A-12), 9/22 1,000kg (R-A-22)
     - 9/15 1,000kg (R-B-15)

재고는 날짜마다 아래처럼 계산합니다. 그날 들어온 입고는 그날 생산에 바로 씁니다.

.. code-block:: text

   당일 마감 재고 = 전일 마감 재고 + 당일 입고 − 당일 Chip 소요량

* **안전재고 미만:** 마감 재고가 200kg보다 적은 날입니다.
* **부족:** 마감 재고가 0kg보다 적은 날입니다. 음수는 계획대로 생산하면 모자라는 양입니다.
* **추가 확보량:** 9월 내내 안전재고를 지키려면 월초에 더 있어야 했던 양입니다. (안전재고 − 9월 최저 마감 재고, 0보다 작으면 0)

데이터 흐름
--------------

.. image:: ../assets/architecture.svg
   :alt: 전체 구성. Azure Databricks가 원본을 Bronze, Silver로 정제하고 Gold를 계산해 OneLake에 저장합니다. Microsoft Fabric은 같은 Gold로 Semantic model과 Power BI 보고서, Ontology를 만들고, Operations agent가 Teams로 대응안을 제안하면 담당자가 승인합니다.
   :width: 1000

* **Azure Databricks** — 원본을 Bronze → Silver로 정제하고, 원료 재고와 대응안을 계산해 Gold 9개를 OneLake에 저장합니다.
* **Microsoft Fabric** — Gold로 Power BI 보고서와 Ontology를 만들어 원료 수급 현황과 부족 지점을 파악합니다.
* **Operations agent · Teams** — 판단 기준을 만족한 대응안을 Teams로 제안하고, 담당자가 Teams에서 승인합니다.

의사결정 흐름
----------------

#. **현재 계산** — Databricks에서 기준 계획과 긴급 오더의 날짜별 재고를 계산하고 Power BI로 비교합니다.
#. **판단 기준** — 대응안마다 매일 안전재고 200kg 이상, 입고 직후 용량 3,000kg 이하인지 확인합니다.
#. **Agent 제안** — Operations agent가 판단 기준을 만족한 대응안을 Teams로 보냅니다.
#. **사람 승인** — 담당자가 Teams에서 승인하면 승인 내역이 저장됩니다. 발주는 기존 절차로 진행합니다.
실습 순서
------------

전체 약 3시간입니다.

* 00\. 시나리오와 실습 순서 — 10분 (이 문서)
* `01. Databricks 접속과 설정 <01-connect.rst>`_ — Databricks, 20분
* `02. 원본 데이터 만들기 <02-source-data.rst>`_ — Databricks, 15분
* `03. Bronze와 Silver <03-bronze-silver.rst>`_ — Databricks, 20분
* `04. Gold 계산과 OneLake 저장 <04-gold-onelake.rst>`_ — Databricks → Fabric, 25분
* `05. Power BI 보고서 <05-power-bi.rst>`_ — Fabric, 30분
* `06. Fabric IQ Ontology <06-ontology.rst>`_ — Fabric, 30분
* `07. 긴급 오더와 의사결정 <07-emergency-decision.rst>`_ — Databricks → Fabric, 25분
* `08. 마무리 <08-finish.rst>`_ — 5분

실습 파일 내려받기
---------------------

#. 브라우저에서 GitHub 저장소를 엽니다: https://github.com/SookBongnaver/MS_WS_ChipBalance

   비공개 저장소이므로 접근 권한이 있는 GitHub 계정으로 로그인합니다.

#. 파일 목록 위의 **Code** > **Download ZIP**\ 을 누릅니다.
#. 내려받은 ZIP 파일의 압축을 풉니다.
#. 압축을 푼 폴더 안의 ``notebooks`` 폴더를 엽니다.

**예상 결과:** 아래 .ipynb 파일 5개가 보입니다. 01장에서 이 파일을 Databricks로 가져옵니다.

.. code-block:: text

   notebooks
     01_setup.ipynb
     02_source_data.ipynb
     03_bronze_silver.ipynb
     04_gold_baseline.ipynb
     05_emergency_order.ipynb

다음 단계
------------

`01. Databricks 접속과 설정 <01-connect.rst>`_
