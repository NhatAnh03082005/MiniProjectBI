# dbt — Amazon Delivery BI

## Vai trò

dbt biến đổi dữ liệu từ raw staging SQL Server sang mô hình ngôi sao phục vụ Power BI. dbt không đọc CSV trực tiếp, không nạp dữ liệu bằng Mage.ai và không tạo lại raw staging. Raw giữ bất biến; chuẩn hóa, chuyển kiểu, trường dẫn xuất, Dimension và Fact được xử lý từ dbt.

## Source

Source duy nhất của project là:

```text
AmazonDeliveryBI.staging.raw_amazon_delivery
```

Source có 21 cột: `staging_row_id`, 16 trường raw của CSV và bốn trường lineage (`source_file_name`, `source_row_number`, `load_batch_id`, `loaded_at`). Định nghĩa source nằm tại `models/sources/sources.yml`.

## Cấu trúc và lineage

```text
dbt_project/
├── dbt_project.yml
├── profiles.yml.example
├── README.md
├── requirements.txt
├── macros/
│   └── dimension_key_maps.sql
├── models/
│   ├── sources/
│   │   └── sources.yml
│   ├── staging/
│   │   ├── stg_amazon_delivery.sql
│   │   └── staging.yml
│   ├── intermediate/
│   │   ├── int_delivery_enriched.sql
│   │   └── intermediate.yml
│   └── marts/
│       ├── dimensions/
│       ├── facts/
│       └── marts.yml
└── tests/
```

Lineage: `staging.raw_amazon_delivery` → `stg_amazon_delivery` → `int_delivery_enriched` → `int_delivery_accepted` → Dimension/Fact marts. Hard-rule violations from staging also flow through `int_delivery_validation_errors` to `delivery_rejections`.

- `models/staging/`: trim, null-normalization và `TRY_CONVERT`; không loại record thiếu, rating invalid hoặc outlier.
- `models/intermediate/`: derived fields, quality flags, pickup rollover/delay, Haversine distance và analytical groups; phân loại vi phạm cứng trước DDS.
- `models/marts/dimensions/`: năm Dimension semantic.
- `models/marts/facts/`: Fact có một dòng cho một `order_id` hợp lệ theo Data Contract.
- `macros/`: tạo/duy trì technical key-map cho surrogate key ổn định của Dimension phân loại. Đây là mã nguồn dbt, không phải output runtime.
- `tests/`: singular tests; YAML tests nằm cùng model documentation.

## Xử lý lỗi dữ liệu trước DDS

`int_delivery_validation_errors` tạo một dòng cho mỗi cột vi phạm quy tắc cứng, giữ `staging_row_id`, lineage, giá trị raw, mã lỗi và quy tắc mong đợi. `delivery_rejections` materialize danh sách này thành bảng trạng thái hiện tại; bảng được dựng lại cùng Fact, không phải lịch sử các lần sửa lỗi. Dữ liệu gốc ở `staging.raw_amazon_delivery` không bị thay đổi.

Các lỗi chặn DDS: giá trị thiếu ở 11 cột nguồn bắt buộc, gồm `Order_ID`, tuổi, rating, bốn tọa độ, ngày/giờ đặt, giờ lấy hàng và thời gian giao (`NULL`, chuỗi rỗng, `NAN`, `NULL` dạng chuỗi); `order_id` trùng sau trim; giá trị số/ngày/giờ không chuyển kiểu được; tuổi âm; rating ngoài 1–5; tọa độ ngoài phạm vi vĩ độ [-90,90] hoặc kinh độ [-180,180]; thời gian giao âm. Một dòng có nhiều cột lỗi có nhiều dòng trong bảng lỗi nhưng chỉ bị loại một lần khỏi Fact.

Weather, Traffic, Vehicle, Area và Category thiếu được chuyển thành `Unknown` và không tự chặn DDS. `missing_operational_context_flag` ghi nhận Weather/Traffic thiếu; ba cột phân loại còn lại tra vào Unknown Member của Dimension tương ứng. `Order_Time` thiếu vẫn là lỗi chặn. Tuổi dưới 18, thời gian giao cao hơn 195/265 phút, tọa độ cửa hàng (0,0) và khoảng cách lớn hơn 50 km tiếp tục là cảnh báo như trước. Fact và Dimension phân loại cùng đọc `int_delivery_accepted`. Test đối soát kiểm tra số dòng raw bằng số dòng Fact cộng số `staging_row_id` bị loại riêng biệt.

Khoảng cách Haversine tính được trên 50 km vẫn giữ nguyên trong `delivery_distance_km`, có `distance_outlier_flag = 1`, `distance_status = 'Outlier >50 km'` và `distance_band = '>50 km'`. `valid_distance_flag = 1` chỉ biểu thị khoảng cách tính được không quá 50 km, không quyết định dòng có vào Fact hay không. Nếu tọa độ Store là `(0,0)`, không có khoảng cách đáng tin cậy để công bố nên giá trị số vẫn `NULL`; `distance_status = 'Store coordinates (0,0)'` và `distance_band = 'Not calculable (Store 0,0)'` ghi rõ nguyên nhân. Biểu đồ khoảng cách của Power BI dùng các measure `Calculated Distance` để hiển thị cả nhóm trên 50 km; các measure `Valid Distance` chỉ dùng khi cần phân tích nhóm trong ngưỡng.

## Semantic models

Năm Dimension được phê duyệt:

- `dim_date`
- `dim_delivery_condition`
- `dim_vehicle`
- `dim_area`
- `dim_category`

Fact được phê duyệt: `fact_delivery`.

`fact_delivery` chỉ công bố 31 trường logic của Data Contract, giữ năm foreign key, business key `order_id`, `delivery_key`, measures, quality flags và lineage. Fact không chứa exact coordinates, aggregate KPI, SLA hoặc late flag.

