# Workshop: 원료 칩 수급과 긴급 수주 대응

필름 공장에 긴급 수주가 들어왔습니다. 생산 시간을 확보하는 것만으로 납기를 지킬 수 있을까요? **원료 재고, 다른 판매오더의 납기, 대응 비용을 함께 확인**해야 합니다.

이 hands-on Workshop에서는 Azure Databricks와 Microsoft Fabric으로 재고·납기 영향을 계산하고, 보고서와 에이전트로 근거를 검토한 뒤 담당자의 결정을 기록합니다.

**계획 확인 → 긴급 수주 반영 → 대응안 비교 → 근거 검토 → 승인 기록**

처음 시작한다면 [00. 시나리오와 실습 순서](docs/00-scenario.md)에서 업무 상황을 읽고 실습 파일을 내려받습니다.

## 이 실습에서 완성하는 것

| 결과 | 할 수 있는 일 |
|---|---|
| 재고·납기·대응안 Gold 테이블 | 현재 계획과 긴급 수주의 영향을 같은 기준으로 계산하고, 네 대응안의 안전재고·용량·납기·이송 한도와 추가 비용을 비교합니다. |
| Ontology와 근거 답변 | 업무 개념·관계를 데이터에 연결하고, 원료 부족과 추천안에 관한 질문 6개의 답을 Notebook 정답과 비교합니다. |
| Power BI 보고서 2페이지 | 수급 현황은 직접 작성하고, 대응안 페이지는 **Copilot으로 생성**한 뒤 **질문·인사이트 요약**으로 근거를 확인합니다. |
| Teams 제안과 승인 기록 | Operations agent의 제안을 받고, **Foundry agent로 근거를 검토한 뒤 담당자가 Teams에서 승인**합니다. 이벤트 상태와 승인 내역을 저장합니다. |

추천은 계산으로 정하고, AI의 설명은 계산 결과와 대조합니다. **최종 결정은 담당자가 하며, 실습은 승인 기록까지입니다. 실제 발주·이송 지시는 실행하지 않습니다.**

## 전체 구성

Databricks에서 **Bronze → Silver → Gold**로 데이터를 정제·계산합니다. Bronze·Silver는 Unity Catalog에, Gold는 **Fabric OneLake에만** 저장합니다. Fabric의 Ontology·Power BI와 Foundry의 Fabric IQ 도구가 같은 Gold를 근거로 사용합니다.

<img src="assets/architecture.svg" width="1000" alt="전체 구성. Azure Databricks가 Bronze와 Silver를 정제하고 Gold를 계산해 OneLake에 저장합니다. Fabric은 Gold로 semantic model, Power BI 보고서, Ontology를 만듭니다. 내장 Ontology agent가 질문에 답하고, Operations agent는 Eventhouse의 RiskEventStatus를 감시해 Teams로 대응안을 제안합니다. Foundry agent가 Fabric IQ 도구로 Ontology의 근거를 조회하고, 담당자가 승인하면 Fabric Notebook이 승인 상태와 내역을 기록합니다. 실선은 실습 흐름, 점선은 실행 범위 밖의 운영 확장 예시입니다." />

[그림 크게 보기](assets/architecture.png)

질문에는 **Ontology에 내장된 Ontology agent**를 사용합니다. Operations agent는 Lakehouse를 직접 감시하지 않고, 11장에서 Eventhouse로 보낸 **위험 이벤트 상태**를 감시합니다.

구성도의 **실선은 실습 흐름, 점선은 운영 확장 예시**입니다. 실제 원천 시스템 연계, Power Apps·Power Automate, Work IQ·Microsoft 365 Copilot·Cowork·Agent Store 연결은 만들지 않습니다. 운영에 연결하려면 해당 제품의 지원 상태·인증·라이선스·테넌트 정책을 별도로 확인합니다.

## 시작 전 확인

**전체 실습은 관리자가 준비한 활성 유료 Fabric 용량에 참가자 작업 영역을 할당한 상태로 진행합니다.** 필요한 SKU와 동시 참가자 수에 따른 용량 배치는 [관리자 준비 가이드](admin/README.md)를 따릅니다.

| 참가자가 확인할 것 | 관리자에게 받을 안내 |
|---|---|
| 실습 계정·참가자 번호·접속 주소 | Databricks 주소와 본인 번호(예: `p001`), Databricks·Fabric·Foundry·Teams에 사용할 계정 |
| 데이터 실행·접근 환경 | Notebook Serverless, Unity Catalog 권한, Managed Identity를 통한 OneLake 접근, 본인 Fabric 작업 영역·Lakehouse |
| 보고서·에이전트 사용 환경 | Power BI Pro 또는 PPU 라이선스와 작성 권한, AI 기능의 테넌트 설정·지원 지역, Foundry 역할·모델·인증 연결, Teams 사용 권한 |

문서·캡처의 `p001`은 예시입니다. 명령과 작업 영역·Lakehouse 선택에는 **본인 번호**를 사용합니다. `sm_chipbalance`, `ont_chipbalance` 같은 항목 이름은 참가자별 작업 영역 안에서 그대로 씁니다.

