# Mage.ai team setup

## 1. Yêu cầu

- Python 3.11.
- SQL Server và SQL Server Management Studio (SSMS).
- Microsoft ODBC Driver 18 for SQL Server.
- Repository đầy đủ, đặc biệt là `01_data/`, `02_sql/` và `03_mage/`.

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

Trong SSMS, kết nối đúng SQL Server instance, mở `02_sql/run_sql_skeleton.sql` và chọn **Execute** một lần. Kiểm tra phần Messages và các result set validation ở cuối file.

## 4. Tạo junction cục bộ cho Mage

Mage nên chạy qua một junction ngắn trỏ vào `03_mage`. Junction chỉ tồn tại trên máy cá nhân và không được đưa vào repository.

```powershell
$ProjectRoot = (Resolve-Path "D:\duong-dan-mau\BI_AI_Project").Path
$MageAliasParent = Join-Path $env:USERPROFILE "MageProjects"
$MageAlias = Join-Path $MageAliasParent "MageAmazonDelivery"
$MageTarget = Join-Path $ProjectRoot "03_mage"

New-Item -ItemType Directory -Force -Path $MageAliasParent | Out-Null
New-Item -ItemType Junction -Path $MageAlias -Target $MageTarget
```

Nếu `$MageAlias` đã tồn tại, phải kiểm tra target trước; không xóa hoặc ghi đè junction không rõ nguồn gốc.

## 5. Đặt biến môi trường

Các biến này chỉ có hiệu lực trong PowerShell hiện tại. Thay giá trị server bằng instance của người chạy.

```powershell
$env:MSSQL_SERVER = "localhost\SQLEXPRESS"
$env:MSSQL_DATABASE = "AmazonDeliveryBI"
$env:MSSQL_DRIVER = "ODBC Driver 18 for SQL Server"
$env:BI_PROJECT_ROOT = $ProjectRoot
```

Không ghi password hoặc credential vào Python, YAML hay Git.

## 6. Khởi động và chạy pipeline

```powershell
mage start $MageAlias
```

Trong Mage UI, chạy theo thứ tự:

1. `test_sql_server_connection`.
2. `amazon_delivery_full_load`.

Không chạy trực tiếp `03_mage/data_loaders/full_load_amazon_delivery.py`. File này là Mage block và phụ thuộc decorator/runtime của Mage.

Kết quả mong đợi:

- Lần đầu: `SUCCEEDED`, đọc và nạp 43.739 dòng.
- Chạy lại cùng file/checksum: `SKIPPED`, `rows_loaded = 0`, tổng số dòng staging không tăng.

## 7. Quy tắc commit

Nên commit:

- `03_mage/metadata.yaml`.
- `03_mage/data_loaders/*.py`.
- `03_mage/pipelines/*/metadata.yaml` và `__init__.py`.
- `MAGE_TEAM_SETUP.md` và các tài liệu liên quan.

Không commit:

- `.venv/`, `__pycache__/`, `*.pyc`, `.ipynb_checkpoints/`.
- `03_mage/.mage_data/`, `03_mage/.ssh_tunnel/`, log và output tạm.
- Junction `MageAmazonDelivery` hoặc đường dẫn cá nhân.
- `.env`, password, connection string chứa credential.

## 8. Checklist trước khi bàn giao cho dbt

- [ ] `02_sql/run_sql_skeleton.sql` chạy thành công trên đúng instance.
- [ ] Pipeline connection xác nhận database, schema và hai bảng tồn tại.
- [ ] Full Load trả `SUCCEEDED` và staging có 43.739 dòng.
- [ ] Chạy lại trả `SKIPPED` và không tăng row count.
- [ ] `audit.load_batch` có checksum SHA-256, status và row counts đúng.
- [ ] Raw có đủ 16 cột nguồn cùng bốn trường lineage.
- [ ] Không có credential hoặc đường dẫn máy cá nhân trong file commit.
- [ ] dbt source trỏ tới `AmazonDeliveryBI.staging.raw_amazon_delivery`.
