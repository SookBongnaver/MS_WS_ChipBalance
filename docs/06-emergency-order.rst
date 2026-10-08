06. 긴급 수주와 대응안
=========================

`목차 <../README.rst>`_ | 이전: `05. Gold와 OneLake <05-gold-onelake.rst>`_ | 다음: `07. 정답 계산과 Genie <07-genie.rst>`_

10월 1일, 고객 누리전자소재가 L3 제품 ``P-L3-05``\ (반광택 75μm 후막) 100,000kg을 10월 8일까지 요청했습니다.
``06_emergency_order``\ 로 긴급 수주를 생산계획에 넣고 Bunker별·날짜별 재고를 다시 계산합니다.
안전재고 아래로 내려가는 Bunker를 찾고, 대응안 4개를 같은 판단 기준으로 확인해 추천안을 정합니다.

.. list-table::
   :header-rows: 1
   :widths: 8 52 40

   * - 순서
     - 계산
     - Gold 테이블
   * - 1
     - 긴급 수주 접수
     - ``gold_fact_sales_order``
   * - 2
     - 긴급 생산계획 (10월 5·6일 긴급 생산, 10월 5~10일 L3 생산을 2일씩 미룸)
     - ``gold_fact_plan``
   * - 3
     - 날짜별 Bunker Balance, Bunker 위험 요약, 판매오더 납기
     - ``gold_fact_balance``, ``gold_fact_bunker_summary``, ``gold_fact_order_fulfillment``
   * - 4
     - 대응안 4개와 판단 기준 C1~C4
     - ``gold_fact_response_option``, ``gold_fact_option_balance``
   * - 5
     - 위험 이벤트와 추천안
     - ``gold_fact_risk_event``

긴급 수주를 반영한 결과는 시나리오 ``emergency``\ 로 저장합니다. 05장의 현재 계획(``baseline``) 행은 그대로 남아 두 시나리오를 비교할 수 있습니다.

1. Notebook 열고 실행
------------------------

#. ``ChipBalance`` 폴더에서 ``06_emergency_order``\ 를 엽니다.
#. 오른쪽 위 Compute 목록에 **Serverless**\ 가 선택되어 있는지 확인합니다.
#. 위에서부터 **Shift+Enter**\ 로 한 셀씩 실행합니다. 위쪽 **Run all**\ 로 한 번에 실행해도 됩니다. 전체 실행에 3~4분 걸립니다.

2. 셀별 결과 확인
--------------------

#. **1. 설정 불러오기**

   **예상 결과:** 01에서 본 결과가 다시 표시되고, 맨 아래에 ``연결 확인 완료``\ 가 보입니다.

#. **2. 긴급 오더 접수**

   긴급 수주의 고객, 제품, 수량, 납기와 긴급 생산 일정을 값으로 넣습니다. 판매오더 번호는 마지막 판매오더 번호의 다음 번호입니다.

   **예상 결과:** 1행. ``SO-10322``, 누리전자소재, ``P-L3-05``, 100,000kg, 납기 2026-10-08

   .. image:: ../assets/screenshots/d06-order.png
      :alt: 2. 긴급 오더 접수 결과. sales_order_id SO-10322, order_date 2026-10-01, customer_name 누리전자소재, product_id P-L3-05, product_name BOPET 반광택 75μm 후막, order_qty_kg 100000, due_date 2026-10-08, priority high인 1행 표입니다.
      :width: 900

#. **3. 긴급 생산계획**

   현재 계획을 복사해 긴급 생산 2행을 넣고, 10월 5~10일 L3 생산을 2일씩 미룹니다.
   ``change_type``\ 은 ``urgent``\ (긴급 생산), ``moved``\ (미룬 생산), ``none``\ (그대로)입니다.

   **예상 결과:** L3 10월 1~16일 13행. 10월 5·6일은 ``P-L3-05`` 긴급 생산이고, ``P-L3-01`` 6행이 10월 7~12일로 밀립니다.
   모든 행에서 생산일(``plan_date``)이 납기(``due_date``)보다 앞섭니다.

   .. image:: ../assets/screenshots/d06-plan.png
      :alt: 3. 긴급 생산계획 결과. plan_date, original_plan_date, change_type, product_id, planned_output_kg, sales_order_id, due_date 열이 있는 13행 표입니다. 2026-10-05와 10-06은 urgent P-L3-05 50000, 10-07부터 10-12는 moved P-L3-01입니다.
      :width: 900

#. **4. Balance 계산 함수**

   05장 **7. 날짜별 Bunker Balance**\ 와 같은 계산을 함수 ``compute_balance``\ 로 만듭니다. 긴급 수주와 대응안마다 다시 계산하기 위해서입니다.

   **예상 결과:** 결과 없이 끝납니다.

