데이터 설계
===========

개요
----

SAP, FPIMS, PVSS 추출 파일을 Bronze로 적재한 뒤 Silver 품질 규칙을 적용하고 Gold 테이블을 계산합니다. Gold는 Fabric workspace ``chipbalance-p001`` 의 Lakehouse ``lh_chipbalance_p001`` 내 ``gold`` 스키마에 적재됩니다. 원천 파일은 Unity Catalog ``lab_factory.chipbalance_p001`` 의 Volume ``raw`` 에 업로드됩니다. Fabric은 SQL analytics endpoint, Power BI Direct Lake, Fabric IQ Ontology, Data agent, Operations agent에서 Gold를 사용합니다. 승인된 의사결정은 Fabric Notebook이 ``dbo.chip_decision_log`` 에 기록하며 Databricks는 이 테이블을 쓰지 않습니다.

원천 파일
---------

.. list-table:: 원천 파일과 행 수
   :header-rows: 1

   * - 파일명
     - 시스템
     - 형식
     - 행 수
     - 설명
   * - sap_material.csv
     - SAP
     - CSV
     - 12
     - 원료, 단가, 기준 단위
   * - sap_supplier.csv
     - SAP
     - CSV
     - 6
     - 공급사, 표준 리드타임, 당김 한도, 주문 단위
   * - sap_purchase_receipt_2025-10_2026-09.csv
     - SAP
     - CSV
     - 1,900
     - 입고 실적과 약속일
   * - sap_purchase_order_open_2026Q4.csv
     - SAP
     - CSV
     - 735
     - Q4 미결 PO
   * - sap_sales_order_open_2026Q4.csv
     - SAP
     - CSV
     - 360
     - 판매오더와 납기
   * - fpims_line.csv
     - FPIMS
     - CSV
     - 6
     - 생산 라인
   * - fpims_bunker.csv
     - FPIMS
     - CSV
     - 24
     - 라인별 Bunker, 용량, 안전재고
   * - fpims_product.csv
     - FPIMS
     - CSV
     - 30
     - 제품 마스터
   * - fpims_recipe.csv
     - FPIMS
     - CSV
     - 118
     - 제품별 표준 원단위
   * - fpims_bunker_transfer_route.csv
     - FPIMS
     - CSV
     - 12
     - 동일 원료 Bunker 간 이송 경로
   * - fpims_production_lot_2025-10_2026-09.csv
     - FPIMS
     - CSV
     - 4,132
     - 생산 Lot 실적
   * - fpims_material_consumption_2025-10_2026-09.csv
     - FPIMS
     - CSV
     - 16,252
     - Lot별 원료 소비 실적
   * - fpims_production_plan_2026Q4.csv
     - FPIMS
     - CSV
     - 547
     - Q4 기준 생산계획, L3 예비일 5일 제외
   * - pvss_bunker_level_2026-09.json
     - PVSS
     - JSON Lines
     - 17,278
     - 9월 시간별 Bunker 레벨

총 원천 행 수는 41,412행입니다. Gold 총 행 수는 6,633행이며 합계는 48,045행입니다.

원천 컬럼
---------

.. list-table:: 원천 컬럼 정의
   :header-rows: 1

   * - 파일
     - 컬럼
     - 타입
     - 설명
   * - sap_material.csv
     - material_id, material_name, description, unit_price_krw_per_kg, base_uom
     - string, string, string, bigint, string
     - 원료 마스터와 KRW/kg 단가
   * - sap_supplier.csv
     - supplier_id, supplier_name, standard_lead_time_days, max_pull_in_days, order_unit_kg
     - string, string, bigint, bigint, bigint
     - 신규 구매 리드타임, PO 당김 계약 한도, 주문 단위
   * - sap_purchase_receipt_2025-10_2026-09.csv
     - receipt_id, purchase_order_id, supplier_id, material_id, promised_date, received_date, quantity, unit
     - string, string, string, string, YYYYMMDD, YYYYMMDD, double, string
     - 공급사 지연은 ``received_date - promised_date`` 로만 계산합니다.
   * - sap_purchase_order_open_2026Q4.csv
     - purchase_order_id, po_line_no, supplier_id, material_id, bunker_id, promised_date, quantity, unit
     - string, string, string, string, string, YYYYMMDD, double, string
     - 예정 입고와 품질 격리 대상
   * - sap_sales_order_open_2026Q4.csv
     - sales_order_id, customer_segment, product_id, order_qty_kg, due_date, priority
     - string, string, string, bigint, YYYYMMDD, string
     - 납기 기준 확인용
   * - fpims_bunker.csv
     - bunker_id, line_id, material_id, capacity_kg, safety_stock_kg
     - string, string, string, bigint, bigint
     - Bunker별 고정 원료와 재고 기준
   * - fpims_recipe.csv
     - product_id, line_id, material_id, std_kg_per_kg
     - string, string, string, double
     - 표준 kg/kg 원단위만 제공합니다.
   * - fpims_production_plan_2026Q4.csv
     - plan_id, plan_date, line_id, product_id, planned_output_kg, sales_order_id
     - string, YYYYMMDD, string, string, bigint, string
     - 일별 요구량 계산 입력
   * - pvss_bunker_level_2026-09.json
     - bunker_id, timestamp, level_kg
     - string, timestamp, bigint
     - 기초재고 계산 입력

