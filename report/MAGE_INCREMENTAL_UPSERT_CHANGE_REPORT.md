# Báo cáo hoàn thiện Mage incremental và upsert

## Trạng thái nghiệm thu

- **Trạng thái:** `CLOSED`
- **Ngày nghiệm thu:** 2026-11-12 (Asia/Bangkok)
- **Phạm vi:** Mage, SQL staging/audit, tài liệu hợp đồng dữ liệu và kiểm thử hồi quy dbt.
- **Kết luận:** toàn bộ yêu cầu chỉnh sửa của giảng viên đã được triển khai và các lớp kiểm thử đều thành công.

## Kết quả theo 10 bước đề xuất

| Bước | Kết quả thực hiện | Trạng thái |
|---|---|---|
| 1. Chốt current-state staging hay raw history | Chọn **current-state staging**. Giữ một dòng hiện hành cho mỗi `Order_ID`; file nguồn tiếp tục là nơi lưu raw history. | Hoàn tất |
| 2. Cho phép batch động | Bỏ whitelist/tên batch cố định; kiểm tra batch name động, không rỗng và tối đa 50 ký tự. | Hoàn tất |
| 3. Bổ sung hash và update metadata | Thêm `row_hash`, `updated_at`, `updated_load_batch_id`, `updated_source_file_name`, `updated_source_row_number`; giữ nguyên 16 cột raw. | Hoàn tất |
| 4. Bổ sung audit counters | Thêm `rows_inserted`, `rows_updated`, `rows_unchanged`; đối soát với `rows_read`, `rows_rejected`, `rows_loaded`. | Hoàn tất |
| 5. Sửa loader và transformer Mage | Loader nhận file runtime và sinh batch động; transformer chỉ kiểm tra kỹ thuật, tính range/hash từ dữ liệu thật. | Hoàn tất |
| 6. Thay duplicate error bằng upsert | Insert bản ghi mới, update khi hash đổi, bỏ qua khi hash không đổi; xử lý set-based trong một transaction. | Hoàn tất |
| 7. Sửa verification và test | Verification kiểm tra audit, hash, lineage và công thức counter; có unit test và integration test SQL Server. | Hoàn tất |
| 8. Xóa batch mặc định khỏi metadata | Pipeline incremental không còn biến batch/date/count gán cứng và không còn `variables_dir` cá nhân. | Hoàn tất |
| 9. Cập nhật Data Contract và README | Ghi rõ current-state, hash, upsert, lineage, boundary Mage/dbt và hướng dẫn vận hành. | Hoàn tất |
| 10. Kiểm tra tác động dbt | Không chuyển business transform sang Mage; `dbt build` đạt toàn bộ 67 node/test. | Hoàn tất |

## Thay đổi theo file

### Logic dùng chung của Mage

| File | Thay đổi và chức năng | Tối ưu so với trước |
|---|---|---|
| `mage_project/amazon_delivery_contract.py` | Định nghĩa 16 cột nguồn, sinh batch name động, resolve source runtime, validate schema/key/date, phát hiện key trùng trong batch và tính SHA-256 `row_hash`. | Xóa cấu hình date/count cố định; full và incremental dùng chung một contract, tránh lệch rule. |
| `mage_project/amazon_delivery_loader.py` | Đọc file nguồn, tính checksum và tạo payload batch động cho cả full/incremental. | Không còn lặp code loader hoặc phụ thuộc một batch mặc định. |
| `mage_project/amazon_delivery_repository.py` | Ghi audit và thực hiện set-based upsert trong transaction; đối soát action counters; rollback khi lỗi. | Thay insert từng dòng/duplicate error bằng xử lý tập hợp, idempotent và an toàn giao dịch. |

### Các block của pipeline Mage

