13. 마무리
============

`목차 <../README.rst>`_ | 이전: `12. Foundry agent <12-foundry-agent.rst>`_

만든 결과를 한 번에 확인하고, 용량을 쓰는 항목을 멈춥니다.

1. 만든 것 확인하기
----------------------

.. list-table::
   :header-rows: 1
   :widths: 12 38 50

   * - 장
     - 만든 것
     - 확인할 결과
   * - 02~04
     - 원천 파일 14개, Bronze, Silver
     - 중복·공란·미등록 코드·센서 이상값 23행이 ``silver_quarantine``\ 에 격리됩니다.
   * - 05
     - Gold, OneLake 저장
     - Lakehouse ``lh_chipbalance_p001``\ 의 ``gold`` 스키마에 Gold 테이블이 있습니다.
   * - 06
     - 긴급 수주와 대응안 4개
     - 긴급 수주를 반영하면 BNK-L3-2(L3 PET-SD)가 2026-10-06에 안전재고 아래로 내려가고, 판단 기준을 모두 만족하는 추천안은 ``OPT-2``\ 입니다.
   * - 07
     - Unity Catalog 설명, Genie
     - Genie가 Q1~Q6에 정답과 같은 값으로 답합니다.
   * - 08~09
     - Ontology ``ont_chipbalance``, Ontology agent
     - Ontology agent가 같은 질문에 답합니다. 예: ``OPT-2``\ 를 반영해도 BNK-L1-2의 최저 기말재고는 16,763 kg으로 안전재고 6,000 kg 이상입니다.
   * - 10
     - Semantic model ``sm_chipbalance``, 보고서 ``rpt_chipbalance``
     - 원료 수급 현황과 긴급 오더 대응안 두 페이지에서 부족 지점과 추천안을 봅니다.
   * - 11
     - Eventhouse ``eh_chipbalance``, Operations agent ``oa_chipbalance``, Notebook ``nb_record_decision``
     - Teams에서 ``OPT-2``\ 를 승인하면 ``RiskEventStatus``\ 에 ``approved`` 행이, ``dbo.chip_decision_log``\ 에 승인 내역이 생깁니다.
   * - 12
     - Foundry 프로젝트 ``chipbalance-p001``, 에이전트 ``fa-chipbalance``
     - 에이전트가 Fabric IQ 도구로 ``ont_chipbalance``\ 에 물어, ``OPT-2``\ 를 반영한 BNK-L1-2의 최저 기말재고 16,763 kg이 안전재고 6,000 kg 이상이라고 답합니다.

같은 Gold를 Genie, Ontology agent, Power BI, Operations agent, Foundry agent가 함께 씁니다.
계산은 Databricks에서 한 번 하고, 결정은 담당자가 Teams에서 합니다.

2. 에이전트 멈추기
---------------------

#. Fabric 작업 영역 ``chipbalance-p001``\ 에서 ``oa_chipbalance``\ 를 엽니다. 도구 모음에 **Start**\ 가 보이면 멈춘 상태입니다. **Stop**\ 이 보이면 **Stop**\ 을 누릅니다.
#. Foundry 에이전트 ``fa-chipbalance``\ 는 질문할 때만 모델을 호출하므로 따로 멈추지 않습니다.
#. Databricks Compute는 20분 동안 쓰지 않으면 자동으로 종료됩니다. 바로 끄려면 **Compute**\ 에서 배정받은 Compute를 **Terminate**\ 합니다.

**예상 결과:** ``oa_chipbalance``\ 의 도구 모음에 **Start**\ 가 보입니다.

3. 실습 항목 정리
--------------------

실습 항목은 관리자가 한 번에 지웁니다(`관리자 준비 가이드 <../admin/README.rst>`_\ 의 "7. 종료 후 정리"). 참가자가 직접 지우라는 안내를 받았다면 아래 순서로 지웁니다.

#. Fabric 작업 영역 ``chipbalance-p001``: ``oa_chipbalance`` → ``nb_record_decision`` → ``eh_chipbalance`` → ``rpt_chipbalance`` → ``sm_chipbalance`` → ``ont_chipbalance``. 항목의 **...** > **Delete**\ 를 누릅니다. ``ont_chipbalance``\ 를 지우면 함께 만들어진 ``ont_chipbalance_eh_…``, ``ont_chipbalance_graph_…``\ 도 지웁니다.
#. Foundry: ``fa-chipbalance`` 에이전트 목록의 **작업** > **삭제**\ 로 에이전트를 지웁니다. 프로젝트와 Foundry 리소스 ``fdy-chipbalance-p001``\ 은 관리자가 Azure portal에서 지웁니다.
#. Databricks: Unity Catalog 스키마 ``lab_factory.chipbalance_p001``\ 은 관리자가 지웁니다.

Fabric 용량 일시 중지는 관리자가 합니다.

다음 단계
------------

수고하셨습니다. `목차 <../README.rst>`_\ 로 돌아가 필요한 장을 다시 볼 수 있습니다.