관계
----

::

   sap_supplier 1 ── n sap_purchase_receipt / sap_purchase_order_open
   sap_material 1 ── n fpims_bunker
   fpims_line 1 ── n fpims_product / fpims_bunker / fpims_production_plan
   fpims_product 1 ── n fpims_recipe / fpims_production_lot
   fpims_production_lot 1 ── n fpims_material_consumption
   fpims_bunker 1 ── n pvss_bunker_level / chip_fact_balance

Bunker 기준
-----------

.. list-table:: 용량과 안전재고
   :header-rows: 1

   * - 원료
     - 용량 kg
     - 안전재고 kg
   * - PET-BR
     - 250,000
     - 45,000
   * - PET-SD
     - 250,000
     - 12,000
   * - PET-RC
     - 150,000
     - 35,000
   * - PET-CO
     - 150,000
     - 32,000
   * - NY6-F
     - 170,000
     - 35,000
   * - NY6-H
     - 150,000
     - 18,000
   * - MB-AB / MB-SL / MB-WH / MB-NA / MB-NS
     - 16,000-20,000
     - 1,800-2,500

Silver 품질 규칙
----------------

.. list-table:: 품질 이슈와 처리
   :header-rows: 1

   * - 이슈
     - 건수
     - 규칙
   * - Open PO 중복
     - 5
     - ``purchase_order_id, po_line_no`` 첫 행만 사용하고 나머지는 ``duplicate_open_po`` 로 격리합니다.
   * - Open PO 수량 Null
     - 4
     - ``null_quantity`` 로 격리합니다.
   * - Open PO 단위 TO
     - 8
     - ``quantity * 1000`` 으로 KG 환산합니다.
   * - Open PO 미등록 원료
     - 3
     - ``unknown_material`` 로 격리합니다.
   * - Sensor 범위 초과
     - 6
     - ``level_kg < 0`` 또는 용량 초과는 ``sensor_spike_out_of_capacity`` 로 격리합니다.
   * - Sensor 중복
     - 5
     - 동일 ``bunker_id, timestamp`` 첫 정상 행만 사용하고 나머지는 ``duplicate_sensor_timestamp`` 로 격리합니다.
   * - Sensor 결측 시간
     - 7
     - 격리 행은 없고 품질 지표로 기록합니다.

Gold 계산 규칙
--------------

* 모든 kg 저장값은 HALF-UP 정수 반올림을 사용합니다.
* 실제 사용계수는 ``sum(consumed_kg) / sum(output_kg)`` by ``product_id, material_id`` 입니다. 소비 실적은 표준 원단위에 숨은 제품-원료별 손실 1-4%와 Lot 단위 ±0.5%p 변동을 적용해 생성합니다.
* 기초재고는 정제 후 ``2026-09-30T23:00:00+09:00`` 이하 마지막 정상 센서값입니다.
* 공급사 지연은 12개월 입고 실적 평균을 HALF-UP 일수로 반올림합니다.
* 예상 입고일은 ``promised_date + rounded_avg_delay_days`` 입니다.
* 일별 잔량은 ``closing = previous_closing + receipts + transfers_in - transfers_out - requirement`` 입니다.
* ``below_safety`` 는 ``closing < safety_stock_kg`` 이고 ``shortage`` 는 ``closing < 0`` 입니다.
* ``over_capacity`` 는 ``previous_closing + receipts + transfers_in > capacity_kg`` 입니다.

예비일과 긴급 오더
------------------

L3 기준계획에는 2026-10-11부터 2026-10-15까지 5개 예비일이 있으며 해당 날짜에는 L3 계획 행이 없습니다. 긴급 오더 ``URG-20261001-L3-001`` 은 ``P-L3-05`` 100,000kg, 납기 2026-10-08입니다. 긴급 시나리오는 2026-10-05부터 2026-10-06까지 L3 행을 긴급 제품으로 교체하고, 기존 5개 행은 예비일에 순서대로 이동합니다. 기존 sales_order_id와 수량은 유지합니다. 기준과 긴급 시나리오의 기존 판매오더는 모두 납기 이내입니다.

대응안 도출 규칙과 판단 기준
----------------------------