| File | Thay đổi và chức năng |
|---|---|
| `mage_project/data_loaders/full_load_amazon_delivery.py` | Wrapper full-load gọi loader dùng chung. |
| `mage_project/data_loaders/incremental_load_amazon_delivery.py` | Wrapper incremental gọi loader dùng chung và nhận source runtime. |
| `mage_project/transformers/validate_full_amazon_delivery.py` | Áp dụng technical contract dùng chung. |
| `mage_project/transformers/validate_incremental_amazon_delivery.py` | Validate kỹ thuật và tính hash; không thực hiện business cleansing của dbt. |
| `mage_project/data_exporters/export_full_amazon_delivery.py` | Gọi repository upsert và kiểm tra output audit. |
| `mage_project/data_exporters/export_incremental_amazon_delivery.py` | Gọi cùng cơ chế upsert idempotent cho incremental. |
| `mage_project/custom/verify_amazon_delivery_batch.py` | Xác minh trạng thái batch, checksum, counter, hash và insert/update lineage. |

### SQL staging và audit

| File | Thay đổi và chức năng | Tối ưu so với trước |
|---|---|---|
| `sql/audit/01_create_load_batch.sql` | Migration idempotent cho dynamic batch và ba action counters. | Chạy lại an toàn, audit mô tả đúng insert/update/unchanged. |
| `sql/staging/01_create_raw_amazon_delivery.sql` | Migration additive cho hash/update lineage; backfill metadata; index hỗ trợ upsert. | Không đổi tên bảng, không xóa/đổi kiểu 16 cột raw nên giữ interface với dbt. |
| `sql/validation/01_validate_sql_skeleton.sql` | Kiểm tra schema, counter reconciliation và duplicate normalized `Order_ID`. | Phát hiện sai lệch cấu trúc và dữ liệu ngay sau migration. |
| `sql/run_sql_skeleton.sql` | Orchestrator SQLCMD gọi các script thành phần theo thứ tự. | Loại bỏ bản sao DDL lớn, chỉ còn một nguồn sự thật. |
| `sql/run_sql_skeleton_demo.sql` | Orchestrator demo dùng cùng migration/validation chính. | Demo không còn lệch với bản triển khai. |
| `sql/README.md` | Hướng dẫn chạy migration, pipeline và test. | Quy trình cài đặt/nghiệm thu có thể lặp lại trên database local của từng thành viên. |

### Metadata và tài liệu

| File | Thay đổi và chức năng |
|---|---|
| `mage_project/pipelines/amazon_delivery_incremental_load/metadata.yaml` | Xóa batch/date/count mặc định. |
| `mage_project/pipelines/test_sql_server_connection/metadata.yaml` | Xóa đường dẫn variables cá nhân. |
| `mage_project/README.md` | Mô tả kiến trúc, biến runtime, upsert, test và boundary Mage/dbt. |
| `MAGE_TEAM_SETUP.md` | Cập nhật hướng dẫn setup đồng nhất cho từng database local. |
| `project_management/DATA_CONTRACT.md` | Chốt current-state staging, dynamic batch, hash, counters và lineage. |
| `project_management/DECISION_LOG.md` | Ghi nhận các quyết định kiến trúc liên quan. |
| `README.md` | Đồng bộ mô tả trạng thái pipeline. |
| `dbt_project/models/sources/sources.yml` | Cập nhật mô tả các cột metadata additive; không đổi business model của dbt. |

### Kiểm thử tự động

| File | Phạm vi |
|---|---|
| `mage_project/tests/test_amazon_delivery_contract.py` | Batch name động, hash ổn định/nhạy thay đổi, range động, reject kỹ thuật, duplicate key và counter reconciliation. |
| `mage_project/tests/test_sqlserver_upsert_integration.py` | Tạo database tạm an toàn, kiểm tra insert → unchanged → update, bảo toàn initial lineage, cập nhật latest lineage, rồi xóa database tạm. |

## Hành vi upsert sau thay đổi

Khóa so khớp là `Order_ID` sau chuẩn hóa trim/case-fold. Hash SHA-256 được tạo từ 15 thuộc tính raw còn lại với giá trị chưa business-clean.

| Trạng thái incoming | Hành động | Lineage |
|---|---|---|
| `Order_ID` chưa tồn tại | Insert | Ghi `load_batch_id`, `loaded_at` và đồng thời khởi tạo update lineage. |
| `Order_ID` tồn tại, hash giống | Không ghi lại dữ liệu | Tăng `rows_unchanged`; tránh write không cần thiết. |
| `Order_ID` tồn tại, hash khác | Update 15 thuộc tính raw và hash | Giữ nguyên `load_batch_id`/`loaded_at`; cập nhật các cột `updated_*`. |

