# 데이터 설계

## 개요

SAP, FPIMS, PVSS 추출 파일을 Bronze로 적재한 뒤 Silver 품질 규칙을 적용하고 Gold 테이블을 계산합니다. Gold는 Fabric workspace `chipbalance-p001`의 Lakehouse `lh_chipbalance_p001` 내 `gold` 스키마에 적재됩니다. 원천 파일은 Unity Catalog `lab_factory_p001.chipbalance_p001`의 Volume `raw`에 생성되고 Bronze·Silver도 이 스키마에 저장됩니다. Databricks의 `gold_*` 이름은 OneLake Gold를 읽은 세션 임시 뷰이며 Unity Catalog 관리형 Gold 테이블이 아닙니다. 선택 연결을 준비하면 Foreign Catalog `fabric_chipbalance_p001.gold.<테이블>`에서 같은 데이터를 읽습니다.

Fabric은 SQL analytics endpoint, Power BI Direct Lake, Fabric IQ Ontology, Ontology agent에서 Gold를 사용합니다. Microsoft Foundry 에이전트 `fa-chipbalance`는 Fabric IQ 도구로 Ontology `ont_chipbalance`의 정의를 읽습니다. Operations agent는 Eventhouse `eh_chipbalance`의 `RiskEventStatus` 테이블을 감시합니다. 승인된 의사결정은 Fabric Notebook `nb_record_decision`이 `RiskEventStatus`와 `dbo.chip_decision_log`에 기록하며 Databricks는 이 테이블을 쓰지 않습니다.

아래 수치는 `src/notebooks/source_systems.py`의 고정 seed `20261001`, `05_gold`와 `06_emergency_order` 및 로컬 계산 `tools/reference_pipeline.py`를 기준으로 합니다. 시나리오의 `TODAY`는 실제 실행일이 아니라 **2026-10-01**입니다.

## 원천 파일

**원천 파일과 행 수**

| 파일명 | 시스템 | 형식 | 행 수 | 설명 |
|----|----|----|----|----|
| sap_material.csv | SAP | CSV | 12 | 원료, 단가, 기준 단위 |
| sap_supplier.csv | SAP | CSV | 6 | 공급사, 표준 리드타임, 당김 한도, 주문 단위 |
| sap_purchase_receipt_2025-10_2026-09.csv | SAP | CSV | 2,849 | 입고 실적과 약속일 |
| sap_purchase_order_open_2026Q4.csv | SAP | CSV | 731 | Q4 미결 PO |
| sap_sales_order_open_2026Q4.csv | SAP | CSV | 321 | 판매오더와 납기 |
| fpims_line.csv | FPIMS | CSV | 6 | 생산 라인 |
| fpims_bunker.csv | FPIMS | CSV | 24 | 라인별 Bunker, 용량, 안전재고 |
| fpims_product.csv | FPIMS | CSV | 30 | 제품 마스터 |
| fpims_recipe.csv | FPIMS | CSV | 118 | 제품별 표준 원단위 |
| fpims_bunker_transfer_route.csv | FPIMS | CSV | 12 | 동일 원료 Bunker 간 이송 경로 |
| fpims_production_lot_2025-10_2026-09.csv | FPIMS | CSV | 4,308 | 생산 Lot 실적 |
| fpims_material_consumption_2025-10_2026-09.csv | FPIMS | CSV | 17,168 | Lot별 원료 소비 실적 |
| fpims_production_plan_2026Q4.csv | FPIMS | CSV | 547 | Q4 기준 생산계획, L3 예비일 5일 제외 |
| pvss_bunker_level_2026-09.json | PVSS | JSON Lines | 17,278 | 9월 시간별 Bunker 레벨 |

총 원천 행 수는 **43,410행**입니다. 05장 직후 baseline Gold는 **18개 테이블, 4,765행**입니다. 06장까지 실행한 최종 Gold는 **21개 테이블, 8,335행**이며 원천과 최종 Gold의 합계는 **51,745행**입니다. 합계에 Bronze·Silver 복제 행이나 의사결정 로그는 포함하지 않습니다.

## 원천 컬럼

**원천 컬럼 정의**

CSV·JSON 원천 값은 Bronze에서 문자로 보존합니다. 아래 타입은 날짜의 원천 표기와 Silver에서 해석할 타입입니다.

