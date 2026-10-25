# SQL Server skeleton

## 1. Tổng quan

Thư mục này chứa SQL bootstrap cho database `AmazonDeliveryBI`. Phiên bản trước đã được nhóm chạy trên SQL Server; phiên bản hiện tại đã bổ sung contract incremental và mới được kiểm tra tĩnh, vì vậy phải được thực thi và xác nhận lại trên database kiểm thử sạch.

| Schema | Vai trò |
|---|---|
| `audit` | Theo dõi batch ingest, file nguồn, checksum, trạng thái, thời gian, số dòng và lỗi. |
| `staging` | Tiếp nhận dữ liệu nguồn dạng chuỗi và giữ lineage trước khi dbt chuẩn hóa. |
| `dw` | Dành cho năm Dimension và một Fact ở giai đoạn dbt/DWH sau; skeleton chưa tạo các bảng này. |

Hai bảng DDL hiện có là `audit.load_batch` và `staging.raw_amazon_delivery`. Bảng có thể chưa chứa dữ liệu; row count bằng `0` là hợp lệ trước khi Mage chạy. Đây chưa phải toàn bộ Data Warehouse; phần SQL này chỉ bootstrap audit/raw staging, còn Mage và dbt nằm trong các thư mục riêng của repository.

SQL thực tế là nguồn sự thật chính cho kiểu dữ liệu, nullability, khóa và constraint được mô tả dưới đây.

## 2. Cấu trúc thư mục và script

| Thành phần | Chức năng |
|---|---|
| [`database/`](database/) | Tạo database và schema nền. |
| [`audit/`](audit/) | Tạo bảng audit vòng đời batch. |
| [`staging/`](staging/) | Tạo raw staging với 16 cột nguồn và lineage. |
| [`validation/`](validation/) | Truy vấn chỉ đọc để kiểm tra skeleton. |
| [`run_sql_skeleton.sql`](run_sql_skeleton.sql) | Bản SQL tổng hợp để mở trong SSMS và Execute một lần. |

1. [`database/01_create_database.sql`](database/01_create_database.sql): tạo `AmazonDeliveryBI` nếu chưa tồn tại.
2. [`database/02_create_schemas.sql`](database/02_create_schemas.sql): tạo `staging`, `dw`, `audit` nếu thiếu.
3. [`audit/01_create_load_batch.sql`](audit/01_create_load_batch.sql): tạo `audit.load_batch`.
4. [`staging/01_create_raw_amazon_delivery.sql`](staging/01_create_raw_amazon_delivery.sql): tạo `staging.raw_amazon_delivery`.
5. [`validation/01_validate_sql_skeleton.sql`](validation/01_validate_sql_skeleton.sql): liệt kê schema, bảng, metadata raw và row count.

## 3. Thứ tự thực thi bắt buộc

```text
1. database/01_create_database.sql
2. database/02_create_schemas.sql
3. audit/01_create_load_batch.sql
4. staging/01_create_raw_amazon_delivery.sql
5. validation/01_validate_sql_skeleton.sql
```

Database phải tồn tại trước schema; schema phải tồn tại trước bảng. `audit.load_batch` phải được tạo trước `staging.raw_amazon_delivery` vì staging có FK tham chiếu batch audit. Validation chạy cuối để quan sát kết quả của bốn bước DDL.

[`run_sql_skeleton.sql`](run_sql_skeleton.sql) đã ghép năm bước trên theo đúng thứ tự. Trong SSMS, chỉ cần mở file tổng, kết nối đúng instance và Execute một lần; không cần mở từng file thành phần hoặc bật SQLCMD Mode.

## 4. Data dictionary — `audit.load_batch`

Bảng có 15 cột, không có identity. Mỗi dòng biểu diễn một lần chạy full hoặc incremental load, kể cả lần chạy được bỏ qua do batch đã thành công.

