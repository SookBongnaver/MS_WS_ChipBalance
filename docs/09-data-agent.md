# 09. Data agent로 Ontology에 질문하기

[목차](../README.md) \| 이전: [08. Ontology](08-ontology.md) \| 다음: [10. Power BI 보고서](10-power-bi.md)

08장에서 만든 Ontology를 **Fabric Data agent의 원본으로 연결**하고, 현재 연결된 데이터로 원료 재고·부족·납기·입고·이송 경로를 한국어로 질문합니다. 목표는 **실제 조회 근거와 답의 범위를 확인하고, 없는 데이터로 판단하지 않는 것**입니다.

**업무 설명 준비 → Data agent 만들기 → Ontology 연결 → 지침 저장 → 질문·근거 확인** 순서로 진행합니다. 08장의 **내장 Ontology agent는 구조 작성**, 이 장의 **별도 Data agent는 업무 질의**에 사용합니다. 12장의 Foundry는 Fabric IQ로 Ontology에 직접 질문하는 별도 경로입니다.

## 시작 전 확인

- 본인 `ont_chipbalance`에 연결된 재고·생산계획·납기·입고·이송 경로의 키·바인딩과 실제 데이터를 08장에서 확인했습니다. **Graph 생성은 필수가 아닙니다.**
- 07장의 `07_answers`에서 질문 6개의 계산 정답을 확인할 수 있습니다. Genie를 만들지 않았어도 비교할 수 있습니다.
- **활성 유료 Fabric 용량**, Data agent 생성·사용을 허용하는 AI 테넌트 설정, 본인 작업 영역의 작성 권한과 **Ontology 및 바인딩된 원본의 읽기 권한**이 필요합니다([Data agent 요구 사항](https://learn.microsoft.com/fabric/data-science/concept-data-agent), [테넌트 설정](https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings)).

작업 영역·Lakehouse의 `p001`은 본인 번호로 바꿉니다. `ont_chipbalance`, `da_chipbalance`라는 항목 이름은 본인 작업 영역 안에서 그대로 사용합니다. 캡처의 참가자 번호는 예시입니다.

이 장의 `Scenario`, `Plan`, `BunkerBalance` 등은 현재 업무 개념의 이름 예시입니다. 본인 설계의 이름이나 개수는 달라도 됩니다. 원본 바인딩으로 해당 업무 개념을 찾습니다. 물리 `gold` 테이블·열 이름은 바꾸지 않습니다.

## 1. Ontology의 업무 설명 준비

테이블의 `moved`만 보고는 "긴급 오더 때문에 미룬 생산"인지 알기 어렵습니다. 코드의 의미를 **Ontology의 Description에 남겨**, Data agent와 12장의 Foundry가 같은 업무 맥락을 참고하게 합니다. 재고·납기 계산값은 원본 Gold에서 조회합니다.

1.  본인 `ont_chipbalance`에서 **Home → Ontology agent**를 열고 **Act**를 선택합니다.
2.  아래 요청은 현재 확인된 **Scenario, Plan, BunkerBalance, Route, OrderFulfillment**의 설명만 보강합니다. 본인 온톨로지에서 이름이 다르면 원본 바인딩으로 대응되는 타입을 확인합니다. 없는 타입을 추가하거나 이름·키·바인딩·관계를 바꾸는 단계가 아닙니다.

    ``` text
    현재 온톨로지에 존재하고 원본에 바인딩된 아래 타입의 설명에만 업무 의미를 한국어로 반영해줘.
    이름이 다르면 괄호 안의 원본 테이블로 대응 타입을 찾아줘. 실제 바인딩된 열에 해당하는 설명만 넣고, 없는 타입이나 열은 건너뛰어줘.
    이름, 키, 속성, 데이터 바인딩, 관계는 변경하지 말고, 새 타입이나 데이터를 만들지 마. 이미 같은 설명이 있으면 중복해서 덧붙이지 마.
    - Scenario (gold.dim_scenario): scenario_id의 baseline은 현재 계획, emergency는 긴급 오더를 반영한 계획입니다. scenario_name은 표시 이름이며 scenario_id 코드와 구분합니다.
    - Plan (gold.fact_plan): change_type의 urgent는 긴급 오더 생산, moved는 긴급 오더 때문에 뒤로 미룬 생산, none은 변경하지 않은 생산입니다. original_plan_date는 변경 전 생산일입니다. 생산계획은 scenario_id로 구분합니다.
    - BunkerBalance (gold.fact_balance): 시나리오·벙커·날짜별 재고입니다. closing_kg는 기말 재고, safety_stock_kg는 안전재고이며 below_safety는 기말 재고가 안전재고보다 적은 상태, shortage는 기말 재고가 0보다 적은 상태입니다.
    - Route (gold.dim_route): from_bunker_id는 보내는 벙커, to_bunker_id는 받는 벙커입니다. max_kg_per_day는 하루 이송 한도, lead_time_days는 이송 소요일입니다. 경로 정보 자체는 이송 실행 결과가 아닙니다.
    - OrderFulfillment (gold.fact_order_fulfillment): 시나리오별 판매오더의 납기 준수 결과입니다. finish_date는 생산 완료일, due_date는 납기이며 on_time이 true면 생산 완료일이 납기 이내입니다.
    수정한 타입과 건너뛴 항목을 구분해 보여줘. 이 요청은 설명 보강이며, 현재 데이터로 확인할 수 없는 업무 범위를 추가하는 요청이 아니야.
    ```

3.  변경 요약에서 **설명만 수정**했는지 확인합니다. Explorer에서 **Plan → View Entity Type details → Configure → Description**을 열어 문장이 저장됐는지 확인하고, 나머지 대상 타입도 같은 방법으로 봅니다. 이름이 다르면 `gold.fact_plan`에 연결된 타입을 선택합니다.

**확인할 결과:** 현재 존재하는 대상 타입의 설명에 업무 의미가 반영되고 구조·바인딩은 유지됩니다. 건너뛴 항목은 설명 보강 결과에서 구분합니다. 이 단계의 완료가 대응안 비교나 위험 이벤트 데이터까지 준비됐다는 뜻은 아닙니다. 이 설명은 실행 규칙이 아닙니다. **Overview → Rules**의 Business rule도 자연어 메타데이터이며, 아래 Agent instructions나 데이터 원본 지침을 대신하는 것으로 간주하지 않습니다.

## 2. Data agent 만들고 Ontology 연결

1.  작업 영역 `chipbalance-p001`으로 돌아가 **+ New item / 새 항목**에서 **Data agent / 데이터 에이전트**를 고릅니다. 이름을 **`da_chipbalance`**로 입력하고 **Create / 만들기**를 누릅니다. 둘러보기 창이 나오면 **Skip for now / 지금은 건너뛰기**를 누릅니다.
2.  시작 화면의 **Add ontology / 온톨로지 추가**를 누릅니다. OneLake 카탈로그에서 `ont_chipbalance`를 검색하고 **본인 작업 영역의 Ontology**를 선택한 뒤 **Add / 추가**를 누릅니다. 이미 에이전트 편집 화면이면 **Add source / 원본 추가**에서 Ontology 연결을 선택합니다.
3.  **Explorer → Sources / 원본**에서 연결된 `ont_chipbalance`를 펼칩니다. **Entity types / 엔터티 형식**에 08장에서 적용한 타입이 있고, **Data sources for ontology / 온톨로지용 데이터 원본**에 본인의 `lh_chipbalance_p001`이 있는지 확인합니다. 아래 캡처의 17개는 참고 설계의 개수입니다.

    <img src="../assets/screenshots/d09-data-agent-sources.png" width="400" alt="실제 Data agent의 원본 탐색기. ont_chipbalance의 엔터티 타입 17개와 온톨로지용 데이터 원본 lh_chipbalance_p901, gold 스키마가 연결되어 있습니다." />

**확인할 결과:** Ontology와 **그 바인딩에서 연결된 Lakehouse**가 함께 표시됩니다. 해당 엔터티가 사용하는 테이블·열만 원본에 노출될 수 있습니다. 이것은 Gold 복사나 새 Ontology 생성이 아닙니다. 이 실습에서는 Lakehouse를 **기타 데이터 원본**으로 중복 추가하지 않습니다.

한글 UI에서 Ontology 구역이 **존재론**으로 표시될 수 있습니다. 제품·교재의 업무 개념은 **Ontology(온톨로지)**로 읽습니다.

## 3. 에이전트 지침과 데이터 원본 지침 저장

지침은 두 위치에 넣습니다. **Agent instructions**는 답변 방식·원본 선택을, **Data source instructions**는 실제 열·필터·조인 규칙을 설명합니다. Ontology 연결만으로 모든 쿼리가 정확해지는 것은 아닙니다.

아래 두 지침은 **현재 연결된 데이터 범위**를 사용합니다. 대응안·대응안별 재고·위험 이벤트는 조회 대상으로 지정하지 않습니다. 기본 안내나 다른 지침을 남겨 섞지 말고 각 입력 영역의 내용을 전체 교체합니다.

### 에이전트 지침

1.  **Explorer → Setup / 설정 → Agent instructions / 에이전트 지침**을 엽니다.
2.  Markdown 영역을 눌러 편집하고 기본 안내 문장을 전체 선택해 지웁니다. 아래 내용을 붙여 넣은 뒤 **Markdown preview / 미리 보기 영역**을 눌러 저장합니다. 화면에 저장 버튼이 있으면 저장합니다.

    ``` text
    이 Data agent는 필름 공장 Chip Balance의 재고·생산계획·납기·입고·이송 경로를 읽기 전용으로 설명합니다.
    - ont_chipbalance에 실제로 존재하는 엔터티·관계·설명과 바인딩된 OneLake Gold만 조회합니다. 엔터티 이름은 현재 온톨로지에서 확인하며, 별도 원본이나 인터넷 정보로 숫자를 추측하지 않습니다.
    - baseline은 긴급 오더를 반영하지 않은 현재 계획, emergency는 긴급 오더를 반영한 계획입니다. 질문에 시나리오가 없으면 baseline으로 답합니다. baseline과 emergency는 scenario_id 코드이고 scenario_name은 한국어 표시 이름입니다.
    - 미룬 생산의 판매오더 수는 change_type=moved인 sales_order_id를 중복 없이 셉니다. 생산계획과 납기 이행을 연결할 때 양쪽 시나리오를 emergency로 맞춥니다.
    - below_safety는 closing_kg가 safety_stock_kg보다 적은 날, shortage는 closing_kg가 0보다 적은 날입니다. 최저 재고와 안전재고까지의 필요 보충량을 구분합니다.
    - 이송 경로는 보내는 벙커·받는 벙커·하루 한도·소요일을 설명하는 기준 정보입니다. 경로가 있다는 것만으로 실제 이송 가능 수량이나 이송 후 재고 안전성을 확정하지 않습니다.
    - 현재 원본 범위에는 대응안 비교·추천, 대응안별 이송 후 재고, 위험 이벤트의 처리 상태가 포함되지 않습니다. 이런 질문에는 현재 데이터로 확인할 수 없다고 답하고, 없는 엔터티·테이블·열이나 결과를 만들지 않습니다.
    - 한국어로 짧게 답하고 실제 근거 엔터티·시나리오·벙커·날짜·단위를 보여 줍니다. 없는 열이나 읽지 못한 데이터는 확인 불가로 구분합니다.
    - 발주·이송·승인·데이터 변경은 하지 않습니다.
    ```

### 데이터 원본 지침

1.  같은 **Setup / 설정**의 **온톨로지용 데이터 원본**에서 본인 Lakehouse 행에 마우스를 올립니다.
2.  **Add custom setup / 사용자 지정 설정 추가**를 누르고, 생긴 **Data source instructions / 데이터 원본 지침**을 엽니다. 이미 항목이 있으면 바로 엽니다.
3.  **데이터 원본 설명**과 **데이터 원본 지침** 중 **지침** 영역에 아래 내용을 넣고 저장합니다.

    ``` text
    이 원본은 ont_chipbalance에 실제 바인딩된 gold 스키마 테이블입니다. 먼저 노출된 테이블·열을 확인하고 존재하는 항목만 SQL에 사용합니다. 아래 규칙도 해당 테이블·열이 원본에 있을 때만 적용합니다.
    - gold.dim_scenario에서 baseline과 emergency는 scenario_id 코드입니다. scenario_name은 한국어 표시 이름입니다. 영문 코드를 scenario_name으로 필터하지 않습니다.
    - fact_plan, fact_order_fulfillment, fact_balance, fact_bunker_summary는 scenario_id로 현재 계획 baseline 또는 긴급 계획 emergency를 구분하고 조인 양쪽의 scenario_id를 맞춥니다.
    - fact_sales_order에는 scenario_id가 없습니다. 긴급 오더는 is_urgent로 구분합니다.
    - 미룬 판매오더는 fact_plan에서 scenario_id=emergency, change_type=moved인 sales_order_id를 DISTINCT로 구합니다. fact_order_fulfillment도 scenario_id=emergency로 제한해 finish_date, due_date, on_time을 비교합니다.
    - 위험은 fact_bunker_summary의 below_safety_days > 0으로 찾고 first_below_safety_date, first_shortage_date, min_closing_kg, min_closing_date, required_topup_kg를 조회합니다.
    - 재고는 fact_balance에서 scenario_id·bunker_id·balance_date로 구분합니다. 기간 최저 재고를 묻는 경우 해당 기간의 closing_kg 최솟값과 발생일을 확인합니다.
    - 이송 경로는 dim_route의 from_bunker_id에서 to_bunker_id로 갑니다. dim_bunker의 bunker_id와 연결해 양쪽 벙커를 확인합니다. max_kg_per_day는 하루 한도, lead_time_days는 소요일이며 실제 이송 실행 내역이나 이송 후 재고가 아닙니다.
    - 입고는 fact_inbound에서 bunker_id·material_id와 expected_date로 찾습니다. 지정 날짜 뒤는 그 날짜를 초과한 첫 입고입니다. 공급사는 supplier_id로 dim_supplier를 연결하고 quantity_kg를 읽습니다.
    - fact_balance를 대응안별 재고로 해석하거나 이 테이블에 option_id가 있다고 가정하지 않습니다. 현재 계획·긴급 계획의 재고를 이송 후 재고로 대신하지 않습니다.
    - 대응안 평가·추천·추가 비용 및 위험 이벤트 처리 상태는 현재 조회 범위 밖입니다. 해당 결과를 추정하거나 존재하지 않는 테이블을 조회하지 않습니다.
    - 조인으로 행이 제외되거나 중복되지 않는지 확인합니다. 선택적 연결은 LEFT JOIN을 검토하고, 판매오더 건수는 DISTINCT로 셉니다.
    ```

**확인할 결과:** 편집 영역을 다시 열어 저장된 지침을 읽을 수 있습니다. `Ctrl+A`로 기본 문장을 지운 뒤 붙여 넣어야 하며, 입력한 문장 뒤에 기본 안내가 남아 있지 않은지 확인합니다. 질문의 **정답 숫자를 지침에 넣어 답을 맞추지 않습니다.**

## 4. 한국어로 질문하고 계산 정답과 비교

아래 질문은 현재 연결된 재고·생산계획·납기·입고·이송 경로만 사용합니다. 해당 원본이나 필요한 열이 연결되지 않았다면 확인 불가로 구분합니다. 정답 숫자는 질문에 넣지 않습니다.

1.  **Test data agent / 테스트 데이터 에이전트**를 열고 **응답 테스트** 입력란에 아래 질문을 하나씩 보냅니다.
2.  답을 받은 뒤 07장의 정답과 비교합니다. 지침을 수정했다면 **Clear chat / 채팅 지우기**로 새 대화에서 다시 평가합니다. 브라우저 새로 고침만으로 대화가 초기화된다고 가정하지 않습니다.

| 번호 | 질문 | 확인할 정답 |
|---|---|---|
| Q1 | 긴급 오더를 반영하지 않은 현재 계획에서 4분기에 안전재고 아래로 내려가는 Bunker가 있어? | 없음 (`baseline`) |
| Q2 | 긴급 오더를 반영하면 어느 Bunker가 언제부터 안전재고 아래로 내려가고, 얼마나 부족해? | BNK-L3-2. 미달 10/06, 부족 10/07. 최저 -23,630kg(11/26), 필요 보충량 35,630kg |
| Q3 | 긴급 오더 때문에 미뤄진 생산의 판매오더는 납기를 지켜? | 중복 없는 3건 모두 준수. SO-10108: 10/08 완료·10/11 납기, SO-10109: 10/10 완료·10/14 납기, SO-10110: 10/12 완료·10/15 납기 |
| Q4 | BNK-L3-2로 PET-SD를 보내는 등록된 이송 경로와 출발 Bunker는 어디야? | BNK-L1-2 → BNK-L3-2, R-01. 경로 기준 정보이며 이송 후 안전성의 근거는 아님 |
| Q5 | BNK-L3-2에 10월 6일 뒤 처음 들어오는 PET-SD 입고는 언제, 어느 공급사에서, 몇 kg이야? | 2026-10-09, SUP-PET-B(세미폴리머), 25,000kg |
| Q6 | 이 데이터만으로 이송 후 재고가 안전한지, 어떤 대응안을 추천할지 판단할 수 있어? | 현재 연결된 데이터로 확인 불가. 경로·현재 재고만으로 이송 후 재고나 추천안을 만들지 않음 |

**전체 기간을 확인합니다.** Q2의 첫 미달일 부족량과 4분기 최저 재고·보충량은 다릅니다. 아래처럼 실제 원본과 조회 범위를 밝혀 확인합니다.

**Q2의 전체 위험 요약 확인**

``` text
현재 온톨로지에서 gold.fact_bunker_summary에 바인딩된 타입을 찾아 scenario_id=emergency, below_safety_days > 0인 행의 bunker_id, first_below_safety_date, first_shortage_date, min_closing_kg, min_closing_date, required_topup_kg를 조회해 주세요. 해당 원본이나 열이 연결되지 않았으면 확인 불가로 알려 주세요.
```

<img src="../assets/screenshots/d09-data-agent-q2.png" width="1000" alt="실제 Data agent의 Q2 확인용 재질문 답변. BNK-L3-2, 10월 6일 첫 미달, 10월 7일 부족, 11월 26일 최저 -23,630kg, 보충량 35,630kg이 보입니다." />

**Q4의 등록된 이송 경로 확인**

``` text
현재 온톨로지에서 gold.dim_route에 바인딩된 타입을 찾아 to_bunker_id=BNK-L3-2, material_id=PET-SD인 경로의 route_id, from_bunker_id, to_bunker_id, max_kg_per_day, lead_time_days를 보여 주세요. 경로 정보만으로 이송 후 재고가 안전하다고 판단하지 마세요.
```

**Q6은 조회 범위의 한계를 확인하는 질문**입니다. 답에 추천안 ID·비용·이송 후 재고가 나오면 근거가 없는 결과로 처리합니다. Q2 캡처는 응답 예시이며 현재 세션의 조회 성공을 대신하지 않습니다.

## 5. 조회 근거 확인

1.  답의 **원본 표시 `ont_chipbalance`**와 **단계 완료 / completed steps**를 확인합니다. **응답 확장 → 데이터 / 단계 완료**에서도 답과 수행 단계를 볼 수 있습니다.
2.  조회 대상이 본인 Ontology의 연결 원본인지 확인합니다. Lakehouse 분석 단계가 보일 수 있습니다. 이는 Ontology의 맥락을 참고해 **바인딩된 물리 테이블을 조회**하는 경로이며, 내장 Ontology agent의 `ask_ontology` 호출과 같다고 설명하지 않습니다.
3.  표시되는 실행 단계·쿼리에서 아래 조건을 대조합니다. UI가 SQL 전체를 보여 주지 않으면 쿼리를 본 것으로 간주하지 말고, 확인용 질문과 정답 Notebook으로 근거 값을 대조합니다.

| 질문 | 확인할 조회 범위 |
|---|---|
| Q1·Q2 | `scenario_id`에 각각 `baseline`·`emergency`. `scenario_name`에 영문 코드를 넣지 않음 |
| Q3 | `change_type=moved`, DISTINCT 판매오더. 계획·납기 이행 양쪽 모두 `emergency` |
| Q4 | `gold.dim_route`, `to_bunker_id=BNK-L3-2`, `material_id=PET-SD`. 출발·도착·하루 한도·소요일만 확인 |
| Q5 | `bunker_id=BNK-L3-2`, `material_id=PET-SD`, `expected_date > 2026-10-06`의 첫 행 |
| Q6 | 현재 원본에 없는 대응안·이송 후 재고를 조회하거나 추정하지 않고 확인 불가로 구분 |

이 장은 **초안 편집·테스트**까지 진행합니다. 다른 사용자나 외부 서비스에서 쓸 때의 **Publish / 게시·공유·MCP 인증**은 별도 준비입니다. 12장의 Ontology 직접 연결을 위해 Data agent를 게시할 필요는 없습니다.

## 이 장의 완료 기준

`da_chipbalance`에 **본인 `ont_chipbalance`와 연결 원본**이 표시되고 두 위치의 지침이 저장되어 있습니다. Q1·Q2·Q3·Q5와 Q4의 이송 경로를 실제 조회 근거로 확인합니다. Q4의 이송 후 안전성·Q6의 대응안 추천은 **현재 데이터로 확인 불가**로 구분하며, 숫자나 추천안을 추측하지 않습니다. 실제 조회가 실패한 질문은 완료로 처리하지 않습니다.

Data agent는 데이터를 읽는 역할입니다. Gold·Ontology를 바꾸거나 승인하지 않습니다. 다음 장에서는 같은 결과를 보고서로 봅니다.

## Troubleshooting

- **온톨로지 추가**가 없거나 추가가 실패하면 올바른 테넌트·계정, 본인 Ontology, AI 설정과 용량·원본 권한을 확인합니다. UI에 원본이 보이는 것과 실제 조회 성공은 별개입니다.
- 연결 원본이나 엔터티가 빠졌으면 08장의 바인딩과 원본 읽기 권한을 확인합니다. 화면에 표시되는 **Refresh / 새로 고침**을 사용하고 원본 목록을 다시 봅니다. 캐시 문제 때문에 06장을 재실행하지 않습니다.
- `데이터 없음`이라는 답이면 실제 조회 조건을 먼저 확인합니다. 검증 중 `scenario_name='emergency'`를 써서 데이터가 있는데도 없다고 답한 사례가 있었습니다. **scenario_id**로 제한하고, 지침을 저장한 뒤 새 대화에서 다시 확인합니다.
- Q3가 0건이거나 3건보다 많으면 다음처럼 범위를 명시합니다.

  ``` text
  현재 온톨로지에서 gold.fact_plan에 연결된 타입의 scenario_id=emergency, change_type=moved인 sales_order_id를 중복 없이 구하고, gold.fact_order_fulfillment에 연결된 타입도 scenario_id=emergency로 제한해 판매오더별 finish_date, due_date, on_time을 보여 주세요.
  ```

- Q4에서 이송 후 안전성을 답하면 경로 정보만 요청한 것인지 확인합니다. 현재 재고·경로는 이송 후 안전성을 입증하지 않습니다.
- Q5가 입고를 찾지 못하면 ID와 날짜를 명시합니다.

  ``` text
  현재 온톨로지에서 gold.fact_inbound에 연결된 타입의 bunker_id=BNK-L3-2이고 material_id=PET-SD인 입고 중 expected_date가 2026-10-06보다 큰 첫 행을 expected_date 오름차순으로 조회해 주세요. supplier_id로 gold.dim_supplier에 연결된 타입을 찾아 공급사 ID·이름과 quantity_kg를 보여 주세요. 원본이 연결되지 않았으면 확인 불가로 알려 주세요.
  ```

- Q6에서 추천안이나 추가 비용을 제시하면 현재 원본의 조회 근거를 확인합니다. 근거가 없으면 결과를 사용하지 않고 지침을 저장한 뒤 새 대화로 재평가합니다.
- Markdown에 기본 안내가 남아 있거나 변경이 사라지면 전체 선택 후 입력·저장을 확인합니다. 새로 열어 실제 저장된 문장을 확인합니다.
- AI 모델·런타임 변경 알림은 결과가 같다는 보장이 아닙니다. 검증한 런타임에서 정답을 다시 비교합니다. 이 실습의 확인 화면은 **표준 / Standard 런타임**입니다.

## 공식 문서

- [Data agent의 지원 원본·권한·지침](https://learn.microsoft.com/fabric/data-science/concept-data-agent)
- [원본 추가·테스트·게시 절차](https://learn.microsoft.com/fabric/data-science/data-agent-end-to-end-tutorial)
- [Data agent 테넌트 설정](https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings)

## 다음 단계

[10. Power BI 보고서](10-power-bi.md)에서 현재 연결된 Gold의 재고·안전재고·부족 규모를 수급 현황 화면으로 만듭니다.