| 파일 | 컬럼 | 타입 | 설명 |
|----|----|----|----|
| sap_material.csv | material_id, material_name, description, unit_price_krw_per_kg, base_uom | string, string, string, int, string | 원료 마스터와 KRW/kg 단가 |
| sap_supplier.csv | supplier_id, supplier_name, standard_lead_time_days, max_pull_in_days, order_unit_kg, pull_in_fee_krw_per_kg, spot_premium_pct | string, string, int, int, bigint, int, int | 신규 구매 리드타임, PO 당김 한도, 주문 단위, 당김 수수료, 긴급 할증률(%) |
| sap_purchase_receipt_2025-10_2026-09.csv | receipt_id, purchase_order_id, supplier_id, material_id, bunker_id, promised_date, received_date, quantity, unit | string, string, string, string, string, YYYYMMDD, YYYYMMDD, bigint, string | 공급사 지연은 `received_date - promised_date`로 계산합니다. |
| sap_purchase_order_open_2026Q4.csv | purchase_order_id, po_line_no, supplier_id, material_id, bunker_id, promised_date, quantity, unit | string, string, string, string, string, YYYYMMDD, bigint, string | 예정 입고와 품질 격리 대상. 수량 공란은 숫자로 바꾸기 전에 격리 |
| sap_sales_order_open_2026Q4.csv | sales_order_id, order_date, customer_id, customer_name, product_id, order_qty_kg, due_date, priority | string, YYYYMMDD, string, string, string, bigint, YYYYMMDD, string | 고객, 수주일과 납기 |
| fpims_line.csv | line_id, plant_id, line_family, default_daily_output_kg | string, string, string, bigint | 공장과 라인별 기본 생산량 |
| fpims_bunker.csv | bunker_id, line_id, material_id, capacity_kg, safety_stock_kg | string, string, string, bigint, bigint | Bunker별 고정 원료와 재고 기준 |
| fpims_product.csv | product_id, line_id, product_name, film_family, default_daily_output_kg | string, string, string, string, bigint | 라인별 제품 마스터 |
| fpims_recipe.csv | product_id, line_id, material_id, std_kg_per_kg | string, string, string, decimal(10,6) | 표준 kg/kg 원단위 |
| fpims_bunker_transfer_route.csv | route_id, from_bunker_id, to_bunker_id, material_id, max_kg_per_day, lead_time_days, cost_krw_per_kg | string, string, string, string, bigint, int, int | 같은 원료 이송 경로와 한도·시간·비용 |
| fpims_production_lot_2025-10_2026-09.csv | lot_id, line_id, product_id, start_ts, end_ts, output_kg | string, string, string, timestamp, timestamp, bigint | 주·야간 Lot 생산 실적 |
| fpims_material_consumption_2025-10_2026-09.csv | consumption_id, lot_id, line_id, bunker_id, material_id, consumed_kg | string, string, string, string, string, bigint | Lot·Bunker별 소비 실적 |
| fpims_production_plan_2026Q4.csv | plan_id, plan_date, line_id, product_id, planned_output_kg, sales_order_id | string, YYYYMMDD, string, string, bigint, string | 일별 요구량 계산 입력 |
| pvss_bunker_level_2026-09.json | bunker_id, timestamp, level_kg | string, timestamp, bigint | 기초재고 계산 입력 |

## 관계

    sap_supplier 1 ── n sap_purchase_receipt / sap_purchase_order_open
    sap_material 1 ── n fpims_bunker
    fpims_line 1 ── n fpims_product / fpims_bunker / fpims_production_plan
    fpims_product 1 ── n fpims_recipe / fpims_production_lot
    fpims_production_lot 1 ── n fpims_material_consumption
    fpims_bunker 1 ── n pvss_bunker_level / gold.fact_balance

Gold에서는 `dim_customer → fact_sales_order → fact_plan / fact_order_fulfillment`, `dim_supplier → fact_inbound`, `dim_bunker → fact_balance / fact_bunker_summary`로 이어집니다. `scenario_id`가 있는 Fact는 `fact_plan`, `fact_order_fulfillment`, `fact_balance`, `fact_bunker_summary`, `fact_response_option`, `fact_risk_event`의 6개입니다. 이들끼리 조인할 때는 시나리오도 맞춥니다. `fact_sales_order`는 `is_urgent`, `fact_option_balance`는 `option_id`로 구분하며 공통 Fact에 `scenario_id`는 없습니다.

## Bunker 기준

**용량과 안전재고**

