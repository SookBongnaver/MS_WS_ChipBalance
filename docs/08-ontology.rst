08. Ontology
=============

`목차 <../README.rst>`_ | 이전: `07. Unity Catalog 설명과 Genie <07-genie.rst>`_ | 다음: `09. Ontology agent에 질문하기 <09-ontology-agent.rst>`_

Ontology는 업무에서 쓰는 개념(엔터티 타입)과 개념 사이의 관계를 정의하고, 각 개념을 Lakehouse 테이블에 연결(데이터 바인딩)한 모델입니다.
이 장에서는 Ontology agent에 프롬프트를 주어 Gold 테이블로 엔터티 타입 17개와 관계 26개를 만들고, 설명·키·바인딩·관계를 점검합니다.
09장의 Ontology agent가 이 Ontology로 질문에 답합니다.

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - 엔터티 타입
     - 테이블 (키)
     - 한 행
   * - Line, Bunker, Material, Supplier, Product, Customer
     - ``gold.dim_*``
     - 라인, 원료 Bunker, 원료, 공급사, 제품, 고객 기준 정보
   * - TransferRoute
     - ``gold.dim_route`` (``route_id``)
     - Bunker 간 이송 경로. 보내는 Bunker와 받는 Bunker
   * - Scenario
     - ``gold.dim_scenario`` (``scenario_id``)
     - ``baseline``\ (현재 계획), ``emergency``\ (긴급 오더 반영)
   * - SalesOrder, OrderFulfillment
     - ``gold.fact_sales_order``, ``gold.fact_order_fulfillment``
     - 판매오더, 시나리오별 납기 준수 여부
   * - ProductionPlan
     - ``gold.fact_plan`` (``plan_key``)
     - 시나리오별 생산계획 한 건
   * - DailyBalance
     - ``gold.fact_balance`` (``balance_key``)
     - 시나리오·Bunker·날짜별 원료 재고
   * - BunkerRisk
     - ``gold.fact_bunker_summary`` (``summary_key``)
     - 시나리오·Bunker별 미달 일수, 최저 재고, 필요 보충량
   * - InboundDelivery
     - ``gold.fact_inbound`` (``inbound_key``)
     - 입고 예정 한 건
   * - ResponseOption, OptionBalance
     - ``gold.fact_response_option``, ``gold.fact_option_balance``
     - 긴급 오더 대응안 4개와 대응안별 Bunker 재고
   * - RiskEvent
     - ``gold.fact_risk_event`` (``event_id``)
     - 06장에서 감지한 부족 이벤트와 추천 대응안

1. Ontology 만들기
---------------------

#. Fabric 작업 영역 ``chipbalance-p001``\ 에서 **+ New item**\ 을 누릅니다.
#. **New item** 창의 검색 칸에 ``Ontology``\ 를 입력하고 **Ontology (preview)**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d08-new-item.png
      :alt: New item 창. 검색 칸에 Ontology가 입력되어 있고, 아래에 Ontology (preview) 카드가 있습니다.
      :width: 600

#. **New Ontology** 창에서 **Name**\ 에 ``ont_chipbalance``\ 를 입력하고, **Location**\ 이 ``chipbalance-p001``\ 인지 확인한 뒤 **Create**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d08-new-ontology.png
      :alt: New Ontology 창. Name은 ont_chipbalance, Location은 chipbalance-p001이고, 오른쪽 아래에 Create 버튼이 있습니다.
      :width: 400

#. **Welcome to Ontology** 창이 나오면 오른쪽 위 **X**\ 를 눌러 닫습니다.

**예상 결과:** 가운데에 **Get started**\ 와 카드 3개(**Start with Ontology agent**, **Import ontology**, **Learn more**)가 보입니다. 왼쪽 **Explorer**\ 에는 아직 엔터티 타입이 없습니다.

.. image:: ../assets/screenshots/d08-get-started.png
   :alt: ont_chipbalance의 Home 화면. 위 리본에 Add entity type, Ontology agent, Explore graph, Manage graph가 있고, 가운데에 Get started와 Start with Ontology agent, Import ontology, Learn more 카드가 있습니다. 왼쪽 Explorer에는 No entity types available이 표시됩니다.
   :width: 900

2. Ontology agent로 초안 만들기
----------------------------------

