# Databricks notebook source
# MAGIC %md
# MAGIC # 06. 긴급 오더와 대응안
# MAGIC 10월 1일에 접수된 긴급 오더를 생산계획에 넣고, Bunker별·날짜별 재고를 다시 계산합니다.
# MAGIC 안전재고 아래로 내려가는 Bunker를 찾고, 대응안 4개를 같은 판단 기준으로 확인해 추천안을 정합니다.
# MAGIC
# MAGIC | 순서 | 계산 | Gold 테이블 |
# MAGIC |---|---|---|
# MAGIC | 1 | 긴급 오더 접수 | `gold_fact_sales_order` |
# MAGIC | 2 | 긴급 생산계획 | `gold_fact_plan` |
# MAGIC | 3 | 날짜별 Bunker Balance, Bunker 위험 요약, 판매오더 납기 | `gold_fact_balance`, `gold_fact_bunker_summary`, `gold_fact_order_fulfillment` |
# MAGIC | 4 | 대응안 4개와 판단 기준 C1~C4 | `gold_fact_response_option`, `gold_fact_option_balance` |
# MAGIC | 5 | 위험 이벤트와 추천안 | `gold_fact_risk_event` |
# MAGIC
# MAGIC 긴급 오더를 반영한 결과는 시나리오 `emergency`로 저장합니다. 05에서 만든 현재 계획(`baseline`) 행은 그대로 남습니다.
# MAGIC Gold는 05에서 OneLake에 저장한 것을 불러와 이어서 계산하고, 결과도 OneLake에 저장합니다. Unity Catalog에는 만들지 않습니다.
# MAGIC
# MAGIC 1. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 2. 마지막 셀까지 확인하면 교재 06장으로 돌아갑니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정과 Gold 불러오기
# MAGIC 05에서 OneLake에 저장한 Gold 테이블 18개를 읽어 임시 뷰(`gold_…`)로 등록합니다. 아래 계산이 이 뷰를 씁니다.
# MAGIC
# MAGIC **예상 결과:** 01에서 본 결과가 다시 표시되고, `연결 확인 완료`가 나옵니다. 다음 셀에서 `OneLake에서 불러온 Gold: 18개`가 표시됩니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
for table in GOLD_TABLES:
    read_gold(table)
print("OneLake에서 불러온 Gold:", f"{len(GOLD_TABLES)}개")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. 긴급 오더 접수
# MAGIC 고객 누리전자소재(`C-1004`)가 L3 제품 `P-L3-05`(반광택 75μm 후막) 100,000kg을 10월 8일까지 요청했습니다.
# MAGIC 판매오더 번호는 마지막 판매오더 번호의 다음 번호입니다.
# MAGIC
# MAGIC | 값 | 내용 |
# MAGIC |---|---|
# MAGIC | `urgent_production` | L3에서 10월 5일과 6일에 50,000kg씩 긴급 생산합니다. |
# MAGIC | `move_from`, `move_to`, `move_days` | 10월 5–10일에 잡혀 있던 L3 생산을 2일씩 미룹니다. 10월 11–15일 예비일을 씁니다. |
# MAGIC | `today` | 판단 기준일입니다. 대응안의 출고·발주는 다음 날부터 할 수 있습니다. |
# MAGIC
# MAGIC **예상 결과:** 1행. `SO-10322`, 누리전자소재, `P-L3-05`, 100,000kg, 납기 2026-10-08

# COMMAND ----------
from datetime import date, timedelta

today = date(2026, 10, 1)
urgent = {"customer_id": "C-1004", "product_id": "P-L3-05", "line_id": "L3", "order_qty_kg": 100000,
          "order_date": date(2026, 10, 1), "due_date": date(2026, 10, 8), "priority": "high"}
urgent_production = [(date(2026, 10, 5), 50000), (date(2026, 10, 6), 50000)]
move_from, move_to, move_days = date(2026, 10, 5), date(2026, 10, 10), 2

last_number = spark.sql("SELECT MAX(CAST(substring(sales_order_id, 4) AS INT)) FROM gold_fact_sales_order WHERE NOT is_urgent").first()[0]
urgent["sales_order_id"] = f"SO-{last_number + 1}"

spark.createDataFrame(
    [(urgent["sales_order_id"], urgent["order_date"], urgent["customer_id"], urgent["product_id"], urgent["line_id"],
      urgent["order_qty_kg"], urgent["due_date"], urgent["priority"], True)],
    "sales_order_id string, order_date date, customer_id string, product_id string, line_id string, "
    "order_qty_kg bigint, due_date date, priority string, is_urgent boolean").createOrReplaceTempView("urgent_order")
