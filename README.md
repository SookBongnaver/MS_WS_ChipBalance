# Workshop: 원료 칩 수급과 긴급 수주 대응

필름 공장의 원료 칩 재고와 긴급 수주 대응을 주제로 한 hands-on Workshop입니다.

- **Azure Databricks:** SAP·FPIMS·PVSS 원천 파일을 만들고 메달리온 아키텍처(Bronze → Silver → Gold)로 정제·계산합니다. Gold는 Unity Catalog에 만들지 않고 Microsoft Fabric OneLake에만 저장합니다(인증 방식: Managed Identity). 같은 Gold로 질문 6개의 정답을 계산합니다. Genie로 질문하려면 OneLake를 Unity Catalog에 연결하는 선택 확장이 필요합니다.
- **Microsoft Fabric:** Gold로 Fabric IQ Ontology와 Power BI 보고서를 만들어 원료 수급 현황과 부족 지점을 파악합니다. 이 실습에서는 Ontology에 내장된 Ontology agent가 질문에 답합니다.
- **의사결정:** Fabric Operations agent가 Eventhouse에 들어온 위험 이벤트를 감시해 대응안을 Microsoft Teams로 제안하고, 담당자가 Teams에서 승인하면 Notebook이 승인 기록을 남깁니다.
- **Microsoft Foundry:** Foundry agent에 Fabric IQ 도구로 Ontology를 연결해, 담당자가 승인하기 전에 대응안의 근거를 묻습니다.

## 전체 구성

<img src="assets/architecture.svg" width="1000" alt="전체 구성. Azure Databricks가 Bronze와 Silver를 정제하고 Gold를 계산해 OneLake에 저장합니다. Fabric은 Gold로 Semantic model, Power BI 보고서, Ontology를 만듭니다. 내장 Ontology agent가 질문에 답하고, Operations agent는 Eventhouse의 RiskEventStatus를 감시해 Teams로 대응안을 제안합니다. 담당자가 Proceed와 Confirm으로 승인하면 Fabric Notebook이 승인 상태와 내역을 기록합니다. Foundry agent는 Fabric IQ 도구로 Ontology에 질문합니다. 점선은 이 실습 범위 밖의 선택 연결 예시입니다." />

[그림 크게 보기](assets/architecture.png)

구성도는 운영에 적용할 수 있는 연결을 포함한 개념도입니다. **실습에서는 09장의 Ontology agent로 질문하고, 11장은 Gold 위험 이벤트를 Eventhouse `eh_chipbalance`에 직접 보내 Operations agent가 감시합니다.** 별도의 Data agent 생성이나 Ontology를 Operations agent에 직접 연결하는 단계는 포함하지 않습니다.

점선의 Work IQ, Microsoft 365 Copilot·Cowork, Agent Store 연결은 이 가이드의 실행 범위 밖입니다. 적용할 때 해당 제품의 지원 상태, 인증, 라이선스와 테넌트 정책을 확인합니다.

실선은 실습에서 만들고 실행하는 흐름입니다. 점선의 원천 시스템 연계, Power Apps, Power Automate는 운영에 적용할 때 연결합니다. 승인은 Teams에서 끝나므로 Power Apps가 없어도 됩니다.

## 실습 순서

