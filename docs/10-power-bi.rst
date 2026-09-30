10. Power BI 보고서
===================

`목차 <../README.rst>`_ | 이전: `09. Ontology agent에 질문하기 <09-ontology-agent.rst>`_ | 다음: `11. Operations agent <11-operations-agent.rst>`_

Lakehouse의 Gold 테이블로 Direct Lake semantic model을 만들고, 관계와 측정값을 넣은 뒤 두 페이지짜리 보고서를 만듭니다.
Direct Lake는 OneLake의 Delta 테이블을 가져오기(Import) 없이 바로 읽는 저장 모드입니다.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - 페이지
     - 보여 주는 것
   * - 원료 수급 현황
     - 현재 계획과 긴급 수주에서 안전재고 아래로 내려가는 Bunker 수, 처음 미달하는 날, 필요 보충량. 선택한 Bunker의 날짜별 기말 재고와 안전재고
   * - 긴급 오더 대응안
     - 대응안 4개의 판단 기준(C1~C4) 결과와 추천 순위, 추천안과 추가 비용, 추천안을 적용한 뒤의 기말 재고

이 장에서 쓰는 파일은 00장에서 압축을 푼 폴더의 ``fabric`` 폴더에 있습니다.

* ``fabric\sm_chipbalance.tmdl`` — 관계와 측정값을 만드는 TMDL 스크립트
* ``fabric\chipbalance-theme.json`` — 보고서 테마(색, 글꼴 크기, 배경, 테두리)

1. Semantic model 만들기
---------------------------

#. Fabric 작업 영역 ``chipbalance-p001``\ 에서 Lakehouse ``lh_chipbalance_p001``\ 을 엽니다.
#. 리본의 **New semantic model**\ 을 누릅니다.
#. **New semantic model** 창에 아래와 같이 입력하고 **Confirm**\ 을 누릅니다.

   * **Direct Lake semantic model name**: ``sm_chipbalance``
   * **Workspace**: ``chipbalance-p001``
   * 테이블: ``gold`` 아래에서 7개를 체크합니다. ``dim_bunker``, ``dim_date``, ``dim_scenario``, ``fact_balance``, ``fact_bunker_summary``, ``fact_option_balance``, ``fact_response_option``

   .. image:: ../assets/screenshots/d10-new-model.png
      :alt: New semantic model 창. Direct Lake semantic model name은 sm_chipbalance, Workspace는 chipbalance-p001입니다. gold 아래 dim_bunker, dim_date, dim_scenario, fact_balance가 체크되어 있고 dim_customer, dim_line, dim_material, dim_product, dim_route, dim_supplier는 체크되어 있지 않습니다. 오른쪽 아래에 Confirm 버튼이 있습니다.
      :width: 400

**예상 결과:** ``sm_chipbalance``\ 가 **Model view**\ 로 열립니다. 오른쪽 **Data** 창에 테이블 7개가 있고, 오른쪽 위는 **Editing**\ 입니다. (1분 이내)

2. 관계와 측정값 넣기
------------------------

TMDL(Tabular Model Definition Language)은 semantic model의 테이블, 관계, 측정값을 글로 적는 형식입니다.
``sm_chipbalance.tmdl``\ 은 관계 8개와 측정값 19개를 만듭니다.
측정값 안에 시나리오(``baseline``/``emergency``)와 추천안(``recommendation_rank = 1``) 조건이 들어 있어, 시각적 개체에 측정값만 넣으면 필요한 숫자가 나옵니다.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 측정값
     - 뜻
   * - 현재 계획 재고 (kg), 긴급 오더 재고 (kg)
     - 시나리오별 기말 재고
   * - 안전재고 (kg)
     - Bunker의 안전재고
   * - 미달 Bunker 수 (현재 계획), 미달 Bunker 수 (긴급 오더)
     - 4분기에 안전재고 아래로 내려가는 날이 있는 Bunker 수. 슬라이서에서 고른 Bunker와 관계없이 전체를 셉니다.
   * - 첫 미달일 (긴급 오더), 필요 보충량 (kg)
     - 긴급 수주에서 처음 안전재고 아래로 내려가는 날, 4분기 내내 안전재고를 지키려면 더 있어야 하는 양
   * - 추천안 적용 후 재고 (kg)
     - 추천안(추천 순위 1)을 반영한 기말 재고
   * - 기준 충족 대응안 수, 추천안, 추천안 추가 비용 (원)
     - 판단 기준을 모두 만족한 대응안 수, 추천안과 추가 비용
   * - C1 안전재고, C2 용량, C3 납기, C4 이송 한도
     - 대응안별 판단 기준 결과. 만족하면 ✅, 만족하지 못하면 ❌
   * - 추천 순위, 추가 비용 (원), 첫 도착일, 판단
     - 대응안별 추천 순위, 추가 비용, 첫 입고·도착일, 만족하지 못한 기준

