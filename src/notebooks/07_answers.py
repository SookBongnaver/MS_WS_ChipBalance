# Databricks notebook source
# MAGIC %md
# MAGIC # 07. 정답 계산
# MAGIC Gold는 Fabric Lakehouse(OneLake)에만 있습니다. 이 Notebook은 OneLake의 Gold로 Genie와 Fabric agent에 물어볼 질문 6개의 정답을 계산합니다.
# MAGIC Genie 답과 비교할 기준 값입니다.
# MAGIC
# MAGIC 1. 위에서부터 셀을 하나씩 실행합니다. (**Shift+Enter**)
# MAGIC 2. **2. Genie 질문의 정답**의 표를 Genie 답과 비교합니다.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. 설정과 Gold 불러오기
# MAGIC 05와 06에서 OneLake에 저장한 Gold 테이블 21개(05의 18개와 06이 새로 만든 3개)를 읽어 임시 뷰(`gold_…`)로 등록합니다. 아래 계산이 이 뷰를 씁니다.
# MAGIC
# MAGIC **예상 결과:** 01에서 본 결과가 다시 표시되고, 다음 셀에서 `OneLake에서 불러온 Gold: 21개`가 표시됩니다.

# COMMAND ----------
# MAGIC %run ./01_setup

# COMMAND ----------
for table in GOLD_TABLES + EMERGENCY_GOLD_TABLES:
    read_gold(table)
print("OneLake에서 불러온 Gold:", f"{len(GOLD_TABLES) + len(EMERGENCY_GOLD_TABLES)}개")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Genie 질문의 정답
# MAGIC 07장에서 Genie에 물어볼 질문 6개의 정답을 Gold 테이블로 계산합니다. Genie 답과 이 표를 비교합니다.
# MAGIC 같은 질문을 09장에서 Fabric의 Ontology agent에도 합니다.
# MAGIC
# MAGIC | 번호 | 질문 |
# MAGIC |---|---|
# MAGIC | Q1 | 긴급 오더를 반영하지 않은 현재 계획에서 4분기에 안전재고 아래로 내려가는 Bunker가 있어? |
# MAGIC | Q2 | 긴급 오더를 반영하면 어느 Bunker가 언제부터 안전재고 아래로 내려가고, 얼마나 부족해? |
# MAGIC | Q3 | 긴급 오더 때문에 미뤄진 생산의 판매오더는 납기를 지켜? |
# MAGIC | Q4 | BNK-L3-2로 PET-SD를 보내 줄 수 있는 Bunker는 어디야? 이송 대응안대로 보내면 보내는 Bunker의 재고는 괜찮아? |
# MAGIC | Q5 | BNK-L3-2에 10월 6일 뒤 처음 들어오는 PET-SD 입고는 언제, 어느 공급사에서, 몇 kg이야? |
# MAGIC | Q6 | 대응안 4개 가운데 판단 기준을 모두 만족하는 안과 추천안은? |
# MAGIC
# MAGIC **예상 결과:** 6행
# MAGIC
# MAGIC | 번호 | 정답 | 근거 |
# MAGIC |---|---|---|
# MAGIC | Q1 | 없음 | 24개 Bunker 중 0개 |
# MAGIC | Q2 | BNK-L3-2 | BNK-L3-2 (L3 PET-SD) 10/06부터 미달, 10/07부터 부족, 최저 -23,630 kg (11/26), 필요 보충량 35,630 kg |
# MAGIC | Q3 | 모두 준수 | SO-10108 10/08 완료 (납기 10/11); SO-10109 10/10 완료 (납기 10/14); SO-10110 10/12 완료 (납기 10/15) |
# MAGIC | Q4 | BNK-L1-2 | BNK-L1-2 (R-01, 하루 40,000 kg, 1일, 25원/kg). 이송 후 최저 16,763 kg, 안전재고 6,000 kg |
# MAGIC | Q5 | 10/09 | 10/09 세미폴리머(SUP-PET-B) 25,000 kg (4500010294-00020) |
# MAGIC | Q6 | OPT-2 | OPT-2 Bunker 간 이송 (1순위, 1,000,000원); OPT-3 추가 구매 (2순위, 3,750,000원) |