#. **Start with Ontology agent** 카드를 누릅니다. 오른쪽에 **Ontology Agent** 창이 열립니다.

   입력 칸 아래 스위치가 **Plan**\ 이면 에이전트는 초안을 만들고 검증만 합니다. **Act**\ 로 바꾸어야 Ontology에 적용합니다.

#. **Say something** 칸에 아래 프롬프트를 붙여 넣습니다. 참가자 번호가 ``p001``\ 이 아니면 첫 줄의 ``lh_chipbalance_p001``\ 을 본인 Lakehouse로 바꿉니다.

   .. code-block:: text

      lh_chipbalance_p001 Lakehouse의 gold 스키마 테이블로 원료 Chip Balance 온톨로지를 만들어줘.
      업무 범위: 필름 공장의 원료 Chip Bunker 재고, 생산계획, 입고 예정, 긴급 오더 대응안. dbo 스키마와 Files 폴더는 쓰지 마.
      엔터티 타입과 관계 이름은 영어로, 설명과 동의어는 한국어로 써. Bunker는 한국어로 '벙커'라고 써. 각 엔터티 타입에는 테이블의 모든 열을 속성으로 넣고, 괄호 안의 열을 키로 써.
      엔터티 타입:
      - Line: gold.dim_line (line_id)
      - Bunker: gold.dim_bunker (bunker_id)
      - Material: gold.dim_material (material_id)
      - Supplier: gold.dim_supplier (supplier_id)
      - Product: gold.dim_product (product_id)
      - Customer: gold.dim_customer (customer_id)
      - TransferRoute: gold.dim_route (route_id)
      - Scenario: gold.dim_scenario (scenario_id)
      - SalesOrder: gold.fact_sales_order (sales_order_id)
      - OrderFulfillment: gold.fact_order_fulfillment (fulfillment_key)
      - ProductionPlan: gold.fact_plan (plan_key)
      - DailyBalance: gold.fact_balance (balance_key)
      - BunkerRisk: gold.fact_bunker_summary (summary_key)
      - InboundDelivery: gold.fact_inbound (inbound_key)
      - ResponseOption: gold.fact_response_option (option_id)
      - OptionBalance: gold.fact_option_balance (option_balance_key)
      - RiskEvent: gold.fact_risk_event (event_id)
      관계 (이름은 모두 다르게, 출발 → 도착, 연결 열):
      - BunkerOnLine: Bunker → Line (dim_bunker.line_id)
      - BunkerStoresMaterial: Bunker → Material (dim_bunker.material_id)
      - MaterialSuppliedBy: Material → Supplier (dim_material.supplier_id)
      - ProductOnLine: Product → Line (dim_product.line_id)
      - OrderedByCustomer: SalesOrder → Customer (fact_sales_order.customer_id)
      - OrderForProduct: SalesOrder → Product (fact_sales_order.product_id)
      - FulfillmentOfOrder: OrderFulfillment → SalesOrder (fact_order_fulfillment.sales_order_id)
      - FulfillmentInScenario: OrderFulfillment → Scenario (fact_order_fulfillment.scenario_id)
      - PlanForOrder: ProductionPlan → SalesOrder (fact_plan.sales_order_id)
      - PlanOnLine: ProductionPlan → Line (fact_plan.line_id)
      - PlanInScenario: ProductionPlan → Scenario (fact_plan.scenario_id)
      - BalanceOfBunker: DailyBalance → Bunker (fact_balance.bunker_id)
      - BalanceInScenario: DailyBalance → Scenario (fact_balance.scenario_id)
      - RiskOfBunker: BunkerRisk → Bunker (fact_bunker_summary.bunker_id)
      - RiskInScenario: BunkerRisk → Scenario (fact_bunker_summary.scenario_id)
      - InboundToBunker: InboundDelivery → Bunker (fact_inbound.bunker_id)
      - InboundFromSupplier: InboundDelivery → Supplier (fact_inbound.supplier_id)
      - RouteFromBunker: TransferRoute → Bunker (dim_route.from_bunker_id)
      - RouteToBunker: TransferRoute → Bunker (dim_route.to_bunker_id)
      - OptionForBunker: ResponseOption → Bunker (fact_response_option.target_bunker_id)
      - OptionUsesRoute: ResponseOption → TransferRoute (fact_response_option.route_id)
      - OptionBalanceOfOption: OptionBalance → ResponseOption (fact_option_balance.option_id)
      - OptionBalanceOfBunker: OptionBalance → Bunker (fact_option_balance.bunker_id)
      - EventAtBunker: RiskEvent → Bunker (fact_risk_event.bunker_id)
      - EventFromOrder: RiskEvent → SalesOrder (fact_risk_event.sales_order_id)
      - EventRecommends: RiskEvent → ResponseOption (fact_risk_event.recommended_option_id)
      먼저 초안을 만들고 검증 결과와 미리 보기를 보여줘. 적용은 내가 Act 모드로 바꾼 다음에 해.

   .. image:: ../assets/screenshots/d08-agent-prompt.png
      :alt: Ontology Agent 창. Hi, how can I help you? 아래 입력 칸에 프롬프트 끝부분 EventRecommends 관계와 먼저 초안을 만들고 검증 결과와 미리 보기를 보여줘 문장이 보이고, 아래에 Plan과 Act 스위치와 보내기 화살표가 있습니다.
      :width: 400

   관계는 연결 열이 있는 테이블의 엔터티에서 출발합니다. 예를 들어 ``dim_bunker.line_id``\ 로 잇는 ``BunkerOnLine``\ 은 Bunker → Line입니다.
   이렇게 정해야 6단계에서 Graph를 만들 때 모든 관계가 데이터에 연결됩니다.