## Các kịch bản dữ liệu cần trình bày khi demo

Phần này là **kịch bản báo cáo**, không phải yêu cầu sửa dữ liệu trong
`staging.raw_amazon_delivery`. Khi cần quay demo, phải sao chép CSV sang một file
test và sử dụng database tạm có prefix `AmazonDeliveryBI_MageTest_`; không sửa
file raw gốc và không chạy các tình huống giả lập vào staging đang dùng chung với
dbt.

### Phân biệt hai trạng thái bắt đầu

| Trạng thái trước lần chạy | Kết quả lần chạy đầu |
|---|---|
| Staging hoàn toàn rỗng | Mọi dòng hợp lệ là `rows_inserted`; chưa có `updated` hoặc `unchanged`. |
| Staging đã có dữ liệu legacy nhưng chưa có `row_hash` | Các dòng khớp `Order_ID` được `rows_updated` một lần để backfill hash và update metadata. Đây là tình huống đã xảy ra khi migration database hiện tại. |

Vì vậy, nhận xét “lần đầu dữ liệu được load toàn bộ” là đúng. Upsert thể hiện rõ
nhất từ lần chạy thứ hai hoặc khi file nguồn có order mới/order cũ bị sửa.

### Bộ dữ liệu mẫu dùng trong báo cáo

Giả sử file test ban đầu chỉ có ba order hợp lệ:

| `Order_ID` | `Agent_Rating` | `Delivery_Time` | Ý nghĩa |
|---|---:|---:|---|
| `ORDER_DEMO_001` | `4.5` | `30` | Dòng dùng để kiểm tra update. |
| `ORDER_DEMO_002` | `4.7` | `25` | Dòng giữ nguyên để kiểm tra unchanged. |
| `ORDER_DEMO_003` | `4.2` | `40` | Dòng giữ nguyên để kiểm tra unchanged. |

### Kịch bản 1 — initial insert

Chạy file test trên database tạm có staging rỗng:

```text
rows_read      = 3
rows_inserted  = 3
rows_updated   = 0
rows_unchanged = 0
rows_rejected  = 0
rows_loaded    = 3
```

Kết quả chứng minh lần chạy đầu tạo current state ban đầu.

### Kịch bản 2 — chạy lại nhưng dữ liệu không thay đổi

Chạy lại chính file của kịch bản 1. Ba `Order_ID` và ba hash đều đã tồn tại:

```text
rows_read      = 3
rows_inserted  = 0
rows_updated   = 0
rows_unchanged = 3
rows_rejected  = 0
rows_loaded    = 0
```

Kết quả chứng minh pipeline idempotent: batch audit mới vẫn được tạo nhưng không
ghi lại staging.

### Kịch bản 3 — sửa dữ liệu để kiểm tra update

Trong **bản sao CSV test**, giữ nguyên `Order_ID=ORDER_DEMO_001` và đổi:

```text
Agent_Rating: 4.5 → 4.9
```

Hai order còn lại không thay đổi. Kết quả mong đợi:

```text
rows_read      = 3
rows_inserted  = 0
rows_updated   = 1
rows_unchanged = 2
rows_rejected  = 0
rows_loaded    = 1
```

`ORDER_DEMO_001` nhận giá trị mới và `row_hash` mới. `load_batch_id`/`loaded_at`
ban đầu được giữ nguyên; `updated_load_batch_id`, `updated_at` và nguồn update
được chuyển sang batch mới.

### Kịch bản 4 — thêm order mới để kiểm tra insert

Trong bản sao CSV tiếp theo, giữ ba order hiện tại và thêm:

```text
Order_ID=ORDER_DEMO_004, Agent_Rating=4.8, Delivery_Time=22
```

Kết quả mong đợi:

```text
rows_read      = 4
rows_inserted  = 1
rows_updated   = 0
rows_unchanged = 3
rows_rejected  = 0
rows_loaded    = 1
```

Kết quả chứng minh pipeline nhận order mới mà không insert lại ba order cũ.

### Kịch bản 5 — đồng thời có insert, update và unchanged

Từ trạng thái có bốn order, thực hiện trên bản sao test:

