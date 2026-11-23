# Dùng ETL và dashboard trên AmazonDeliveryBI

> Cập nhật: đã gộp staging/audit, audit.dbt_run và Monitoring vào `sql/run_sql_skeleton.sql` (database chính) và `sql/run_sql_skeleton_demo.sql` (Demo). Chọn đúng một file tổng hợp, chạy trong SSMS thay cho ba file Monitoring riêng. Không cần SQLCMD Mode. Fact/Dimension vẫn do dbt build trong pipeline tạo/cập nhật. Không reset dữ liệu.

Đã bổ sung code hỗ trợ PRIMARY rõ ràng theo lựa chọn của chủ dự án. Những bước dưới đây do bạn chạy tay; agent chưa chạy SQL/ETL hoặc refresh Power BI.

Mục tiêu cùng một nguồn:

```text
Web Mage → staging/audit trong AmazonDeliveryBI → dbt DDS trong AmazonDeliveryBI
        → monitoring trong AmazonDeliveryBI → Power BI Refresh
```

## 1. Dừng Mage cũ

Ctrl+C tại terminal đang chạy Mage Demo. Không dùng terminal đã bật isolated TEST guard; mở terminal mới nếu cần. Dữ liệu và log Demo giữ nguyên, không chuyển thành lịch sử chạy database chính.

## 2. Chạy SQL Monitoring cho database chính bằng SSMS

Kết nối `NHAT-ANH\SQLEXPRESS`, SQL Authentication `sa`. Chạy theo thứ tự:

1. `sql/monitoring/main/01_monitoring_schema.sql`
2. `sql/monitoring/main/02_logging_procedures.sql`
3. `sql/monitoring/main/03_reporting_views.sql`

Đây là bộ **main**, không phải bộ `demo/` và cũng không phải bộ `primary/` khóa server của thành viên khác. Các file này chạy trực tiếp trong SSMS, có USE AmazonDeliveryBI; không cần SQLCMD mode. Chúng tạo schema/tables/procedures/views Monitoring và marker APPROVED_PRIMARY, không xóa dữ liệu nghiệp vụ, không cấp thêm quyền/login và không sao chép lịch sử Demo.

Nếu schema Monitoring đã có mà khác contract hoặc marker, script báo lỗi; không tự xóa hoặc đổi marker để bỏ qua. Database chính cần sẵn staging/audit/DDS từ dự án; không reset database để tạo log.

Kiểm tra sau khi 3 script chạy thành công:

```sql
USE AmazonDeliveryBI;
SELECT DB_NAME() AS database_name;
SELECT name, CONVERT(nvarchar(128), value) AS environment
FROM sys.extended_properties
WHERE class = 0 AND name = 'ETLMonitoring.Environment';
SELECT name FROM sys.views WHERE schema_id = SCHEMA_ID('monitoring');
```

Kỳ vọng database_name=AmazonDeliveryBI, marker=APPROVED_PRIMARY và 4 reporting views. Các bảng log có thể còn rỗng cho đến khi chạy pipeline với Monitoring bật.

## 3. Khởi động Mage + dbt + Monitoring trên database chính

```powershell
Set-Location 'D:\BI\Mini Project\BI_AI_Project'

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\demo\start_etl_demo.ps1 `
  -Server 'NHAT-ANH\SQLEXPRESS' `
  -Database 'AmazonDeliveryBI' `
  -Authentication sql -User sa -Monitoring