# COMMAND ----------
q1 = spark.sql("SELECT COUNT_IF(below_safety_days > 0) AS bunkers, COUNT(*) AS total FROM gold_fact_bunker_summary WHERE scenario_id = 'baseline'").first()
q2 = spark.sql("""
SELECT s.bunker_id, s.line_id, s.material_id, s.first_below_safety_date, s.first_shortage_date, s.min_closing_kg, s.min_closing_date,
       s.required_topup_kg
FROM gold_fact_bunker_summary s JOIN gold_fact_bunker_summary b ON b.bunker_id = s.bunker_id AND b.scenario_id = 'baseline'
WHERE s.scenario_id = 'emergency' AND s.below_safety_days > 0 AND b.below_safety_days = 0
""").collect()
q3 = spark.sql("""
SELECT f.sales_order_id, f.finish_date, f.due_date, f.on_time
FROM gold_fact_order_fulfillment f
WHERE f.scenario_id = 'emergency'
  AND f.sales_order_id IN (SELECT sales_order_id FROM gold_fact_plan WHERE scenario_id = 'emergency' AND change_type = 'moved')
ORDER BY f.finish_date
""").collect()
q4 = spark.sql("""
SELECT r.route_id, r.from_bunker_id, r.max_kg_per_day, r.lead_time_days, r.cost_krw_per_kg, MIN(b.closing_kg) AS min_closing_kg,
       MAX(b.safety_stock_kg) AS safety_stock_kg
FROM gold_dim_route r
JOIN gold_fact_option_balance b ON b.option_id = 'OPT-2' AND b.bunker_id = r.from_bunker_id
WHERE r.to_bunker_id = 'BNK-L3-2' AND r.material_id = 'PET-SD'
GROUP BY ALL
""").collect()
q5 = spark.sql("""
SELECT i.expected_date, s.supplier_name, i.supplier_id, i.quantity_kg, i.purchase_order_id, i.po_line_no
FROM gold_fact_inbound i JOIN gold_dim_supplier s ON s.supplier_id = i.supplier_id
WHERE i.bunker_id = 'BNK-L3-2' AND i.expected_date > DATE'2026-10-06'
ORDER BY i.expected_date, i.inbound_key LIMIT 1
""").first()
q6 = spark.sql("SELECT option_id, option_name, recommendation_rank, added_cost_krw FROM gold_fact_response_option WHERE meets_all ORDER BY recommendation_rank").collect()

kg = lambda v: f"{v:,} kg"
answers = [
    ("Q1", "긴급 오더를 반영하지 않은 현재 계획에서 4분기에 안전재고 아래로 내려가는 Bunker가 있어?",
     "없음" if q1.bunkers == 0 else f"{q1.bunkers}개", f"{q1.total}개 Bunker 중 {q1.bunkers}개"),
    ("Q2", "긴급 오더를 반영하면 어느 Bunker가 언제부터 안전재고 아래로 내려가고, 얼마나 부족해?",
     ", ".join(r.bunker_id for r in q2),
     "; ".join(f"{r.bunker_id} ({r.line_id} {r.material_id}) {r.first_below_safety_date:%m/%d}부터 미달, {r.first_shortage_date:%m/%d}부터 부족, "
               f"최저 {kg(r.min_closing_kg)} ({r.min_closing_date:%m/%d}), 필요 보충량 {kg(r.required_topup_kg)}" for r in q2)),
    ("Q3", "긴급 오더 때문에 미뤄진 생산의 판매오더는 납기를 지켜?",
     "모두 준수" if all(r.on_time for r in q3) else "지연 있음",
     "; ".join(f"{r.sales_order_id} {r.finish_date:%m/%d} 완료 (납기 {r.due_date:%m/%d})" for r in q3)),
    ("Q4", "BNK-L3-2로 PET-SD를 보내 줄 수 있는 Bunker는 어디야? 이송 대응안대로 보내면 보내는 Bunker의 재고는 괜찮아?",
     ", ".join(r.from_bunker_id for r in q4),
     "; ".join(f"{r.from_bunker_id} ({r.route_id}, 하루 {kg(r.max_kg_per_day)}, {r.lead_time_days}일, {r.cost_krw_per_kg}원/kg). "
               f"이송 후 최저 {kg(r.min_closing_kg)}, 안전재고 {kg(r.safety_stock_kg)}" for r in q4)),
    ("Q5", "BNK-L3-2에 10월 6일 뒤 처음 들어오는 PET-SD 입고는 언제, 어느 공급사에서, 몇 kg이야?",
     f"{q5.expected_date:%m/%d}",
     f"{q5.expected_date:%m/%d} {q5.supplier_name}({q5.supplier_id}) {kg(q5.quantity_kg)} ({q5.purchase_order_id}-{q5.po_line_no})"),
    ("Q6", "대응안 4개 가운데 판단 기준을 모두 만족하는 안과 추천안은?",
     q6[0].option_id,
     "; ".join(f"{r.option_id} {r.option_name} ({r.recommendation_rank}순위, {r.added_cost_krw:,}원)" for r in q6)),
]
display(spark.createDataFrame([(n, a, b) for n, _, a, b in answers], "`번호` string, `정답` string, `근거` string"))