#. 오른쪽 아래 화살표를 눌러 보냅니다. 에이전트가 Lakehouse의 열과 샘플 행을 살펴보고 초안을 만든 뒤 검증합니다. (3~5분)

**예상 결과:** "초안과 검증을 완료했습니다"로 시작하는 답에 엔터티 17개, 관계 26개, 이슈 없음이 보입니다.
참고에 나온 4개(``dim_date``, ``fact_monthly_usage``, ``fact_opening_stock``, ``fact_usage_factor``)는 Balance 계산에 쓴 중간 결과이므로 넣지 않습니다.
답의 문장과 제목은 매번 조금씩 다를 수 있습니다. 엔터티 수, 관계 수, 이슈를 확인합니다.

.. image:: ../assets/screenshots/d08-agent-draft.png
   :alt: Ontology Agent의 답. 초안과 검증을 완료했습니다, 검증 결과는 문제 없음이었고 현재 초안은 엔터티 17개 / 관계 26개로 구성되어 있습니다 아래에 확인된 근거, 미리 보기 요약, 검증 결과(엔터티 수 17, 관계 수 26, 이슈 없음), 참고(gold.dim_date, gold.fact_monthly_usage, gold.fact_opening_stock, gold.fact_usage_factor 제외)가 보입니다.
   :width: 400

3. 미리 보기와 적용
----------------------

#. 답 아래 **Preview ontology**\ 를 누릅니다. 가운데 캔버스에 초안이 열립니다.
#. 캔버스 왼쪽 아래 **Fit to screen** 아이콘(네 모서리 모양)을 눌러 전체를 봅니다.

   **예상 결과:** 위에 "You are viewing a proposed ontology from the agent. Approve to keep this ontology. This is a read-only view."가 보이고, 캔버스 아래에 ``Visible: 17 of 17 entities | 26 of 26 relationships``\ 가 보입니다.
   왼쪽 **Explorer**\ 의 **AI Proposal** 아래에 엔터티 타입 17개가 있습니다.

   .. image:: ../assets/screenshots/d08-preview.png
      :alt: 초안 미리 보기. 위에 You are viewing a proposed ontology from the agent 안내가 있고, 가운데 캔버스에 엔터티 타입 17개와 관계가 선으로 연결되어 있습니다. 아래에 Visible: 17 of 17 entities, 26 of 26 relationships가 보입니다. 오른쪽 에이전트 창에 Switch to 'Act' + approve 버튼이 있습니다.
      :width: 1000

#. 에이전트 창의 **Switch to 'Act' + approve**\ 를 누릅니다. 스위치가 **Act**\ 로 바뀌고 에이전트가 초안을 적용합니다. (2~3분)

