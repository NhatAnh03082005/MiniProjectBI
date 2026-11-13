# Mage team setup

## Yêu cầu

- Python 3.11 và môi trường `.venv`.
- SQL Server, `sqlcmd` hoặc SSMS.
- Microsoft ODBC Driver 17/18.
- Repository đầy đủ gồm `data`, `sql`, `mage_project`.

## SQL migration

Từ thư mục `sql`, chọn đúng database cần triển khai:

```powershell
# Database chính: AmazonDeliveryBI
sqlcmd -S localhost -E -C -b -i run_sql_skeleton.sql

# Database demo: AmazonDeliveryBI_Demo
sqlcmd -S localhost -E -C -b -i run_sql_skeleton_demo.sql
```

Nếu dùng SSMS, mở đúng một file tổng rồi Execute; không cần SQLCMD Mode.
Script giữ dữ liệu hiện có, bổ sung hash/update metadata và action counters.

## Môi trường Mage

Từ root repository:

```powershell
$ProjectRoot = (Resolve-Path '.').Path
$env:MSSQL_SERVER = 'localhost\SQLEXPRESS'
$env:MSSQL_DATABASE = 'AmazonDeliveryBI'
$env:MSSQL_DRIVER = 'ODBC Driver 18 for SQL Server'
$env:BI_PROJECT_ROOT = $ProjectRoot
$env:PYTHONUTF8 = '1'

& '.\.venv\Scripts\Activate.ps1'
mage start mage_project
```

Không lưu credential trong Python, YAML hoặc Git.

## Chạy pipeline

1. Chạy `test_sql_server_connection`.
2. Chạy `amazon_delivery_full_load` trên staging mới, hoặc
   `amazon_delivery_incremental_load` cho các lần ingest tiếp theo.

Không nhập `batch_name`; loader sinh tên động. Runtime variable tùy chọn
`source_file_path` trỏ đến file mới, theo đường dẫn tuyệt đối hoặc tương đối
từ project root.

Kết quả mong đợi khi chạy snapshot baseline:

- Lần đầu trên staging trống: 43.739 insert.
- Lần chạy đầu sau migration bảng cũ chưa có hash: 43.739 update để backfill
  hash, không tăng row count.
- Chạy lại cùng file: 43.739 unchanged, 0 insert, 0 update.
- File có ID mới: insert.
- File có ID cũ nhưng thuộc tính raw đổi: update.

Đối soát:

```sql
SELECT COUNT_BIG(*) AS staging_rows
FROM staging.raw_amazon_delivery;

SELECT batch_name, status, rows_read, rows_inserted, rows_updated,
       rows_unchanged, rows_rejected, rows_loaded, source_file_checksum,
       started_at, finished_at
FROM audit.load_batch
ORDER BY started_at DESC;
```

## Test

```powershell
$env:RUN_SQLSERVER_INTEGRATION = '1'
Push-Location mage_project
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
Pop-Location
```

Integration test tạo và xóa một database tạm riêng, không thay đổi database
phát triển.

## Checklist bàn giao dbt

- [ ] SQL migration và validation pass.
- [ ] 16 cột raw/các cột lineage cũ không đổi tên hoặc kiểu.
- [ ] Mọi dòng current-state có `row_hash`.
- [ ] Rerun cùng file chỉ tạo unchanged.
- [ ] Read = insert + update + unchanged + rejected.
- [ ] Loaded = insert + update.
- [ ] `Order_ID` duy nhất sau trim/case-fold.
- [ ] dbt source vẫn đọc `staging.raw_amazon_delivery`.
- [ ] Không có credential hoặc đường dẫn cá nhân trong commit.