#. 화면 아래 **TMDL View (Preview)** 탭을 누릅니다. **Edit your model with TMDL** 안내가 나오면 **Try it now**\ 를 누릅니다.
#. 00장에서 압축을 푼 폴더의 ``fabric\sm_chipbalance.tmdl``\ 을 메모장으로 열고, **Ctrl+A**, **Ctrl+C**\ 로 전체를 복사합니다.
#. TMDL 편집기의 1행을 누르고 **Ctrl+V**\ 로 붙여 넣습니다. 1행이 ``createOrReplace``\ 입니다.

   .. image:: ../assets/screenshots/d10-tmdl-paste.png
      :alt: TMDL View. 편집기 1행에 createOrReplace가 있고, 그 아래 relationship fact_balance_scenario, fact_balance_bunker, fact_balance_date, fact_bunker_summary_scenario, fact_bunker_summary_bunker의 fromColumn과 toColumn이 보입니다. 편집기 위에 Apply와 Preview 버튼, 아래 Output에 No output to display, 오른쪽 Data 창에 테이블 7개가 있습니다.
      :width: 1000

#. 편집기 위 **Apply**\ 를 누릅니다.

   **예상 결과:** 편집기 위에 **Changes applied to the model.**\ 이 보이고, 아래 **Output**\ 에 ``[success] Successfully applied TMDL script.``\ 가 나옵니다. 아래 **Script 1** 탭에 초록색 체크가 붙습니다.

   .. image:: ../assets/screenshots/d10-tmdl-applied.png
      :alt: Apply를 누른 뒤의 TMDL View. 편집기 위에 Changes applied to the model.이 있고, 아래 Output에 [success] Successfully applied TMDL script.가 보입니다. 아래 Script 1 탭에 초록색 체크가 있습니다.
      :width: 1000

#. 화면 아래 **Model view** 탭을 누릅니다. 리본에서 **Refresh** 아래 화살표를 누르고 **Data**\ 를 누른 뒤, **Refresh** 확인 창에서 **Refresh**\ 를 누릅니다.
   새로 만든 관계로 Direct Lake 데이터를 다시 읽습니다. (1분 이내)

   .. image:: ../assets/screenshots/d10-refresh.png
      :alt: Model view의 Home 리본. Refresh 아래 메뉴에 Schema and data, Schema, Data, Schedule refresh, Refresh history, Create advanced refresh (preview)가 있습니다.
      :width: 500

#. 오른쪽 **Properties** 창과 **Data** 창 위의 **»**\ 를 눌러 접고, 화면 오른쪽 아래 **Fit to page** 아이콘을 누릅니다.

**예상 결과:** 테이블 7개가 한 줄로 보입니다. ``dim_bunker``, ``dim_date``, ``dim_scenario``\ 가 ``fact_`` 테이블과 관계선으로 이어지고, ``fact_option_balance``\ 와 ``fact_response_option``\ 도 관계선으로 이어집니다.

.. image:: ../assets/screenshots/d10-model-view.png
   :alt: Model view. dim_bunker, dim_date, dim_scenario, fact_balance, fact_bunker_summary, fact_option_balance, fact_response_option 테이블 7개가 한 줄로 있고, dim 테이블과 fact 테이블, fact_option_balance와 fact_response_option 사이가 관계선으로 이어져 있습니다. 오른쪽 Properties 창과 Data 창은 접혀 있습니다.
   :width: 1000

3. 보고서 만들기와 테마 적용
-------------------------------