| Column | SQL type | Nullable | Default/Identity | Key | Business meaning | Validation/constraint |
|---|---|---:|---|---|---|---|
| `load_batch_id` | `VARCHAR(64)` | Không | Không | PK `PK_load_batch` | Mã duy nhất của batch. | Duy nhất qua PK. |
| `batch_name` | `VARCHAR(50)` | Không | Không | — | Tên logic của cửa sổ load. | `FULL_DATASET`, `INITIAL_FULL`, `INCREMENTAL_01`, `INCREMENTAL_02`. |
| `batch_type` | `VARCHAR(20)` | Không | Không | — | Loại batch. | `CK_load_batch_batch_type`: `FULL_LOAD`, `INCREMENTAL`. |
| `source_file_name` | `NVARCHAR(260)` | Không | Không | — | Tên file nguồn, hỗ trợ Unicode. | Chưa có CHECK nội dung. |
| `source_file_checksum` | `CHAR(64)` | Không | Không | — | SHA-256 đầy đủ dạng hex. | `CK_load_batch_checksum`: chỉ `0-9`, `A-F`, `a-f`; độ dài cố định 64. |
| `expected_date_from` | `DATE` | Có | Không | — | Ngày dữ liệu kỳ vọng bắt đầu. | Đi cùng ngày kết thúc. |
| `expected_date_to` | `DATE` | Có | Không | — | Ngày dữ liệu kỳ vọng kết thúc. | Không nhỏ hơn ngày bắt đầu. |
| `expected_row_count` | `INT` | Có | Không | — | Số dòng kỳ vọng. | Null hoặc không âm. |
| `started_at` | `DATETIME2(3)` | Không | `DF_load_batch_started_at = SYSUTCDATETIME()` | — | Thời điểm bắt đầu theo UTC. | Mốc dưới của `finished_at`. |
| `finished_at` | `DATETIME2(3)` | Có | Không | — | Thời điểm kết thúc; null khi chưa kết thúc. | Không sớm hơn `started_at`. |
| `status` | `VARCHAR(20)` | Không | Không | — | Trạng thái batch. | `CK_load_batch_status`: `STARTED`, `SUCCEEDED`, `FAILED`, `SKIPPED`. |
| `rows_read` | `INT` | Không | `DF_load_batch_rows_read = 0` | — | Số dòng đọc từ nguồn. | Không âm. |
| `rows_loaded` | `INT` | Không | `DF_load_batch_rows_loaded = 0` | — | Số dòng ghi vào raw staging. | Không âm. |
| `rows_rejected` | `INT` | Không | `DF_load_batch_rows_rejected = 0` | — | Số dòng bị từ chối theo rule tương lai. | Không âm. |
| `error_message` | `NVARCHAR(MAX)` | Có | Không | — | Thông tin lỗi, hỗ trợ Unicode. | Chưa có CHECK nghiệp vụ. |

DDL không cưỡng chế `rows_read = rows_loaded + rows_rejected`: `SKIPPED` hợp lệ với `rows_read = expected_row_count`, `rows_loaded = 0`, `rows_rejected = 0`. Loader chịu trách nhiệm áp dụng semantics này.

## 5. CHECK constraints — `audit.load_batch`

| Constraint | Điều kiện được database cưỡng chế |
|---|---|
| `CK_load_batch_batch_type` | `batch_type` thuộc `FULL_LOAD`, `INCREMENTAL`. |
| `CK_load_batch_batch_name` | `batch_name` thuộc bốn batch được hỗ trợ. |
| `CK_load_batch_name_type` | `FULL_DATASET`/`INITIAL_FULL` là `FULL_LOAD`; hai batch còn lại là `INCREMENTAL`. |
| `CK_load_batch_status` | `status` thuộc `STARTED`, `SUCCEEDED`, `FAILED`, `SKIPPED`. |
| `CK_load_batch_checksum` | Checksum 64 ký tự, không có ký tự ngoài miền hex. |
| `CK_load_batch_expected_dates` | Hai ngày cùng null, hoặc cùng có giá trị và ngày bắt đầu không sau ngày kết thúc. |
| `CK_load_batch_expected_row_count` | Expected count null hoặc `>= 0`. |
| `CK_load_batch_row_counts` | `rows_read`, `rows_loaded`, `rows_rejected` đều `>= 0`. |
| `CK_load_batch_finished_at` | `finished_at` null hoặc `>= started_at`. |