- [00. 시나리오와 실습 순서](docs/00-scenario.md) — 업무 상황, 원천 데이터, 계산 방식을 확인하고 실습 파일을 내려받습니다.
- [01. Databricks 접속과 설정](docs/01-connect.md) — Notebook을 가져와 Serverless에서 실행하고, OneLake 연결을 확인합니다(인증 방식: Managed Identity).
- [02. 원천 데이터 만들기](docs/02-source-data.md) — Notebook으로 SAP·FPIMS·PVSS 원천 파일 14개를 만들고, 원료·Bunker·생산계획의 관계를 확인합니다.
- [03. Bronze](docs/03-bronze.md) — 원천 파일을 그대로 Bronze 테이블로 적재합니다.
- [04. Silver](docs/04-silver.md) — 형식·단위를 맞추고 중복·공란·미등록 코드·센서 이상값을 격리합니다.
- [05. Gold와 OneLake](docs/05-gold-onelake.md) — 실제 소요량과 4분기 날짜별 재고를 계산해 Fabric Lakehouse에 저장합니다.
- [06. 긴급 수주와 대응안](docs/06-emergency-order.md) — 긴급 수주를 반영하고, 대응안 4개를 판단 기준으로 확인해 추천안을 정합니다.
- [07. 정답 계산과 Genie](docs/07-genie.md) — OneLake의 Gold로 질문 6개의 정답을 계산합니다. Genie는 선택 확장입니다.
- [08. Ontology](docs/08-ontology.md) — Ontology agent 프롬프트로 라인·Bunker·원료·생산계획의 관계를 만들고 점검한 뒤 Graph를 만듭니다.
- [09. Ontology agent에 질문하기](docs/09-ontology-agent.md) — 업무 규칙을 Ontology 설명에 넣고, Genie와 같은 질문을 Ontology agent에 해 정답과 비교합니다.
- [10. Power BI 보고서](docs/10-power-bi.md) — Direct Lake semantic model에 관계와 측정값을 넣고, 원료 수급 현황 보고서를 만들고, 긴급 수주 대응안 페이지는 Copilot으로 만들어 질문합니다.
- [11. Operations agent](docs/11-operations-agent.md) — Eventhouse에 위험 이벤트를 보내면 Operations agent가 대응안을 Teams로 제안하고, 승인하면 Notebook이 승인 기록을 남깁니다.
- [12. Foundry agent](docs/12-foundry-agent.md) — Microsoft Foundry 에이전트에 Fabric IQ 도구로 Ontology를 연결하고, 대응안의 근거 수치를 묻습니다.
- [13. 마무리](docs/13-finish.md) — 만든 결과를 확인하고, 에이전트를 멈추고 용량을 정리합니다.

## 실습 파일

`notebooks/ChipBalance.zip`은 Databricks로 한 번에 가져오는 Notebook 8개입니다. 같은 내용을 `notebooks/*.ipynb`로도 볼 수 있습니다. 원천 데이터는 02장에서 Notebook을 실행해 만듭니다. `fabric` 폴더에는 10장의 semantic model 스크립트(`sm_chipbalance.tmdl`)와 보고서 테마(`chipbalance-theme.json`), 11장의 승인 기록 Notebook(`nb_record_decision.ipynb`)이 있습니다.

관리자에게 받을 값은 Databricks 주소와 참가자 번호(예: `p001`)입니다.

## 시작 전 확인

문서와 캡처의 `p001`은 예시입니다. 명령·설정·작업 영역 선택에서는 본인의 참가자 번호로 바꿉니다. `sm_chipbalance`, `ont_chipbalance` 같은 항목 이름은 참가자별 작업 영역 안에서 그대로 씁니다.

| 실행 범위 | 필요한 준비 |
|---|---|
| 01~07 | Databricks의 Notebook Serverless, Unity Catalog 권한, OneLake 접근 권한, 활성 Fabric 용량. Gold 생성·조회는 Trial로도 할 수 있습니다. |
| 07 Genie 선택 단계 | OneLake Federation 설정, SQL warehouse **Can use** 권한. Notebook Serverless와 SQL warehouse는 별도 Compute입니다. |
| 08~09, 10 Copilot, 11, 12 Fabric IQ 연결 | 활성 **유료 F2 이상 용량**, 기능별 테넌트 설정·권한. Trial에서는 이 가이드의 AI 단계를 진행하지 않습니다. |
| 10 보고서 작성 | Power BI Pro 또는 PPU 사용자 라이선스, 모델·보고서 작성 권한 |

관리자는 [관리자 준비 가이드](admin/README.md)의 사전 점검을 마친 뒤 참가자에게 안내합니다. AI가 만드는 구조·페이지·답변은 매번 달라질 수 있으므로, 각 장의 예상 결과는 비교할 기준이지 성공 보장이 아닙니다.

## 관리자용

- [관리자 준비 가이드](admin/README.md) — 환경 준비와 종료 후 정리 방법입니다. 참가자는 보지 않아도 됩니다.
- [데이터 설계](admin/data-design.md) — 원천·Silver·Gold 테이블 구조, 계산 규칙, 예상 결과입니다.
- [구성도 아이콘 출처](assets/icon-attribution.md) — 구성도에 쓴 공식 아이콘과 그림을 다시 만드는 방법입니다.