**예상 결과:** "적용했습니다. 승인된 온톨로지가 생성되었습니다" 아래 **결과**\ 에 상태 적용 완료, 이슈 없음, 엔터티 타입 17개, 관계 26개가 보입니다.
왼쪽 **Explorer**\ 의 **Entity Types** 아래에 Line부터 RiskEvent까지 17개가 있습니다.

.. image:: ../assets/screenshots/d08-applied.png
   :alt: 적용 후 화면. 왼쪽 Explorer의 Entity Types에 Line, Bunker, Material부터 RiskEvent까지 17개가 있고, 가운데 캔버스에 Bunker를 중심으로 관계가 보입니다. 오른쪽 에이전트 답에 적용했습니다, 상태 적용 완료, 이슈 없음, 엔터티 타입 17개, 관계 26개, 설명과 동의어는 한국어로 반영, Bunker는 설명에서 벙커로 표기가 보입니다.
   :width: 1000

4. 엔터티 타입과 관계 점검
-----------------------------

09장의 Ontology agent는 엔터티 타입과 관계의 설명·동의어를 읽고 질문의 단어를 엔터티에 연결합니다. 키, 데이터 바인딩, 설명이 제대로 들어갔는지 확인합니다.

#. 오른쪽 위 **X**\ 를 눌러 에이전트 창을 닫습니다.
#. 왼쪽 **Explorer**\ 에서 **Bunker**\ 를 누르고, 리본의 **View Entity Type details**\ 를 누릅니다. 안내 풍선이 나오면 **X**\ 로 닫습니다.

   **예상 결과:** **Configure** 탭에 **Entity type key**\ 가 ``bunker_id``\ 이고, 속성 6개의 **Data source**\ 가 모두 ``dim_bunker``\ 의 같은 이름 열입니다.
   **Entity metadata**\ 에 한국어 **Description**\ 과 **Synonyms**\ (벙커, 원료 벙커 등)가 있습니다. 오른쪽 **Relationships**\ 에는 Bunker에 연결된 관계가 보입니다.
   설명과 동의어는 에이전트가 만들므로 문장이 조금씩 다를 수 있습니다.

   .. image:: ../assets/screenshots/d08-bunker-configure.png
      :alt: Bunker의 Configure 탭. Entity type key는 bunker_id이고, 속성 bunker_id, bunker_name, capacity_kg, line_id, material_id, safety_stock_kg의 Data source가 dim_bunker 열입니다. 아래 Description은 원료 칩을 저장하는 벙커를 나타내는 차원입니다, Synonyms는 벙커, 원료 벙커, 저장 벙커, 원료 저장소입니다. 오른쪽에 Bunker 관계 그래프가 있습니다.
      :width: 1000

#. **Instances** 탭을 누릅니다. 안내 풍선이 나오면 **X**\ 로 닫습니다.

   **예상 결과:** ``gold.dim_bunker``\ 의 Bunker 24개가 보입니다. ``BNK-L3-2``\ 는 ``L3 PET-SD``, 용량 ``150000``, 안전재고 ``12000``\ 입니다. 바인딩한 테이블의 실제 데이터가 엔터티 인스턴스로 읽힙니다.

   .. image:: ../assets/screenshots/d08-bunker-instances.png
      :alt: Bunker의 Instances 탭. bunker_id, bunker_name, line_id, material_id, capacity_kg, safety_stock_kg 열이 있는 표에 BNK-L1-1부터 BNK-L4-4까지 보입니다. BNK-L3-2는 L3 PET-SD, L3, PET-SD, 150000, 12000입니다.
      :width: 1000

#. **Configure** 탭으로 돌아가 오른쪽 위 **Manage relationships**\ 를 누르고 목록에서 **BalanceOfBunker**\ 를 누릅니다.

   **예상 결과:** **Origin entity type**\ 이 ``DailyBalance``, **Target entity type**\ 이 ``Bunker``\ 이고, 두 쪽 **Property**\ 가 모두 ``bunker_id``\ 입니다. 일별 재고 한 행이 ``bunker_id``\ 로 Bunker 하나에 연결됩니다.

   .. image:: ../assets/screenshots/d08-relationship.png
      :alt: BalanceOfBunker 관계 화면. DailyBalance > Bunker, Use mapping table? Off입니다. Origin entity type은 DailyBalance, Property 1은 bunker_id, Relationship name은 BalanceOfBunker, Target entity type은 Bunker, Property 1은 bunker_id입니다. 아래 Description은 일별 재고 균형이 어느 벙커에 대한 것인지 연결합니다.
      :width: 1000