Genie 질의와 Ontology Graph 생성은 **선택 단계**입니다. Genie에는 별도의 OneLake Federation과 SQL warehouse 사용 권한이 필요하며, Notebook Serverless와 SQL warehouse는 별개입니다. 12장의 Work IQ는 선택 화면을 살펴보고 취소하는 참고 단계입니다. 이 연결들이 없어도 필수 흐름은 진행할 수 있습니다.

## 실습 순서

00장부터 순서대로 진행하며, 각 장의 **완료 기준**을 확인한 뒤 다음 장으로 넘어갑니다. 예상 시간은 약 **6시간 20분**이며 휴식·환경 준비 대기는 별도입니다([장별 일정](docs/00-scenario.md#실습-일정)).

| 장 | 이번 단계에서 할 일 |
|---|---|
| [00. 시나리오와 실습 순서](docs/00-scenario.md) | 업무 상황·판단 기준을 이해하고 실습 파일을 내려받습니다. |
| [01. Databricks 접속과 설정](docs/01-connect.md) | Notebook을 가져오고 참가자 번호를 넣어 OneLake 쓰기·읽기를 확인합니다. |
| [02. 원천 데이터 만들기](docs/02-source-data.md) | 가상 SAP·FPIMS·PVSS 파일 14개를 생성하고 데이터 관계를 읽어 봅니다. |
| [03. Bronze](docs/03-bronze.md) | 원천 파일을 바꾸지 않고 테이블로 적재해 원본을 보존합니다. |
| [04. Silver](docs/04-silver.md) | 형식·단위를 맞추고 중복·공란·미등록 코드·센서 이상값을 격리합니다. |
| [05. Gold와 OneLake](docs/05-gold-onelake.md) | 현재 계획의 날짜별 재고·납기를 계산해 OneLake에 저장합니다. |
| [06. 긴급 수주와 대응안](docs/06-emergency-order.md) | 긴급 수주의 영향을 계산하고 대응안 4개를 비교해 추천안을 정합니다. |
| [07. 정답 계산과 Genie](docs/07-genie.md) | 질문 6개의 정답을 계산합니다. Genie 질의는 선택입니다. |
| [08. Ontology](docs/08-ontology.md) | 엔터티·관계·데이터 바인딩을 만들고 실제 데이터를 확인합니다. Graph는 선택입니다. |
| [09. Ontology agent에 질문하기](docs/09-ontology-agent.md) | 업무 규칙을 설명에 넣고 질문의 답을 07장의 계산 정답과 비교합니다. |
| [10. Power BI 보고서](docs/10-power-bi.md) | 수급 현황은 직접 만들고 대응안은 Copilot으로 생성해 질문·인사이트를 확인합니다. |
| [11. Operations agent](docs/11-operations-agent.md) | 위험 이벤트를 Eventhouse로 보내 Teams 제안을 받습니다. 12장 검토를 마치고 돌아와 승인·기록 확인·Stop을 완료합니다. |
| [12. Foundry agent](docs/12-foundry-agent.md) | Fabric IQ로 Ontology의 근거를 검토한 뒤 11장 승인 단계로 돌아갑니다. |
| [13. 마무리](docs/13-finish.md) | 결과와 감시·실행 중지를 확인합니다. 삭제·유료 용량 정리는 관리자 안내에 따릅니다. |

**11장 Teams 제안 → 12장 근거 검토 → 11장 승인·결과 확인·Stop → 13장 마무리** 순서를 지킵니다. AI가 만드는 구조·페이지·답변은 달라질 수 있으므로, 완료 메시지만 믿지 않고 각 장의 데이터·필드·근거와 비교합니다.

## 실습 파일

[00장의 내려받기 안내](docs/00-scenario.md#실습-파일-내려받기)에 따라 **저장소 ZIP을 내려받아 압축을 풉니다.** 그 안의 아래 파일을 사용합니다.

| 파일 | 용도 |
|---|---|
| `notebooks\ChipBalance.zip` | 01장에서 Databricks로 가져오는 Notebook 8개입니다. **이 ZIP 자체는 풀지 않고 Import**합니다. 개별 Notebook은 `notebooks` 폴더에서도 볼 수 있습니다. |
| `fabric\sm_chipbalance.tmdl`, `fabric\chipbalance-theme.json` | 10장의 모델 관계·측정값과 보고서 테마입니다. |
| `fabric\nb_record_decision.ipynb` | 11장에서 Operations agent에 연결할 승인 기록 Notebook입니다. |

원천 파일은 별도로 준비하지 않습니다. **02장에서 가상 실습 데이터를 생성**하며 실제 SAP·FPIMS·PVSS에 접속하지 않습니다.

## 관리자용

관리자는 참가자가 시작하기 전에 리소스·권한·기능 설정을 준비합니다. 참가자는 각 장의 안내를 따라 진행하고, 환경·권한 오류가 나면 관리자에게 확인합니다.

- [관리자 준비 가이드](admin/README.md) — 실습 환경·권한·용량 준비와 종료 후 정리
- [데이터 설계](admin/data-design.md) — 테이블 구조·계산 규칙·정답 수치
- [구성도 아이콘 출처](assets/icon-attribution.md) — 공식 아이콘과 구성도 생성 방법