spark.sql("""
CREATE OR REPLACE TEMP VIEW emergency_orders AS
SELECT * FROM gold_fact_sales_order WHERE NOT is_urgent
UNION ALL
SELECT * FROM urgent_order
""")
display(spark.sql("""
SELECT u.sales_order_id, u.order_date, c.customer_name, u.product_id, p.product_name, u.order_qty_kg, u.due_date, u.priority
FROM urgent_order u JOIN gold_dim_customer c USING (customer_id) JOIN gold_dim_product p USING (product_id)
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. 긴급 생산계획
# MAGIC 현재 계획(`baseline`)을 복사해 긴급 생산 2행을 넣고, 10월 5~10일 L3 생산을 2일씩 미룹니다.
# MAGIC `change_type`은 `urgent`(긴급 생산), `moved`(미룬 생산), `none`(그대로)입니다.
# MAGIC
# MAGIC **예상 결과:** L3 10월 1–16일 13행. 10월 5·6일은 `P-L3-05` 긴급 생산이고, `P-L3-01` 6행이 10월 7–12일로 밀립니다.
# MAGIC 모든 행에서 생산일(`plan_date`)이 납기(`due_date`)보다 앞섭니다.

# COMMAND ----------
urgent_values = ", ".join(f"(DATE'{d}', {kg})" for d, kg in urgent_production)
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW emergency_plan AS
WITH plan AS (
    SELECT plan_id,
           CASE WHEN line_id = '{urgent["line_id"]}' AND plan_date BETWEEN DATE'{move_from}' AND DATE'{move_to}'
                THEN date_add(plan_date, {move_days}) ELSE plan_date END AS plan_date,
           line_id, product_id, planned_output_kg, sales_order_id, plan_date AS original_plan_date,
           CASE WHEN line_id = '{urgent["line_id"]}' AND plan_date BETWEEN DATE'{move_from}' AND DATE'{move_to}'
                THEN 'moved' ELSE 'none' END AS change_type
    FROM gold_fact_plan WHERE scenario_id = 'baseline'
    UNION ALL
    SELECT concat('PP-', date_format(d, 'yyyyMMdd'), '-{urgent["line_id"]}-U'), d, '{urgent["line_id"]}', '{urgent["product_id"]}',
           CAST(kg AS BIGINT), '{urgent["sales_order_id"]}', d, 'urgent'
    FROM VALUES {urgent_values} AS t(d, kg)
)
SELECT concat('emergency|', plan_id) AS plan_key, 'emergency' AS scenario_id, plan_id, plan_date, line_id, product_id,
       planned_output_kg, sales_order_id, original_plan_date, change_type
FROM plan
""")
display(spark.sql("""
SELECT p.plan_date, p.original_plan_date, p.change_type, p.product_id, p.planned_output_kg, p.sales_order_id, o.due_date
FROM emergency_plan p JOIN emergency_orders o USING (sales_order_id)
WHERE p.line_id = 'L3' AND p.plan_date <= DATE'2026-10-16'
ORDER BY p.plan_date
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Balance 계산 함수
# MAGIC 05 Gold **7. 날짜별 Bunker Balance**와 같은 계산입니다. 긴급 오더와 대응안마다 다시 계산하도록 함수로 만듭니다.
# MAGIC 계산 단위(`case_id`)마다 Bunker별 재고를 따로 누적합니다.
# MAGIC
# MAGIC | 입력 뷰 | 열 |
# MAGIC |---|---|
# MAGIC | 생산계획 | `case_id`, `plan_date`, `line_id`, `product_id`, `planned_output_kg`, `sales_order_id` |
# MAGIC | 입고 | `case_id`, `bunker_id`, `receipt_date`, `quantity_kg` |
# MAGIC | 이송 | `case_id`, `route_id`, `from_bunker_id`, `to_bunker_id`, `ship_date`, `arrival_date`, `qty_kg` |
# MAGIC
# MAGIC **예상 결과:** 결과 없이 끝납니다.

# COMMAND ----------
TRANSFER_SCHEMA = ("case_id string, route_id string, from_bunker_id string, to_bunker_id string, "
                   "ship_date date, arrival_date date, qty_kg bigint")


def compute_balance(plan_view, receipt_view, transfer_view):
    return spark.sql(f"""
    WITH cases AS (
        SELECT DISTINCT case_id FROM {plan_view}
    ), requirement AS (
        SELECT p.case_id, b.bunker_id, p.plan_date AS balance_date,
               SUM(CAST(ROUND(p.planned_output_kg * f.actual_kg_per_kg, 0) AS BIGINT)) AS requirement_kg
        FROM {plan_view} p
        JOIN gold_fact_usage_factor f ON f.product_id = p.product_id
        JOIN gold_dim_bunker b ON b.line_id = p.line_id AND b.material_id = f.material_id
        GROUP BY p.case_id, b.bunker_id, p.plan_date
    ), receipt AS (
        SELECT case_id, bunker_id, receipt_date AS balance_date, SUM(quantity_kg) AS receipt_kg
        FROM {receipt_view} GROUP BY case_id, bunker_id, receipt_date
    ), transfer_in AS (
        SELECT case_id, to_bunker_id AS bunker_id, arrival_date AS balance_date, SUM(qty_kg) AS transfer_in_kg
        FROM {transfer_view} GROUP BY case_id, to_bunker_id, arrival_date
    ), transfer_out AS (
        SELECT case_id, from_bunker_id AS bunker_id, ship_date AS balance_date, SUM(qty_kg) AS transfer_out_kg
        FROM {transfer_view} GROUP BY case_id, from_bunker_id, ship_date
    ), flow AS (
        SELECT c.case_id, b.bunker_id, d.date_key AS balance_date, s.opening_kg AS start_kg, b.safety_stock_kg, b.capacity_kg,
               COALESCE(r.receipt_kg, 0) AS receipt_kg, COALESCE(ti.transfer_in_kg, 0) AS transfer_in_kg,
               COALESCE(tx.transfer_out_kg, 0) AS transfer_out_kg, COALESCE(q.requirement_kg, 0) AS requirement_kg
        FROM cases c
        CROSS JOIN gold_dim_bunker b
        CROSS JOIN gold_dim_date d
        JOIN gold_fact_opening_stock s ON s.bunker_id = b.bunker_id
        LEFT JOIN receipt r ON r.case_id = c.case_id AND r.bunker_id = b.bunker_id AND r.balance_date = d.date_key
        LEFT JOIN transfer_in ti ON ti.case_id = c.case_id AND ti.bunker_id = b.bunker_id AND ti.balance_date = d.date_key
        LEFT JOIN transfer_out tx ON tx.case_id = c.case_id AND tx.bunker_id = b.bunker_id AND tx.balance_date = d.date_key
        LEFT JOIN requirement q ON q.case_id = c.case_id AND q.bunker_id = b.bunker_id AND q.balance_date = d.date_key
    ), balance AS (
        SELECT *, start_kg + SUM(receipt_kg + transfer_in_kg - transfer_out_kg - requirement_kg)
                      OVER (PARTITION BY case_id, bunker_id ORDER BY balance_date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS closing_kg
        FROM flow
    )
    SELECT case_id, bunker_id, balance_date,
           closing_kg + requirement_kg + transfer_out_kg - transfer_in_kg - receipt_kg AS opening_kg,
           receipt_kg, transfer_in_kg, transfer_out_kg, requirement_kg, closing_kg, safety_stock_kg, capacity_kg,
           closing_kg < safety_stock_kg AS below_safety, closing_kg < 0 AS shortage,
           closing_kg + requirement_kg + transfer_out_kg > capacity_kg AS over_capacity
    FROM balance
    """)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. 긴급 오더를 반영한 Balance
# MAGIC 긴급 생산계획과 입고 예정으로 Bunker 24개의 4분기 재고를 계산합니다. `BNK-L3-2`(L3 PET-SD)의 10월 1~12일을 봅니다.
# MAGIC
# MAGIC **예상 결과:** 12행. 10월 5·6일 사용량이 23,162kg으로 늘어, 10월 6일 기말 재고 3,733kg이 안전재고 12,000kg보다 적습니다(`below_safety`).
# MAGIC 10월 7일에는 -2,560kg으로 부족합니다(`shortage`). 10월 9일 입고 25,000kg으로도 안전재고를 회복하지 못합니다.

# COMMAND ----------
spark.sql("CREATE OR REPLACE TEMP VIEW emergency_case_plan AS SELECT 'emergency' AS case_id, * FROM emergency_plan")
spark.sql("""
CREATE OR REPLACE TEMP VIEW emergency_case_receipt AS
SELECT 'emergency' AS case_id, bunker_id, expected_date AS receipt_date, quantity_kg FROM gold_fact_inbound
""")
spark.createDataFrame([], TRANSFER_SCHEMA).createOrReplaceTempView("no_transfer")
compute_balance("emergency_case_plan", "emergency_case_receipt", "no_transfer").createOrReplaceTempView("emergency_case_balance")
spark.sql("""
CREATE OR REPLACE TEMP VIEW emergency_balance AS
SELECT concat('emergency|', bunker_id, '|', balance_date) AS balance_key, 'emergency' AS scenario_id, bunker_id, balance_date,
       opening_kg, receipt_kg, transfer_in_kg, transfer_out_kg, requirement_kg, closing_kg, safety_stock_kg, capacity_kg,
       below_safety, shortage, over_capacity
FROM emergency_case_balance
""")
display(spark.table("emergency_balance")
        .filter("bunker_id = 'BNK-L3-2' AND balance_date <= '2026-10-12'")
        .select("balance_date", "receipt_kg", "requirement_kg", "closing_kg", "safety_stock_kg", "below_safety", "shortage")
        .orderBy("balance_date"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Bunker 위험 요약
# MAGIC 05 Gold **8. Bunker 위험 요약**과 같은 방식으로 요약하고, 현재 계획과 비교합니다.
# MAGIC
# MAGIC **예상 결과:** 1행. 긴급 오더로 안전재고 아래로 내려가는 Bunker는 `BNK-L3-2`뿐입니다.
# MAGIC 안전재고 미달 일수가 현재 계획 0일에서 57일로 늘고, 10월 6일부터 미달, 10월 7일부터 부족합니다.
# MAGIC 가장 낮은 재고는 11월 26일 -23,630kg이며, 필요 보충량은 35,630kg입니다.

# COMMAND ----------
spark.sql("""
CREATE OR REPLACE TEMP VIEW emergency_summary AS
SELECT concat('emergency|', f.bunker_id) AS summary_key, 'emergency' AS scenario_id, f.bunker_id, b.line_id, b.material_id,
       COUNT_IF(f.below_safety) AS below_safety_days,
       MIN(CASE WHEN f.below_safety THEN f.balance_date END) AS first_below_safety_date,
       MIN(CASE WHEN f.shortage THEN f.balance_date END) AS first_shortage_date,
       MIN(f.closing_kg) AS min_closing_kg,
       MIN_BY(f.balance_date, struct(f.closing_kg, f.balance_date)) AS min_closing_date,
       GREATEST(0, MAX(f.safety_stock_kg) - MIN(f.closing_kg)) AS required_topup_kg
FROM emergency_balance f JOIN gold_dim_bunker b ON b.bunker_id = f.bunker_id
GROUP BY f.bunker_id, b.line_id, b.material_id
""")
display(spark.sql("""
SELECT e.bunker_id, e.material_id, b.below_safety_days AS `현재 계획 미달일`, e.below_safety_days AS `긴급 오더 미달일`,
       e.first_below_safety_date AS `첫 미달일`, e.first_shortage_date AS `첫 부족일`, e.min_closing_kg AS `최저 재고(kg)`,
       e.min_closing_date AS `최저 재고일`, e.required_topup_kg AS `필요 보충량(kg)`
FROM emergency_summary e JOIN gold_fact_bunker_summary b ON b.bunker_id = e.bunker_id AND b.scenario_id = 'baseline'
WHERE e.below_safety_days > 0
ORDER BY e.first_below_safety_date, e.bunker_id
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. 판매오더 납기
# MAGIC 긴급 생산계획으로 판매오더마다 생산 완료일을 다시 구합니다. 생산이 바뀐 오더만 봅니다.
# MAGIC
# MAGIC **예상 결과:** 4행, 모두 `on_time`이 `true`입니다. 긴급 오더 `SO-10322`는 10월 6일에 생산을 마쳐 납기보다 2일 빠릅니다.
# MAGIC 미룬 `SO-10108`, `SO-10109`, `SO-10110`도 납기 안에 끝납니다. 아래에 `납기 지연: 0개`가 표시됩니다.

# COMMAND ----------
spark.sql("""
CREATE OR REPLACE TEMP VIEW emergency_fulfillment AS
SELECT concat('emergency|', o.sales_order_id) AS fulfillment_key, 'emergency' AS scenario_id, o.sales_order_id, o.customer_id, o.product_id,
       o.line_id, o.due_date, MAX(p.plan_date) AS finish_date, datediff(o.due_date, MAX(p.plan_date)) AS slack_days,
       MAX(p.plan_date) <= o.due_date AS on_time
FROM emergency_orders o JOIN emergency_plan p ON p.sales_order_id = o.sales_order_id
GROUP BY o.sales_order_id, o.customer_id, o.product_id, o.line_id, o.due_date
""")
display(spark.sql("""
SELECT f.sales_order_id, c.customer_name, f.product_id, f.due_date, b.finish_date AS baseline_finish_date, f.finish_date, f.slack_days, f.on_time
FROM emergency_fulfillment f
JOIN gold_dim_customer c ON c.customer_id = f.customer_id
LEFT JOIN gold_fact_order_fulfillment b ON b.sales_order_id = f.sales_order_id AND b.scenario_id = 'baseline'
WHERE f.sales_order_id IN (SELECT sales_order_id FROM emergency_plan WHERE change_type <> 'none')
ORDER BY f.finish_date
"""))
late_orders = spark.sql("SELECT COUNT_IF(NOT on_time) FROM emergency_fulfillment").first()[0]
print(f"납기 지연: {late_orders}개")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. 대응안 4개 만들기
# MAGIC 부족해지는 Bunker(`BNK-L3-2`)의 필요 보충량 35,630kg을 채우는 방법 4가지를 만듭니다. 값은 모두 Gold 테이블에서 가져옵니다.
# MAGIC
# MAGIC | 대응안 | 방법 | 추가 비용 |
# MAGIC |---|---|---|
# MAGIC | `OPT-1` 입고 앞당김 | 미달 시작일 뒤 첫 입고 예정을 공급사가 당길 수 있는 최대 일수(`max_pull_in_days`)만큼 당깁니다. | 수량 × 앞당김 수수료 |
# MAGIC | `OPT-2` Bunker 간 이송 | 같은 원료를 보관하는 Bunker에서 비용이 가장 낮은 경로로 옮깁니다. 5,000kg 단위, 경로의 하루 한도까지 매일 출고합니다. | 수량 × 이송 비용 |
# MAGIC | `OPT-3` 추가 구매 | 공급사에 발주 단위로 긴급 구매합니다. 표준 리드타임 + 계획 지연일 뒤에 들어옵니다. | 수량 × 단가 × 긴급 할증률 |
# MAGIC | `OPT-4` 생산 순서 조정 | 긴급 생산을 다음 입고 뒤 L3 계획이 없는 날로 옮깁니다. | 0 |
# MAGIC
# MAGIC **예상 결과:** 4행
# MAGIC
# MAGIC | 대응안 | 내용 | 수량 | 첫 도착 | 추가 비용 |
# MAGIC |---|---|---|---|---|
# MAGIC | `OPT-1` | 4500010294-00020 입고일을 10/09에서 10/07로 앞당김 | 25,000kg | 10/07 | 500,000원 |
# MAGIC | `OPT-2` | BNK-L1-2에서 BNK-L3-2로 PET-SD 40,000kg 이송 (R-01) | 40,000kg | 10/03 | 1,000,000원 |
# MAGIC | `OPT-3` | 세미폴리머(SUP-PET-B)에 PET-SD 50,000kg 긴급 구매 | 50,000kg | 10/05 | 3,750,000원 |
# MAGIC | `OPT-4` | 긴급 생산을 10/11~10/12로 이동 | 100,000kg | - | 0원 |

# COMMAND ----------
def ceil_to(value, step):
    return -(-value // step) * step


target = spark.sql("""
SELECT e.bunker_id, e.material_id, e.first_below_safety_date, e.required_topup_kg
FROM emergency_summary e JOIN gold_fact_bunker_summary b ON b.bunker_id = e.bunker_id AND b.scenario_id = 'baseline'
WHERE e.below_safety_days > 0 AND b.below_safety_days = 0
ORDER BY e.first_below_safety_date, e.bunker_id
LIMIT 1
""").first()
material = spark.table("gold_dim_material").filter(f"material_id = '{target.material_id}'").first()
supplier = spark.table("gold_dim_supplier").filter(f"supplier_id = '{material.supplier_id}'").first()
next_in = spark.table("gold_fact_inbound").filter(
    f"bunker_id = '{target.bunker_id}' AND expected_date > DATE'{target.first_below_safety_date}'").orderBy("expected_date", "inbound_key").first()
route = spark.table("gold_dim_route").filter(
    f"to_bunker_id = '{target.bunker_id}' AND material_id = '{target.material_id}'").orderBy("cost_krw_per_kg", "route_id").first()

# OPT-1: 첫 입고 예정을 앞당김
pulled_promised = max(next_in.promised_date - timedelta(days=supplier.max_pull_in_days), today + timedelta(days=1))
pulled_date = pulled_promised + timedelta(days=supplier.planning_delay_days)

# OPT-2: 경로의 하루 한도까지 매일 출고
transfer_qty = ceil_to(target.required_topup_kg, 5000)
transfers, left, ship = [], transfer_qty, today + timedelta(days=1)
while left > 0:
    qty = min(left, route.max_kg_per_day)
    transfers.append(("OPT-2", route.route_id, route.from_bunker_id, target.bunker_id, ship,
                      ship + timedelta(days=route.lead_time_days), qty))
    left -= qty
    ship += timedelta(days=1)

# OPT-3: 발주 단위로 긴급 구매
spot_qty = ceil_to(target.required_topup_kg, supplier.order_unit_kg)
spot_date = today + timedelta(days=supplier.standard_lead_time_days + supplier.planning_delay_days)
spot_cost = (spot_qty * material.unit_price_krw_per_kg * supplier.spot_premium_pct + 50) // 100

# OPT-4: 다음 입고 뒤 L3 계획이 없는 날
free_days = [r.date_key for r in spark.sql(f"""
    SELECT date_key FROM gold_dim_date
    WHERE date_key > DATE'{next_in.expected_date}'
      AND date_key NOT IN (SELECT plan_date FROM gold_fact_plan WHERE scenario_id = 'baseline' AND line_id = '{urgent["line_id"]}')
    ORDER BY date_key""").collect()][:len(urgent_production)]

options = [
    ("OPT-1", "입고 앞당김", None, None, next_in.purchase_order_id, supplier.supplier_id, next_in.quantity_kg, pulled_date,
     next_in.quantity_kg * supplier.pull_in_fee_krw_per_kg,
     f"{next_in.purchase_order_id}-{next_in.po_line_no} 입고일을 {next_in.expected_date:%m/%d}에서 {pulled_date:%m/%d}로 앞당김"),
    ("OPT-2", "Bunker 간 이송", route.from_bunker_id, route.route_id, None, None, transfer_qty, transfers[0][5],
     transfer_qty * route.cost_krw_per_kg,
     f"{route.from_bunker_id}에서 {target.bunker_id}로 {target.material_id} {transfer_qty:,} kg 이송 "
     f"({route.route_id}, {transfers[0][4]:%m/%d} 출고, {transfers[-1][5]:%m/%d} 도착)"),
    ("OPT-3", "추가 구매", None, None, None, supplier.supplier_id, spot_qty, spot_date, spot_cost,
     f"{supplier.supplier_name}({supplier.supplier_id})에 {target.material_id} {spot_qty:,} kg 긴급 구매 ({spot_date:%m/%d} 입고)"),
    ("OPT-4", "생산 순서 조정", None, None, None, None, urgent["order_qty_kg"], None, 0,
     f"긴급 생산을 다음 입고({next_in.expected_date:%m/%d}) 뒤 {free_days[0]:%m/%d}~{free_days[-1]:%m/%d}로 이동"),
]
spark.createDataFrame(options, "option_id string, option_name string, source_bunker_id string, route_id string, "
                               "purchase_order_id string, supplier_id string, qty_kg bigint, first_arrival_date date, "
                               "added_cost_krw bigint, action_detail string").createOrReplaceTempView("option_input")
display(spark.sql("SELECT option_id, option_name, qty_kg, first_arrival_date, added_cost_krw, action_detail FROM option_input ORDER BY option_id"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. 대응안별 Balance와 판단 기준
# MAGIC 대응안마다 Bunker 24개의 4분기 재고를 다시 계산하고, 아래 기준을 모두 만족하는지 확인합니다.
# MAGIC 기준을 모두 만족한 대응안에만 추가 비용이 낮은 순서로 추천 순위(`recommendation_rank`)를 붙입니다.
# MAGIC
# MAGIC | 기준 | 내용 |
# MAGIC |---|---|
# MAGIC | C1 안전재고 | 모든 Bunker의 매일 기말 재고 ≥ 안전재고 |
# MAGIC | C2 용량 | 모든 Bunker의 매일 기초 재고 + 입고 + 이송 입고 ≤ 용량 |
# MAGIC | C3 납기 | 모든 판매오더의 생산 완료일 ≤ 납기 |
# MAGIC | C4 이송 한도 | 하루 이송량 ≤ 경로의 하루 한도 |
# MAGIC
# MAGIC **예상 결과:** 4행. `OPT-2`(Bunker 간 이송)가 추천 1순위, `OPT-3`(추가 구매)가 2순위입니다.
# MAGIC `OPT-1`은 C1(10/06부터 미달), `OPT-4`는 C1과 C3(`SO-10322` 완료 10/12, 납기 10/08)을 만족하지 못합니다.

# COMMAND ----------
option_ids = [o[0] for o in options]
urgent_rows = spark.sql("SELECT plan_date, planned_output_kg FROM emergency_plan WHERE change_type = 'urgent' ORDER BY plan_date").collect()
moved_urgent = ", ".join(f"(DATE'{d}', {r.planned_output_kg})" for r, d in zip(urgent_rows, free_days))
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW option_case_plan AS
SELECT o.option_id AS case_id, p.plan_date, p.line_id, p.product_id, p.planned_output_kg, p.sales_order_id
FROM emergency_plan p CROSS JOIN (SELECT explode(array('OPT-1', 'OPT-2', 'OPT-3')) AS option_id) o
UNION ALL
SELECT 'OPT-4', plan_date, line_id, product_id, planned_output_kg, sales_order_id FROM gold_fact_plan WHERE scenario_id = 'baseline'
UNION ALL
SELECT 'OPT-4', d, '{urgent["line_id"]}', '{urgent["product_id"]}', CAST(kg AS BIGINT), '{urgent["sales_order_id"]}'
FROM VALUES {moved_urgent} AS t(d, kg)
""")
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW option_case_receipt AS
SELECT o.option_id AS case_id, i.bunker_id,
       CASE WHEN o.option_id = 'OPT-1' AND i.inbound_key = '{next_in.inbound_key}' THEN DATE'{pulled_date}' ELSE i.expected_date END AS receipt_date,
       i.quantity_kg
FROM gold_fact_inbound i CROSS JOIN (SELECT explode(array({", ".join(f"'{o}'" for o in option_ids)})) AS option_id) o
UNION ALL
SELECT 'OPT-3', '{target.bunker_id}', DATE'{spot_date}', CAST({spot_qty} AS BIGINT)
""")
spark.createDataFrame(transfers, TRANSFER_SCHEMA).createOrReplaceTempView("option_case_transfer")
compute_balance("option_case_plan", "option_case_receipt", "option_case_transfer").createOrReplaceTempView("option_case_balance")

checks = {r.option_id: r for r in spark.sql("""
WITH below AS (
    SELECT case_id, COUNT(*) AS days, MIN(balance_date) AS first_date, MIN_BY(bunker_id, struct(balance_date, bunker_id)) AS first_bunker
    FROM option_case_balance WHERE below_safety GROUP BY case_id
), over AS (
    SELECT case_id, COUNT(*) AS days, MIN(balance_date) AS first_date, MIN_BY(bunker_id, struct(balance_date, bunker_id)) AS first_bunker
    FROM option_case_balance WHERE over_capacity GROUP BY case_id
), finish AS (
    SELECT p.case_id, p.sales_order_id, MAX(p.plan_date) AS finish_date, MAX(o.due_date) AS due_date
    FROM option_case_plan p JOIN emergency_orders o ON o.sales_order_id = p.sales_order_id
    GROUP BY p.case_id, p.sales_order_id
), late AS (
    SELECT case_id, COUNT(*) AS orders, MIN_BY(struct(sales_order_id, finish_date, due_date), struct(finish_date, sales_order_id)) AS first_order
    FROM finish WHERE finish_date > due_date GROUP BY case_id
), bad_route AS (
    SELECT t.case_id, COUNT(*) AS transfers, MIN(t.route_id) AS first_route
    FROM option_case_transfer t JOIN gold_dim_route r ON r.route_id = t.route_id
    WHERE t.qty_kg > r.max_kg_per_day GROUP BY t.case_id
)
SELECT o.option_id, COALESCE(b.days, 0) AS below_days, b.first_date AS below_date, b.first_bunker AS below_bunker,
       COALESCE(v.days, 0) AS over_days, v.first_date AS over_date, v.first_bunker AS over_bunker,
       COALESCE(l.orders, 0) AS late_orders, l.first_order, COALESCE(x.transfers, 0) AS bad_transfers, x.first_route
FROM option_input o
LEFT JOIN below b ON b.case_id = o.option_id
LEFT JOIN over v ON v.case_id = o.option_id
LEFT JOIN late l ON l.case_id = o.option_id
LEFT JOIN bad_route x ON x.case_id = o.option_id
""").collect()}

rows = []
for o in options:
    c = checks[o[0]]
    passed = (c.below_days == 0, c.over_days == 0, c.late_orders == 0, c.bad_transfers == 0)
    notes = []
    if not passed[0]:
        notes.append(f"C1 안전재고: {c.below_bunker} {c.below_date:%m/%d}부터 미달")
    if not passed[1]:
        notes.append(f"C2 용량: {c.over_bunker} {c.over_date:%m/%d} 초과")
    if not passed[2]:
        notes.append(f"C3 납기: {c.first_order.sales_order_id} 완료 {c.first_order.finish_date:%m/%d}, 납기 {c.first_order.due_date:%m/%d}")
    if not passed[3]:
        notes.append(f"C4 이송 한도: {c.first_route} 하루 한도 초과")
    rows.append((o[0], o[1], "emergency", target.bunker_id, o[2], o[3], o[4], o[5], o[6], o[7], o[8], *passed, all(passed),
                 c.below_days, c.late_orders, o[9], "; ".join(notes) or "모든 기준 충족"))
spark.createDataFrame(rows, "option_id string, option_name string, scenario_id string, target_bunker_id string, "
                            "source_bunker_id string, route_id string, purchase_order_id string, supplier_id string, qty_kg bigint, "
                            "first_arrival_date date, added_cost_krw bigint, c1_safety_pass boolean, c2_capacity_pass boolean, "
                            "c3_due_date_pass boolean, c4_route_limit_pass boolean, meets_all boolean, below_safety_days bigint, "
                            "late_order_count bigint, action_detail string, result_note string").createOrReplaceTempView("option_checked")
spark.sql("""
CREATE OR REPLACE TEMP VIEW response_option AS
SELECT option_id, option_name, scenario_id, target_bunker_id, source_bunker_id, route_id, purchase_order_id, supplier_id, qty_kg,
       first_arrival_date, added_cost_krw, c1_safety_pass, c2_capacity_pass, c3_due_date_pass, c4_route_limit_pass, meets_all,
       below_safety_days, late_order_count,
       CASE WHEN meets_all THEN CAST(ROW_NUMBER() OVER (PARTITION BY meets_all ORDER BY added_cost_krw, option_id) AS INT) END AS recommendation_rank,
       action_detail, result_note
FROM option_checked
""")
display(spark.sql("""
SELECT option_id AS `대응안`, option_name AS `이름`, c1_safety_pass AS C1, c2_capacity_pass AS C2, c3_due_date_pass AS C3,
       c4_route_limit_pass AS C4, recommendation_rank AS `추천 순위`, added_cost_krw AS `추가 비용(원)`, result_note AS `판단`
FROM response_option ORDER BY option_id
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 10. 추천안의 두 Bunker 확인
# MAGIC 추천안 `OPT-2`는 `BNK-L1-2`의 PET-SD를 `BNK-L3-2`로 옮깁니다. 받는 Bunker와 보내는 Bunker 모두 안전재고를 지키는지 봅니다.
# MAGIC 대응안마다 재고가 바뀌는 Bunker(부족한 Bunker와 이송 출발 Bunker)의 날짜별 재고는 `option_balance`에 모읍니다.
# MAGIC
# MAGIC **예상 결과:** 2행. 두 Bunker 모두 `below_safety_days`가 0입니다. 가장 낮은 재고는 `BNK-L1-2` 16,763kg(11월 1일, 안전재고 6,000kg),
# MAGIC `BNK-L3-2` 16,370kg(11월 26일, 안전재고 12,000kg)입니다.

# COMMAND ----------
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW option_balance AS
SELECT concat(b.case_id, '|', b.bunker_id, '|', b.balance_date) AS option_balance_key, b.case_id AS option_id, b.bunker_id, b.balance_date,
       b.opening_kg, b.receipt_kg, b.transfer_in_kg, b.transfer_out_kg, b.requirement_kg, b.closing_kg, b.safety_stock_kg, b.capacity_kg,
       b.below_safety, b.shortage, b.over_capacity
FROM option_case_balance b
WHERE b.bunker_id = '{target.bunker_id}'
   OR EXISTS (SELECT 1 FROM option_case_transfer t WHERE t.case_id = b.case_id AND t.from_bunker_id = b.bunker_id)
""")
display(spark.sql("""
SELECT option_id, bunker_id, COUNT_IF(below_safety) AS below_safety_days, MIN(closing_kg) AS min_closing_kg,
       MIN_BY(balance_date, struct(closing_kg, balance_date)) AS min_closing_date, MAX(safety_stock_kg) AS safety_stock_kg
FROM option_balance WHERE option_id = 'OPT-2'
GROUP BY option_id, bunker_id ORDER BY bunker_id
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 11. 위험 이벤트
# MAGIC 부족해지는 Bunker, 원인이 된 판매오더, 다음 입고, 추천안을 한 행으로 모읍니다. Fabric Operations agent가 이 행을 보고 담당자에게 대응안을 제안합니다.
# MAGIC `detected_at`은 이 셀을 실행한 시각이고, `status`는 처음에 `open`입니다.
# MAGIC
# MAGIC **예상 결과:** 1행. `EVT-20261001-001`, `SO-10322`, `BNK-L3-2`, 추천안 `OPT-2`, `status` `open`

# COMMAND ----------
detected_at = spark.sql("SELECT date_format(current_timestamp(), 'yyyy-MM-dd HH:mm:ss')").first()[0]
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW risk_event AS
SELECT concat('EVT-', date_format(DATE'{today}', 'yyyyMMdd'), '-001') AS event_id, TIMESTAMP'{detected_at}' AS detected_at,
       'emergency' AS scenario_id, '{urgent["sales_order_id"]}' AS sales_order_id, s.bunker_id, s.line_id, s.material_id,
       s.first_below_safety_date, s.first_shortage_date, s.min_closing_kg, s.min_closing_date, s.required_topup_kg,
       '{next_in.inbound_key}' AS next_inbound_key, o.option_id AS recommended_option_id, o.action_detail AS recommended_action,
       'open' AS status
FROM emergency_summary s CROSS JOIN response_option o
WHERE s.bunker_id = '{target.bunker_id}' AND o.recommendation_rank = 1
""")
display(spark.table("risk_event").select("event_id", "detected_at", "sales_order_id", "bunker_id", "required_topup_kg",
                                         "recommended_option_id", "status"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 12. Gold 테이블 저장
# MAGIC 긴급 오더 결과를 OneLake의 Gold 테이블에 넣고, 바뀐 테이블 9개를 Fabric Lakehouse의 `gold` 스키마에 다시 저장합니다. 05와 같은 방법입니다.
# MAGIC 다시 실행하면 `emergency` 행과 긴급 판매오더를 지우고 다시 넣습니다. 대응안, 대응안별 재고, 위험 이벤트는 새 Gold 테이블입니다.
# MAGIC Unity Catalog에는 만들지 않습니다.
# MAGIC
# MAGIC **예상 결과:** 9행 (1~2분)
# MAGIC
# MAGIC | Gold 테이블 | OneLake 행 수 | `emergency` 행 수 |
# MAGIC |---|---|---|
# MAGIC | `gold_dim_scenario` | 2 | 1 |
# MAGIC | `gold_fact_sales_order` | 322 | 1 (긴급 오더) |
# MAGIC | `gold_fact_plan` | 1,096 | 549 |
# MAGIC | `gold_fact_order_fulfillment` | 643 | 322 |
# MAGIC | `gold_fact_balance` | 4,416 | 2,208 |
# MAGIC | `gold_fact_bunker_summary` | 48 | 24 |
# MAGIC | `gold_fact_response_option` | 4 | 4 |
# MAGIC | `gold_fact_option_balance` | 460 | 460 |
# MAGIC | `gold_fact_risk_event` | 1 | 1 |

# COMMAND ----------
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW emergency_scenario AS
SELECT 'emergency' AS scenario_id, '긴급 오더 반영' AS scenario_name,
       concat('{urgent["order_date"]} 접수 {urgent["sales_order_id"]} (', customer_name, ', {urgent["product_id"]} ',
              format_number({urgent["order_qty_kg"]}, 0), ' kg)') AS description
FROM gold_dim_customer WHERE customer_id = '{urgent["customer_id"]}'
""")

replaced = [("gold_dim_scenario", "scenario_id = 'emergency'", "emergency_scenario"),
            ("gold_fact_sales_order", "is_urgent", "urgent_order"),
            ("gold_fact_plan", "scenario_id = 'emergency'", "emergency_plan"),
            ("gold_fact_order_fulfillment", "scenario_id = 'emergency'", "emergency_fulfillment"),
            ("gold_fact_balance", "scenario_id = 'emergency'", "emergency_balance"),
            ("gold_fact_bunker_summary", "scenario_id = 'emergency'", "emergency_summary")]
created = [("gold_fact_response_option", "response_option"), ("gold_fact_option_balance", "option_balance"),
           ("gold_fact_risk_event", "risk_event")]

from pyspark.sql import functions as F

counts = []
for table, condition, view in replaced:
    name = table.removeprefix("gold_")
    kept = spark.table(table).where(f"NOT coalesce({condition}, false)")
    added = spark.table(view).toDF(*kept.columns).select([F.col(f.name).cast(f.dataType) for f in kept.schema.fields])
    publish_gold(name, kept.union(added))
    counts.append((table, onelake_gold_rows(name), spark.table(table).filter(condition).count()))
for table, view in created:
    name = table.removeprefix("gold_")
    publish_gold(name, spark.table(view))
    counts.append((table, onelake_gold_rows(name), onelake_gold_rows(name)))
display(spark.createDataFrame(counts, "`Gold 테이블` string, `OneLake 행 수` long, `emergency 행 수` long"))
print("OneLake 경로:", f"{ONELAKE_ROOT}/Tables/gold")
