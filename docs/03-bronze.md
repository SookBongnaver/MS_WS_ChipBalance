# 03. Bronze

[목차](../README.md) \| 이전: [02. 원천 데이터 만들기](02-source-data.md) \| 다음: [04. Silver](04-silver.md)

`03_bronze`로 02장에서 만든 원천 파일 14개를 Unity Catalog의 Bronze 테이블 14개로 적재합니다.

Bronze는 원본을 바꾸지 않습니다. 값은 모두 문자로 두고, 어느 파일의 몇 번째 행인지(`_source_file`, `_source_row`)와 적재 시각(`_ingested_at`)만 붙입니다. Silver나 Gold 결과가 이상하면 Bronze에서 원본 행을 찾아 비교합니다.

| 계층 | 저장 위치 | 내용 |
|----|----|----|
| 원천 | Volume `raw` | SAP·FPIMS·PVSS 추출 파일 (CSV, JSON) |
| **Bronze** | `bronze_*` 테이블 14개 | 파일 내용 그대로 + 원천 위치·적재 시각 |
| Silver | `silver_*` 테이블 15개 | 형식·단위를 맞추고 문제 행을 격리 (04장) |
| Gold | Fabric OneLake의 `gold.<테이블>` | 업무 계산 결과 (05·06장). Databricks의 `gold_*`는 세션 임시 뷰이며 Unity Catalog에 저장하지 않음 |

## 1. Notebook 열고 실행

1.  `ChipBalance` 폴더에서 `03_bronze`를 엽니다.
2.  오른쪽 위 Compute 목록에 **Serverless**가 선택되어 있는지 확인합니다. (02장 1단계와 같습니다.)
3.  위에서부터 **Shift+Enter**로 한 셀씩 실행합니다. 위쪽 **Run all**로 한 번에 실행해도 됩니다. 전체 실행에 1–2분 걸립니다.

## 2. 셀별 결과 확인

1.  **1. 설정 불러오기**

    **예상 결과:** 01에서 본 결과가 다시 표시되고, 맨 아래에 `연결 확인 완료`가 보입니다.

2.  **2. 파일과 Bronze 테이블**

    파일 하나가 Bronze 테이블 하나가 됩니다. 테이블 이름은 `bronze_<시스템>_<내용>`입니다. 셀은 파일을 읽어 원천 위치와 적재 시각을 붙이는 함수 `read_raw`를 만듭니다.

    **예상 결과:** 결과 없이 끝납니다.

3.  **3. Bronze 테이블 만들기**

    파일마다 Delta 테이블로 저장합니다. 다시 실행하면 테이블을 덮어씁니다.

    **예상 결과:** 표 14행, 아래에 `합계: 43,410행`. 02장에서 만든 파일의 행 수와 같습니다.

    <img src="../assets/screenshots/d03-tables.png" width="900" alt="3. Bronze 테이블 만들기 결과. Bronze 테이블, 원천 파일, 행 수 열이 있는 14행 표입니다. bronze_pvss_bunker_level은 17278행이고 아래에 합계 43,410행이 표시됩니다." />

4.  **4. 원본 그대로인지 확인**

    `bronze_sap_purchase_order_open`에서 `BNK-L3-2`의 10월 입고 예정을 봅니다. 02장 **8. BNK-L3-2 입고 예정**과 같은 내용이어야 합니다.

    **예상 결과:** 6행. 10월 2일 줄은 여전히 `50` `TO`이고, 10월 9일 `00020` 줄이 두 번 있습니다. `_source_row`는 원천 파일의 몇 번째 행인지 알려 줍니다(113–118).

    <img src="../assets/screenshots/d03-po.png" width="900" alt="4. 원본 그대로인지 확인 결과. purchase_order_id, po_line_no, promised_date, quantity, unit, _source_row, _ingested_at 열이 있는 6행 표입니다. 00010 줄은 50, TO이고 00020 줄은 _source_row 114와 115로 두 번 있습니다." />

5.  **5. 열 형식 확인**

    Bronze는 형식을 바꾸지 않으므로 날짜와 수량도 문자(`string`)입니다. 04장에서 날짜·숫자 형식으로 바꿉니다.

    **예상 결과:** 9행. `plan_date`, `planned_output_kg`가 `string`이고, 붙인 열 `_source_row`는 `int`, `_ingested_at`은 `timestamp`입니다.

    <img src="../assets/screenshots/d03-types.png" width="900" alt="5. 열 형식 확인 결과. bronze_fpims_production_plan의 col_name, data_type, comment 9행입니다. plan_id부터 sales_order_id까지 string, _source_file string, _source_row int, _ingested_at timestamp입니다." />

Bronze·Silver는 Unity Catalog에서 확인합니다. Gold는 05장 마지막에 Fabric Lakehouse에서 확인하며, 선택 연결이 준비된 경우에만 Unity Catalog의 Foreign Catalog에서도 읽을 수 있습니다.

## Troubleshooting

- `PATH_NOT_FOUND`처럼 파일을 찾지 못한다는 오류가 나면 02장 `02_source_data`를 다시 실행합니다.
- 행 수가 다르면 02장 **2. 원천 파일 만들기**부터 다시 실행한 뒤 이 Notebook을 다시 실행합니다.

## 다음 단계

[04. Silver](04-silver.md)