| 원료                                  | 용량 kg       | 안전재고 kg |
|---------------------------------------|---------------|-------------|
| PET-BR                                | 250,000       | 45,000      |
| PET-SD (BNK-L1-2)                     | 150,000       | 6,000       |
| PET-SD (BNK-L3-2)                     | 150,000       | 12,000      |
| PET-RC                                | 150,000       | 20,000      |
| PET-CO                                | 150,000       | 20,000      |
| NY6-F                                 | 170,000       | 35,000      |
| NY6-H                                 | 150,000       | 12,000      |
| MB-AB                                 | 20,000        | 2,500       |
| MB-SL / MB-WH                         | 18,000        | 2,200       |
| MB-UV                                 | 16,000        | 1,500       |
| MB-NA / MB-NS                         | 16,000        | 1,800       |

## Silver 품질 규칙

**품질 이슈와 처리**

| 이슈 | 건수 | 규칙 |
|----|----|----|
| Open PO 중복 | 5 | `purchase_order_id, po_line_no` 첫 정상 행만 사용하고 나머지는 `duplicate_line`으로 격리합니다. |
| Open PO 수량 공란 | 4 | `blank_quantity`로 격리합니다. |
| Open PO 단위 TO | 8 | `quantity * 1000` 으로 KG 환산합니다. |
| Open PO 미등록 원료 | 3 | `unknown_material` 로 격리합니다. |
| Sensor 범위 초과 | 6 | `level_kg < 0` 또는 용량 초과는 `out_of_range`로 격리합니다. |
| Sensor 중복 | 5 | 동일 `bunker_id, timestamp` 첫 정상 행만 사용하고 나머지는 `duplicate_reading`으로 격리합니다. |
| Sensor 결측 시간 | 7 | 격리 행은 없고 품질 지표로 기록합니다. |

Open PO는 미등록 원료 → 수량 공란 → 중복 순서로 검사합니다. Silver는 정상 PO **719행**, 정상 센서 **17,267행**, `silver_quarantine` **23행**을 포함한 15개 테이블입니다.

## Gold 계산 규칙

- 모든 kg 저장값은 HALF-UP 정수 반올림을 사용합니다.
- 실제 사용계수는 제품별 Lot 생산량 합계를 분모, 제품·원료별 소비량 합계를 분자로 하여 소수 6자리로 반올림합니다. 소비 실적 조인으로 생산량을 중복 합산하지 않습니다. 소비 실적은 표준 원단위에 제품·원료별 손실 1~4%와 Lot 단위 ±0.5%p 변동을 적용해 생성합니다. `P-L3-05`의 PET-SD 실제 사용계수는 `0.463237`입니다.
- 기초재고는 정제 후 `2026-09-30T23:00:00+09:00` 이하 마지막 정상 센서값입니다.
- 공급사 지연은 12개월 입고 실적 평균을 HALF-UP 일수로 반올림합니다.
- 예상 입고일은 `promised_date + planning_delay_days`입니다.
- 계획 지연일은 SUP-PET-A 0, SUP-PET-B 0, SUP-MB-A 1, SUP-NY-A 1, SUP-NY-B 2, SUP-ADD-A 3일입니다.
- 일별 요구량은 **각 생산계획 행**의 `planned_output_kg × actual_kg_per_kg`를 kg 정수로 반올림한 뒤 Bunker·일자별 합산합니다.
- 일별 잔량은 `closing = previous_closing + receipts + transfers_in - transfers_out - requirement` 입니다.
- `below_safety` 는 `closing < safety_stock_kg` 이고 `shortage` 는 `closing < 0` 입니다.
- `over_capacity` 는 `previous_closing + receipts + transfers_in > capacity_kg` 입니다.

## 예비일과 긴급 수주

L3 기준계획에는 2026-10-11부터 2026-10-15까지 5개 예비일이 있으며 해당 날짜에는 L3 계획 행이 없습니다. 긴급 수주 `SO-10322`는 고객 `C-1004`(누리전자소재)의 `P-L3-05` 100,000kg, 납기 2026-10-08입니다. 긴급 시나리오는 2026-10-05·06에 50,000kg씩 긴급 생산 2행을 추가하고, 기존 10월 5~10일 L3 생산 **6행을 각각 2일씩** 미룹니다(10월 7~12일). 기존 sales_order_id와 수량은 유지합니다. 기준과 긴급 시나리오의 기존 판매오더는 모두 납기 이내입니다.

## 대응안 도출 규칙과 판단 기준