Vòng đời load là tạo batch `STARTED`, commit audit, sau đó cập nhật `SUCCEEDED` hoặc `FAILED`. Rerun của một batch đã thành công được ghi thành audit `SKIPPED`. Mage tính checksum, cấp ID, kiểm tra expected count/duplicate, cập nhật thời gian, số dòng, trạng thái và lỗi.

## 6. Data dictionary — `staging.raw_amazon_delivery`

Bảng có đúng 21 cột: một khóa kỹ thuật, 16 cột nguồn và bốn cột metadata. Raw không trim, không sửa `Metropolitian`, không chuẩn hóa `NaN`, không đổi dấu tọa độ và không loại outlier.

| Column | Source/metadata | SQL type | Nullable | Key | Meaning | Notes |
|---|---|---|---:|---|---|---|
| `staging_row_id` | Metadata kỹ thuật | `BIGINT IDENTITY(1,1)` | Không | PK `PK_raw_amazon_delivery` | Khóa kỹ thuật raw row. | Không phải business key. |
| `Order_ID` | Source | `VARCHAR(32)` | Có | — | Mã bản ghi nguồn. | Giữ chuỗi raw. |
| `Agent_Age` | Source | `VARCHAR(16)` | Có | — | Tuổi dạng chuỗi. | Parse sau. |
| `Agent_Rating` | Source | `VARCHAR(16)` | Có | — | Rating dạng chuỗi. | Giữ null-like và 6,0. |
| `Store_Latitude` | Source | `VARCHAR(32)` | Có | — | Latitude cửa hàng. | Không sửa dấu hoặc `(0,0)`. |
| `Store_Longitude` | Source | `VARCHAR(32)` | Có | — | Longitude cửa hàng. | Không sửa dấu. |
| `Drop_Latitude` | Source | `VARCHAR(32)` | Có | — | Latitude điểm giao. | Chỉ dùng ở lớp kỹ thuật. |
| `Drop_Longitude` | Source | `VARCHAR(32)` | Có | — | Longitude điểm giao. | Chỉ dùng ở lớp kỹ thuật. |
| `Order_Date` | Source | `VARCHAR(16)` | Có | — | Ngày order dạng chuỗi. | Chưa parse `DATE`. |
| `Order_Time` | Source | `VARCHAR(16)` | Có | — | Giờ order dạng chuỗi. | Missing được giữ. |
| `Pickup_Time` | Source | `VARCHAR(16)` | Có | — | Giờ pickup dạng chuỗi. | Chưa áp dụng rollover. |
| `Weather` | Source | `VARCHAR(32)` | Có | — | Weather nguồn. | Không trim/chuẩn hóa. |
| `Traffic` | Source | `VARCHAR(32)` | Có | — | Traffic nguồn. | Có thể còn trailing space. |
| `Vehicle` | Source | `VARCHAR(32)` | Có | — | Vehicle nguồn. | Có thể còn trailing space. |
| `Area` | Source | `VARCHAR(64)` | Có | — | Area nguồn. | Không sửa `Metropolitian`. |
| `Delivery_Time` | Source | `VARCHAR(16)` | Có | — | Thời lượng dạng chuỗi. | Chưa ép số; phút là project assumption. |
| `Category` | Source | `VARCHAR(64)` | Có | — | Category nguồn. | Giữ cả `Grocery`. |
| `source_file_name` | Metadata lineage | `NVARCHAR(260)` | Không | — | Tên file nguồn. | Unicode cho tên file quốc tế/tiếng Việt. |
| `source_row_number` | Metadata lineage | `BIGINT` | Không | — | Số dòng trong file. | Pipeline cấp; chưa CHECK/unique. |
| `load_batch_id` | Metadata lineage | `VARCHAR(64)` | Không | FK `FK_raw_amazon_delivery_load_batch` | Batch tạo raw row. | Tham chiếu `audit.load_batch.load_batch_id`. |
| `loaded_at` | Metadata lineage | `DATETIME2(3)` | Không | — | Thời điểm nạp raw row. | Không có default; Mage cấp. |

Mười sáu cột nguồn nullable để lớp tiếp nhận giữ dữ liệu thiếu/lỗi mà không làm rơi record. Bốn metadata lineage là bắt buộc. Unique index bảo vệ `(load_batch_id, source_row_number)` và `Order_ID`; loader vẫn phải kiểm tra NULL/rỗng, duplicate trong batch và overlap với staging để tạo thông báo audit rõ ràng trước khi insert.