#. **Model view**\ 의 리본에서 **New report**\ 를 누릅니다. 새 브라우저 탭에 빈 보고서가 편집 화면으로 열립니다. 로그인 창이 나오면 같은 계정으로 로그인합니다.
#. 위쪽 **View** 메뉴에서 **Theme**\ 를 누릅니다. 오른쪽 **Visualizations** 창에 **Theme settings**\ 가 열립니다.
#. **Theme** 아래 **Custom theme name** 오른쪽 **...**\ 를 누르고 **Import**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d10-theme-import.png
      :alt: Visualizations 창의 Theme settings. Theme 아래 Custom theme name 입력 칸 오른쪽 ... 메뉴에 Import, Export, Remove가 있습니다. 오른쪽 Data 창에 테이블 7개가 있습니다.
      :width: 360

#. 파일 선택 창에서 ``fabric\chipbalance-theme.json``\ 을 엽니다.

   **예상 결과:** **Custom theme name**\ 이 ``Chip Balance``\ 가 되고, 페이지 배경이 연한 회색이 됩니다.
   테마는 계열 색(첫째 파랑, 둘째 빨강, 셋째 회색), 글꼴 크기, 시각적 개체의 흰 배경과 테두리, 표 머리글 색을 정합니다.

#. 캔버스 빈 곳을 누르고 **Visualizations** 창의 가운데 아이콘(**Format page**)을 누릅니다. **Canvas settings**\ 를 펼쳐 크기가 ``1920 x 1080 (Full HD)``\ 인지 확인합니다.
   이 장의 위치와 크기 값은 이 페이지 크기를 기준으로 합니다.

4. 1페이지: 원료 수급 현황
-----------------------------

시각적 개체를 넣을 때마다 위치와 크기를 맞춥니다.
시각적 개체를 선택하고 **Visualizations** 창의 가운데 아이콘(**Format visual**)을 누른 뒤, **General** 탭 → **Properties**\ 의 **Size**\ (**Height**, **Width**)와 **Position**\ (**Horizontal**, **Vertical**)에 값을 입력합니다.
필드는 **Data** 창에서 테이블을 펼치고 필드 왼쪽 체크 상자를 눌러 넣습니다. 체크한 순서대로 들어갑니다.

#. 아래쪽 **Page 1** 탭을 두 번 누르고 ``원료 수급 현황``\ 을 입력한 뒤 **Enter**\ 를 누릅니다.
#. **카드** — 캔버스 빈 곳을 누르고 **Visualizations** 창의 **Build visual**\ 에서 **Card**\ 를 누릅니다. ``fact_bunker_summary``\ 에서 아래 측정값을 차례로 체크합니다.

   ``미달 Bunker 수 (현재 계획)``, ``미달 Bunker 수 (긴급 오더)``, ``첫 미달일 (긴급 오더)``, ``필요 보충량 (kg)``

   위치와 크기: Height ``160``, Width ``1856``, Horizontal ``32``, Vertical ``124``

#. **슬라이서** — 캔버스 빈 곳을 누르고 **Slicer**\ 를 누른 뒤, ``dim_bunker``\ 의 ``bunker_id``\ 를 체크합니다.

   * **Format visual** → **Visual** 탭 → **Slicer settings**\ 에서 **Options**\ 의 **Style**\ 을 **Dropdown**\ 으로, **Selection**\ 의 **Single select**\ 를 **On**\ 으로 합니다.
   * 위치와 크기: Height ``104``, Width ``320``, Horizontal ``1568``, Vertical ``12``

   .. image:: ../assets/screenshots/d10-slicer-settings.png
      :alt: 슬라이서를 선택한 화면. 캔버스 오른쪽 위 슬라이서 제목은 bunker_id이고, Format visual의 Visual 탭에서 Slicer settings를 펼치면 Options의 Style은 Dropdown, Selection의 Single select는 On입니다.
      :width: 440

#. 슬라이서를 선택한 채로 캔버스 오른쪽의 접힌 **Filters** 창을 눌러 펼칩니다. **Filters on this visual**\ 의 ``bunker_id`` 카드에서 **Select all**\ 을 체크하고 **(Blank)**\ 의 체크를 풉니다.

   Direct Lake 모델에서는 관계가 있는 차원의 목록에 빈 항목 **(Blank)**\ 가 함께 보이므로, 이 필터로 슬라이서 목록에서 뺍니다.

   **예상 결과:** 카드 제목 아래에 ``is not (Blank)``\ 가 보입니다.

   .. image:: ../assets/screenshots/d10-slicer-filter.png
      :alt: 카드와 슬라이서가 있는 페이지에서 슬라이서를 선택하고 Filters 창을 펼친 화면. Filters on this visual의 bunker_id 카드에 is not (Blank)가 있고, Filter type은 Basic filtering, Select all은 일부 체크, (Blank)는 체크 해제, BNK-L1-1부터 BNK-L1-4는 체크되어 있습니다. 오른쪽 Format visual의 General 탭에 Height 104, Width 320, Horizontal 1568, Vertical 12가 보입니다.
      :width: 1000