- 필요 보충량은 긴급 시나리오의 대상 Bunker `max(0, safety - min_closing)`입니다. 값은 **35,630kg**입니다.
- OPT-1은 대상 Bunker에서 최초 안전재고 미만일 이후 도착하는 가장 빠른 PO를 공급사 `max_pull_in_days`만큼 앞당깁니다. 예상 도착일은 `max(TODAY+1, expected_date - max_pull_in_days)`입니다. 25,000kg을 10/09에서 10/07로 당기며 추가 비용은 수량 × `pull_in_fee_krw_per_kg` = 500,000원입니다.
- OPT-2는 동일 원료이며 대상 Bunker로 향하는 경로 중 `cost_krw_per_kg` 최저, 동률 시 `from_bunker_id` 오름차순을 선택합니다. 수량은 필요 보충량을 5,000kg 단위로 올림한 **40,000kg**입니다. `TODAY+1`부터 경로의 일별 한도 이하로 나눠 출고합니다. R-01은 10/02 출고, 10/03 도착이며 추가 비용은 1,000,000원입니다.
- OPT-3은 필요 보충량을 공급사 `order_unit_kg`로 올림한 50,000kg을 추가 구매합니다. 예상 도착일은 `TODAY + standard_lead_time_days + planning_delay_days`로 10/05입니다. `added_cost_krw`는 구매 총액이 아니라 **수량 × 단가 × 긴급 할증률**(6%) = 3,750,000원입니다.
- OPT-4는 대상 Bunker의 다음 예상 입고일 이후 첫 L3 예비일들로 긴급 생산을 이동합니다.
- C1은 모든 Bunker, 모든 일자의 잔량이 안전재고 이상인지 확인합니다.
- C2는 모든 Bunker, 모든 일자의 `previous_closing + receipts + transfers_in` 이 용량 이하인지 확인합니다.
- C3은 모든 판매오더의 마지막 계획일이 납기 이하인지 확인합니다.
- C4 코드는 생성된 각 이송 행이 등록된 경로의 한도 이하인지 검사합니다. 이 데이터는 R-01에 하루 한 건으로 생성되어 유효합니다. 임의 입력의 미등록 경로, Bunker·원료 일치, 같은 경로·날짜의 여러 행 합계를 검증하는 범용 검사기는 아닙니다.
- 통과한 대응안은 `added_cost_krw` 오름차순, `option_id` 오름차순으로 순위를 부여합니다.

## Gold 테이블 정의

OneLake의 실제 이름은 아래 `gold.<테이블>`입니다. SQL의 `gold_*`는 Notebook 세션 임시 뷰 이름일 뿐입니다. kg와 비용은 `BIGINT`, 소수는 OneLake에서 `DOUBLE`로 저장하고 Notebook에서 필요한 열만 `DECIMAL`로 복원합니다. `INT`로 명시한 열은 그대로 저장합니다.

**Gold 컬럼 정의와 행 수** (`05 직후` / `06 이후`; `—`는 05장이 만들지 않는 테이블)