## 7. Lựa chọn kiểu dữ liệu raw

Mười sáu trường nguồn dùng `VARCHAR(n)` có giới hạn vì snapshot chủ yếu là tiếng Anh/ASCII. Raw giữ biểu diễn nguồn trước khi dbt trim, chuẩn hóa null-like và ép sang số/ngày/giờ. `n` là giới hạn tối đa, không có nghĩa mọi giá trị chiếm đúng `n` ký tự hoặc byte.

Không dùng `VARCHAR(MAX)`/`NVARCHAR(MAX)` tràn lan vì miền độ dài nguồn nhỏ và biết trước. Giới hạn rõ giúp phát hiện chuỗi bất thường, kiểm soát data quality, metadata/indexing và tránh LOB không cần thiết. Pipeline không được âm thầm cắt chuỗi vượt giới hạn; lỗi phải làm batch `FAILED` và được ghi vào audit.

`source_file_name` dùng `NVARCHAR(260)` để hỗ trợ Unicode. SQL Server hiển thị `max_length = 520` byte là bình thường vì metadata của `NVARCHAR` tính tối đa hai byte cho mỗi UTF-16 code unit trong miền BMP; không có nghĩa cột chứa 520 ký tự.

## 8. Khóa và quan hệ

- `audit.load_batch`: PK `PK_load_batch` trên `load_batch_id`; không có identity.
- `staging.raw_amazon_delivery`: PK `PK_raw_amazon_delivery` trên `staging_row_id`, `IDENTITY(1,1)`.
- FK `FK_raw_amazon_delivery_load_batch`: `staging.raw_amazon_delivery.load_batch_id` → `audit.load_batch.load_batch_id`.
- Index `IX_load_batch_batch_name_status` hỗ trợ tìm lần chạy theo batch và trạng thái.
- Index `IX_raw_amazon_delivery_load_batch_id` hỗ trợ kiểm đếm/tra cứu lineage theo batch.
- Unique index `UX_raw_amazon_delivery_batch_source_row` bảo vệ số dòng nguồn trong từng batch.
- Filtered unique index `UX_raw_amazon_delivery_order_id` bảo vệ `Order_ID` khác NULL trên toàn staging.
- Một audit batch có thể có nhiều raw rows; mỗi raw row thuộc một batch tồn tại.
- DDL không khai báo `ON DELETE`/`ON UPDATE`; SQL Server dùng `NO ACTION`, không cascade.

Không thể xóa hoặc đổi khóa batch cha khi còn raw rows tham chiếu. Quy trình là tạo audit row trước, nạp raw rows sau, rồi cập nhật audit row.

## 9. Nullability và phạm vi validation

Các cột audit nhận diện, loại, file, checksum, thời gian bắt đầu, status và row counts là `NOT NULL`; expected fields, thời gian kết thúc và lỗi có thể null. Trong raw, PK và bốn metadata bắt buộc, còn 16 cột nguồn nullable để missing không làm mất record.

DDL chỉ cưỡng chế constraint đã liệt kê. Parse, trim, null normalization, valid rating, pickup rollover, Haversine, distance rule, group boundaries, unique `Order_ID` và quality flags thuộc dbt staging/intermediate sau này.

## 10. Chạy toàn bộ skeleton một lần trong SSMS

1. Mở SQL Server Management Studio.
2. Kết nối đúng SQL Server instance bằng tài khoản có quyền tạo database, schema và table.
3. Mở [`run_sql_skeleton.sql`](run_sql_skeleton.sql).
4. Chọn **Execute** một lần.
5. Kiểm tra Messages và các result set validation ở cuối.

File tổng chứa trực tiếp nội dung của năm SQL script theo đúng thứ tự, nên không cần SQLCMD Mode, `sqlcmd`, PowerShell hoặc đường dẫn tuyệt đối. DDL kiểm tra object trước khi tạo nên có thể Execute lại sau khi xử lý lỗi.

