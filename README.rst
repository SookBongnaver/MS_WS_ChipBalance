Workshop: 원료 Chip Balance와 긴급 오더 대응
============================================================

필름 공장의 원료 Chip 재고를 예로, 생산계획대로 생산할 때 Chip이 언제 부족해지는지 계산하는 hands-on Workshop입니다.
Azure Databricks에서 데이터를 만들고 계산해 Microsoft Fabric OneLake에 저장하고,
Fabric에서 Power BI 보고서와 Fabric IQ Ontology로 결과를 활용합니다.
마지막으로 긴급 오더가 들어왔을 때 대응안을 정하는 의사결정 흐름을 직접 따라 해 봅니다.

.. code-block:: text

   [Azure Databricks]
     02 원본 데이터 → 03 Bronze·Silver → 04·05 Gold 계산
           │
           │  Gold 테이블 9개를 OneLake에 직접 저장
           ▼
   [Microsoft Fabric]
     Lakehouse gold → SQL 확인 → Power BI → Ontology → 긴급 오더 의사결정

실습 순서
------------

* `00. 시나리오와 실습 순서 <docs/00-scenario.rst>`_ — 문제 상황과 데이터 관계를 이해하고 실습 파일을 내려받습니다.
* `01. Databricks 접속과 설정 <docs/01-connect.rst>`_ — Notebook을 가져오고 Compute를 연결한 뒤 설정값을 입력합니다.
* `02. 원본 데이터 만들기 <docs/02-source-data.rst>`_ — 9월 교육용 데이터를 만들어 Volume에 JSON 파일로 저장합니다.
* `03. Bronze와 Silver <docs/03-bronze-silver.rst>`_ — 원본을 Bronze 테이블로 적재하고, 중복·결측을 정리해 Silver를 만듭니다.
* `04. Gold 계산과 OneLake 저장 <docs/04-gold-onelake.rst>`_ — 날짜별 원료 재고를 계산해 Fabric Lakehouse에 저장하고 확인합니다.
* `05. Power BI 보고서 <docs/05-power-bi.rst>`_ — Gold 테이블로 원료 재고 보고서를 만듭니다. (작성 중)
* `06. Fabric IQ Ontology <docs/06-ontology.rst>`_ — 원료·Bunker·생산계획의 관계를 Ontology로 만들고 탐색합니다. (작성 중)
* `07. 긴급 오더와 의사결정 <docs/07-emergency-decision.rst>`_ — 긴급 오더를 계산해 비교하고, Agent 제안과 사람 승인으로 대응안을 정합니다. (작성 중)
* `08. 마무리 <docs/08-finish.rst>`_ — 결과를 정리하고 Workshop을 마칩니다. (작성 중)

참가자 파일
--------------

``notebooks`` 폴더의 파일 5개를 Databricks로 가져와 사용합니다.

* ``01_setup.ipynb`` — 설정값과 공통 함수. 02~05 Notebook이 이 Notebook을 불러옵니다.
* ``02_source_data.ipynb`` — 교육용 원본 데이터 6종을 만들어 Volume에 저장합니다.
* ``03_bronze_silver.ipynb`` — 원본을 Bronze로 적재하고, 정리한 결과를 Silver로 저장합니다.
* ``04_gold_baseline.ipynb`` — 기준 계획의 날짜별 재고를 계산해 OneLake에 Gold로 저장합니다.
* ``05_emergency_order.ipynb`` — 긴급 오더를 계산해 기준 계획과 비교하고 대응안을 저장합니다.

준비된 환경
--------------

관리자가 환경을 미리 준비하고 아래 값을 알려 줍니다.

* Databricks 주소와 배정받은 Compute 이름
* 참가자 번호 (예: ``p001``)
* Fabric 작업 영역 (예: ``factory-p001``)과 Lakehouse (예: ``lh_factory_p001``)
* OneLake 저장에 쓰는 secret scope 이름

관리자용
-----------

* `관리자 준비 가이드 <admin/README.rst>`_ — 환경 준비와 종료 후 정리 방법입니다. 참가자는 보지 않아도 됩니다.
