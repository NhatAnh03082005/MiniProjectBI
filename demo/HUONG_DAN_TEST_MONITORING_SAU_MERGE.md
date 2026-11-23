# Test tay sau khi tích hợp ETL Monitoring

> Cập nhật: đã gộp staging/audit, audit.dbt_run và Monitoring vào `sql/run_sql_skeleton.sql` (database chính) và `sql/run_sql_skeleton_demo.sql` (Demo). Chọn đúng một file tổng hợp, chạy trong SSMS thay cho ba file Monitoring riêng. Không cần SQLCMD Mode. Fact/Dimension vẫn do dbt build trong pipeline tạo/cập nhật. Không reset dữ liệu.

> Đây là hướng dẫn cho DEMO. Đã bổ sung hỗ trợ database chính theo yêu cầu chủ dự án; xem HUONG_DAN_MONITORING_DATABASE_CHINH.md trong cùng thư mục. Các câu DEMO-only dưới đây mô tả phiên bản bàn giao ban đầu.

## Phạm vi bản tích hợp

- Giữ pipeline main 5 block, shared SQL/Windows auth, upsert Order_ID + row_hash, application lock, dbt runner và audit hiện có.
- Thêm hooks/COMMITTED export witness vào transaction của exporter main; không gọi đường runtime.export riêng của nhánh Monitoring.
- Runner dbt cũ gọi một process dbt duy nhất, truyền ticket/run/execution/attempt qua --vars; kiểm chứng manifest/run_results rồi kết thúc dbt, warehouse và parent Monitoring.
- Trang thứ 5 giữ thiết kế/measures của nhánh Monitoring, 4 bảng Monitoring dùng parameter kết nối DEMO; bỏ bộ lọc mặc định REAL-only/MAGE_ENGINE-only để không ẩn run demo hoặc run chưa có native engine ID.
- Bản tích hợp web Mage này hỗ trợ Monitoring trên AmazonDeliveryBI_Demo bằng cùng tài khoản sa/Windows với business connection; không dùng principal Monitoring-only để ghi staging. Các script/adapter PRIMARY và isolated TEST của nhánh gốc giữ riêng, không tự chạy hoặc mở rộng quyền.
- Không có ETL/DDL/Power BI refresh nào được agent thực thi khi merge. Kiểm tra tĩnh không thay thế E2E trên máy người dùng.

## 1. Triển khai SQL Monitoring một lần bằng SSMS

Kết nối `NHAT-ANH\SQLEXPRESS` với `sa`, chọn database demo. Nếu chưa có staging/audit thì chạy bootstrap demo trước (không tự xóa dữ liệu cũ).

Chạy 3 file theo đúng thứ tự, trực tiếp bằng SSMS, không cần SQLCMD mode:

1. `sql/monitoring/demo/01_monitoring_schema.sql`
2. `sql/monitoring/demo/02_logging_procedures.sql`
3. `sql/monitoring/demo/03_reporting_views.sql`

Chúng tạo các bảng, procedures, views trong schema monitoring và marker APPROVED_DEMO; không truncate/reset business data và không sửa schema audit.load_batch. Không chạy script PRIMARY/TEST hoặc 00_additive_alignment.sql để chuẩn bị DEMO này.

Nếu schema có sẵn nhưng khác contract, script sẽ báo lỗi để bạn kiểm tra; không xóa tự động. SQL cần version hỗ trợ CREATE OR ALTER, STRING_AGG như bản Monitoring gốc.

## 2. Khởi động web Mage với Monitoring

Dừng Mage cũ bằng Ctrl+C. Dùng terminal mới nếu trước đó đã chạy isolated TEST guard.

```powershell
Set-Location 'D:\BI\Mini Project\BI_AI_Project'
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\demo\start_etl_demo.ps1 `
  -Server 'NHAT-ANH\SQLEXPRESS' `
  -Database 'AmazonDeliveryBI_Demo' `
  -Authentication sql -User sa -Monitoring
