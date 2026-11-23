# Mage Amazon Delivery ingestion

Mage chịu trách nhiệm ingest file, validation kỹ thuật, dynamic batch, raw row
hash, current-state upsert và audit. Mage không trim/normalize/cast dữ liệu
nghiệp vụ; các bước đó tiếp tục thuộc dbt.

## Pipeline

Cả full load và incremental load có năm block:

1. Loader đọc một snapshot byte của file CSV, tính SHA-256 file checksum và
   sinh `batch_name` động dạng
   `amazon_delivery_inc_YYYYMMDDTHHMMSSZ_<suffix>`.
2. Transformer kiểm tra đúng 16 cột/header, kiểm tra business key kỹ thuật,
   loại khỏi lần load các dòng không có `Order_ID`/ngày hợp lệ, phát hiện
   duplicate trong batch và tính SHA-256 `row_hash` trên 15 giá trị raw ngoài
   `Order_ID`.
3. Exporter dùng một transaction set-based:
   - ID mới: insert.
   - ID cũ, hash khác: update 15 thuộc tính raw.
   - ID cũ, hash giống: unchanged, không ghi lại.
4. Verification đối soát audit, lineage staging và công thức action counter.
5. `build_amazon_delivery_dds` chạy `dbt build` (models + tests) rồi đối soát
   staging = Fact + distinct dbt rejected rows. Block lỗi làm pipeline thất bại.

Hướng dẫn khởi động, batch demo, đầu ra và rerun:
[Mage → dbt demo](../demo/HUONG_DAN_MAGE_DBT_DEMO.md).

dbt dùng cơ chế xác thực của Mage (SQL hoặc Windows) và đúng server/database/driver của Mage, với
profile riêng cho mỗi attempt. Không cần cấu hình lại `dbt_project/profiles.yml`
cá nhân để chạy qua pipeline. Python mặc định là `.venv` của repo; có thể đặt
`DBT_PYTHON_EXECUTABLE`. Không chạy hai pipeline đồng thời vào cùng database.

Full và incremental dùng chung contract/repository nên không có rule lặp.

## Current-state staging

`staging.raw_amazon_delivery` giữ một phiên bản hiện hành cho mỗi
`Order_ID`. Mười sáu cột nguồn vẫn là raw string để dbt tiếp tục thực hiện
trim, null normalization, cast và business rules.

- `load_batch_id`, `loaded_at`, `source_file_*`: lần insert đầu tiên.
- `updated_load_batch_id`, `updated_at`, `updated_source_file_*`: lần
  thay đổi gần nhất.
- `row_hash`: SHA-256 của 15 thuộc tính raw ngoài khóa.

Repo có archive nguồn trong `data/raw/archive` để đối soát/replay. Loader hiện không tự archive mọi file demo/đầu vào; người vận hành phải giữ tệp nếu cần replay. Project chưa
tách một raw-history table riêng nhằm giữ interface dbt hiện tại ổn định.

## Dynamic incremental

Pipeline không còn `INITIAL_FULL`, `INCREMENTAL_01`,
`INCREMENTAL_02`, date range hay row count gán cứng. Mỗi file được đọc và
đối chiếu theo `Order_ID + row_hash`; min/max `Order_Date` chỉ là metadata
quan sát trong audit. Cách này không bỏ sót correction cho order có ngày cũ.

Runtime variable tùy chọn:

- `source_file_path`: đường dẫn tuyệt đối hoặc đường dẫn tương đối từ
  `BI_PROJECT_ROOT`. Mặc định là `data/raw/amazon_delivery.csv`.

Không truyền `batch_name`; loader tự sinh cho từng lần chạy.

## Audit

Mỗi batch ghi:

- `rows_read`
- `rows_inserted`
- `rows_updated`
- `rows_unchanged`
- `rows_rejected`
- `rows_loaded = rows_inserted + rows_updated`

Điều kiện đối soát:

`rows_read = rows_inserted + rows_updated + rows_unchanged + rows_rejected`

`audit.load_batch.status` chỉ phản ánh ingestion. Bước dbt ghi riêng vào
`audit.dbt_run`, liên kết bằng `load_batch_id`; mỗi attempt có log/artifact riêng
ở `logs/etl/<load_batch_id>/<dbt_attempt_id>/`. Bảng được tạo nếu chưa có bằng
`sql/audit/02_create_dbt_run.sql` trong database hiện hành. Có thể chạy script
trước nếu tài khoản Mage không có quyền tạo bảng.

Nếu dbt lỗi sau khi staging commit, ingestion vẫn SUCCEEDED nhưng pipeline FAILED.
Sửa nguyên nhân rồi chạy lại toàn pipeline với cùng file; upsert không tạo trùng
và dbt vẫn build kể cả không có insert/update. Không tự reset dữ liệu khi retry.

## Test

Từ root project:

```powershell
$env:MSSQL_SERVER = 'localhost'
$env:MSSQL_DATABASE = 'AmazonDeliveryBI'
$env:MSSQL_DRIVER = 'ODBC Driver 17 for SQL Server'
$env:RUN_SQLSERVER_INTEGRATION = '1'

Push-Location mage_project
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
Pop-Location
```

Integration test tạo database tạm có prefix
`AmazonDeliveryBI_MageTest_`, kiểm tra insert/unchanged/update/lineage rồi
xóa đúng database tạm đó.


## Cập nhật SQL Authentication

Script khởi động mặc định dùng SQL Authentication với user `sa`, hỏi mật khẩu bằng Read-Host -AsSecureString. Mage và dbt dùng chung MSSQL_AUTHENTICATION=sql, MSSQL_USER, MSSQL_PASSWORD. Profile sinh ra chỉ chứa tham chiếu env_var cho user/password, không lưu mật khẩu. Muốn dùng Windows chọn -Authentication windows.