#. **5. 긴급 오더를 반영한 Balance**

   ``BNK-L3-2``\ (L3 PET-SD)의 10월 1~12일을 봅니다.

   **예상 결과:** 12행. 10월 5·6일 사용량이 23,162kg으로 늘어, 10월 6일 기말 재고 3,733kg이 안전재고 12,000kg보다 적습니다(``below_safety``).
   10월 7일에는 -2,560kg으로 부족합니다(``shortage``). 10월 9일 입고 25,000kg으로도 안전재고를 회복하지 못합니다.

   .. image:: ../assets/screenshots/d06-balance.png
      :alt: 5. 긴급 오더를 반영한 Balance 결과. balance_date, receipt_kg, requirement_kg, closing_kg, safety_stock_kg, below_safety, shortage 열이 있는 12행 표입니다. 10월 6일 closing 3733, below_safety true이고 10월 7일 closing -2560, shortage true입니다.
      :width: 900

#. **6. Bunker 위험 요약**

   05장과 같은 방식으로 요약하고 현재 계획과 비교합니다.

   **예상 결과:** 1행. 긴급 수주로 안전재고 아래로 내려가는 Bunker는 ``BNK-L3-2``\ 뿐입니다.
   안전재고 미달 일수가 현재 계획 0일에서 긴급 수주 반영 후 57일로 늘고, 10월 6일부터 미달, 10월 7일부터 부족합니다.
   가장 낮은 재고는 11월 26일 -23,630kg이며, 필요 보충량은 35,630kg입니다.

   .. image:: ../assets/screenshots/d06-summary.png
      :alt: 6. Bunker 위험 요약 결과. BNK-L3-2 PET-SD 1행입니다. 현재 계획 미달일 0, 긴급 오더 미달일 57, 첫 미달일 2026-10-06, 첫 부족일 2026-10-07, 최저 재고(kg) -23630, 최저 재고일 2026-11-26, 필요 보충량(kg) 35630입니다.
      :width: 900

#. **7. 판매오더 납기**

   긴급 생산계획으로 판매오더마다 생산 완료일을 다시 구합니다. 생산이 바뀐 오더만 봅니다.

   **예상 결과:** 4행, 모두 ``on_time``\ 이 ``true``\ 입니다. 긴급 수주 ``SO-10322``\ 는 10월 6일에 생산을 마쳐 납기보다 2일 빠릅니다.
   미룬 ``SO-10108``, ``SO-10109``, ``SO-10110``\ 도 납기 안에 끝납니다. 아래에 ``납기 지연: 0개``\ 가 표시됩니다.

   .. image:: ../assets/screenshots/d06-orders.png
      :alt: 7. 판매오더 납기 결과. sales_order_id, customer_name, product_id, due_date, baseline_finish_date, finish_date, slack_days, on_time 열이 있는 4행 표입니다. SO-10322는 finish 2026-10-06, slack 2이고 모두 on_time true입니다. 아래에 납기 지연: 0개가 표시됩니다.
      :width: 900

#. **8. 대응안 4개 만들기**

   ``BNK-L3-2``\ 의 필요 보충량 35,630kg을 채우는 방법 4가지를 만듭니다. 값은 모두 Gold 테이블에서 가져옵니다.

   .. list-table::
      :header-rows: 1
      :widths: 22 53 25

      * - 대응안
        - 방법
        - 추가 비용
      * - ``OPT-1`` 입고 앞당김
        - 미달 시작일 뒤 첫 입고 예정을 공급사가 당길 수 있는 최대 일수만큼 당깁니다.
        - 수량 × 앞당김 수수료
      * - ``OPT-2`` Bunker 간 이송
        - 같은 원료를 보관하는 Bunker에서 비용이 가장 낮은 경로로 옮깁니다. 5,000kg 단위, 경로의 하루 한도까지 매일 출고합니다.
        - 수량 × 이송 비용
      * - ``OPT-3`` 추가 구매
        - 공급사에 발주 단위로 긴급 구매합니다. 표준 리드타임 + 계획 지연일 뒤에 들어옵니다.
        - 수량 × 단가 × 긴급 할증률
      * - ``OPT-4`` 생산 순서 조정
        - 긴급 생산을 다음 입고 뒤 L3 계획이 없는 날로 옮깁니다.
        - 0

   **예상 결과:** 4행. ``OPT-1`` 25,000kg 10/07 도착 500,000원, ``OPT-2`` 40,000kg 10/03 도착 1,000,000원, ``OPT-3`` 50,000kg 10/05 도착 3,750,000원, ``OPT-4`` 긴급 생산을 10/11~10/12로 이동 0원

   .. image:: ../assets/screenshots/d06-options.png
      :alt: 8. 대응안 4개 만들기 결과. option_id, option_name, qty_kg, first_arrival_date, added_cost_krw, action_detail 열이 있는 4행 표입니다. OPT-2는 40000kg, 2026-10-03, 1000000원입니다.
      :width: 900