| 테이블 | 컬럼 | 타입(컬럼 순서) | 05 직후 | 06 이후 | 설명 |
|----|----|----|----|----|----|
| gold.dim_line | line_id, plant_id, line_family, default_daily_output_kg | string, string, string, bigint | 6 | 6 | 생산 라인 |
| gold.dim_bunker | bunker_id, bunker_name, line_id, material_id, capacity_kg, safety_stock_kg | string, string, string, string, bigint, bigint | 24 | 24 | Bunker 이름과 기준 |
| gold.dim_material | material_id, material_name, description, unit_price_krw_per_kg, supplier_id | string, string, string, int, string | 12 | 12 | 원료와 공급사 |
| gold.dim_product | product_id, product_name, line_id, film_family | string, string, string, string | 30 | 30 | 제품 |
| gold.dim_supplier | supplier_id, supplier_name, standard_lead_time_days, max_pull_in_days, order_unit_kg, pull_in_fee_krw_per_kg, spot_premium_pct, receipt_count, avg_delay_days, planning_delay_days | string, string, int, int, bigint, int, int, bigint, double, int | 6 | 6 | 공급 계약과 지연 실적 |
| gold.dim_customer | customer_id, customer_name | string, string | 12 | 12 | 판매오더의 고객 |
| gold.dim_route | route_id, from_bunker_id, to_bunker_id, material_id, max_kg_per_day, lead_time_days, cost_krw_per_kg | string, string, string, string, bigint, int, int | 12 | 12 | 이송 경로 |
| gold.dim_date | date_key, yyyymm, day_of_week, weekday_name | date, string, int, string | 92 | 92 | Q4 92일, 월요일=1 |
| gold.dim_scenario | scenario_id, scenario_name, description | string, string, string | 1 | 2 | baseline, emergency |
| gold.fact_usage_factor | usage_factor_key, product_id, material_id, std_kg_per_kg, actual_kg_per_kg, loss_pct, consumed_kg, output_kg | string, string, string, double, double, double, bigint, bigint | 118 | 118 | 실제 소요량과 손실률 |
| gold.fact_monthly_usage | monthly_usage_key, usage_month, bunker_id, material_id, consumed_kg | string, string, string, string, bigint | 288 | 288 | 월·Bunker별 소비 |
| gold.fact_opening_stock | bunker_id, as_of_date, reading_ts, opening_kg | string, date, timestamp, bigint | 24 | 24 | 10/01 시작 재고 |
| gold.fact_inbound | inbound_key, purchase_order_id, po_line_no, supplier_id, material_id, bunker_id, promised_date, expected_date, quantity_kg, source_quantity, source_unit | string, string, string, string, string, string, date, date, bigint, bigint, string | 719 | 719 | 정제 PO와 예상 도착일 |
| gold.fact_sales_order | sales_order_id, order_date, customer_id, product_id, line_id, order_qty_kg, due_date, priority, is_urgent | string, date, string, string, string, bigint, date, string, boolean | 321 | 322 | scenario_id 없음 |
| gold.fact_plan | plan_key, scenario_id, plan_id, plan_date, line_id, product_id, planned_output_kg, sales_order_id, original_plan_date, change_type | string, string, string, date, string, string, bigint, string, date, string | 547 | 1,096 | baseline 547 + emergency 549 |
| gold.fact_order_fulfillment | fulfillment_key, scenario_id, sales_order_id, customer_id, product_id, line_id, due_date, finish_date, slack_days, on_time | string, string, string, string, string, string, date, date, int, boolean | 321 | 643 | 시나리오별 납기 |
| gold.fact_balance | balance_key, scenario_id, bunker_id, balance_date, opening_kg, receipt_kg, transfer_in_kg, transfer_out_kg, requirement_kg, closing_kg, safety_stock_kg, capacity_kg, below_safety, shortage, over_capacity | string, string, string, date, bigint, bigint, bigint, bigint, bigint, bigint, bigint, bigint, boolean, boolean, boolean | 2,208 | 4,416 | 시나리오별 24 Bunker × 92일 |
| gold.fact_bunker_summary | summary_key, scenario_id, bunker_id, line_id, material_id, below_safety_days, first_below_safety_date, first_shortage_date, min_closing_kg, min_closing_date, required_topup_kg | string, string, string, string, string, bigint, date, date, bigint, date, bigint | 24 | 48 | Bunker별 위험 요약 |
| gold.fact_response_option | option_id, option_name, scenario_id, target_bunker_id, source_bunker_id, route_id, purchase_order_id, supplier_id, qty_kg, first_arrival_date, added_cost_krw, c1_safety_pass, c2_capacity_pass, c3_due_date_pass, c4_route_limit_pass, meets_all, below_safety_days, late_order_count, recommendation_rank, action_detail, result_note | string, string, string, string, string, string, string, string, bigint, date, bigint, boolean, boolean, boolean, boolean, boolean, bigint, bigint, int, string, string | — | 4 | 대응안 평가와 순위 |
| gold.fact_option_balance | option_balance_key, option_id, bunker_id, balance_date, opening_kg, receipt_kg, transfer_in_kg, transfer_out_kg, requirement_kg, closing_kg, safety_stock_kg, capacity_kg, below_safety, shortage, over_capacity | string, string, string, date, bigint, bigint, bigint, bigint, bigint, bigint, bigint, bigint, boolean, boolean, boolean | — | 460 | 영향 Bunker만 저장; scenario_id 없음 |
| gold.fact_risk_event | event_id, detected_at, scenario_id, sales_order_id, bunker_id, line_id, material_id, first_below_safety_date, first_shortage_date, min_closing_kg, min_closing_date, required_topup_kg, next_inbound_key, recommended_option_id, recommended_action, status | string, timestamp, string, string, string, string, string, date, date, bigint, date, bigint, string, string, string, string | — | 1 | Operations agent 입력 이벤트 |