#. 아무것도 바꾸지 않고 오른쪽 아래 **Cancel**\ 을 누른 뒤, 왼쪽 위 **Home**\ 을 누릅니다.

5. Graph 만들기
------------------

Graph는 엔터티 인스턴스를 노드로, 관계를 에지로 저장해 여러 단계의 관계를 따라가며 조회하게 합니다. 리본의 **Explore graph**\ 에서 Graph를 조회할 수 있습니다.

#. 리본의 **Manage graph**\ 를 누릅니다. **Choose what to project** 화면이 열립니다.
#. **Entities** 표에서 **Line** 왼쪽 **>**\ 를 눌러 펼칩니다.

   **예상 결과:** **Use the entire Ontology**\ 가 **Yes**\ 이고, 17개 엔터티가 모두 체크되어 있으며 **Status**\ 가 **Eligible**\ 입니다.
   Line 아래 관계 ``BunkerOnLine``\ (``dim_bunker``), ``ProductOnLine``\ (``dim_product``), ``PlanOnLine``\ (``fact_plan``)도 **Eligible**\ 입니다. 오른쪽 **Preview**\ 에 노드와 에지가 보입니다.

   .. image:: ../assets/screenshots/d08-manage-graph.png
      :alt: Configure Graph의 Choose what to project 화면. Use the entire Ontology는 Yes이고, Entities 표에서 Line을 펼치면 BunkerOnLine(dim_bunker), ProductOnLine(dim_product), PlanOnLine(fact_plan)이 모두 Eligible입니다. 아래 Bunker부터 ProductionPlan까지 체크되어 있고 Status는 Eligible입니다. 오른쪽 Preview에 엔터티 노드와 관계 에지가 그려져 있습니다.
      :width: 1000

#. 왼쪽 아래 **Continue**\ 를 누르고, **Configure projection** 화면에서 왼쪽 아래 **Materialize**\ 를 누릅니다.

**예상 결과:** 오른쪽 위에 **Creating graph model** 알림이 보이고, 위쪽 탭에 ``ont_chipbalance_graph_``\ 로 시작하는 Graph model이 열립니다. 데이터를 불러오는 데 5~15분 걸립니다.

.. image:: ../assets/screenshots/d08-materialize.png
   :alt: Configure projection 화면. 오른쪽 위에 Creating graph model, This process may take a few minutes 알림이 있고, 위쪽 탭에 ont_chipbalance_graph_로 시작하는 Graph model이 열려 있습니다. Entities 표의 엔터티와 관계는 모두 Eligible입니다.
   :width: 1000

문제가 생기면
----------------

* 초안에 엔터티 타입이 17개보다 적으면 답의 참고 내용에서 빠진 테이블을 확인합니다. 06장을 실행하고 Lakehouse에 ``fact_response_option``, ``fact_option_balance``, ``fact_risk_event``\ 가 있는지 확인한 뒤, "빠진 테이블을 lh_chipbalance_p001의 gold 스키마에서 다시 찾아서 초안에 추가해줘"라고 요청합니다.
* **Manage graph**\ 에서 관계의 **Source**\ 가 **Not mapped**\ 이면 그 관계의 방향을 확인합니다. 연결 열이 있는 테이블의 엔터티가 **Origin entity type**\ 이어야 합니다.
* 적용을 요청했는데 아무 변화가 없으면 입력 칸 아래 스위치가 **Act**\ 인지 확인합니다.
* 브라우저를 새로 고치면 에이전트 대화가 사라집니다. 이미 적용한 엔터티 타입과 관계는 Ontology에 남아 있습니다.
* 에이전트가 답하지 않거나 오류를 보이면 같은 대화에 ``Try again``\ 을 보냅니다.
* **Instances**\ 에 데이터가 없으면 05장 **3. Fabric Lakehouse에서 Gold 확인**\ 으로 Lakehouse에 ``gold`` 테이블이 있는지 확인합니다.

다음 단계
------------

`09. Ontology agent에 질문하기 <09-ontology-agent.rst>`_
