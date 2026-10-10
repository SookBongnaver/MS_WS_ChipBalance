# 13. 마무리

[목차](../README.md) \| 이전: [12. Foundry agent](12-foundry-agent.md)

원천 데이터에서 출발해 긴급 수주의 위험을 찾고, 대응안을 비교하고, 담당자의 결정을 기록했습니다. 마지막으로 **만든 결과를 확인하고 실습 중인 감시·실행을 멈춥니다.** 항목 삭제와 Fabric 용량 일시 중지는 관리자 안내에 따라 별도로 진행합니다.

**시작 전:** 12장의 근거 검토에서 11장으로 돌아가 Teams 승인·기록 확인·Operations agent Stop을 완료했는지 확인합니다. 결과를 확인하려고 06장이나 승인 Notebook을 다시 실행하지 않습니다.

## 1. 만든 것 확인하기

| 장 | 만든 것 | 확인할 결과 |
|----|----|----|
| 02–04 | 원천 파일 14개, Bronze 14개, Silver 15개 | 원천·Bronze는 각각 43,410행이며, 문제 행 23개가 `silver_quarantine`에 남아 있습니다. |
| 05–06 | Gold, OneLake 저장 | 본인 Lakehouse `lh_chipbalance_p001`의 `gold` 스키마에 최종 21개 테이블이 있고, `fact_balance`에서 `baseline`·`emergency`를 구분합니다. |
| 06 | 긴급 수주와 대응안 4개 | 긴급 수주를 반영하면 BNK-L3-2(L3 PET-SD)가 2026-10-06에 안전재고 아래로 내려가고, 판단 기준을 모두 만족하는 추천안은 `OPT-2`입니다. |
| 07 | 정답 계산 `07_answers` | Q1–Q6의 정답 6행이 표시됩니다. (Genie는 선택 확장) |
| 08–09 | Ontology `ont_chipbalance`, Ontology agent | Ontology agent가 같은 질문에 답합니다. 예: `OPT-2`를 반영해도 BNK-L1-2의 최저 기말재고는 16,763 kg으로 안전재고 6,000 kg 이상입니다. |
| 10 | Semantic model `sm_chipbalance`, 보고서 `rpt_chipbalance` | 수동 작성한 수급 현황 페이지와 Copilot으로 생성한 대응안 페이지가 있고, Copilot 질문·인사이트로 근거를 살펴봅니다. |
| 11 | Eventhouse `eh_chipbalance`, Operations agent `oa_chipbalance`, Notebook `nb_record_decision` | Teams에서 결정한 `OPT-2`가 Eventhouse 상태 이력, Lakehouse 승인 로그와 위험 이벤트에 `approved`로 기록되어 있습니다. |
| 12 | Foundry 프로젝트 `chipbalance-p001`, 에이전트 `fa-chipbalance` | 에이전트가 Fabric IQ 도구로 `ont_chipbalance`에 물어, `OPT-2`를 반영한 BNK-L1-2의 최저 기말재고 16,763 kg이 안전재고 6,000 kg 이상이라고 답합니다. |

정답 Notebook·보고서·에이전트에서 **같은 데이터의 근거를 비교**했고, 결정은 담당자가 Teams에서 했습니다. Foundry는 Ontology를 통해 근거를 조회하며 Operations agent는 Eventhouse의 상태를 감시합니다. 승인 기록은 실제 발주·이송 실행과 구분합니다.

## 2. 감시와 실행 멈추기

1.  Fabric 작업 영역 `chipbalance-p001`에서 `oa_chipbalance`를 엽니다. 도구 모음에 **Start**가 보이면 멈춘 상태입니다. **Stop**이 보이면 **Stop**을 누릅니다.
2.  11장에서 만든 확인용 Fabric Notebook `nb_verify_approval`에 활성 Spark 세션이 남아 있으면 중지합니다. 승인 결과를 다시 조회할 필요는 없습니다.
3.  Foundry 에이전트 `fa-chipbalance`는 질문할 때 모델을 호출합니다. 새 질문을 보내지 않으며 에이전트에 별도의 Stop 조작은 하지 않습니다.
4.  Databricks Notebook Serverless에는 별도로 종료할 사용자 관리 클러스터가 없습니다. Notebook 셀을 추가 실행하지 않습니다.
5.  Genie 또는 SQL 미리보기에 사용한 SQL warehouse `chipbalance-pro`는 Notebook Serverless와 별개입니다. **본인 전용이거나 다른 참가자가 쓰지 않는 warehouse**는 **SQL Warehouses**에서 **Stop**합니다. 공용 warehouse는 관리자가 종료하며 임의로 중지하지 않습니다.

**확인할 결과:** `oa_chipbalance`의 도구 모음에 **Start**가 보이고, 본인이 실행한 확인용 Spark 세션·전용 warehouse도 중지되어 있습니다. **Operations agent Stop과 Fabric 용량 일시 중지는 다릅니다.** 유료 용량 자체의 비용 관리는 관리자에게 확인합니다.

## 3. (관리자 안내 시) 실습 항목 삭제

실습 항목은 관리자가 한 번에 지웁니다([관리자 준비 가이드](../admin/README.md)의 "7. 종료 후 정리"). **직접 삭제하라는 안내를 받은 경우에만**, 필요한 결과를 보관한 뒤 아래 순서로 지웁니다. 모든 `p001`은 본인 번호이며 공용·다른 참가자의 리소스는 삭제하지 않습니다.

1.  Fabric 작업 영역 `chipbalance-p001`: `oa_chipbalance` → `nb_record_decision` → `eh_chipbalance` → `rpt_chipbalance` → `sm_chipbalance` → `ont_chipbalance`. 항목의 **...** \> **Delete**를 누릅니다. `ont_chipbalance`를 지우면 함께 만들어진 `ont_chipbalance_eh_…`, `ont_chipbalance_graph_…`도 지웁니다.
2.  Foundry: `fa-chipbalance` 에이전트 목록의 **작업** \> **삭제**로 에이전트를 지웁니다. 프로젝트와 Foundry 리소스 `fdy-chipbalance-p001`은 관리자가 Azure portal에서 지웁니다.
3.  Databricks: Unity Catalog 스키마 `lab_factory_p001.chipbalance_p001`(Bronze·Silver)은 관리자가 지웁니다. Genie 선택 단계를 만들었다면 `fabric_chipbalance_p001`과 `onelake_connection_p001`도 사용 의존성을 확인한 뒤 관리자가 정리합니다. Gold 원본은 Fabric Lakehouse에 있습니다.

Fabric 용량 일시 중지는 관리자가 합니다. 삭제 안내가 없다면 항목을 보존하고 감시·실행 중지만 확인합니다.

## 마무리 완료 기준

실습 결과와 승인 근거·기록을 확인했고, 본인의 감시·실행을 중지했으면 완료입니다. 항목 보존·삭제와 유료 용량 정리는 관리자에게 인계합니다.

## 다음 단계

수고하셨습니다. [목차](../README.md)로 돌아가 필요한 장을 다시 볼 수 있습니다.
