# Mage → dbt: pipeline hoàn chỉnh và batch demo

## 1. Đã nối những gì?

Cả `amazon_delivery_full_load` và `amazon_delivery_incremental_load` có 5 block:

```text
Loader → Validate → Export/upsert → Verify staging → build_amazon_delivery_dds
                                                     ├─ dbt build (models + tests)
                                                     └─ đối soát staging/Fact/rejection
```

Không cần chạy dbt bằng tay sau pipeline. Lịch/trigger và video do trưởng nhóm thực hiện. Không tự refresh Power BI hoặc gọi AI trong luồng này.

Đây là mã và dữ liệu đã chuẩn bị để bạn test tay; chưa chạy ETL/dbt vào database và chưa khẳng định nghiệm thu end-to-end.

## 2. Chuẩn bị môi trường

Thực hiện từ thư mục gốc repo `D:\BI\Mini Project\BI_AI_Project`.

1. SQL Server/SQL Express và ODBC Driver phải sẵn sàng.
2. Dùng **database demo riêng** `AmazonDeliveryBI_Demo`. Nếu chưa có, tự chạy `sql/run_sql_skeleton_demo.sql` trong SSMS. Script nối mới không tự reset/xóa database.
3. Tài khoản Windows chạy Mage cần quyền đọc/ghi staging/audit và tạo/cập nhật các model dbt trong database demo.
4. Python dbt mặc định là `.venv/Scripts/python.exe`. Nếu dùng môi trường khác, đặt `DBT_PYTHON_EXECUTABLE` thành đường dẫn tuyệt đối tới Python của môi trường đã cài `dbt-core` và `dbt-sqlserver` (xem `dbt_project/requirements.txt`).
5. Khi cần cài thư viện, dùng đúng Python của môi trường dbt, không cài lẫn vào Python hệ thống.

Khởi động Mage:

```powershell
.\demo\start_etl_demo.ps1
```

Hoặc chọn SQL instance khác:

```powershell
.\demo\start_etl_demo.ps1 -Server 'localhost\SQLEXPRESS' -Database AmazonDeliveryBI_Demo
```

Script chỉ thiết lập biến môi trường và mở Mage, không nạp dữ liệu. Nếu đã mở Mage bằng cửa sổ khác, dừng instance cũ trước để các biến mới có hiệu lực.

Runner tạo profile dbt riêng cho mỗi attempt, dùng cơ chế xác thực của Mage (SQL hoặc Windows), cùng server/driver/database của Mage; không sửa hoặc đọc `dbt_project/profiles.yml` cá nhân. `DBT_SQLSERVER_DATABASE` cũng được đặt cho process con để source dbt đọc đúng database demo. Schema đích giữ `dw`, threads=1.

Biến môi trường dùng thêm:

| Biến | Giá trị/mục đích |
|---|---|
| `BI_PROJECT_ROOT` | Đường dẫn tuyệt đối tới repo |
| `MSSQL_SERVER`, `MSSQL_DATABASE`, `MSSQL_DRIVER` | Kết nối chung Mage/dbt, cơ chế xác thực của Mage (SQL hoặc Windows) |
| `DBT_PYTHON_EXECUTABLE` | Tùy chọn, Python đã cài dbt; mặc định `.venv` của repo |
| `DBT_BUILD_TIMEOUT_SECONDS` | Timeout cho process dbt, mặc định 1800 giây |

## 3. Bộ batch đã chuẩn bị

Các file ở `demo/etl_batches/`. CSV gốc được giữ nguyên. Có thể tái tạo file bằng:

```powershell
.\.venv\Scripts\python.exe .\demo\prepare_etl_batches.py
```

Lệnh này chỉ tạo file và tính kết quả ingestion mong đợi, không kết nối SQL hoặc chạy pipeline.

**Điều kiện để số liệu dưới đúng:** staging database demo ban đầu rỗng, chạy 01 → 05 một lượt theo thứ tự. Full load hiện là upsert, không có nghĩa truncate/reset; không chạy baseline lên database đã đầy rồi mong số dòng tăng như bảng.

| Thứ tự | File | Pipeline | Read | Insert | Update | Unchanged | Reject Mage | Tổng staging sau run |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | `01_baseline.csv` | Full | 8058 | 8058 | 0 | 0 | 0 | 8058 |
| 2 | `02_incremental.csv` | Incremental | 19409 | 19409 | 0 | 0 | 0 | 27467 |
| 3 | `03_incremental.csv` | Incremental | 16272 | 16272 | 0 | 0 | 0 | 43739 |
| 4 | `04_mixed.csv` | Incremental | 8 | 2 | 2 | 2 | 2 | 43741 |
| 5 | `05_rerun.csv` | Incremental | 8 | 0 | 0 | 6 | 2 | 43741 |

