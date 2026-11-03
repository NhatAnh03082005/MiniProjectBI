# Mage.ai team setup

## 1. Yêu cầu

- Python 3.11.
- SQL Server và SQL Server Management Studio (SSMS).
- Microsoft ODBC Driver 18 for SQL Server.
- Repository đầy đủ, đặc biệt là `data/`, `sql/` và `mage_project/`.

## 2. Tạo môi trường Python

Chạy từ root repository:

```powershell
py -3.11 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install mage-ai==0.9.80 pyodbc pandas
```

`.venv/` là môi trường cục bộ và không được commit.

## 3. Khởi tạo SQL skeleton

Trong SSMS, kết nối đúng SQL Server instance, mở `sql/run_sql_skeleton.sql` và chọn **Execute** một lần. Kiểm tra phần Messages và các result set validation ở cuối file.

## 4. Xác nhận Mage project

Mage project dùng trực tiếp thư mục `mage_project` trong repository. Không tạo junction, symlink hoặc thư mục trung gian.

```powershell
$ProjectRoot = (Resolve-Path ".").Path
$MageProject = Join-Path $ProjectRoot "mage_project"

Test-Path (Join-Path $MageProject "metadata.yaml")
Test-Path (Join-Path $MageProject "pipelines\test_sql_server_connection\metadata.yaml")
```

Hai lệnh kiểm tra phải trả về `True`.

## 5. Đặt biến môi trường

Các biến này chỉ có hiệu lực trong PowerShell hiện tại. Thay giá trị server bằng instance của người chạy.

```powershell
$env:MSSQL_SERVER = "localhost\SQLEXPRESS"
$env:MSSQL_DATABASE = "AmazonDeliveryBI"
$env:MSSQL_DRIVER = "ODBC Driver 18 for SQL Server"
$env:BI_PROJECT_ROOT = $ProjectRoot
$env:PYTHONUTF8 = "1"
$env:DEBUG = "0"
```

Không ghi password hoặc credential vào Python, YAML hay Git.

## 6. Khởi động và chạy pipeline

```powershell
Set-Location $ProjectRoot
mage start mage_project
```

`PYTHONUTF8=1` buộc Python dùng UTF-8 khi Mage đọc mã nguồn để gợi ý trong
giao diện. Trên Windows, nếu không đặt biến này, Mage có thể dùng `cp1252` và
báo `UnicodeDecodeError` với file Python chứa tiếng Việt. Đặt biến trước khi
khởi động Mage; nếu Mage đang chạy, dừng bằng `Ctrl+C` rồi khởi động lại.

Trong Mage UI, chạy theo thứ tự để kiểm tra full load trên staging trống:

1. `test_sql_server_connection`.
2. `amazon_delivery_full_load`.

Không chạy trực tiếp `mage_project/data_loaders/full_load_amazon_delivery.py`. File này là Mage block và phụ thuộc decorator/runtime của Mage.

Kết quả mong đợi:

- Lần đầu: `SUCCEEDED`, đọc và nạp 43.739 dòng.
- Chạy lại cùng file/checksum: `SKIPPED`, `rows_loaded = 0`, tổng số dòng staging không tăng.

### Kiểm tra cách nạp theo ba batch lịch sử

Chỉ thực hiện trên **staging trống riêng**; không chạy tiếp sau full load vì cùng
`Order_ID` sẽ bị trùng. Chạy `test_sql_server_connection`, rồi chạy pipeline
`amazon_delivery_incremental_load` ba lần. Mỗi lần nhập runtime variable
`batch_name` trong Mage UI, không dùng giá trị mặc định:

| Lần chạy | `batch_name` | Dòng nạp | Tổng dòng staging |
|---|---|---:|---:|
| 1 | `INITIAL_FULL` | 6.982 | 6.982 |
| 2 | `INCREMENTAL_01` | 30.658 | 37.640 |
| 3 | `INCREMENTAL_02` | 6.099 | 43.739 |

Chạy lại `INCREMENTAL_02` với cùng CSV phải trả `SKIPPED`, `rows_loaded = 0`
và tổng staging vẫn là 43.739. Pipeline này mô phỏng ba batch từ cùng một CSV;
chưa tự phát hiện file mới theo lịch.

Đối soát trong SSMS sau mỗi lần chạy:

```sql
USE AmazonDeliveryBI;
SELECT COUNT_BIG(*) AS staging_rows
FROM staging.raw_amazon_delivery;

SELECT batch_name, status, rows_read, rows_loaded, source_file_checksum,
       started_at, finished_at
FROM audit.load_batch
ORDER BY started_at, load_batch_id;
```

Loader đọc một snapshot byte của CSV, tính SHA-256 và parse DataFrame từ cùng
snapshot đó. Exporter dùng checksum và tên file do loader chuyển qua các block;
không mở lại file nguồn. Metadata pipeline không chứa đường dẫn `variables_dir`
của máy cá nhân. Mỗi lần chạy incremental phải truyền `batch_name` tường minh.

## 7. Quy tắc commit

Nên commit:

- `mage_project/metadata.yaml`.
- `mage_project/data_loaders/*.py`.
- `mage_project/pipelines/*/metadata.yaml` và `__init__.py`.
- `MAGE_TEAM_SETUP.md` và các tài liệu liên quan.

Không commit:

- `.venv/`, `__pycache__/`, `*.pyc`, `.ipynb_checkpoints/`.
- `mage_project/.mage_data/`, `mage_project/.ssh_tunnel/`, log và output tạm.
- Junction, symlink, thư mục trung gian hoặc đường dẫn cá nhân.
- `.env`, password, connection string chứa credential.

## 8. Checklist trước khi bàn giao cho dbt

- [ ] `sql/run_sql_skeleton.sql` chạy thành công trên đúng instance.
- [ ] Pipeline connection xác nhận database, schema và hai bảng tồn tại.
- [ ] Full Load trả `SUCCEEDED` và staging có 43.739 dòng.
- [ ] Chạy lại trả `SKIPPED` và không tăng row count.
- [ ] `audit.load_batch` có checksum SHA-256, status và row counts đúng.
- [ ] Nếu demo incremental trên staging riêng: ba batch cộng thành 43.739 dòng;
      chạy lại batch cuối trả `SKIPPED` và không tăng row count.
- [ ] Raw có đủ 16 cột nguồn cùng bốn trường lineage.
- [ ] Không có credential hoặc đường dẫn máy cá nhân trong file commit.
- [ ] dbt source trỏ tới `AmazonDeliveryBI.staging.raw_amazon_delivery`.