- đổi `Delivery_Time` của `ORDER_DEMO_002` từ `25` thành `27`;
- thêm `ORDER_DEMO_005`;
- giữ nguyên ba order còn lại.

Kết quả mong đợi:

```text
rows_read      = 5
rows_inserted  = 1
rows_updated   = 1
rows_unchanged = 3
rows_rejected  = 0
rows_loaded    = 2
```

Đây là tình huống gần với một batch incremental thực tế nhất.

### Kịch bản 6 — dòng kỹ thuật không hợp lệ

Thêm vào bản sao test một dòng có `Order_ID` rỗng hoặc `Order_Date` không parse
được. Dòng đó không được đưa vào staging và được tính vào `rows_rejected`.

Ví dụ với năm dòng hợp lệ và một dòng lỗi:

```text
rows_read      = 6
rows_inserted + rows_updated + rows_unchanged = 5
rows_rejected  = 1
```

Audit luôn phải thỏa công thức:

```text
rows_read = rows_inserted + rows_updated + rows_unchanged + rows_rejected
```

### Kịch bản 7 — trùng `Order_ID` ngay trong cùng file incoming

Nếu một file test chứa hai dòng có cùng `Order_ID` sau trim/case-fold, pipeline
đánh dấu validation error và không upsert batch đó. Transaction bảo đảm không có
trạng thái nạp dở dang.

### Nguyên tắc không ảnh hưởng staging hiện tại

- Không chỉnh sửa `data/raw/amazon_delivery.csv` để tạo tình huống demo.
- Không chạy CSV đã chỉnh sửa vào database `AmazonDeliveryBI` đang phục vụ dbt.
- Chỉ mô tả các trường hợp trong báo cáo hoặc chạy integration test trên database
  tạm tự tạo/tự xóa.
- Nếu cần bằng chứng trực quan, chụp audit và staging trong database tạm trước khi
  test bị xóa; không sao chép dữ liệu giả sang staging thật.

## Bằng chứng kiểm thử

| Kiểm thử | Kết quả |
|---|---|
| Python compile | Thành công cho toàn bộ `mage_project`. |
| Unit + SQL Server integration | **7/7 test đạt**. |
| YAML parse | **4/4 file hợp lệ**. |
| SQL migration + validation | Thành công; staging có **43.739** dòng và **43.739** dòng có hash. |
| Chạy thật lần đầu sau migration | `rows_updated=43.739`, không insert/reject; backfill hash thành công. |
| Chạy lại cùng file | `rows_unchanged=43.739`, `rows_loaded=0`; chứng minh idempotent. |
| Database test tạm còn sót | **0**. |
| dbt regression | `dbt build` thành công; **PASS=67, WARN=0, ERROR=0, SKIP=0**. |
| Git whitespace validation | `git diff --check` thành công. |

## Tác động và giới hạn đã chốt

- Cấu trúc cũ của `staging.raw_amazon_delivery` được giữ nguyên theo hướng additive; dbt hiện tại tiếp tục đọc được.
- Nội dung một dòng staging có thể thay đổi khi cùng `Order_ID` nhận dữ liệu mới. Đây là hành vi đúng của current-state staging.
- Mage chỉ thực hiện technical validation. Các rule chuyển `null`/`unknown`, cảnh báo business quality và quyết định nạp DDS vẫn thuộc dbt.
- Thiết kế hiện tại không lưu mọi phiên bản trong staging. Raw history được giữ bằng file nguồn/checksum; nếu cần lịch sử bản ghi ở tương lai, triển khai bảng history riêng thay vì phá interface hiện tại.

## Lệnh nghiệm thu có thể chạy lại

```powershell
sqlcmd -S localhost -E -C -b -i .\sql\run_sql_skeleton.sql

$env:MSSQL_DRIVER='ODBC Driver 18 for SQL Server'
$env:MSSQL_SERVER='localhost'
$env:MSSQL_DATABASE='AmazonDeliveryBI'
$env:MSSQL_TRUSTED_CONNECTION='yes'
$env:RUN_SQLSERVER_INTEGRATION='1'
.\.venv\Scripts\python.exe -m unittest discover -s mage_project/tests -q

Set-Location .\dbt_project
..\.venv\Scripts\dbt.exe build --profiles-dir ..\..\tmp\demo_check_profiles
```
