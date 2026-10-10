# 00. 시나리오와 실습 순서

[목차](../README.md) \| 다음: [01. Databricks 접속과 설정](01-connect.md)

## 업무 상황

필름 공장 한 곳에 BOPET 라인 4개(L1–L4)와 BOPA 라인 2개(L5·L6)가 있습니다. 라인마다 Bunker 4개에 원료 칩을 보관하고, 생산계획에 맞춰 Chip을 투입합니다. 생산 담당자는 4분기(2026년 10월 1일–12월 31일) 동안 Bunker별 Chip 재고가 안전재고 아래로 내려가지 않도록 관리합니다.

10월 1일, L3 라인 제품 `P-L3-05` 100,000kg 긴급 수주가 접수되었습니다. 납기는 10월 8일입니다. `P-L3-05`는 제품 1kg에 PET-SD Chip 0.45kg을 쓰며, L3의 다른 제품보다 PET-SD를 3배 이상 많이 씁니다. 담당자는 PET-SD가 언제부터 부족해지는지 계산하고 대응안을 정해야 합니다.

확인할 질문은 세 가지입니다.

1.  기준 계획에서 모든 Bunker의 재고가 4분기 내내 안전재고 이상인가?
2.  긴급 수주를 반영하면 어느 Bunker가 언제부터 안전재고 아래로 내려가고, 얼마나 부족한가?
3.  입고 앞당김, Bunker 간 이송, 추가 구매, 생산 순서 조정 가운데 어떤 대응안이 판단 기준을 만족하는가?

## 원천 데이터 (가상)

SAP, FPIMS, PVSS에서 추출한 것과 같은 형식의 파일 14개를 씁니다. 모두 43,410행입니다. 02장에서 Notebook을 실행해 공장 한 곳의 1년 운영 기록과 4분기 계획을 만듭니다.

| 시스템 | 데이터 | 기간 | 행 수 |
|----|----|----|----|
| SAP | 원료 칩 12종과 단가, 공급사 6곳(리드타임, 발주 단위) | 기준정보 | 18 |
| SAP | 원료 입고 실적 (약속일, 실제 입고일) | 2025-10 – 2026-09 | 2,849 |
| SAP | 미결 발주 = 4분기 입고예정 (Bunker별) | 2026-10 – 12 | 731 |
| SAP | 판매오더 (제품, 수량, 납기) | 2026-10 – 12 | 321 |
| FPIMS | 라인 6개, Bunker 24개(용량, 안전재고), 제품 30개, 제품별 원료 소요량 기준, Bunker 간 이송 경로 | 기준정보 | 190 |
| FPIMS | 생산 Lot 실적과 Lot별 원료 사용 실적 | 2025-10 – 2026-09 | 21,476 |
| FPIMS | 생산계획 (라인·일자별 제품과 생산량) | 2026-10 – 12 | 547 |
| PVSS | Bunker 레벨 센서 (1시간 간격) | 2026-09 | 17,278 |

## 데이터와 관계

``` text
라인 ──보유──▶ Bunker ──보관──▶ 원료 Chip ◀──공급── 공급사
제품 ──소요량 기준──▶ 원료 Chip
판매오더 ──▶ 생산계획(라인·일자·제품) ──원료 소요──▶ Bunker
미결 발주(입고예정) ──입고──▶ Bunker
Bunker ──이송 경로──▶ 같은 원료를 보관하는 다른 라인의 Bunker
생산 Lot ──원료 투입 실적──▶ Bunker
레벨 센서 ──시간별 재고──▶ Bunker
```

과거 실적으로 계획에 쓸 값을 먼저 구합니다.

- **실제 소요량 기준:** 1년 동안의 원료 사용 실적 ÷ 생산 실적 (제품·원료별). 표준 소요량보다 1–4% 많습니다.
- **10월 1일 시작 재고:** 9월 30일 23시 센서값
- **입고 예정일:** 발주 약속일 + 공급사의 평균 입고 지연일

그다음 4분기 92일 동안 Bunker별 재고를 날짜마다 계산합니다.