#. **9. 대응안별 Balance와 판단 기준**

   대응안마다 Bunker 24개의 4분기 재고를 다시 계산하고 아래 기준을 모두 만족하는지 확인합니다.
   기준을 모두 만족한 대응안에만 추가 비용이 낮은 순서로 추천 순위를 붙입니다.

   * **C1 안전재고:** 모든 Bunker의 매일 기말 재고 ≥ 안전재고
   * **C2 용량:** 모든 Bunker의 매일 기초 재고 + 입고 + 이송 입고 ≤ 용량
   * **C3 납기:** 모든 판매오더의 생산 완료일 ≤ 납기
   * **C4 이송 한도:** 하루 이송량 ≤ 경로의 하루 한도

   **예상 결과:** 4행. ``OPT-2``\ (Bunker 간 이송)가 추천 1순위, ``OPT-3``\ (추가 구매)가 2순위입니다.
   ``OPT-1``\ 은 C1(10/06부터 미달), ``OPT-4``\ 는 C1과 C3(``SO-10322`` 완료 10/12, 납기 10/08)을 만족하지 못합니다.

   .. image:: ../assets/screenshots/d06-checks.png
      :alt: 9. 대응안별 판단 기준 결과. 대응안, 이름, C1, C2, C3, C4, 추천 순위, 추가 비용(원), 판단 열이 있는 4행 표입니다. OPT-2는 모두 true, 추천 순위 1, 1000000원이고 OPT-3은 추천 순위 2, 3750000원입니다.
      :width: 900

#. **10. 추천안의 두 Bunker 확인**

   추천안 ``OPT-2``\ 는 ``BNK-L1-2``\ 의 PET-SD를 ``BNK-L3-2``\ 로 옮깁니다. 받는 Bunker와 보내는 Bunker가 모두 안전재고를 지키는지 봅니다.

   **예상 결과:** 2행. 두 Bunker 모두 ``below_safety_days``\ 가 0입니다. 가장 낮은 재고는 ``BNK-L1-2`` 16,763kg(11월 1일, 안전재고 6,000kg),
   ``BNK-L3-2`` 16,370kg(11월 26일, 안전재고 12,000kg)입니다.

   .. image:: ../assets/screenshots/d06-transfer.png
      :alt: 10. 추천안의 두 Bunker 확인 결과. OPT-2의 BNK-L1-2와 BNK-L3-2 2행입니다. below_safety_days는 모두 0이고 min_closing_kg는 16763과 16370입니다.
      :width: 900

#. **11. 위험 이벤트**

   부족해지는 Bunker, 원인이 된 판매오더, 추천안을 한 행으로 모읍니다. 11장에서 Fabric Operations agent가 이 행을 보고 담당자에게 대응안을 제안합니다.
   ``detected_at``\ 은 이 셀을 실행한 시각이고, ``status``\ 는 처음에 ``open``\ 입니다.

   **예상 결과:** 1행. ``EVT-20261001-001``, ``SO-10322``, ``BNK-L3-2``, 추천안 ``OPT-2``, ``status`` ``open``

   .. image:: ../assets/screenshots/d06-risk.png
      :alt: 11. 위험 이벤트 결과. event_id EVT-20261001-001, detected_at, sales_order_id SO-10322, bunker_id BNK-L3-2, required_topup_kg 35630, recommended_option_id OPT-2, status open인 1행 표입니다.
      :width: 900

#. **12. Gold 테이블 저장**

   긴급 수주 결과를 OneLake의 Gold 테이블에 넣고, 바뀐 테이블 9개를 Fabric Lakehouse의 ``gold`` 스키마에 다시 저장합니다. 05와 같은 방법입니다.
   다시 실행하면 ``emergency`` 행과 긴급 판매오더를 지우고 다시 넣습니다. Unity Catalog에는 만들지 않습니다.

   **예상 결과:** 9행. ``gold_fact_plan`` 1,096행(``emergency`` 549행), ``gold_fact_balance`` 4,416행(``emergency`` 2,208행),
   ``gold_fact_response_option`` 4행, ``gold_fact_option_balance`` 460행, ``gold_fact_risk_event`` 1행. 표 아래에 OneLake 경로가 표시됩니다.

정리: 판단 기준으로 고른 추천안
----------------------------------

.. code-block:: text

   긴급 오더 SO-10322 (P-L3-05 100,000kg, 10/5·10/6 생산)
     → BNK-L3-2 PET-SD가 10/06부터 안전재고 미달, 10/07부터 부족, 필요 보충량 35,630kg
   대응안 4개 × 판단 기준 C1~C4
     OPT-1 입고 앞당김   500,000원  C1 불만족 (10/06부터 미달)
     OPT-2 Bunker 간 이송 1,000,000원 모두 만족 → 추천 1순위
     OPT-3 추가 구매   3,750,000원 모두 만족 → 추천 2순위
     OPT-4 생산 순서 조정       0원  C1·C3 불만족 (SO-10322 납기 초과)

추천은 계산 결과입니다. 11장에서 Operations agent가 이 추천을 Teams로 보내고, 담당자가 승인합니다.

Troubleshooting
---------------

* 맨 위 **1. 설정과 Gold 불러오기**\ 에서 오류가 나면 05장 ``05_gold``\ 를 먼저 실행합니다. 이 Notebook은 05가 OneLake에 저장한 Gold를 읽어 시작합니다.
* 05장을 다시 실행하면 ``emergency`` 행이 지워집니다. 이 Notebook을 다시 실행합니다.

다음 단계
------------

`07. 정답 계산과 Genie <07-genie.rst>`_