#. 슬라이서의 드롭다운을 열고 ``BNK-L3-2``\ 를 고릅니다.
#. **묶은 세로 막대형 차트** — 캔버스 빈 곳을 누르고 **Clustered column chart**\ 를 누릅니다. 아래 필드를 차례로 체크합니다. **Y-axis**\ 에 넣은 순서대로 파랑, 빨강 막대가 됩니다.

   * ``fact_balance``\ 의 ``현재 계획 재고 (kg)``, ``긴급 오더 재고 (kg)`` → **Y-axis**
   * ``dim_date``\ 의 ``date_key`` → **X-axis**

   **Format visual** → **General** 탭 → **Title**\ 을 펼치고, **Title**\ 의 **Text**\ 에 아래 제목을 입력합니다. 그 아래 **Subtitle**\ 은 **Off**\ 로 합니다.

   .. code-block:: text

      선택한 Bunker의 기말 재고 (kg): 현재 계획 · 긴급 오더 (점선: 안전재고)

   위치와 크기: Height ``736``, Width ``1856``, Horizontal ``32``, Vertical ``308``

   .. image:: ../assets/screenshots/d10-chart-title.png
      :alt: 묶은 세로 막대형 차트의 Format visual General 탭. Title이 On이고, Title 아래 Text에 선택한 Bunker의 기말이 보입니다. Heading, Font, Text color, Background color, Horizontal alignment, Text wrap 아래에 Subtitle Off, Divider Off, Spacing이 있습니다.
      :width: 200

   **Visual** 탭의 **Columns** → **Layout**\ 에서 **Space between categories**\ 를 ``10``\ 으로 합니다. 막대가 굵어집니다.

#. **안전재고 점선** — 차트를 선택한 채로 **Visualizations** 창의 오른쪽 아이콘(**Analytics**)을 누릅니다.

   * **Y-Axis Constant Line**\ 을 펼치고 **+ Add line**\ 을 누릅니다. 생긴 줄의 연필 아이콘을 눌러 이름을 ``안전재고``\ 로 바꿉니다.
   * **Line**\ 의 **Value** 오른쪽 **fx**\ 를 누릅니다. **Format style**\ 은 **Field value**\ 로 두고, **What field should we base this on?**\ 에서 **All data** → ``fact_balance`` → ``안전재고 (kg)``\ 를 고른 뒤 **OK**\ 를 누릅니다.

     .. image:: ../assets/screenshots/d10-refline-fx.png
        :alt: Value - Apply settings to 창. Format style은 Field value, What field should we base this on?은 안전재고 (kg)이고, 오른쪽 아래에 OK와 Cancel 버튼이 있습니다.
        :width: 600

   * **Color**\ 는 검정, **Transparency**\ 는 ``0``\ 으로 합니다. **Line style**\ 은 **Dashed** 그대로 둡니다.
   * **Data label**\ 을 **On**\ 으로 하고, 펼쳐서 **Horizontal position**\ 은 **Right**, **Style**\ 은 **Both**, **Color**\ 는 검정으로 합니다.

   **예상 결과:** 차트에 검은 점선과 ``안전재고: 12,000``\ 이 보입니다. 슬라이서에서 고른 Bunker의 안전재고 높이에 선이 그어집니다.

   .. image:: ../assets/screenshots/d10-p1-refline.png
      :alt: 원료 수급 현황 페이지에서 묶은 세로 막대형 차트를 선택하고 Analytics 창을 연 화면. Y-Axis Constant Line (1) 아래 안전재고 줄이 있고, Line의 Value는 fx로 지정되어 있으며 Color 검정, Transparency 0 %, Line style Dashed, Data label On입니다. 차트에는 검은 점선이 0K 바로 위에 가로로 그어져 있습니다.
      :width: 1000