``` text
당일 마감 재고 = 전일 마감 재고 + 입고 + 이송 입고 − 이송 출고 − 원료 소요량
원료 소요량 = 생산계획(kg) × 실제 소요량 기준
```

- **안전재고 미만:** 마감 재고가 Bunker의 안전재고보다 적은 날입니다.
- **부족:** 마감 재고가 0kg보다 적은 날입니다. 음수는 계획대로 생산하면 모자라는 양입니다.
- **필요 보충량:** 4분기 내내 안전재고를 지키려면 더 있어야 하는 양입니다. `max(0, 안전재고 − 최저 마감 재고)`로 계산합니다.

## 데이터 흐름

<img src="../assets/architecture.svg" width="1000" alt="전체 구성. Azure Databricks가 Bronze와 Silver를 정제하고 Gold를 계산해 OneLake에 저장합니다. Fabric은 Gold로 Semantic model, Power BI 보고서, Ontology를 만듭니다. 내장 Ontology agent가 질문에 답하고, Operations agent는 Eventhouse의 RiskEventStatus를 감시해 Teams로 대응안을 제안합니다. Foundry agent가 Fabric IQ로 근거를 조회하고, 담당자가 승인하면 Notebook이 승인 기록을 남깁니다. 점선은 실습 범위 밖의 선택 연결 예시입니다." />

09장은 내장 Ontology agent로 질문하고, 11장은 Eventhouse `eh_chipbalance`를 거쳐 제안을 받습니다. Teams 제안의 근거를 12장 Foundry agent로 검토한 뒤, 11장으로 돌아와 승인·결과 확인을 마칩니다. 점선의 Work IQ·Microsoft 365·Power Platform 연결은 이 실습 범위 밖이며, 적용 시 지원 상태·인증·라이선스·정책을 별도로 확인합니다.

- **Azure Databricks** — 원천 파일을 Bronze → Silver로 정제하고, 재고와 대응안을 계산해 Gold 21개를 OneLake에만 저장합니다.
- **Microsoft Fabric** — Gold로 Ontology와 Power BI 보고서를 만들어 원료 수급 현황과 부족 지점을 파악합니다. Ontology agent는 질문에 답하고, Operations agent는 Eventhouse의 위험 이벤트를 감시해 대응안을 제안합니다.
- **Microsoft Foundry** — Foundry agent가 Fabric IQ 도구로 Ontology를 읽어, 승인하기 전에 대응안의 근거를 답합니다.
- **Microsoft 365** — 담당자가 Teams에서 Operations agent의 제안을 받고 승인합니다.

## 의사결정 흐름

1.  **현재 계산** — Databricks에서 기준 계획과 긴급 수주의 날짜별 재고를 계산하고 Power BI로 비교합니다.
2.  **판단 기준** — 대응안마다 모든 Bunker의 안전재고, Bunker 용량, 판매오더 납기, 이송 한도를 확인합니다.
3.  **Agent 제안** — Operations agent가 판단 기준을 만족한 대응안을 Teams로 보냅니다.
4.  **사람 승인** — 담당자가 Teams에서 승인하면 승인 내역이 저장됩니다. 발주와 이송 지시는 기존 절차로 진행합니다.

## 실습 순서

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

## 실습 파일 내려받기

1.  브라우저에서 GitHub 저장소를 엽니다: <https://github.com/SookBongnaver/MS_WS_ChipBalance>

    저장소가 비공개인 경우 접근 권한이 있는 GitHub 계정으로 로그인합니다.

2.  파일 목록 위의 **Code** \> **Download ZIP**을 누릅니다.

3.  내려받은 ZIP 파일의 압축을 풉니다.

**예상 결과:** 압축을 푼 폴더에 `notebooks\ChipBalance.zip`과 `fabric` 폴더가 있습니다. `ChipBalance.zip`은 01장에서 Databricks로 가져오는 Notebook 8개이고, `fabric` 폴더의 모델·테마는 10장, 승인 기록 Notebook은 11장에서 씁니다.

## 다음 단계

[01. Databricks 접속과 설정](01-connect.md)