* 필요 보충량은 긴급 시나리오의 대상 Bunker ``max(0, safety - min_closing)`` 입니다. 값은 31,188kg입니다.
* OPT-1은 대상 Bunker에서 최초 안전재고 미만일 이후 도착하는 가장 빠른 PO를 공급사 ``max_pull_in_days`` 만큼 앞당깁니다. 약속일은 ``TODAY+1`` 보다 빨라질 수 없습니다.
* OPT-2는 동일 원료이며 대상 Bunker로 향하는 경로 중 ``cost_krw_per_kg`` 최저, 동률 시 ``from_bunker_id`` 오름차순을 선택합니다. 수량은 필요 보충량을 5,000kg 단위로 올림한 35,000kg입니다. 선적은 ``TODAY+1`` 부터 일별 route 한도 이하로 나눕니다.
* OPT-3은 필요 보충량을 공급사 ``order_unit_kg`` 로 올림한 50,000kg을 추가 구매합니다. 약속일은 ``TODAY + standard_lead_time_days`` 이고 예상 도착일은 공급사 평균 지연을 더합니다.
* OPT-4는 대상 Bunker의 다음 예상 입고일 이후 첫 L3 예비일들로 긴급 생산을 이동합니다.
* C1은 모든 Bunker, 모든 일자의 잔량이 안전재고 이상인지 확인합니다.
* C2는 모든 Bunker, 모든 일자의 ``previous_closing + receipts + transfers_in`` 이 용량 이하인지 확인합니다.
* C3은 모든 판매오더의 마지막 계획일이 납기 이하인지 확인합니다.
* C4는 모든 이송 선적이 존재하는 route를 사용하고 일별 한도 이하인지 확인합니다.
* 통과한 대응안은 ``added_cost_krw`` 오름차순, ``option_id`` 오름차순으로 순위를 부여합니다.

Gold 테이블 정의
----------------

.. list-table:: Gold 컬럼 정의
   :header-rows: 1

   * - 테이블
     - 컬럼
     - 타입
     - 설명
   * - chip_dim_line
     - line_id, plant_id, line_family, default_daily_output_kg
     - string, string, string, bigint
     - 생산 라인 차원
   * - chip_dim_bunker
     - bunker_id, line_id, material_id, capacity_kg, safety_stock_kg
     - string, string, string, bigint, bigint
     - Bunker 차원
   * - chip_dim_material
     - material_id, material_name, description, unit_price_krw_per_kg, base_uom
     - string, string, string, bigint, string
     - 원료 차원
   * - chip_dim_product
     - product_id, line_id, product_name, film_family, default_daily_output_kg
     - string, string, string, string, bigint
     - 제품 차원
   * - chip_dim_supplier
     - supplier_id, supplier_name, standard_lead_time_days, max_pull_in_days, order_unit_kg
     - string, string, bigint, bigint, bigint
     - 공급사 차원
   * - chip_dim_date
     - date_key, calendar_date, yyyymm, day_of_week
     - string, date, string, bigint
     - 92일 계획 기간 날짜 차원
   * - chip_dim_scenario
     - scenario_id, scenario_name, description
     - string, string, string
     - baseline, emergency
   * - chip_fact_usage_factor
     - usage_factor_key, product_id, material_id, actual_kg_per_kg, std_kg_per_kg, variance_kg_per_kg, total_consumed_kg, total_output_kg
     - string, string, string, double, double, double, bigint, bigint
     - 실제 원단위
   * - chip_fact_monthly_usage
     - monthly_usage_key, month, bunker_id, consumed_kg
     - string, string, string, bigint
     - 월별 Bunker 소비
   * - chip_fact_supplier_delay
     - supplier_id, receipt_count, avg_delay_days, rounded_delay_days
     - string, bigint, double, bigint
     - 공급사 평균 지연
   * - chip_fact_opening_stock
     - opening_stock_key, as_of_date, bunker_id, source_timestamp, opening_kg
     - string, date, string, timestamp, bigint
     - 2026-10-01 기초재고
   * - chip_fact_plan
     - plan_key, scenario_id, plan_id, plan_date, line_id, product_id, planned_output_kg, sales_order_id
     - string, string, string, date, string, string, bigint, string
     - 시나리오별 생산계획
   * - chip_fact_balance
     - balance_key, scenario_id, bunker_id, line_id, material_id, balance_date, opening_kg, receipt_kg, transfer_in_kg, transfer_out_kg, requirement_kg, closing_kg, safety_stock_kg, capacity_kg, below_safety, shortage, over_capacity
     - string, string, string, string, string, date, bigint, bigint, bigint, bigint, bigint, bigint, bigint, bigint, boolean, boolean, boolean
     - 일별 Bunker Balance
   * - chip_scenario_summary
     - summary_key, scenario_id, bunker_id, line_id, material_id, first_below_safety_date, first_shortage_date, min_closing_kg, min_closing_date, ending_closing_kg, required_topup_kg
     - string, string, string, string, string, date, date, bigint, date, bigint, bigint
     - Bunker별 시나리오 요약
   * - chip_response_option
     - option_id, option_name, c1_safety_pass, c2_capacity_pass, c3_due_date_pass, c4_route_limit_pass, added_cost_krw, below_safety_days, first_below_safety_date, late_order_count, action_detail, source_bunker_id, target_bunker_id, qty_kg, first_arrival_date, meets_all, rank
     - string, string, boolean, boolean, boolean, boolean, bigint, bigint, date, bigint, string, string, string, bigint, date, boolean, bigint
     - 대응안 평가와 파라미터
   * - chip_option_balance
     - option_balance_key, option_id, scenario_id, bunker_id, line_id, material_id, balance_date, opening_kg, receipt_kg, transfer_in_kg, transfer_out_kg, requirement_kg, closing_kg, safety_stock_kg, capacity_kg, below_safety, shortage, over_capacity
     - string, string, string, string, string, string, date, bigint, bigint, bigint, bigint, bigint, bigint, bigint, bigint, boolean, boolean, boolean
     - 대응안 영향 Bunker 일별 Balance
   * - chip_risk_event
     - event_id, detected_at, scenario_id, bunker_id, material_id, line_id, first_below_safety_date, first_shortage_date, min_closing_kg, required_topup_kg, recommended_option_id, recommended_action, status
     - string, timestamp, string, string, string, string, date, date, bigint, bigint, string, string, string
     - Operations agent 이벤트. Reference는 ``<current_timestamp>`` placeholder를 사용하고 정확값 비교에서 제외합니다.

