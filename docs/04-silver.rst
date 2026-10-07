04. Silver
============

`목차 <../README.rst>`_ | 이전: `03. Bronze <03-bronze.rst>`_ | 다음: `05. Gold와 OneLake <05-gold-onelake.rst>`_

``04_silver``\ 로 Bronze 테이블을 계산에 쓸 수 있는 Silver 테이블로 바꿉니다.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - 작업
     - 예
   * - 형식 맞추기
     - 문자 ``20261002`` → 날짜 ``2026-10-02``, 문자 ``50000`` → 숫자
   * - 단위 통일
     - 발주 수량 ``50`` ``TO``\ (톤) → ``50000`` kg
   * - 격리
     - 중복, 수량 공란, 미등록 원료 코드, 범위를 벗어난 센서 값 → ``silver_quarantine``

격리한 행은 지우지 않고 이유(``reason``)와 Bronze 원본 행 번호를 함께 남깁니다.

1. Notebook 열고 실행
------------------------

#. ``ChipBalance`` 폴더에서 ``04_silver``\ 를 엽니다.
#. 오른쪽 위 Compute 목록에 **Serverless**\ 가 선택되어 있는지 확인합니다.
#. 위에서부터 **Shift+Enter**\ 로 한 셀씩 실행합니다. 위쪽 **Run all**\ 로 한 번에 실행해도 됩니다. 전체 실행에 1~2분 걸립니다.

2. 셀별 결과 확인
--------------------

#. **1. 설정 불러오기**

   **예상 결과:** 01에서 본 결과가 다시 표시되고, 맨 아래에 ``연결 확인 완료``\ 가 보입니다.

#. **2. 기준 정보와 실적: 형식 맞추기**

   문제 행이 없는 테이블 12개는 형식만 바꿉니다. 날짜는 ``DATE``, 시각은 한국 시간 ``TIMESTAMP``, 수량은 ``BIGINT``, 소요량은 소수 6자리 ``DECIMAL``\ 입니다.

   **예상 결과:** 표 12행. ``Silver 행 수``\ 가 ``Bronze 행 수``\ 와 같습니다.

   .. image:: ../assets/screenshots/d04-typed.png
      :alt: 2. 기준 정보와 실적 결과. Bronze, Silver, Bronze 행 수, Silver 행 수 열이 있는 12행 표입니다. bronze_fpims_material_consumption과 silver_material_consumption이 모두 17168행입니다.
      :width: 900

#. **3. 입고 예정 발주 정리**

   행마다 아래 순서로 확인합니다. 해당하면 격리하고, 통과한 행만 ``silver_purchase_order_open``\ 에 넣습니다.

   .. list-table::
      :header-rows: 1
      :widths: 10 50 40

      * - 순서
        - 확인
        - 처리
      * - 1
        - 원료 코드가 ``silver_material``\ 에 없음
        - ``unknown_material``\ 로 격리
      * - 2
        - 수량이 공란
        - ``blank_quantity``\ 로 격리
      * - 3
        - 발주 번호·항목이 앞 행과 같음
        - ``duplicate_line``\ 으로 격리 (먼저 나온 행만 남김)
      * - 4
        - 단위가 ``TO``
        - 수량 × 1000 → kg. 원래 수량과 단위는 ``source_quantity``, ``source_unit``\ 에 남김

   **예상 결과:** 결과 없이 끝납니다.

#. **4. 발주 정리 결과**

   02·03장에서 본 ``BNK-L3-2``\ 의 10월 입고 예정을 다시 봅니다.

   **예상 결과:** 5행. 10월 2일 줄은 ``quantity_kg``\ 가 ``50000``\ 이고, 원래 값 ``50`` ``TO``\ 가 옆에 남습니다. 10월 9일 줄은 한 번만 나옵니다.

   .. image:: ../assets/screenshots/d04-po.png
      :alt: 4. 발주 정리 결과. purchase_order_id, po_line_no, supplier_id, promised_date, source_quantity, source_unit, quantity_kg 열이 있는 5행 표입니다. 00010 줄은 2026-10-02, 50, TO, 50000입니다.
      :width: 900

