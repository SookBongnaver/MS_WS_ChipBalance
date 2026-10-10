# 00. 시나리오와 실습 순서

[목차](../README.md) \| 다음: [01. Databricks 접속과 설정](01-connect.md)

## 업무 상황

당신은 필름 공장의 생산·원료 수급 담당자입니다. 공장에는 생산 라인 6개와 원료 칩을 보관하는 Bunker(원료 저장조) 24개가 있습니다. 기존 생산계획과 입고계획을 바탕으로 2026년 4분기 동안 원료가 모자라지 않도록 관리해야 합니다.

**10월 1일, L3 라인 제품 `P-L3-05` 100,000kg의 긴급 수주가 들어옵니다. 납기는 10월 8일입니다.** 이 제품은 다른 L3 제품보다 PET-SD 원료를 많이 씁니다. 납기를 맞추려면 긴급 생산을 넣고 일부 기존 생산을 뒤로 미뤄야 합니다.

라인에 생산 시간을 확보하는 것만으로는 충분하지 않습니다. **원료 재고가 버티는지, 다른 판매오더의 납기는 지킬 수 있는지, 어떤 대응안이 가장 적절한지** 함께 판단해야 합니다.

## 오늘 해결할 과제

1.  **기준 계획을 확인합니다.** 긴급 수주가 없을 때 모든 Bunker가 4분기 내내 안전재고를 유지하는지 봅니다.
2.  **긴급 수주의 영향을 계산합니다.** 어느 Bunker가 언제부터 안전재고 아래로 내려가는지, 재고가 얼마나 부족해지는지, 생산을 미룬 판매오더의 납기는 지켜지는지 확인합니다.
3.  **대응안을 비교하고 결정 근거를 확인합니다.** 기준을 만족하는 대응안과 비용을 비교해 추천안을 찾고, 보고서와 에이전트로 근거를 검토한 뒤 Teams에서 승인합니다.

검토할 대응안은 **입고 앞당김, Bunker 간 이송, 추가 구매, 생산 순서 조정**의 네 가지입니다. 재고 부족만 해소하는 안이 아니라, 아래 기준을 함께 만족하는 안을 골라야 합니다.

## 판단 기준

| 기준 | 확인할 내용 |
|---|---|
| C1 안전재고 | 모든 Bunker의 매일 기말 재고가 안전재고 이상인가? |
| C2 용량 | 입고·이송 입고를 반영한 재고가 Bunker의 저장 용량을 넘지 않는가? |
| C3 납기 | 긴급 수주와 기존 판매오더 모두 납기 안에 생산을 마치는가? |
| C4 이송 한도 | 이송량이 해당 경로의 하루 한도를 넘지 않는가? |

**네 기준을 모두 만족하는 안 중 추가 비용이 가장 낮은 안을 추천합니다.** 재고·판정·추천 순위는 Notebook으로 계산하고, AI의 설명은 그 계산 결과와 비교합니다. 최종 승인은 담당자가 합니다.

## 실습 흐름과 완성 결과

**계획 확인 → 긴급 수주 반영 → 대응안 비교 → 근거 검토 → 승인 기록**의 흐름을 직접 만듭니다.

| 실습 | 하는 일 | 완성 결과 |
|---|---|---|
| 01–06 데이터와 계산 | Databricks에서 원천 데이터를 만들고 Bronze·Silver로 정제합니다. 기준 계획, 긴급 수주, 대응안을 계산해 OneLake에 저장합니다. | 같은 기준으로 비교할 수 있는 재고·납기·대응안 Gold 테이블 |
| 07–09 근거 질의 | 계산한 정답을 확인하고, Ontology에 업무 개념과 관계를 연결해 질문합니다. Genie 질의는 선택 단계입니다. | 원료 부족과 추천안의 근거를 데이터로 설명하는 Ontology agent |
| 10 보고서 | 수급 현황 페이지를 직접 만들고, 대응안 페이지는 Power BI Copilot으로 생성합니다. Copilot에게 질문하고 인사이트도 얻습니다. | 현황과 대응안을 비교하는 보고서 2페이지 |
| 11–12 제안·검토·승인 | 위험 이벤트를 Eventhouse에 보내 Operations agent의 Teams 제안을 받습니다. Foundry agent로 근거를 검토한 뒤 담당자가 Teams에서 승인합니다. | Teams 제안, 근거 답변, 승인 내역과 이벤트 상태 |
| 13 마무리 | 결과를 확인하고 에이전트·Compute를 멈춥니다. | 확인된 실습 결과와 정리된 실행 상태 |

