12. Foundry agent
===================

`목차 <../README.rst>`_ | 이전: `11. Operations agent <11-operations-agent.rst>`_ | 다음: `13. 마무리 <13-finish.rst>`_

11장에서 Operations agent가 Teams로 대응안 ``OPT-2``\ 를 제안했습니다.
이 장에서는 Microsoft Foundry에 에이전트 ``fa-chipbalance``\ 를 만들고, **Fabric IQ** 도구로 08장의 Ontology ``ont_chipbalance``\ 를 연결합니다.
담당자는 승인하기 전에 이 에이전트에게 대응안의 근거를 묻습니다. 승인은 그대로 Teams에서 합니다.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 항목
     - 역할
   * - Foundry 프로젝트 ``chipbalance-p001``
     - 에이전트, 모델 배포, 도구 연결을 모아 두는 작업 공간입니다.
   * - 에이전트 ``fa-chipbalance``
     - 한국어 지침에 따라 질문에 답합니다. 모델은 ``gpt-5``\ 입니다.
   * - Fabric IQ 도구 (``ont_chipbalance``)
     - Ontology의 엔터티 타입, 속성, 관계, 데이터 바인딩을 에이전트에 제공합니다. 로그인한 사용자의 Fabric 권한으로 읽습니다.

에이전트 이름에는 영문, 숫자, ``-``\ 만 쓸 수 있습니다. 그래서 ``fa_chipbalance``\ 가 아니라 ``fa-chipbalance``\ 로 만듭니다.

1. Foundry 프로젝트 만들기
-----------------------------

#. 브라우저에서 https://ai.azure.com 을 열고 Fabric과 같은 계정으로 로그인합니다. 오른쪽 위 **새 Foundry** 스위치가 켜져 있는지 확인합니다.
#. **모든 리소스** 화면 오른쪽 위의 **프로젝트 만들기**\ 를 누릅니다.
#. **프로젝트 만들기** 창에서 아래와 같이 입력하고 **만들기**\ 를 누릅니다.

   .. list-table::
      :header-rows: 1
      :widths: 35 65

      * - 필드
        - 값
      * - **프로젝트 이름**
        - ``chipbalance-p001`` 입력
      * - **고급 옵션** > **Foundry 리소스**
        - ``fdy-chipbalance-p001`` 입력
      * - **지역**
        - ``Sweden Central`` 선택 (Fabric 용량과 같은 지역)
      * - **구독**, **리소스 그룹**
        - 관리자가 알려 준 값 선택
      * - **Foundry에서 제공하는 모든 항목을 탐색할 수 있도록 권장 리소스를 설정합니다.**
        - 끔. 추적 기록용 App Insights 리소스를 만들지 않습니다.

   .. image:: ../assets/screenshots/d12-create-project.png
      :alt: 프로젝트 만들기 창. 프로젝트 이름 chipbalance-p001, 고급 옵션의 Foundry 리소스 fdy-chipbalance-p001, 지역 Sweden Central, 구독과 리소스 그룹이 선택되어 있고, 권장 리소스 스위치는 꺼져 있습니다. 아래에 만들기 버튼이 있습니다.
      :width: 600

#. **프로젝트를 만드는 중** 창이 닫히고 **모두 완료했습니다. 에이전트를 구성해 보겠습니다.**\ 가 보이면 **그럼 시작합시다.**\ 를 누릅니다.

**예상 결과:** 위쪽에 ``chipbalance-p001``\ 이 보이고, **환영합니다** 아래에 **에이전트 빌드** 카드와 **프로젝트 엔드포인트**\ 가 있습니다. (2~3분)

.. image:: ../assets/screenshots/d12-project-home.png
   :alt: chipbalance-p001 프로젝트 홈. 환영합니다, MOD Administrator 님 아래에 모델 사용, 에이전트 빌드(빌드 시작), 에이전트 코딩 카드와 프로젝트 엔드포인트 https://fdy-chipbalance-p001.services.ai.azure.com, Azure OpenAI 엔드포인트가 보입니다.
   :width: 1000

2. 에이전트 만들기
---------------------

#. **에이전트 빌드** 카드의 **빌드 시작**\ 을 누릅니다.
#. **에이전트 만들기** 창의 **에이전트 이름**\ 에 ``fa-chipbalance``\ 를 입력합니다. **상호 작용 모드**\ 는 **텍스트**\ 를 그대로 두고 **만들기**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d12-agent-name.png
      :alt: 에이전트 만들기 창. 에이전트 이름에 fa-chipbalance가 입력되어 있고, 상호 작용 모드는 텍스트가 선택되어 있습니다. 만들기와 취소 버튼이 있습니다.
      :width: 500

**예상 결과:** ``gpt-5``\ 를 배포한 뒤 ``fa-chipbalance``\ 의 **플레이그라운드**\ 가 열립니다. **모델**\ 은 ``gpt-5``, **도구**\ 에는 **웹 검색**\ 이 들어 있습니다. (1~2분)