#. **5. 센서 값 정리**

   값이 0 미만이거나 Bunker 용량보다 크면 ``out_of_range``, 같은 Bunker·시각이 앞 행과 같으면 ``duplicate_reading``\ 으로 격리합니다.
   기록이 빠진 시각은 채우지 않습니다. 시작 재고에는 9월 30일 23시 값만 쓰기 때문입니다.

   **예상 결과:** 결과 없이 끝납니다.

#. **6. 격리 테이블 만들기**

   격리한 행을 ``silver_quarantine``\ 에 모읍니다. ``raw_record``\ 에는 Bronze 원본 행을 JSON으로 남깁니다.

   **예상 결과:** 5행, 합계 23행. ``unknown_material`` 3, ``duplicate_line`` 5, ``blank_quantity`` 4, ``out_of_range`` 6, ``duplicate_reading`` 5

   .. image:: ../assets/screenshots/d04-quarantine.png
      :alt: 6. 격리 테이블 만들기 결과. source_table, reason, rows 열이 있는 5행 표입니다. 발주에서 unknown_material 3, duplicate_line 5, blank_quantity 4, 센서에서 out_of_range 6, duplicate_reading 5입니다.
      :width: 900

#. **7. 격리한 행 보기**

   미등록 원료 코드와 범위를 벗어난 센서 값을 봅니다. ``source_row_number``\ 로 Bronze 원본 행을 찾을 수 있습니다.

   **예상 결과:** 9행. 센서 값 ``-100``, ``255000``\ 처럼 0보다 작거나 용량보다 큰 값과, 원료 코드 ``PET-HV``, ``MB-AS``, ``NY6-R``\ 가 보입니다.

   .. image:: ../assets/screenshots/d04-quarantine-rows.png
      :alt: 7. 격리한 행 보기 결과. source_table, source_row_number, record_key, reason, raw_record 열이 있는 표입니다. bronze_pvss_bunker_level의 out_of_range 6행과 bronze_sap_purchase_order_open의 unknown_material 행이 보입니다.
      :width: 900

#. **8. 센서 기록이 빠진 시각**

   9월 한 달은 Bunker 24개 × 720시간 = 17,280개 기록이 있어야 합니다. 빠진 시각을 찾습니다.

   **예상 결과:** 7행. 예: ``BNK-L1-1``\ 의 9월 3일 02시, ``BNK-L3-2``\ 의 9월 7일 18시

   .. image:: ../assets/screenshots/d04-missing.png
      :alt: 8. 센서 기록이 빠진 시각 결과. bunker_id, reading_ts 열이 있는 7행 표입니다. 첫 행은 BNK-L1-1, 2026-09-03 02:00입니다.
      :width: 900

#. **9. Silver 정리 결과**

   Silver 테이블 15개의 행 수입니다.

   **예상 결과:** 15행. ``silver_purchase_order_open`` 719행(Bronze 731행 − 격리 12행), ``silver_bunker_level`` 17,267행(Bronze 17,278행 − 격리 11행), ``silver_quarantine`` 23행

   .. image:: ../assets/screenshots/d04-counts.png
      :alt: 9. Silver 정리 결과. Silver 테이블, 행 수 열이 있는 15행 표입니다. silver_purchase_order_open 719, silver_bunker_level 17267, silver_quarantine 23입니다.
      :width: 900

Troubleshooting
---------------

* ``TABLE_OR_VIEW_NOT_FOUND`` 오류가 나면 03장 ``03_bronze``\ 를 먼저 실행합니다.
* 격리 건수가 다르면 02장부터 다시 실행합니다. 02를 다시 실행하면 03, 04도 다시 실행합니다.

다음 단계
------------

`05. Gold와 OneLake <05-gold-onelake.rst>`_