Năm file thành phần vẫn là nguồn bảo trì theo từng chức năng. Khi một DDL thành phần thay đổi, phải đồng bộ `run_sql_skeleton.sql` để tránh hai phiên bản lệch nhau.

## 11. Cách chạy thay thế

### SQL Server Management Studio

Nếu không dùng file tổng, kết nối đúng instance, mở năm file theo thứ tự mục 3, Execute lần lượt và kiểm tra Messages/Results. Dừng khi có lỗi.

### VS Code

VS Code chỉ là công cụ gửi lệnh. Cần extension SQL Server phù hợp và connection tới đúng instance. Có thể chạy file tổng nếu extension hỗ trợ `GO`; nếu chạy từng file thì phải giữ đúng thứ tự. Chỉ mở file không tự tạo database.

## 12. Validation và kết quả mong đợi

[`validation/01_validate_sql_skeleton.sql`](validation/01_validate_sql_skeleton.sql) chỉ đọc. Bản hiện tại kiểm tra ba schema, hai bảng, column metadata của raw và row count. `USE AmazonDeliveryBI` thành công cũng xác nhận database truy cập được.

Kỳ vọng:

- Ba schema `audit`, `dw`, `staging`.
- Hai bảng `audit.load_batch`, `staging.raw_amazon_delivery`.
- Audit: 15 cột, một PK, chín CHECK, một nonclustered index, không identity.
- Raw: 21 cột, một PK identity, một FK, hai unique index và một nonclustered index hỗ trợ batch.
- Row count có thể bằng `0` trước khi load.

Validation file chưa tự liệt kê audit columns, PK, FK hoặc CHECK. Dùng truy vấn đọc bổ sung:

```sql
SELECT
    OBJECT_SCHEMA_NAME(c.object_id) AS schema_name,
    OBJECT_NAME(c.object_id) AS table_name,
    c.column_id, c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length, c.is_nullable, c.is_identity
FROM sys.columns AS c
WHERE c.object_id IN (
    OBJECT_ID(N'audit.load_batch'),
    OBJECT_ID(N'staging.raw_amazon_delivery')
)
ORDER BY schema_name, table_name, c.column_id;

SELECT
    OBJECT_SCHEMA_NAME(kc.parent_object_id) AS schema_name,
    OBJECT_NAME(kc.parent_object_id) AS table_name,
    kc.name AS primary_key_name
FROM sys.key_constraints AS kc
WHERE kc.type = 'PK'
  AND kc.parent_object_id IN (
      OBJECT_ID(N'audit.load_batch'),
      OBJECT_ID(N'staging.raw_amazon_delivery')
  );

SELECT
    fk.name AS foreign_key_name,
    OBJECT_SCHEMA_NAME(fk.parent_object_id) AS child_schema,
    OBJECT_NAME(fk.parent_object_id) AS child_table,
    fk.delete_referential_action_desc AS on_delete,
    fk.update_referential_action_desc AS on_update
FROM sys.foreign_keys AS fk
WHERE fk.parent_object_id = OBJECT_ID(N'staging.raw_amazon_delivery');

SELECT cc.name, cc.definition
FROM sys.check_constraints AS cc
WHERE cc.parent_object_id = OBJECT_ID(N'audit.load_batch')
ORDER BY cc.name;

SELECT COUNT_BIG(*) AS audit_batch_count FROM audit.load_batch;
SELECT COUNT_BIG(*) AS staging_row_count FROM staging.raw_amazon_delivery;
```

## 13. Rerun safety và idempotency

DDL kiểm tra object trước khi tạo: database qua `DB_ID`, schema qua `sys.schemas`, bảng qua `OBJECT_ID`; validation chỉ đọc. Nếu file tổng dừng giữa chừng, object đã tạo trước đó vẫn tồn tại. Sau khi sửa lỗi có thể Execute lại và các bước đã tồn tại sẽ được bỏ qua; không có transaction chung cho toàn bộ file.

DDL rerun safety khác pipeline idempotency. Loader dùng `batch_name`, khoảng ngày, expected count, checksum và số staging rows của lần `SUCCEEDED` để nhận diện rerun; mỗi rerun được audit `SKIPPED`. Duplicate `Order_ID` còn được bảo vệ ở cả Python và unique index của staging.