예상 결과
---------

.. list-table:: BNK-L3-2 요약
   :header-rows: 1

   * - 시나리오
     - 최초 안전재고 미만일
     - 최초 부족일
     - 최소 잔량 kg
     - 종료 잔량 kg
     - 필요 보충 kg
   * - baseline
     - 
     - 
     - 42,622
     - 67,007
     - 0
   * - emergency
     - 2026-10-05
     - 2026-10-06
     - -19,188
     - 5,197
     - 31,188

.. list-table:: 대응안 결과
   :header-rows: 1

   * - option_id
     - C1
     - C2
     - C3
     - C4
     - 비용 KRW
     - 안전재고 미만 일수
     - 최초 안전재고 미만일
     - 지연 오더 수
     - 수량 kg
     - 최초 도착일
     - Rank
   * - OPT-1
     - false
     - true
     - true
     - true
     - 0
     - 52
     - 2026-10-12
     - 0
     - 30,000
     - 2026-10-08
     - 
   * - OPT-2
     - true
     - true
     - true
     - true
     - 875,000
     - 0
     - 
     - 0
     - 35,000
     - 2026-10-03
     - 1
   * - OPT-3
     - true
     - true
     - true
     - true
     - 62,500,000
     - 0
     - 
     - 0
     - 50,000
     - 2026-10-05
     - 2
   * - OPT-4
     - false
     - true
     - false
     - true
     - 0
     - 52
     - 2026-10-12
     - 1
     - 250,000
     - 2026-10-11
     - 

.. list-table:: chip_risk_event
   :header-rows: 1

   * - 컬럼
     - 값
   * - event_id
     - EVT-20261001-001
   * - detected_at
     - <current_timestamp>
   * - scenario_id / bunker_id / material_id / line_id
     - emergency / BNK-L3-2 / PET-SD / L3
   * - first_below_safety_date / first_shortage_date
     - 2026-10-05 / 2026-10-06
   * - min_closing_kg / required_topup_kg
     - -19,188 / 31,188
   * - recommended_option_id
     - OPT-3
   * - recommended_action
     - BNK-L1-2에서 BNK-L3-2로 PET-SD 35,000kg 이송
   * - status
     - open


대응안별 안전재고 미만 Bunker breakdown
----------------------------------------

.. list-table:: 안전재고 미만 Bunker-days
   :header-rows: 1

   * - option_id
     - breakdown
   * - OPT-1
     - BNK-L3-2:52
   * - OPT-2
     - 없음
   * - OPT-3
     - 없음
   * - OPT-4
     - BNK-L3-2:52

기준 시나리오 Bunker margin
--------------------------

.. list-table:: 주요 Bunker margin
   :header-rows: 1

   * - bunker_id
     - safety_stock_kg
     - avg_daily_use_kg
     - baseline_min_closing_kg
     - min_safety_ratio
   * - BNK-L3-2
     - 12,000
     - 10,206.4
     - 42,622
     - 3.55
   * - BNK-L1-2
     - 12,000
     - 2,132.9
     - 48,774
     - 9.90

