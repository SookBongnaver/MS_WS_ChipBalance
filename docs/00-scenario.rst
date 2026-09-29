00. 시나리오와 실습 순서
==================================

`목차 <../README.rst>`_ | 다음: `01. Databricks 접속과 설정 <01-connect.rst>`_

이번 Workshop에서 할 일
--------------------------

* Azure Databricks에서 교육용 원본 데이터를 만들고, Bronze → Silver로 정제한 뒤 날짜별 원료 재고를 계산해 Gold를 만듭니다.
* Gold를 Microsoft Fabric OneLake의 Lakehouse에 저장합니다.
* Fabric에서 Gold로 Power BI 보고서와 Fabric IQ Ontology를 만들어 원료 수급 현황과 부족 지점을 파악합니다.
* 긴급 오더가 들어오면 Fabric Data agent가 Gold를 근거로 대응안을 제안하고, 담당자가 확인해 결정합니다.

문제 상황
------------

필름 생산 담당자는 9월 생산계획에 맞춰 원료 Chip이 날짜별로 충분한지 관리합니다.
9월 5일 FILM-A 생산량을 100kg에서 120kg으로 늘리는 긴급 오더가 접수되었습니다.
담당자는 원료가 언제부터 부족해지는지 다시 계산하고, 대응안을 정해야 합니다.

Workshop에서 확인할 질문은 세 가지입니다.

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

재고는 날짜마다 아래처럼 계산합니다. 입고는 그날 생산 전에 쓸 수 있다고 가정합니다.

.. code-block:: text

   당일 마감 재고 = 전일 마감 재고 + 당일 입고 − 당일 Chip 소요량

* **안전재고 미만:** 마감 재고가 200kg보다 적은 날입니다.
* **부족:** 마감 재고가 0kg보다 적은 날입니다. 음수는 실제 재고가 아니라, 계획대로 생산하면 모자라는 양입니다.
* **추가 확보량:** 9월 내내 안전재고를 지키려면 월초에 더 있어야 했던 양입니다. (안전재고 − 9월 최저 마감 재고, 0보다 작으면 0)

데이터 흐름
--------------

.. code-block:: text

   [Azure Databricks]
     02_source_data      교육용 원본 6종 → Volume에 JSON 파일로 저장
     03_bronze_silver    Bronze 테이블 → Silver 테이블 (중복 제거, 결측 격리, 형식 변환)
     04_gold_baseline    기준 계획 계산
     05_emergency_order  긴급 오더 계산, 기준 계획과 비교, 대응안
          │
          │  Gold 테이블 9개를 OneLake에 직접 저장
          ▼
   [Microsoft Fabric] Lakehouse lh_factory_p001 / gold 스키마
          ├─▶ SQL analytics endpoint: 저장 결과 확인
          ├─▶ Semantic model → Power BI 보고서: 원료 수급 현황
          ├─▶ Fabric IQ Ontology: 원료·Bunker·생산계획·대응안 관계 탐색
          └─▶ Fabric Data agent: 대응안 제안 (읽기 전용)

정제와 계산은 Databricks가 합니다. Fabric은 저장된 Gold를 읽어 현황 파악과 의사결정에 사용합니다.
Bronze·Silver 테이블은 Databricks의 Unity Catalog(``lab_factory.lab_p001``)에 남습니다.
전체 구성은 `구성도 <../assets/architecture.png>`_\ 에서 볼 수 있습니다.

의사결정 흐름
----------------

긴급 오더에는 네 단계로 대응합니다.

.. list-table::
   :header-rows: 1
   :widths: 18 27 55

   * - 단계
     - 어디서
     - 이번 Workshop에서 하는 일
   * - 1\. 현재 계산
     - Databricks 04·05 Notebook, Power BI
     - 기준 계획과 긴급 오더의 날짜별 재고, 첫 안전재고 미만일, 첫 부족일, 추가 확보량을 계산하고 비교합니다.
   * - 2\. 판단 기준
     - Databricks 05 Notebook
     - 대응안마다 두 기준을 확인합니다. 9월 모든 날의 마감 재고가 안전재고(200kg) 이상인가?
       입고 직후 Bunker 재고가 용량(3,000kg) 이하인가?
   * - 3\. Agent 제안
     - Fabric Data agent (07장)
     - Agent가 Gold 결과를 근거로 대응안을 제안합니다.
   * - 4\. 사람 승인
     - 담당자 (07장)
     - 담당자가 근거를 확인하고 결정합니다. 실제 발주나 메일 발송은 하지 않습니다.

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