Ba file đầu chia dataset theo ngày: đến 01/03/2022, 02–20/03/2022, sau 20/03/2022. Tất cả đều là dữ liệu gốc.

`04_mixed.csv` và `05_rerun.csv` có nội dung giống hệt nhau, gồm:

- 2 đơn mô phỏng mới: `seminar3_new_001`, `seminar3_new_002`.
- 2 đơn gốc đổi `Delivery_Time`; ID và giá trị mới nằm trong `expected_results.json`.
- 2 đơn gốc giữ nguyên.
- 1 dòng thiếu ID và 1 dòng ngày không hợp lệ: bị loại ở Mage, không xuống staging.

Ngày của đơn mô phỏng vẫn trong lịch Dimension năm 2022. Không dùng ngày tương lai gây Unknown Date không cần thiết.

**Rerun vẫn reject 2 dòng lỗi**; chỉ 6 dòng hợp lệ thành unchanged. Không kỳ vọng cả 8 dòng là unchanged.

`expected_results.json` ghi checksum nguồn/từng batch và kết quả dự kiến, không phải biên bản chạy SQL. Reject ở dbt là tầng khác và có thể xảy ra trên các dòng gốc; không lấy `Reject Mage` làm tổng rejection DDS.

## 4. Nhập biến và chạy trong Mage

Mở pipeline full, chạy với runtime variable:

```json
{"source_file_path": "demo/etl_batches/01_baseline.csv"}
```

Các lần sau mở incremental, đổi đường dẫn lần lượt:

```json
{"source_file_path": "demo/etl_batches/02_incremental.csv"}
```

Tiếp tục với 03, 04, 05. Không truyền batch_name. Chạy **toàn pipeline**, không chỉ Execute một block trong editor. Phải nhìn thấy block thứ 5 `build_amazon_delivery_dds` chạy xong.

Hai pipeline không còn gán cứng đường dẫn demo cá nhân. Nếu không truyền `source_file_path`, loader đọc toàn bộ `data/raw/amazon_delivery.csv`; khi đó không dùng bảng kỳ vọng của bộ demo chia batch.

## 5. Đầu ra và trạng thái

Block cuối trả một DataFrame gồm:

- `load_batch_id`, `batch_name`, `batch_type`, `source_file_name`.
- Các counter ingestion, `verified`.
- `ingestion_status`, `dbt_status`, `etl_status`.
- `dbt_attempt_id`, `dbt_log_directory`.
- Thống kê tests pass/warn/fail/error/skipped.
- `staging_rows`, `fact_rows`, `dbt_rejected_distinct_rows` tại lúc đối soát.

Chỉ có `etl_status=SUCCEEDED` khi ingestion được Verify, dbt exit code 0, artifact không có node fail/error và:

```text
staging_rows = fact_rows + dbt_rejected_distinct_rows
```

dbt WARN do rejection có chủ đích không tự biến thành FAILED. Không đếm error records như distinct rejected rows.

### Audit SQL

- `audit.load_batch`: giữ trạng thái/counters **ingestion**, không đổi thành FAILED chỉ vì dbt lỗi.
- `audit.dbt_run`: một dòng mỗi attempt của block dbt, liên kết `load_batch_id`, lưu trạng thái, thời gian, exit code, thư mục log và JSON snapshot `result_summary`.
- Bảng mới được runner tạo nếu chưa có, bằng `sql/audit/02_create_dbt_run.sql`. Nếu tài khoản Mage không có quyền CREATE TABLE, người quản lý DB chạy file này trước trong đúng database demo.
- Không có dòng dbt cho batch dừng ở loader/validate/export/verify; người làm dashboard phải hiển thị chưa chạy/chưa ghi nhận, không suy ra dbt thành công.
- Lỗi trước exporter như tệp không tồn tại được Mage báo thất bại nhưng cơ chế ingestion hiện tại có thể chưa có dòng `audit.load_batch`. Không coi bảng mới là audit bao phủ mọi run từ lúc trigger.
- Xem `demo/inspect_etl_results.sql` để đối chiếu. File chỉ SELECT, không xóa dữ liệu. Cần có bảng audit và DDS trước khi chạy toàn bộ file.

### Log cục bộ

```text
logs/etl/<load_batch_id>/<dbt_attempt_id>/
  summary.json
  dbt_stdout.log
  profile/profiles.yml
  dbt_logs/
  target/run_results.json
  target/manifest.json
```