#. **제목** — 위쪽 도구 모음의 **Text box**\ 를 누르고 ``원료 Chip Balance 현황: 현재 계획과 긴급 오더``\ 를 입력합니다. 글자를 모두 선택하고, 텍스트 도구 모음에서 글꼴 크기를 ``28``\ 로 하고 **B**\ (굵게)를 누릅니다.

   텍스트 상자를 선택하면 오른쪽 창이 **Format text box**\ 가 됩니다. **General** → **Properties**\ 에 위치와 크기를 입력합니다: Height ``96``, Width ``1480``, Horizontal ``32``, Vertical ``12``

   .. image:: ../assets/screenshots/d10-textbox.png
      :alt: 제목 텍스트 상자를 선택한 화면. 텍스트 도구 모음에 글꼴 Segoe UI, 크기 28, 굵게가 선택되어 있고, 오른쪽은 Format text box 창의 General 탭입니다. 캔버스에 제목, 슬라이서, 카드, 묶은 세로 막대형 차트가 있습니다.
      :width: 1000

**예상 결과:** 카드에 ``0``, ``1``, ``2026-10-06``, ``35,630``\ 이 보입니다. 현재 계획에서는 안전재고 아래로 내려가는 Bunker가 없고, 긴급 수주를 반영하면 1개가 10월 6일부터 미달하며 35,630 kg이 더 필요합니다.
차트에서 파란 막대(현재 계획)는 모두 점선(안전재고) 위에 있고, 빨간 막대(긴급 수주)는 10월 6일부터 점선 아래로 내려가며 0 아래로 내려가는 날도 있습니다.

시각적 개체를 누르면 **Build visual**\ 에 넣은 필드가 보입니다. 카드와 차트의 필드를 확인합니다.

.. image:: ../assets/screenshots/d10-p1-card.png
   :alt: 원료 수급 현황 페이지에서 카드를 선택한 화면. Build visual의 Value에 미달 Bunker 수 (현재 계획), 미달 Bunker 수 (긴급 오더), 첫 미달일 (긴급 오더), 필요 보충량 (kg)이 있고, 카드에 0, 1, 2026-10-06, 35,630이 보입니다.
   :width: 1000

.. image:: ../assets/screenshots/d10-p1-chart.png
   :alt: 원료 수급 현황 페이지에서 묶은 세로 막대형 차트를 선택한 화면. X-axis에 date_key, Y-axis에 현재 계획 재고 (kg), 긴급 오더 재고 (kg)가 있습니다. 차트 제목은 선택한 Bunker의 기말 재고 (kg): 현재 계획 · 긴급 오더 (점선: 안전재고)이고, 날짜마다 파란 막대와 빨간 막대가 나란히 있으며 빨간 막대는 점선 아래나 0 아래로 내려가는 날이 많습니다.
   :width: 1000

5. 저장
---------

#. 위쪽 도구 모음의 **Save this report**\ (디스크 아이콘)를 누릅니다.
#. **Save your report** 창의 왼쪽 목록에서 ``chipbalance-p001``\ 을 고르고, **Enter a name for your report**\ 에 ``rpt_chipbalance``\ 를 입력한 뒤 **Save**\ 를 누릅니다.

   .. image:: ../assets/screenshots/d10-save.png
      :alt: Save your report 창의 오른쪽. chipbalance-p001 아래 lh_chipbalance_p001, ont_chipbalance 등 항목이 있고, Enter a name for your report에 rpt_chipbalance가 입력되어 있습니다. 오른쪽 아래에 Save 버튼이 있습니다.
      :width: 600

**예상 결과:** 오른쪽 위에 **Report saved** 알림이 보입니다. 보고서가 읽기 보기로 바뀌면 위쪽 **Edit**\ 를 눌러 편집을 이어 갑니다.

6. 2페이지: 긴급 오더 대응안
-------------------------------

#. 아래쪽 **+**\ 를 눌러 페이지를 추가하고, 새 탭을 두 번 눌러 ``긴급 오더 대응안``\ 으로 이름을 바꿉니다.
#. **슬라이서** — ``원료 수급 현황`` 페이지에서 슬라이서를 누르고 **Ctrl+C**\ 를 누릅니다. ``긴급 오더 대응안`` 페이지로 가서 **Ctrl+V**\ 를 누르고, **Sync visuals** 창에서 **Sync**\ 를 누릅니다.
   슬라이서가 같은 위치에 붙고, 두 페이지의 슬라이서가 같은 Bunker를 고릅니다.
