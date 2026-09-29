구성도 아이콘 출처
====================

`목차 <../README.rst>`_

``architecture.svg``\ ·``architecture.png``\ 는 Workshop 구성을 설명하는 개념도입니다.
상자·선·글자·아이콘을 고치려면 ``architecture.excalidraw``\ 를 https://excalidraw.com 에서 엽니다.

아이콘 출처
------------

* `Microsoft Azure architecture icons <https://learn.microsoft.com/en-us/azure/architecture/icons/>`_ — Azure Public Service Icons v24
* `Microsoft Fabric icons <https://learn.microsoft.com/en-us/fabric/fundamentals/icons>`_ — 공식 페이지의
  `Icons.zip <https://raw.githubusercontent.com/microsoft/fabric-samples/main/docs-samples/Icons.zip>`_ v6.1.0
* `Microsoft Power Platform icons <https://learn.microsoft.com/en-us/power-platform/guidance/icons>`_ — 공식 SVG 아이콘 묶음

세 페이지 모두 아키텍처 그림, 교육 자료, 문서에서 아이콘을 쓰도록 허용합니다.
아이콘은 원본 SVG를 그대로 쓰며 자르기·뒤집기·색 변경·비율 변경을 하지 않습니다.
Ontology는 공식 아이콘 묶음에 없어서 일반 상자로 표시합니다.

.. list-table::
   :header-rows: 1

   * - 파일 (``icons/``)
     - 공식 배포 파일
   * - ``databricks.svg``
     - Azure v24 ``10787-icon-service-Azure-Databricks.svg``
   * - ``storage.svg``
     - Azure v24 ``10086-icon-service-Storage-Accounts.svg``
   * - ``users.svg``
     - Azure v24 ``10230-icon-service-Users.svg``
   * - ``fabric.svg``
     - Fabric ``fabric_48_color.svg``
   * - ``lakehouse.svg``
     - Fabric ``lakehouse_64_item.svg``
   * - ``semantic-model.svg``
     - Fabric ``semantic_model_64_item.svg``
   * - ``power-bi.svg``
     - Fabric ``power_bi_48_color.svg``
   * - ``data-agent.svg``
     - Fabric ``data_agent_64_item.svg``
   * - ``operations-agent.svg``
     - Fabric ``operations_agent_64_item.svg``
   * - ``power-apps.svg``
     - Power Platform ``PowerApps_scalable.svg``
   * - ``power-automate.svg``
     - Power Platform ``PowerAutomate_scalable.svg``

다시 만들기
------------

#. ``python tools/build_architecture.py``\ 를 실행합니다. SVG와 Excalidraw 파일을 만들고 이전 PNG를 지웁니다.
#. ``assets/architecture.svg``\ 를 브라우저에서 1800×1350 크기로 열어 ``assets/architecture.png``\ 로 캡처합니다.