.. image:: ../assets/screenshots/d12-agent-empty.png
   :alt: fa-chipbalance 플레이그라운드. 모델 gpt-5, 지침 입력 칸은 비어 있고, 도구 아래에 웹 검색이 있습니다. 오른쪽 채팅 창에 메시지를 보내 에이전트 테스트를 시작하세요가 보입니다.
   :width: 1000

3. 지침 넣기
---------------

#. **지침** 입력 칸에 아래 내용을 붙여 넣습니다.

   .. code-block:: text

      너는 효성 필름 공장의 칩 밸런스 대응안 검토 도우미다. Operations agent가 Teams로 제안한 대응안을 담당자가 승인하기 전에 근거를 확인하도록 돕는다.
      - 생산계획, 벙커 재고, 오더, 대응안 같은 데이터 질문은 반드시 Fabric IQ 도구(ont_chipbalance)로 조회하고, 조회한 값만 근거로 답한다. 도구 결과에 없는 숫자는 만들지 않는다.
      - 답에는 근거로 쓴 엔터티와 핵심 값(벙커, 날짜, kg)을 적는다.
      - 승인이나 거절은 하지 않는다. 결정은 담당자가 Teams에서 한다.
      - 한국어로 짧게 답한다.

#. **도구**\ 의 **웹 검색** 오른쪽 **⋮**\ 를 누르고 **제거**\ 를 고릅니다. 이 에이전트는 인터넷이 아니라 Ontology만 근거로 답합니다.

4. Fabric IQ 도구로 Ontology 연결하기
----------------------------------------

#. **도구** 아래의 **추가**\ 를 누르고 **도구 추가**\ 를 고릅니다.

   .. image:: ../assets/screenshots/d12-add-menu.png
      :alt: 도구 아래 추가 메뉴. 인기 아래에 웹 검색, 코드 인터프리터 스위치가 있고 맨 아래에 도구 추가가 있습니다.
      :width: 450

#. **도구 선택** 창의 **구성됨** 탭에서 **Fabric IQ(OneLake 카탈로그)**\ 를 고르고 **도구 추가**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d12-tool-catalog.png
      :alt: 도구 선택 창의 구성됨 탭. 파일 검색, 코드 인터프리터, Azure AI Search, Bing Search로 제공, 웹 검색, 컴퓨터 사용, Work IQ, Fabric IQ(OneLake 카탈로그), Grounding with Bing Custom Search, Fabric 데이터 에이전트, SharePoint 카드가 있습니다.
      :width: 1000

#. **OneLake 카탈로그** 창의 **키워드로 필터링**\ 에 ``ont_chipbalance``\ 를 입력합니다. 위치가 ``chipbalance-p001``\ 인 ``ont_chipbalance``\ 를 고르고 **추가**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d12-onelake-select.png
      :alt: OneLake 카탈로그 창. 키워드로 필터링에 ont_chipbalance가 입력되어 있고, 이름 ont_chipbalance, 위치 chipbalance-p001 한 행이 선택되어 있습니다. 오른쪽 아래에 추가 버튼이 있습니다.
      :width: 900

#. 오른쪽 위의 **저장**\ 을 누릅니다.

**예상 결과:** **도구**\ 에 **Fabric IQ (ontchipbalance)** 하나만 있고, **지침**\ 에 3단계 내용이 들어 있습니다. **버전** 번호가 하나 올라갑니다.

.. image:: ../assets/screenshots/d12-agent-saved.png
   :alt: 저장한 fa-chipbalance 플레이그라운드. 지침에 Fabric IQ 도구(ont_chipbalance)로 조회하고, 승인이나 거절은 하지 않는다, 한국어로 짧게 답한다가 보이고, 도구에는 Fabric IQ (ontchipbalance) 미리 보기 하나만 있습니다.
   :width: 1000

5. 에이전트에 질문하기
-------------------------

#. 오른쪽 채팅 창의 **에이전트에 메시지 보내기...**\ 에 아래 질문을 입력하고 보냅니다.

   .. code-block:: text

      OPT-2를 검토하려면 ont_chipbalance의 어떤 엔터티와 속성을 봐야 하나요? 대응안이 판단 기준을 만족하는지 보는 속성과 벙커별 안전재고를 보는 속성을 알려 주세요.

   **예상 결과:** 대응안 판단 기준은 **ResponseOption**\ 의 ``c1_safety_pass``, ``c2_capacity_pass``, ``c3_due_date_pass``, ``c4_route_limit_pass``, ``meets_all``, 벙커별 안전재고는 **Bunker**\ 의 ``safety_stock_kg``\ 와 **OptionBalance**·**DailyBalance**\ 의 ``safety_stock_kg``, ``closing_kg``, ``below_safety``\ 라고 답합니다. 답 아래에 근거 표시 ``ontchipbalance``\ 가 있습니다. 문장은 AI가 만들므로 조금 다를 수 있습니다.

   .. image:: ../assets/screenshots/d12-ask-schema.png
      :alt: fa-chipbalance 채팅 창. 질문 아래 답에 대응안 판단 기준 충족 여부 Entity ResponseOption, Properties c1_safety_pass, c2_capacity_pass, c3_due_date_pass, c4_route_limit_pass, meets_all, option_name, 벙커별 안전재고 확인 Entity Bunker, Property safety_stock_kg, OptionBalance와 DailyBalance의 safety_stock_kg, below_safety, closing_kg가 보입니다. 아래에 근거 ontchipbalance 두 개와 mcp_list_tools, ontchipbalance, message 표시가 있습니다.
      :width: 700