#. **제목** — **Text box**\ 에 ``긴급 오더 대응안: 판단 기준과 추천안``\ 을 입력하고, 글꼴 크기 ``28``, 굵게로 합니다.
   위치와 크기: Height ``96``, Width ``1480``, Horizontal ``32``, Vertical ``12``
#. **카드** — **Card**\ 를 넣고 ``fact_response_option``\ 에서 ``기준 충족 대응안 수``, ``추천안``, ``추천안 추가 비용 (원)``\ 을 차례로 체크합니다.
   위치와 크기: Height ``160``, Width ``1856``, Horizontal ``32``, Vertical ``124``
#. **표** — **Table**\ 을 넣고 ``fact_response_option``\ 에서 아래 필드를 차례로 체크합니다.

   ``option_id``, ``option_name``, ``C1 안전재고``, ``C2 용량``, ``C3 납기``, ``C4 이송 한도``, ``추천 순위``, ``추가 비용 (원)``, ``첫 도착일``, ``판단``

   * **Format visual** → **Visual** 탭에서 **Values** → **Values**\ 의 **Font** 크기를 ``18``, **Column headers** → **Text**\ 의 **Font** 크기를 ``18``\ 로 합니다.
   * **Totals**\ 를 펼쳐 **Values**\ 를 **Off**\ 로 합니다. 표 아래 합계 행이 없어집니다.
   * 위치와 크기: Height ``340``, Width ``1856``, Horizontal ``32``, Vertical ``308``

   .. image:: ../assets/screenshots/d10-p2-table.png
      :alt: 긴급 오더 대응안 페이지에서 표를 선택한 화면. Build visual의 Columns에 option_id, option_name, C1 안전재고, C2 용량, C3 납기, C4 이송 한도, 추천 순위, 추가 비용 (원), 첫 도착일, 판단이 있습니다. 표 머리글은 파란색이고, OPT-1부터 OPT-4까지 4행에 ✅와 ❌, 1순위 (추천), 2순위, 추가 비용, 첫 도착일, 판단이 보입니다.
      :width: 1000

#. **묶은 세로 막대형 차트** — **Clustered column chart**\ 를 넣고 아래 필드를 차례로 체크합니다.

   * ``fact_option_balance``\ 의 ``추천안 적용 후 재고 (kg)``, ``fact_balance``\ 의 ``긴급 오더 재고 (kg)`` → **Y-axis**
   * ``dim_date``\ 의 ``date_key`` → **X-axis**

   **Title**\ 의 **Text**\ 에 아래 제목을 입력하고, **Subtitle**\ 은 **Off**\ 로 합니다. **Columns** → **Layout**\ 의 **Space between categories**\ 는 ``10``\ 으로 합니다.

   .. code-block:: text

      선택한 Bunker의 기말 재고 (kg): 추천안 적용 후 · 긴급 오더 (점선: 안전재고)

   **Analytics**\ 에서 4단계와 같이 **Y-Axis Constant Line**\ 을 넣습니다. 이름 ``안전재고``, **Value**\ 의 **fx** → ``fact_balance``\ 의 ``안전재고 (kg)``, 검정, **Transparency** ``0``, **Data label** **On**\ (**Right**, **Both**, 검정)입니다.

   위치와 크기: Height ``384``, Width ``1856``, Horizontal ``32``, Vertical ``672``

   .. image:: ../assets/screenshots/d10-p2-chart.png
      :alt: 긴급 오더 대응안 페이지에서 묶은 세로 막대형 차트를 선택한 화면. X-axis에 date_key, Y-axis에 추천안 적용 후 재고 (kg), 긴급 오더 재고 (kg)가 있습니다. 파란 막대는 모두 검은 점선 위에 있고, 빨간 막대는 점선 아래나 0 아래로 내려가는 날이 있습니다.
      :width: 1000

#. **Ctrl+S**\ 를 눌러 저장합니다.

7. 읽기 보기에서 확인
------------------------