## 14. Luồng Mage

1. Mage bắt đầu batch và tính checksum.
2. Ghi row `audit.load_batch` với `STARTED`.
3. Giữ `load_batch_id`.
4. Đọc CSV chung, parse `Order_Date` và lọc cửa sổ của `batch_name`.
5. Kiểm tra expected count, `Order_ID` trong batch và overlap với staging.
6. Nếu batch đã thành công, cập nhật lần chạy hiện tại thành `SKIPPED` và không insert.
7. Ghi raw rows cùng `load_batch_id`; insert staging và update `SUCCEEDED` trong cùng transaction.
8. Khi lỗi, rollback staging rồi cập nhật audit `FAILED` và phát sinh lại exception.
9. dbt chuẩn hóa, kiểm thử và xây dựng năm Dimensions cùng một Fact.

## 15. Security và cấu hình

- Không hard-code username, password, API key hoặc token.
- File tổng không chứa thông tin xác thực; nó dùng connection đang mở trong SSMS hoặc VS Code.
- Nếu dùng SQL Authentication, credential phải được quản lý bởi connection profile hoặc secret management, không ghi vào file SQL.
- Không commit `.env` hay secret; [`.env.example`](../.env.example) chỉ là mẫu.

## 16. Pending work và open items

- [x] Mage CSV ingestion, full/incremental load, audit, duplicate check và rerun idempotency.
- [ ] Watermark động, late-arriving data và rejected-record workflow ngoài ba batch cố định.
- [ ] dbt source, staging, intermediate, tests, documentation và lineage.
- [ ] Năm Dimensions và một Fact.
- [ ] Power BI semantic model/dashboard.
- [ ] AI output, evidence, report và end-to-end test.

Open items:

- Incremental loader hiện hỗ trợ đúng ba batch cố định; chưa phải watermark động cho nguồn phát sinh mới.
- Validation SQL chưa truy vấn trực tiếp PK/FK/CHECK; mục 12 cung cấp truy vấn bổ sung.
- Một số tài liệu quản lý cũ vẫn ghi technical implementation chưa triển khai, trong khi repository đã có SQL skeleton DDL. Điều này không chứng minh Mage/dbt/DWH đã triển khai; trạng thái nên được đồng bộ trong task quản lý riêng.

## 17. Troubleshooting

| Hiện tượng | Cách xử lý |
|---|---|
| Không kết nối được | Xác nhận SQL Server service, giao thức và quyền Windows account. |
| Sai instance | Ngắt kết nối và kết nối lại đúng instance trong SSMS, ví dụ `localhost\SQLEXPRESS`. |
| Không có quyền tạo database | Nhờ DBA cấp quyền; không hard-code tài khoản đặc quyền. |
| FK lỗi | Tạo schema và `audit.load_batch` trước raw staging; chạy đúng thứ tự. |
| Object đã tồn tại | Rerun dự kiến; đọc Messages để xác nhận bước tạo được bỏ qua. |
| Row count bằng `0` | Hợp lệ nếu Mage chưa load. |
| `NVARCHAR(260)` có `max_length = 520` | `sys.columns.max_length` tính byte, không phải số ký tự. |
| File tổng dừng giữa chừng | Đọc Messages, sửa nguyên nhân rồi Execute lại; object đã tạo được giữ. |
| File tổng khác file thành phần | Xem file thành phần là nguồn bảo trì và đồng bộ lại `run_sql_skeleton.sql`. |

## 18. References

- [Root README](../README.md)
- [Data Contract](../project_management/DATA_CONTRACT.md)
- [Source-to-Target Mapping](../project_management/SOURCE_TO_TARGET_MAPPING.md)
- [Approved Dimensional Model](../project_management/DIMENSIONAL_MODEL.md)
- [Naming Conventions](../project_management/NAMING_CONVENTIONS.md)
- [Task Board](../project_management/TASK_BOARD.md)
- [SQL skeleton tổng hợp](run_sql_skeleton.sql)
- [Luồng ánh xạ dữ liệu](../report/figures/Luong_anh_xa_du_lieu.png)
- [Ánh xạ theo nhóm trường](../report/figures/anh_xa_theo_field.png)