11장에서는 Teams 제안을 받은 뒤 승인을 보류하고 12장으로 이동합니다. 근거 검토를 마치면 11장으로 돌아와 **승인·결과 확인·Stop**까지 끝냅니다. 이 실습은 승인 기록까지 만들며, 실제 발주와 이송 지시는 하지 않습니다.

실습 데이터는 SAP·FPIMS·PVSS에서 추출한 것과 같은 형식의 **가상 파일 14개**입니다. 파일 내용과 관계는 [02장](02-source-data.md), 재고 계산 방식은 [05장](05-gold-onelake.md), 상세 테이블·행 수는 [데이터 설계](../admin/data-design.md)에서 확인합니다.

<img src="../assets/architecture.svg" width="1000" alt="전체 구성. Azure Databricks가 Bronze와 Silver를 정제하고 Gold를 계산해 OneLake에 저장합니다. Fabric은 Gold로 Semantic model, Power BI 보고서, Ontology를 만듭니다. 내장 Ontology agent가 질문에 답하고, Operations agent는 Eventhouse의 RiskEventStatus를 감시해 Teams로 대응안을 제안합니다. Foundry agent가 Fabric IQ로 근거를 조회하고, 담당자가 승인하면 Notebook이 승인 기록을 남깁니다. 점선은 실습 범위 밖의 선택 연결 예시입니다." />

구성도의 실선은 실습 흐름, 점선은 운영 확장 예시입니다. 점선의 연결은 이 실습에서 만들지 않습니다. Ontology의 Graph 생성도 선택 단계입니다.

## 실습 파일 준비

**전체 실습은 관리자가 준비한 활성 유료 Fabric 용량을 전제로 합니다.** 시작 전에 실습 계정, Databricks 주소, 참가자 번호를 받습니다. 리소스·권한 준비는 [관리자 준비 가이드](../admin/README.md)를 따릅니다.

| 사용할 파일 | 준비 방법 |
|---|---|
| Databricks Notebook 8개 | 관리자가 **Workspace → Shared → ChipBalance**에 원본 폴더 하나를 준비합니다. 01장에서 각자 **본인 Home으로 Clone**합니다. 참가자는 Notebook ZIP을 내려받거나 Import하지 않습니다. |
| Fabric 실습 파일 3개 | 관리자가 전달한 `fabric` 폴더를 본인 PC에 준비합니다. `sm_chipbalance.tmdl`·`chipbalance-theme.json`은 10장, `nb_record_decision.ipynb`는 11장에서 사용합니다. |

**확인할 결과:** 안내받은 Databricks에서 Shared 원본에 접근할 수 있고, PC의 `fabric` 폴더에 위 파일 3개가 있습니다. 공유 원본의 참가자 번호는 고치지 않습니다. **복제 화면과 상세 순서는 [01장](01-connect.md#2-shared-원본을-본인-home에-복제)**에서 확인합니다.

GitHub는 교재와 배포 원본을 관리하는 곳입니다. 파일을 직접 받는 경우에는 [저장소](https://github.com/SookBongnaver/MS_WS_ChipBalance)의 **Code → Download ZIP**으로 내려받아 압축을 풀고 `fabric` 폴더를 사용합니다. 다운로드가 차단된 환경에서는 관리자에게 이 세 파일을 전달받습니다. **Databricks Notebook은 어느 경우든 Shared 원본을 복제**합니다.

## 실습 일정

아래 시간의 합계는 약 6시간 20분입니다. 휴식·환경 준비 대기·AI 응답 대기는 별도이며, 처리 시간은 달라질 수 있습니다.

- 00\. 시나리오와 실습 순서 — 15분 (이 문서)
- [01. Databricks 접속과 설정](01-connect.md) — Databricks, 20분
- [02. 원천 데이터 만들기](02-source-data.md) — Databricks, 20분
- [03. Bronze](03-bronze.md) — Databricks, 15분
- [04. Silver](04-silver.md) — Databricks, 25분
- [05. Gold와 OneLake](05-gold-onelake.md) — Databricks → Fabric, 30분
- [06. 긴급 수주와 대응안](06-emergency-order.md) — Databricks → Fabric, 30분
- [07. 정답 계산과 Genie](07-genie.md) — Databricks, 20분
- [08. Ontology](08-ontology.md) — Fabric, 45분
- [09. Ontology agent에 질문하기](09-ontology-agent.md) — Fabric, 30분
- [10. Power BI 보고서](10-power-bi.md) — Fabric, 45분
- [11. Operations agent](11-operations-agent.md) — Fabric → Teams, 45분
- [12. Foundry agent](12-foundry-agent.md) — Foundry → Fabric, 30분
- [13. 마무리](13-finish.md) — 10분

## 다음 단계

[01. Databricks 접속과 설정](01-connect.md)