#. 위쪽 **Reading view**\ 를 누르고, 왼쪽 **Pages**\ 에서 ``원료 수급 현황``\ 을 고릅니다.

   **예상 결과:** 4단계의 예상 결과와 같은 숫자와 차트가 보입니다.

   .. image:: ../assets/screenshots/d10-report-p1.png
      :alt: 읽기 보기의 원료 수급 현황 페이지. 제목 원료 Chip Balance 현황: 현재 계획과 긴급 오더, 오른쪽 위 슬라이서 BNK-L3-2, 카드 미달 Bunker 수 (현재 계획) 0, 미달 Bunker 수 (긴급 오더) 1, 첫 미달일 (긴급 오더) 2026-10-06, 필요 보충량 (kg) 35,630이 있고, 아래 차트에 날짜마다 파란 막대와 빨간 막대, 검은 점선(안전재고: 12,000)이 있습니다.
      :width: 1000

#. **Pages**\ 에서 ``긴급 오더 대응안``\ 을 고릅니다.

   **예상 결과:** 카드에 ``2``, ``OPT-2 Bunker 간 이송``, ``1,000,000``\ 이 보입니다.
   표에서 ``OPT-2``\ 와 ``OPT-3``\ 은 C1~C4가 모두 ✅이고 추천 순위가 ``1순위 (추천)``, ``2순위``\ 입니다. ``OPT-1``\ 은 C1, ``OPT-4``\ 는 C1과 C3이 ❌입니다.
   차트의 파란 막대(추천안 적용 후)는 모두 점선(안전재고) 위에 있습니다. 06장에서 계산한 결과와 같습니다.

   .. image:: ../assets/screenshots/d10-report-p2.png
      :alt: 읽기 보기의 긴급 오더 대응안 페이지. 카드 기준 충족 대응안 수 2, 추천안 OPT-2 Bunker 간 이송, 추천안 추가 비용 (원) 1,000,000이 있습니다. 표에서 OPT-1은 C1 ❌, OPT-2는 모두 ✅와 1순위 (추천), OPT-3은 모두 ✅와 2순위, OPT-4는 C1과 C3 ❌이고 판단에 C1 안전재고: BNK-L3-2 10/12부터 미달, C3 납기: SO-10322 완료 10/12, 납기 10/08이 두 줄로 보입니다. 아래 차트에서 파란 막대는 모두 검은 점선 위에 있습니다.
      :width: 1000

#. 슬라이서에서 추천안이 PET-SD를 보내는 ``BNK-L1-2``\ 를 고릅니다.

   **예상 결과:** ``긴급 오더 대응안`` 페이지의 파란 막대가 이송한 만큼 빨간 막대보다 낮지만, 최저 16,763 kg으로 점선(안전재고: 6,000) 위에 있습니다. 확인한 뒤 ``BNK-L3-2``\ 로 되돌립니다.

Troubleshooting
---------------

* **Apply** 뒤 오류가 나면 아래 **Problems** 탭에서 오류가 난 줄을 확인합니다. 테이블이 없다는 오류이면 **Model view** 리본의 **Edit tables**\ 에서 1단계의 테이블 7개가 모두 체크되어 있는지 확인하고 다시 **Apply**\ 를 누릅니다.
* 시각적 개체에 관계를 다시 계산해야 한다는 오류가 보이면 2단계의 **Refresh** → **Data**\ 를 다시 실행하고, 1분 뒤 보고서 탭을 새로 고칩니다.
* Semantic model이 **Viewing**\ 으로 열리면 오른쪽 위 **Viewing**\ 을 누르고 **Editing**\ 을 고릅니다.
* TMDL 스크립트 탭은 창을 닫으면 사라집니다. **Apply**\ 로 적용한 관계와 측정값은 모델에 남습니다.
* 슬라이서 목록에 **(Blank)**\ 가 보이면 4단계의 ``is not (Blank)`` 필터를 확인합니다.
* 막대 색이 다르면 **Y-axis**\ 의 필드 순서를 확인합니다. 필드를 끌어서 순서를 바꿀 수 있습니다.
* 점선이 0에 그어지면 **Y-Axis Constant Line**\ 의 **Value**\ 에 **fx**\ 로 ``안전재고 (kg)``\ 를 지정했는지 확인합니다.
* 시각적 개체가 겹쳐 선택하기 어려우면 먼저 위치와 크기를 입력해 자리를 옮깁니다.

다음 단계
------------

`11. Operations agent <11-operations-agent.rst>`_