```

Nhập mật khẩu khi được hỏi. Script bật AMAZON_MONITORING_ENABLED=1, chọn ETL_MONITORING_ENV=DEMO; dbt vẫn dùng cùng server/database/auth. Không truyền -Monitoring thì log Monitoring tắt và pipeline main vẫn chạy như trước; script chủ động tắt flag cũ thay vì ngầm thừa hưởng nó.

Mở http://localhost:6789, chọn pipeline incremental/full. Chạy **toàn pipeline trên web** để có Loader context, không chạy riêng block dbt với context đã terminal.

## 3. Các lần chạy thử

### A. Kiểm tra nhanh trên database đang có dữ liệu

Chạy incremental với runtime variable:

```json
{"source_file_path":"demo/etl_batches/05_rerun.csv"}
```

Nếu bạn đã hoàn tất 01–05 trước đó, kỳ vọng ingestion 8 read, 0 insert/update, 6 unchanged, 2 reject; dbt vẫn build, parent Monitoring kết thúc SUCCEEDED. Các run cũ trước khi bật Monitoring không được tự sao chép thành lịch sử Monitoring.

### B. File lỗi đơn giản

```json
{"source_file_path":"demo/etl_batches/06_bad_header.csv"}
```

Kỳ vọng parent FAILED ở validation, không chạy dbt, không ghi business DML. Log kỹ thuật phải còn thông báo sai header. Có thể thử thêm `07_duplicate_id.csv` hoặc đường dẫn không tồn tại để xem lỗi sớm ở source.

### C. Lỗi dbt và rerun

Đặt DBT_BUILD_TIMEOUT_SECONDS=1 trong terminal trước khi mở lại Mage; dùng batch rerun. Kỳ vọng ingestion có thể thành công, dbt/parent FAILED, giữ nguyên staging đã commit. Sau đó đặt lại 1800, mở lại Mage và rerun **toàn pipeline** để có context/attempt mới. Không reuse terminal context hoặc xóa audit để retry.

### D. Kiểm tra insert/update

Dùng batch có ID mới/thay đổi thực so với trạng thái hiện tại. Bộ 01–05 chỉ có số kỳ vọng ban đầu khi database rỗng và chạy đúng thứ tự. Chạy lại 04 sau 05 sẽ chủ yếu unchanged; không tự gọi đó là lỗi. Không chạy 01 rồi mong nó reset database, vì full hiện là upsert.

## 4. SELECT đối chiếu sau chạy

```sql
USE AmazonDeliveryBI_Demo;

SELECT TOP (20) execution_key, run_id, attempt_id, legacy_load_batch_id,
    source_file, overall_status, source_status, mage_status, dbt_status,
    warehouse_status, execution_origin, evidence_kind, processing_duration_seconds,
    error_message, warning_message
FROM monitoring.vw_etl_run_summary ORDER BY start_time DESC;

SELECT TOP (100) execution_key, step_key, status, native_status, resource_type,
    artifact_verified, duration_seconds
FROM monitoring.vw_etl_step_status ORDER BY start_time DESC;

SELECT TOP (30) execution_key, metric_scope, measurement_state,
    records_read, records_inserted, records_updated, records_unchanged,
    records_rejected, records_written, is_chart_eligible
FROM monitoring.vw_etl_record_metrics ORDER BY execution_key;

SELECT TOP (30) execution_key, step_key, severity, error_code, message
FROM monitoring.vw_etl_error_details ORDER BY occurred_at DESC;
```

- Succesful run cần đủ source/mage/dbt/warehouse SUCCEEDED, dbt nodes/tests có artifact thật và export metric is_chart_eligible=1.
- Rejection warning không đồng nghĩa run thất bại; Mage rejected khác dbt business rejected.
- IN_DOUBT nghĩa là chưa xác nhận được kết quả COMMIT; không tự retry DML. Đối chiếu cùng execution_key/legacy_load_batch_id và COMMITTED witness trước khi quyết định.
- Run lỗi sớm có thể không có legacy batch nhưng phải có parent Monitoring nếu kết nối/schema Monitoring đã sẵn sàng. Mất kết nối trước khi tạo parent không thể tự ghi được vào cùng database.

## 5. Mở dashboard

Mở `powerbi/project/AmazonDeliveryBI.pbip` bằng Power BI Desktop. Trong Transform Data → Edit Parameters:

- ETL Monitoring Server: `NHAT-ANH\SQLEXPRESS` (hoặc server trên máy bạn).
- ETL Monitoring Database: `AmazonDeliveryBI_Demo`.

Chọn Database Authentication và nhập sa/password trong Power BI nếu được hỏi. Không lưu credential vào source. Bốn query Monitoring kiểm tra database và marker APPROVED_DEMO; không âm thầm đọc PRIMARY.

Refresh rồi mở trang ETL Monitoring. Parameter mới chỉ áp dụng cho các bảng Monitoring; 4 trang nghiệp vụ giữ nguồn kết nối cũ, cần tự chọn cùng DDS nếu muốn đối chiếu nghiệp vụ Demo. Không coi Import tự refresh sau Mage.

Các bộ lọc REAL/origin cứng đã bỏ ở trang demo; có thể tự lọc pipeline/status/ngày. evidence_kind=TEST là đúng cho các run thật dùng dữ liệu demo, không phải lịch sử giả. Nếu origin chưa có Mage native ID thì vẫn hiển thị UNKNOWN, không tự bịa MAGE_ENGINE.

## 6. Giới hạn bàn giao

- Merge đã xử lý lỗi Git và ghép code; chưa xác nhận SQL deployment, DAX engine, refresh hoặc E2E.
- Các run/metrics đã terminal không được sửa lại tùy ý. Hỗ trợ test bằng rerun toàn pipeline; retry riêng một block đã terminal có thể bị contract chặn.
- STARTED/WAITING_DBT còn sau khi kill process cần đối soát, chưa có heartbeat/stale reconciler tự động.
- Khi Monitoring tắt, pipeline không có parent Monitoring mới. Đừng đánh giá dashboard từ các run chỉ có audit legacy.
- PRIMARY/test adapters gốc vẫn khóa server/môi trường của nhánh bạn ấy; bản tích hợp này không tuyên bố hỗ trợ production hoặc sửa toàn bộ script đó.
