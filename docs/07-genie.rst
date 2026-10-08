07. 정답 계산과 Genie
=====================

`목차 <../README.rst>`_ | 이전: `06. 긴급 수주와 대응안 <06-emergency-order.rst>`_ | 다음: `08. Ontology <08-ontology.rst>`_

Gold는 Fabric Lakehouse(OneLake)에만 있습니다. 이 장에서는 ``07_answers``\ 로 OneLake의 Gold에서 질문 6개의 정답을 계산합니다.
이 정답은 09장에서 Fabric의 Ontology agent에 같은 질문을 했을 때의 답과 비교하는 기준 값입니다.

Gold가 Unity Catalog에 없으므로, Genie가 Gold를 보려면 OneLake를 Unity Catalog에 연결해야 합니다. 이 연결은 선택 확장이며 관리자가 미리 설정해 둔 경우에만 쓸 수 있습니다. 아래 "선택 확장: Genie로 같은 질문하기
--------------------------------

Genie는 Unity Catalog의 테이블을 읽고 질문을 SQL로 바꿉니다. Gold는 OneLake에만 있으므로, OneLake의 Lakehouse를 Unity Catalog의 **Foreign Catalog**\ 로 연결해 두었을 때만 Genie로 질문할 수 있습니다. 복사 없이 메타데이터만 연결합니다.
Foreign Catalog는 관리자가 ``admin/00_admin_setup`` 6단계에서 만들며, 참가자는 ``fabric_chipbalance_<참가자>`` 카탈로그를 사용합니다. (설정 방법은 `admin README <../admin/README.rst>`_ 를 봅니다.)

* **읽기 전용입니다.** SELECT만 되고 ``COMMENT ON`` 같은 쓰기는 되지 않습니다. 그래서 테이블·열 설명 대신 Genie Agent의 General Instructions에 업무 규칙을 적습니다.
* 연결된 Gold의 이름은 ``fabric_chipbalance_<참가자>.gold.<테이블>``\ 입니다.
* 질문을 실행하려면 SQL warehouse(관리자가 만든 ``chipbalance-pro``)가 필요합니다.
* 자세한 연결 방식은 `OneLake catalog federation <https://learn.microsoft.com/azure/databricks/query-federation/onelake>`_\ 을 따릅니다.

1. Genie Agent 만들기
~~~~~~~~~~~~~~~~~~~~~

#. 왼쪽 메뉴에서 **Genie Agents**\ 를 열고 **New**\ 를 누릅니다.
#. 데이터에서 ``fabric_chipbalance_<참가자>`` 카탈로그의 ``gold`` 스키마를 열고 테이블 21개를 모두 선택한 뒤 **Create**\ 를 누릅니다.
#. 목록에 테이블이 18개만 보이면 06장을 다시 실행하고 새 창에서 다시 엽니다. (목록이 캐시되어 있을 수 있습니다.)
#. 오른쪽 위 **Configure**\ 의 **About**\ 에서 이름을 ``Chip Balance 원료 수급``\ 으로 바꾸고, Default warehouse를 ``chipbalance-pro``\ 로 지정합니다.

2. General Instructions 넣기
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instructions 없이 Q1을 물으면 baseline 질문인데 emergency 수치를 섞어 "BNK-L3-2가 안전재고 아래로 내려간다"고 잘못 답합니다. 두 시나리오가 같은 테이블에 ``scenario_id``\ 로 함께 있기 때문입니다.
**Configure > Instructions**\ 에 다음 내용을 넣고 **Save**\ 를 누릅니다.

.. code-block:: text

   이 Agent는 Chip Balance 시나리오(PET 칩 원료 수급)를 다룬다. 모든 fact 테이블에는 scenario_id가 있다. baseline은 긴급 오더를 반영하지 않은 현재 계획, emergency는 긴급 오더를 반영한 계획이다. 질문에 시나리오가 명시되면 반드시 그 scenario_id로 필터하고 두 시나리오를 섞지 않는다. 안전재고 아래로 내려간 Bunker는 gold_fact_bunker_summary의 below_safety_days > 0 으로 판단한다. 답변은 한국어로, 정답 값과 근거(Bunker, 날짜, kg)를 함께 보여준다.

.. image:: ../assets/screenshots/d07-genie-instructions.png
   :alt: Genie Agent의 Configure 패널 Instructions 탭. General Instructions에 시나리오와 안전재고 판단 규칙이 입력되어 있습니다.
   :width: 900

3. 질문 6개 하기
~~~~~~~~~~~~~~~~

위 표의 질문 6개를 **하나씩 새 대화**\ 로 묻고, 답을 표의 정답과 비교합니다. 질문마다 1~3분 걸립니다.

**예상 결과:** 6개 모두 표의 정답과 같은 값을 답합니다. (Q2 BNK-L3-2 -23,630 kg, Q4 BNK-L1-2 최저 16,763 kg, Q6 OPT-2 등)

.. image:: ../assets/screenshots/d07-genie-answer.png
   :alt: Genie Agent의 Q4 답변. BNK-L1-2에서 BNK-L3-2로 R-01 경로, 40,000 kg 이송을 설명하고 이송 후 재고 추이 차트를 보여줍니다.
   :width: 900
Troubleshooting
---------------

* **1. 설정과 Gold 불러오기**\ 에서 오류가 나면 05장과 06장을 순서대로 먼저 실행합니다. 이 Notebook은 두 장이 OneLake에 저장한 Gold를 읽습니다.
* ``service credential`` 오류가 나면 01장 **5. OneLake 연결 확인**\ 을 다시 실행합니다.
* 06장을 다시 실행하면 Gold가 바뀌므로 이 Notebook도 다시 실행합니다.

다음 단계
------------

`08. Ontology <08-ontology.rst>`_