#. 답 아래의 **추적**\ 을 누르고, 왼쪽 목록에서 **ontchipbalance: list_ontology_entities**\ 를 고릅니다.

   **예상 결과:** 에이전트가 Fabric IQ 도구로 ``list_ontology_entities``\ 를 호출했고, **출력**\ 에 ``ont_chipbalance``\ 의 엔터티 정의(예: ``Line``\ 의 ``backingTable``\ 이 ``dim_line``)가 들어 있습니다. 에이전트는 이 정의를 근거로 답했습니다.

   .. image:: ../assets/screenshots/d12-trace.png
      :alt: 대화 추적 창. 왼쪽에 응답 아래 도구 mcp_list_tools, ontchipbalance: list_ontology_entities, message가 있고 ontchipbalance: list_ontology_entities가 선택되어 있습니다. 오른쪽 입출력 탭의 입력에는 server_label ontchipbalance, operation list_ontology_entities, 출력에는 documents 아래 Line 엔터티 정의와 backingTable dim_line이 보입니다.
      :width: 1000

#. 오른쪽 위 **X**\ 를 눌러 추적 창을 닫습니다.

.. note::

   이 환경에서 Fabric IQ 도구가 에이전트에 주는 기능은 Ontology의 엔터티 목록(``list_ontology_entities``)과 규칙 목록(``list_ontology_rules``)입니다.
   에이전트는 엔터티 타입, 속성, 관계, 데이터 바인딩, 업무 규칙 설명을 근거로 답합니다.
   ``OPT-2``\ 를 반영한 BNK-L1-2의 최저 기말재고(16,763 kg)처럼 날짜별 값이 필요한 질문은 09장 Ontology agent에서 확인합니다.

6. (참고) Work IQ 도구 붙이기
--------------------------------

같은 **도구 추가** 화면에서 **Work IQ**\ 를 붙이면 에이전트가 Microsoft 365의 메일, Teams 메시지, 일정 같은 업무 맥락도 찾습니다.
Work IQ 도구는 Microsoft 365 Copilot 라이선스가 있는 사용자만 조회할 수 있으므로, 이 실습에서는 붙이는 화면만 확인합니다.

#. **도구** 아래의 **추가** > **도구 추가**\ 를 누르고, **도구 선택** 창에서 **Work IQ**\ 를 고른 뒤 **도구 추가**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d12-workiq-select.png
      :alt: 도구 선택 창의 구성됨 탭에서 Work IQ 카드가 선택되어 체크 표시가 있고, 오른쪽 아래 도구 추가 버튼이 활성화되어 있습니다.
      :width: 1000

#. **Work IQ 도구 추가** 창에서 쓸 도구를 고릅니다. 예를 들어 **Work IQ Teams**\ 와 **Work IQ Mail**\ 을 고르면 각각 **새 연결 만들기**\ 가 보입니다.

   .. image:: ../assets/screenshots/d12-workiq-tools.png
      :alt: Work IQ 도구 추가 창. Work IQ(채팅), Work IQ Teams, Work IQ Word, Work IQ Copilot, Work IQ Mail, Work IQ Calendar, Work IQ User, Work IQ SharePoint, Work IQ MCP 목록이 있고, Work IQ Teams와 Work IQ Mail이 선택되어 각각 새 연결 만들기가 보입니다. 아래에 추가와 취소 버튼이 있습니다.
      :width: 550

#. **취소**\ 를 누릅니다. **도구**\ 에는 **Fabric IQ (ontchipbalance)** 하나만 남깁니다.

문제가 생기면
----------------

* **프로젝트 만들기**\ 에서 권한 오류가 나면 관리자에게 리소스 그룹 권한을 확인합니다(`관리자 준비 가이드 <../admin/README.rst>`_\ 의 "4. Microsoft Foundry").
* **에이전트 이름**\ 에 ``_``\ 를 넣으면 만들 수 없습니다. ``fa-chipbalance``\ 처럼 ``-``\ 를 씁니다.
* **OneLake 카탈로그**\ 에 ``ont_chipbalance``\ 가 없으면 Foundry와 Fabric에 같은 계정으로 로그인했는지, ``chipbalance-p001`` 작업 영역에 권한이 있는지 확인합니다.
* 질문을 보냈는데 **추적**\ 에 ``ontchipbalance: list_ontology_entities``\ 가 없으면 **도구**\ 에 **Fabric IQ (ontchipbalance)**\ 가 있는지, **저장**\ 을 눌렀는지 확인하고 오른쪽 위 **새 채팅**\ 에서 다시 묻습니다.

다음 단계
------------

`13. 마무리 <13-finish.rst>`_
