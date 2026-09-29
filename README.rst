Workshop: 원료 Chip Balance와 긴급 오더 대응
============================================================

필름 공장의 원료 Chip 재고와 긴급 오더 대응을 주제로 한 hands-on Workshop입니다.

* **Azure Databricks:** SAP·FPIMS·PVSS 원천 파일을 Bronze → Silver로 정제하고, 4분기 Bunker별 원료 재고와 긴급 오더 대응안을 계산해 Gold를 만듭니다. Gold는 관리 ID로 Microsoft Fabric OneLake에 저장합니다.
* **Microsoft Fabric:** Gold로 Power BI 보고서와 Fabric IQ Ontology를 만들어 원료 수급 현황과 부족 지점을 파악합니다.
* **의사결정:** Fabric IQ Operations agent가 Ontology를 확인해 대응안을 Microsoft Teams로 제안하고, 담당자가 Teams에서 승인합니다.
* **질문:** 담당자는 Microsoft 365 Copilot 채팅으로 Fabric Data agent에 재고와 대응안을 묻습니다.

전체 구성
------------

.. image:: assets/architecture.svg
   :alt: 전체 구성. Azure Databricks가 원천 파일을 Bronze, Silver로 정제하고 Gold를 계산해 OneLake에 저장합니다. Microsoft Fabric은 같은 Gold로 Semantic model과 Power BI 보고서, Ontology를 만들고, Data agent와 Operations agent가 Ontology를 근거로 동작합니다. 담당자는 Microsoft Teams에서 Operations agent의 제안을 승인하고, Microsoft 365 Copilot 채팅으로 Data agent에 질문합니다.
   :width: 1000

`그림 크게 보기 <assets/architecture.png>`_

실선은 실습에서 만들고 실행하는 흐름입니다. 점선의 원천 시스템 연계, Power Apps, Power Automate는 운영에 적용할 때 연결합니다. 승인은 Teams에서 끝나므로 Power Apps가 없어도 됩니다.

실습 순서
------------

* `00. 시나리오와 실습 순서 <docs/00-scenario.rst>`_ — 업무 상황, 원천 데이터, 계산 방식을 확인하고 실습 파일을 내려받습니다.
* `01. Databricks 접속과 설정 <docs/01-connect.rst>`_ — Notebook을 가져오고 Compute를 연결한 뒤, 관리 ID로 OneLake 연결을 확인합니다.
* `02. 원천 데이터 올리기 <docs/02-source-data.rst>`_ — SAP·FPIMS·PVSS 원천 파일 14개를 Volume에 올리고, 원료·Bunker·생산계획의 관계를 확인합니다.
* `03. Bronze와 Silver <docs/03-bronze-silver.rst>`_ — 원천 파일을 Bronze로 적재하고, 형식·단위·중복·이상값을 정리해 Silver를 만듭니다. (작성 중)
* `04. Gold 계산과 OneLake 저장 <docs/04-gold-onelake.rst>`_ — 실제 소요량과 4분기 날짜별 재고를 계산해 Fabric Lakehouse에 저장합니다. (작성 중)
* `05. Power BI 보고서 <docs/05-power-bi.rst>`_ — Gold로 원료 수급 보고서를 만듭니다. (작성 중)
* `06. Ontology와 Data agent <docs/06-ontology.rst>`_ — 라인·Bunker·원료·생산계획의 관계를 Ontology로 만들고, Data agent를 만들어 질문합니다. (작성 중)
* `07. 긴급 오더와 Operations agent <docs/07-emergency-decision.rst>`_ — 긴급 오더와 대응안을 계산하고, Operations agent의 제안을 Teams에서 승인합니다. (작성 중)
* `08. 마무리 <docs/08-finish.rst>`_ — 결과를 정리하고 Workshop을 마칩니다. (작성 중)

실습 파일
------------

* ``notebooks/ChipBalance.zip`` — Databricks로 한 번에 가져오는 Notebook 5개입니다. 같은 내용을 ``notebooks/*.ipynb``\ 로도 볼 수 있습니다.
* ``data`` — SAP·FPIMS·PVSS 원천 파일 14개입니다.

관리자에게 받을 값은 Databricks 주소, 참가자 번호(예: ``p001``), 배정받은 Compute 이름입니다.

관리자용
-----------

* `관리자 준비 가이드 <admin/README.rst>`_ — 환경 준비와 종료 후 정리 방법입니다. 참가자는 보지 않아도 됩니다.
* `데이터 설계 <admin/data-design.rst>`_ — 원천·Silver·Gold 테이블 구조, 계산 규칙, 예상 결과입니다.
* `구성도 아이콘 출처 <assets/icon-attribution.rst>`_ — 구성도에 쓴 공식 아이콘과 그림을 다시 만드는 방법입니다.