`fact_option_balance`는 OPT-1·3·4의 대상 Bunker 3 × 92행과 OPT-2의 출발·도착 Bunker 2 × 92행, 총 460행입니다. C1·C2 계산은 모든 Bunker에 대해 수행하되 이 테이블은 영향 Bunker만 보관합니다. `fact_bunker_summary`에는 종료 잔량 열이 없으며 아래 종료 잔량은 `fact_balance`의 **12월 31일 `closing_kg`**에서 구합니다. `detected_at`은 클라우드 실행 시각이고 reference 계산에서는 기본 `None`이므로 정확값 비교에서 제외합니다. 06 재실행은 위험 이벤트를 덮어쓰고 `status`를 `open`으로 초기화합니다.

## 예상 결과

**BNK-L3-2 요약**

| 시나리오 | 최초 안전재고 미만일 | 최초 부족일 | 최소 잔량 kg | 최소 잔량일 | 종료 잔량 kg | 필요 보충 kg |
|----|----|----|----|----|----|----|
| baseline |  |  | 22,694 | 2026-11-26 | 40,352 | 0 |
| emergency | 2026-10-06 | 2026-10-07 | -23,630 | 2026-11-26 | -5,972 | 35,630 |

**대응안 결과**

| option_id | C1 | C2 | C3 | C4 | 비용 KRW | 안전재고 미만 일수 | 최초 안전재고 미만일 | 지연 오더 수 | 수량 kg | 최초 도착일 | Rank |
|----|----|----|----|----|----|----|----|----|----|----|----|
| OPT-1 | false | true | true | true | 500,000 | 55 | 2026-10-06 | 0 | 25,000 | 2026-10-07 |  |
| OPT-2 | true | true | true | true | 1,000,000 | 0 |  | 0 | 40,000 | 2026-10-03 | 1 |
| OPT-3 | true | true | true | true | 3,750,000 | 0 |  | 0 | 50,000 | 2026-10-05 | 2 |
| OPT-4 | false | true | false | true | 0 | 51 | 2026-10-12 | 1 | 100,000 |  |  |

OPT-4의 수량은 이동하는 제품 생산량이며 원료 입고량이 아닙니다. 긴급 생산을 10/11~10/12로 옮기므로 원료 `first_arrival_date`는 `NULL`, 긴급 판매오더 완료일은 10/12로 납기 10/08을 넘깁니다. 표의 최초 안전재고 미만일은 `fact_option_balance`로 구하는 값이며 `fact_response_option`의 컬럼은 아닙니다.

**gold.fact_risk_event**

| 컬럼 | 값 |
|----|----|
| event_id | EVT-20261001-001 |
| detected_at | Notebook 실행 시각 (reference 기본값 None) |
| scenario_id / bunker_id / material_id / line_id | emergency / BNK-L3-2 / PET-SD / L3 |
| sales_order_id | SO-10322 |
| first_below_safety_date / first_shortage_date | 2026-10-06 / 2026-10-07 |
| min_closing_kg / min_closing_date / required_topup_kg | -23,630 / 2026-11-26 / 35,630 |
| next_inbound_key | 4500010294\|00020 |
| recommended_option_id | OPT-2 |
| recommended_action | BNK-L1-2에서 BNK-L3-2로 PET-SD 40,000 kg 이송 (R-01, 10/02 출고, 10/03 도착) |
| status | open |

## 대응안별 안전재고 미만 Bunker breakdown

**안전재고 미만 Bunker-days**

| option_id | breakdown   |
|-----------|-------------|
| OPT-1     | BNK-L3-2:55 |
| OPT-2     | 없음        |
| OPT-3     | 없음        |
| OPT-4     | BNK-L3-2:51 |

OPT-2 이송 후 최저 잔량은 BNK-L1-2 **16,763kg**(11/01), BNK-L3-2 **16,370kg**(11/26)으로 각각의 안전재고 이상입니다.

## 기준 시나리오 Bunker margin

**주요 Bunker margin**

| bunker_id | safety_stock_kg | avg_daily_use_kg | baseline_min_closing_kg | min_safety_ratio |
|----|----|----|----|----|
| BNK-L3-2 | 12,000 | 6,413.2 | 22,694 | 1.89 |
| BNK-L1-2 | 6,000 | 2,092.2 | 56,763 | 9.46 |

`avg_daily_use_kg`는 baseline 92일의 `requirement_kg` 평균, `min_safety_ratio`는 최소 잔량 ÷ 안전재고입니다. 두 값은 설계 설명용 파생값이며 Gold 컬럼이 아닙니다.
