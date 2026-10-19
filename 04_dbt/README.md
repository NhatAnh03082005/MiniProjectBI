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
04_dbt/
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

Lineage: `staging.raw_amazon_delivery` → `stg_amazon_delivery` → `int_delivery_enriched` → Dimension/Fact marts.

- `models/staging/`: trim, null-normalization và `TRY_CONVERT`; không loại record thiếu, rating invalid hoặc outlier.
- `models/intermediate/`: derived fields, quality flags, pickup rollover/delay, Haversine distance và analytical groups.
- `models/marts/dimensions/`: năm Dimension semantic.
- `models/marts/facts/`: Fact có một dòng cho một `order_id` hợp lệ theo Data Contract.
- `macros/`: tạo/duy trì technical key-map cho surrogate key ổn định của Dimension phân loại. Đây là mã nguồn dbt, không phải output runtime.
- `tests/`: singular tests; YAML tests nằm cùng model documentation.

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

Từ thư mục `04_dbt/`:

```powershell
# Local environment in this workspace
 .\.python312\Scripts\dbt.exe --version
.\.python312\Scripts\dbt.exe parse --profiles-dir .

# Run by the integration owner after SQL Server and Mage are ready
dbt debug
dbt run
dbt test
dbt build
```

Dependencies được pin tại `requirements.txt`. Không commit `.python312/`, `.venv/`, `target/`, `logs/`, `.user.yml`, `profiles.yml` hoặc `dbt_packages/`.

## Validation status

`dbt --version` và `dbt parse` đã được chạy trong môi trường cục bộ. Parse chỉ xác nhận cấu trúc project, Jinja, YAML và dependency graph; nó không truy vấn hay materialize model trong SQL Server.

Chưa runtime-validate với database thật:

- `dbt debug`, `dbt run`, `dbt test`, `dbt build`.
- Quyền SQL Server, ODBC driver và profile thật.
- Tạo key-map tables, materialize Dimension/Fact, FK lookup và row-count/KPI reconciliation.
- Baseline tests trên 43.739 dòng sau Mage ingestion.

## TODO và quyết định cần chốt

1. `LOAD-01` phải chốt duplicate/rerun policy khi `order_id` lặp giữa batch. Code không tự chọn bản ghi để giữ; Fact unique test sẽ fail để báo lỗi.
2. Trưởng nhóm xác nhận quyền dbt `CREATE TABLE`, `INSERT`, `MERGE` và `IDENTITY_INSERT` trong schema `dw` cho key-map technical tables.
3. Tài liệu chưa chốt range nghiệp vụ min/max cho `agent_age`; code chỉ reject tuổi âm và vẫn giữ tuổi 15/50.
4. Các boundary group và physical implementation được ghi Proposed trong MAP-01/Data Contract cần được trưởng nhóm xác nhận trước khi dùng làm chuẩn integration chính thức.