```

Nhập mật khẩu sa khi được hỏi. Tên script còn chữ demo nhưng tham số Database chọn đích; code đã hỗ trợ cả hai đích rõ ràng. Script đặt PRIMARY/integrated/approval flags tương ứng; dùng cùng MSSQL_* và sa cho business data và Monitoring. Không cần chạy Enter-Monitoring.ps1 của bộ PRIMARY legacy, không cần impersonation principal của máy bạn ấy, không mở thêm terminal chạy dbt.

Guard vẫn kiểm tra database và marker; đặt biến môi trường đơn thuần không tự triển khai SQL. Nếu quên -Monitoring, pipeline main chạy nhưng không ghi parent Monitoring mới.

## 4. Chạy một lần bình thường bằng web Mage

Mở http://localhost:6789. Chọn pipeline full `amazon_delivery_full_load`, chạy toàn pipeline với runtime variable:

```json
{"source_file_path":"data/raw/amazon_delivery.csv"}
```

Lần đầu trên database chính nên dùng CSV gốc, không dùng batch mixed mô phỏng để tránh thêm đơn seminar hoặc sửa thời lượng nghiệp vụ bằng dữ liệu demo. Full ở dự án là upsert, không phải truncate. Nếu dữ liệu chính đã khớp CSV thì đa số/toàn bộ dòng hợp lệ là unchanged; nếu khác thì có thể insert/update theo nguồn. Không áp số kỳ vọng của database Demo cho database chính.

Chờ đủ Loader → Validate → Export → Verify → dbt. Runner vẫn build DDS và tests kể cả không có insert/update. Chỉ refresh BI/AI sau khi lần chạy hoàn tất thành công.

Có thể chạy lại đúng file bằng incremental để chứng minh unchanged. Muốn minh họa lỗi đơn giản, dùng `demo/etl_batches/06_bad_header.csv`: fail validation, không ghi business DML hoặc chạy dbt; log thất bại thuộc database chính vì pipeline đã chọn database chính. Những batch thêm/sửa dữ liệu demo khác vẫn nên chạy ở Demo.

## 5. Kiểm tra log trên đúng database

```sql
USE AmazonDeliveryBI;
SELECT TOP (10) source_file, overall_status, source_status, mage_status,
    dbt_status, warehouse_status, evidence_kind, execution_origin,
    legacy_load_batch_id, processing_duration_seconds, error_message
FROM monitoring.vw_etl_run_summary
ORDER BY start_time DESC;
```

Lần thành công cần source/mage/dbt/warehouse SUCCEEDED và parent SUCCEEDED. evidence_kind=REAL biểu thị lần chạy quan sát trên PRIMARY; không đồng nghĩa nguồn là dữ liệu vận hành Amazon chính thức. Lần lỗi header cần parent FAILED, dbt/warehouse SKIPPED hoặc chưa chạy theo contract.

Chưa có log trước khi bật Monitoring là bình thường. Không chép các run Demo sang main để làm đầy dashboard. Nếu IN_DOUBT thì đối soát commit witness trước khi rerun; không tự reset audit.

## 6. Cấu hình Power BI

Mở `powerbi/project/AmazonDeliveryBI.pbip` đã merge bằng Power BI Desktop, không mở một PBIX cũ chưa chứa các query/parameter mới.

Transform Data → Edit Parameters:

| Parameter | Giá trị |
|---|---|
| ETL Monitoring Server | NHAT-ANH\SQLEXPRESS |
| ETL Monitoring Database | AmazonDeliveryBI |

Code mặc định parameter Monitoring Database đã chuyển sang AmazonDeliveryBI. Bốn query Monitoring chấp nhận đúng cặp PRIMARY/APPROVED_PRIMARY hoặc DEMO/APPROVED_DEMO, không tự fallback sang đích khác.

Trong Data source settings, chọn credentials Database/SQL Authentication với sa nếu được hỏi, rồi Close & Apply và Refresh. Không nhúng mật khẩu vào Power Query/source.

Các bảng Fact/Dimension của 4 trang nghiệp vụ giữ cấu hình cũ. Kiểm tra chúng cũng trỏ cùng instance/database chính: localhost\SQLEXPRESS có thể là alias của NHAT-ANH\SQLEXPRESS trên cùng máy, nhưng nếu chuyển máy thì phải đổi source tương ứng. Parameter mới chỉ điều khiển 4 query Monitoring, không tự đổi mọi business query.

Chọn trang ETL Monitoring. Nếu chưa thấy run: kiểm tra đúng PBIP, đúng parameter, Refresh, kết quả SELECT ở bước 5 và bộ lọc ngày/status/pipeline. Import không tự cập nhật sau Mage.

Sau khi kiểm tra hoạt động, Save/Save As thành PBIX bàn giao. Metadata sửa trong PBIP không tự cập nhật các PBIX cũ trên đĩa.

## 7. Trạng thái bàn giao

Code/config và SQL main đã chuẩn bị; guard và cú pháp được kiểm tra không kết nối SQL. Chưa triển khai schema main, chưa chạy ETL/main hoặc kiểm tra DAX/Refresh trên database chính. Thay đổi chưa push GitHub trong bước hướng dẫn này.