## Surrogate keys

- `dim_date.date_key` là `YYYYMMDD`; Unknown Member dùng key `0`.
- `dim_date` hiện chỉ sinh lịch năm 2022 theo phạm vi của dataset mẫu. Ngày hợp lệ ngoài 2022 không phải lỗi nguồn; cần mở rộng Dimension trước khi dùng dữ liệu năm khác để tránh lookup về key `0`.
- Bốn Dimension phân loại dùng key-map kỹ thuật trong schema `dw`, có `IDENTITY` và Unknown Member key `0`.
- Key-map không phải Dimension semantic hoặc nguồn cho Power BI; nó chỉ giữ natural key → surrogate key ổn định qua incremental load.
- Khi chạy database thật, tài khoản dbt cần quyền tạo/quản lý các key-map technical tables trong `dw`.

## Tests

YAML tests kiểm tra:

- Unique/not-null Dimension key.
- Unique/not-null `delivery_key` và `order_id` của Fact.
- Relationship từ năm Fact foreign key đến Dimension.
- Lineage bắt buộc không null ở staging, intermediate và Fact.

Singular tests kiểm tra:

- Grain Fact một dòng mỗi `order_id`.
- Lỗi chuyển kiểu raw → staging.
- Rating valid 1–5, nhưng vẫn cho phép rating null.
- Delivery time không âm, nhưng vẫn cho phép null.
- Age group và underage flag; không áp max age chưa được phê duyệt.
- Pickup/missing-context/baseline-P90 flags.
- Valid-distance rule và distance band.
- Không bỏ sót lỗi chuyển kiểu trong bảng `delivery_rejections`; không để dòng bị loại vào Fact; đối soát raw, Fact và dòng bị loại.
- Mười một trường nguồn bắt buộc đều có giá trị trên các dòng được nhận vào DDS; Weather, Traffic, Vehicle, Area và Category được phép `Unknown`.
- `warn_rejected_delivery_rows` phát cảnh báo khi có dòng raw bị loại, đếm `staging_row_id` riêng biệt; cảnh báo không làm hỏng build. Các test tính đúng quy tắc và đối soát vẫn là lỗi nếu vi phạm.

## Cấu hình profile

Không commit `profiles.yml`, password, connection string hay credential. Trưởng nhóm copy `profiles.yml.example` thành `profiles.yml` trên máy tích hợp và cấp các biến môi trường:

```text
DBT_SQLSERVER_DRIVER
DBT_SQLSERVER_SERVER
DBT_SQLSERVER_PORT
DBT_SQLSERVER_DATABASE
DBT_SQLSERVER_USER
DBT_SQLSERVER_PASSWORD
```

Mẫu profile dùng SQL Server database `AmazonDeliveryBI` và target schema `dw`. Cần có Microsoft ODBC Driver tương ứng trên máy chạy dbt.

## Lệnh dự kiến

Từ thư mục `dbt_project/`:

```powershell
# Local environment in this workspace
.\.venv\Scripts\dbt.exe --version
.\.venv\Scripts\dbt.exe parse --profiles-dir .

# Run by the integration owner after SQL Server and Mage are ready
dbt debug
dbt run
dbt test
dbt build
```

Dependencies được pin tại `requirements.txt`. Không commit `.python312/`, `.venv/`, `target/`, `logs/`, `.user.yml`, `profiles.yml` hoặc `dbt_packages/`.

## Validation status

Logic xử lý lỗi, cột phân loại tùy chọn và khoảng cách mới đã qua `dbt build` trên SQL Server local. Build chạy 7 table models, 4 view models, 79 data tests và đạt `PASS=89, WARN=1, ERROR=0`. Cảnh báo `warn_rejected_delivery_rows` ghi `Got 145 results`; mỗi kết quả là một `staging_row_id` bị loại, không phải một cột lỗi. Đối soát: 43.739 dòng raw = 43.594 dòng Fact + 145 dòng bị loại riêng biệt. Trong Fact, 39.958 dòng có khoảng cách không quá 50 km, 151 dòng có khoảng cách trên 50 km được giữ giá trị và gắn cờ, 3.485 dòng có tọa độ Store `(0,0)` nên không thể tính khoảng cách đáng tin cậy. Bảng lỗi có 54 lỗi rating thiếu, 91 lỗi giờ đặt thiếu và 53 lỗi rating ngoài 1–5. Weather, Traffic, Vehicle, Area và Category thiếu không tự chặn DDS; dữ liệu mẫu hiện không có dòng nào thiếu Vehicle, Area hoặc Category nên ba nhóm Unknown này chưa có trường hợp thực tế để đối soát. Cả 91 dòng thiếu Weather/Traffic hiện cũng thiếu `Order_Time`, nên số dòng Fact chưa đổi. Log cũ trong `evidence/final_etl/` có trước thay đổi này và không đại diện cho build mới.

## TODO và quyết định cần chốt

1. `LOAD-01` phải chốt duplicate/rerun policy khi `order_id` lặp giữa batch. Hiện tất cả dòng có `order_id` trùng sau trim đều bị loại, không tự chọn bản ghi để giữ.
2. Trưởng nhóm xác nhận quyền dbt `CREATE TABLE`, `INSERT`, `MERGE` và `IDENTITY_INSERT` trong schema `dw` cho key-map technical tables.
3. Tài liệu chưa chốt range nghiệp vụ min/max cho `agent_age`; code chỉ reject tuổi âm và vẫn giữ tuổi 15/50.
4. Các boundary group và physical implementation được ghi Proposed trong MAP-01/Data Contract cần được trưởng nhóm xác nhận trước khi dùng làm chuẩn integration chính thức.
