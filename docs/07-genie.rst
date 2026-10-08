07. 정답 계산과 Genie
=====================

`목차 <../README.rst>`_ | 이전: `06. 긴급 수주와 대응안 <06-emergency-order.rst>`_ | 다음: `08. Ontology <08-ontology.rst>`_

Gold는 Fabric Lakehouse(OneLake)에만 있습니다. 이 장에서는 ``07_answers``\ 로 OneLake의 Gold에서 질문 6개의 정답을 계산합니다.
이 정답은 09장에서 Fabric의 Ontology agent에 같은 질문을 했을 때의 답과 비교하는 기준 값입니다.

Gold가 Unity Catalog에 없으므로, Genie가 Gold를 보려면 OneLake를 Unity Catalog에 연결해야 합니다. 이 연결은 선택 확장입니다. 아래 "선택 확장: Genie로 같은 질문하기"를 봅니다.

1. 정답 계산
--------------

#. ``ChipBalance`` 폴더에서 ``07_answers``\ 를 엽니다.
#. 오른쪽 위 Compute 목록에 **Serverless**\ 가 선택되어 있는지 확인합니다.
#. 위에서부터 **Shift+Enter**\ 로 한 셀씩 실행합니다. 위쪽 **Run all**\ 로 한 번에 실행해도 됩니다. (1~2분)

**예상 결과:** **1. 설정과 Gold 불러오기**\ 에서 ``OneLake에서 불러온 Gold: 21개``\ 가 표시되고, **2. Genie 질문의 정답**\ 에서 6행 표가 나옵니다.

.. image:: ../assets/screenshots/d07-answers.png
   :alt: 2. Genie 질문의 정답 셀 결과. 번호, 정답, 근거 열이 있는 6행 표입니다. Q1 없음, Q2 BNK-L3-2, Q3 모두 준수, Q4 BNK-L1-2, Q5 10/09, Q6 OPT-2입니다.
   :width: 900

.. list-table::
   :header-rows: 1
   :widths: 6 50 44

   * - 번호
     - 질문
     - 정답
   * - Q1
     - 긴급 오더를 반영하지 않은 현재 계획에서 4분기에 안전재고 아래로 내려가는 Bunker가 있어?
     - 없음
   * - Q2
     - 긴급 오더를 반영하면 어느 Bunker가 언제부터 안전재고 아래로 내려가고, 얼마나 부족해?
     - BNK-L3-2. 10/06부터 미달, 10/07부터 부족, 최저 -23,630 kg (11/26), 필요 보충량 35,630 kg
   * - Q3
     - 긴급 오더 때문에 미뤄진 생산의 판매오더는 납기를 지켜?
     - 모두 준수. SO-10108, SO-10109, SO-10110
   * - Q4
     - BNK-L3-2로 PET-SD를 보내 줄 수 있는 Bunker는 어디야? 이송 대응안대로 보내면 보내는 Bunker의 재고는 괜찮아?
     - BNK-L1-2 (R-01). 이송 후 최저 16,763 kg, 안전재고 6,000 kg 이상
   * - Q5
     - BNK-L3-2에 10월 6일 뒤 처음 들어오는 PET-SD 입고는 언제, 어느 공급사에서, 몇 kg이야?
     - 10/09, SUP-PET-B(세미폴리머), 25,000 kg
   * - Q6
     - 대응안 4개 가운데 판단 기준을 모두 만족하는 안과 추천안은?
     - OPT-2(1순위), OPT-3(2순위). 추천안은 OPT-2

같은 6개 질문을 09장에서 Fabric의 Ontology agent에도 합니다.

선택 확장: Genie로 같은 질문하기
--------------------------------

Genie는 Unity Catalog의 테이블과 설명을 읽고 질문을 SQL로 바꿉니다. Gold를 Unity Catalog에 만들지 않으므로, Genie로 질문하려면 OneLake의 Lakehouse를 Unity Catalog의 **Foreign Catalog**\ 로 연결해야 합니다.
복사 없이 메타데이터만 연결합니다.

* **읽기 전용입니다.** SELECT만 되고 쓰기는 되지 않습니다. 테이블·열 설명을 Unity Catalog에 쓰는 방식(Genie Code로 ``COMMENT ON``\ )이 연결된 카탈로그에서 되는지는 이 Workshop에서 확인하지 않았습니다.
* 필요 조건: Databricks Runtime 18.0 이상과 Standard access mode(Serverless는 확인이 필요합니다), Fabric 관리자의 테넌트 설정 3개, Fabric 작업 영역의 OneLake 설정, Unity Catalog의 storage credential·Connection·Foreign Catalog.
* 연결된 Gold의 이름은 ``<foreign catalog>.gold.fact_balance``\ 처럼 Lakehouse의 ``gold`` 스키마를 따릅니다.
* 설정 방법은 `OneLake catalog federation <https://learn.microsoft.com/azure/databricks/query-federation/onelake>`_\ 를 따릅니다.

이 확장은 아직 Workshop 순서에 넣지 않았습니다. 확인되면 Genie Agent로 위 질문 6개를 하고 정답과 비교하는 단계를 이 장에 추가합니다.

Troubleshooting
---------------

* **1. 설정과 Gold 불러오기**\ 에서 오류가 나면 05장과 06장을 순서대로 먼저 실행합니다. 이 Notebook은 두 장이 OneLake에 저장한 Gold를 읽습니다.
* ``service credential`` 오류가 나면 01장 **5. OneLake 연결 확인**\ 을 다시 실행합니다.
* 06장을 다시 실행하면 Gold가 바뀌므로 이 Notebook도 다시 실행합니다.

다음 단계
------------

`08. Ontology <08-ontology.rst>`_