Mỗi attempt có thư mục riêng, tránh đọc nhầm artifact thành công cũ. `logs/` được Git ignore. Profile dùng cơ chế xác thực của Mage (SQL hoặc Windows), không chứa mật khẩu. Sao chép bằng chứng đã kiểm tra vào thư mục evidence nếu cần bàn giao.

## 6. Xử lý lỗi và rerun

| Tình huống | Hành vi |
|---|---|
| Sai header: `06_bad_header.csv` | Export ghi ingestion FAILED rồi raise; dbt không chạy |
| Trùng ID cùng batch: `07_duplicate_id.csv` | Cả batch thất bại; không chọn tùy tiện một dòng; dbt không chạy |
| Không tồn tại tệp | Loader raise, Mage báo lỗi; dbt không chạy |
| Dòng thiếu ID/ngày sai trong file đúng header | Reject dòng đó; dòng hợp lệ tiếp tục; dbt vẫn chạy |
| Thiếu thư viện dbt, timeout, dbt exit code khác 0 | Block cuối raise; pipeline FAILED; xem dbt audit/log |
| Đối soát DDS sai | Block cuối FAILED; không tuyên bố ETL thành công |
| Đang có ingestion/dbt giữ khóa | Lần ghi mới thất bại rõ ràng; chạy lại sau, không tự lặp vô hạn |

Để chạy các file lỗi dùng incremental với đúng `source_file_path`. Muốn mô phỏng timeout dbt, có thể dừng Mage, đặt `$env:DBT_BUILD_TIMEOUT_SECONDS='1'`, khởi động lại và chạy batch; sau đó khôi phục 1800 và khởi động lại trước khi rerun.

Sau lỗi dbt:

1. Sửa cấu hình/nguyên nhân, cập nhật môi trường và khởi động lại Mage nếu cần.
2. Chạy lại **toàn pipeline với cùng file**. Loader sinh batch mới.
3. Các dòng staging đã commit thường thành unchanged; không insert trùng. Reject kỹ thuật được đánh giá lại.
4. dbt build lại toàn DDS và tests; không bỏ qua dbt chỉ vì `rows_loaded=0`.
5. Lần lỗi cũ vẫn còn; lần mới có ID/attempt/artifact riêng.

Không tự truncate staging hoặc xóa audit để chữa lỗi. dbt có thể đã dựng một số bảng trước khi thất bại; không cam kết rollback toàn bộ DDS. Chạy lại thành công mới xác nhận snapshot DDS hoàn chỉnh, và chỉ refresh Power BI/AI sau đó.

## 7. Khi lập lịch

Trưởng nhóm chọn một trong hai pipeline và truyền đúng `source_file_path`. Không tạo trigger trong phần thay đổi này.

- Các CSV đã sinh không tự được phát hành luân phiên. Muốn demo tuần tự phải đổi runtime variable theo từng run hoặc thiết kế bước nhận batch riêng.
- Chạy cùng file theo lịch sau khi thành công sẽ cho unchanged, đó là kết quả hợp lệ.
- Không chạy full/incremental chồng nhau; chỉ giữ một lịch ghi vào cùng DB.
- Export và dbt dùng cùng SQL application lock để tránh staging thay đổi trong lúc dbt build. Khóa không thay thế điều phối tuần tự toàn pipeline: vẫn có khoảng giữa các block, nên không hứa dữ liệu là snapshot riêng cho từng run nếu cố chạy nhiều pipeline chồng nhau.
- Không chạy dbt thủ công hoặc sửa staging bằng SSMS đồng thời với pipeline vì các thao tác đó có thể không dùng khóa.

## 8. Checklist bạn tự nghiệm thu

- [ ] Cả full/incremental có block dbt cuối, cùng DB với Mage.
- [ ] 01–05 có counters đúng theo điều kiện ban đầu.
- [ ] 06/07 thất bại và không chạy dbt.
- [ ] Rerun không tạo trùng; dbt vẫn chạy khi toàn unchanged.
- [ ] Có audit dbt, artifact riêng và kết quả đối soát.
- [ ] dbt lỗi không báo toàn ETL thành công.
- [ ] Refresh Power BI sau khi ETL thành công; không coi Import tự refresh.

Không có kết quả test runtime/database được tạo sẵn trong bàn giao này; bạn điền kết quả thật sau khi test tay.


## Cập nhật SQL Authentication

Script khởi động mặc định dùng SQL Authentication với user `sa`, hỏi mật khẩu bằng Read-Host -AsSecureString. Mage và dbt dùng chung MSSQL_AUTHENTICATION=sql, MSSQL_USER, MSSQL_PASSWORD. Profile sinh ra chỉ chứa tham chiếu env_var cho user/password, không lưu mật khẩu. Muốn dùng Windows chọn -Authentication windows.
