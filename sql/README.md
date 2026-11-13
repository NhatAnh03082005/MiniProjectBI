# SQL Server bootstrap and migration

Thư mục SQL tạo database, schema, audit và current-state raw staging cho Mage.
Các script DDL là idempotent: có thể chạy trên database mới hoặc nâng cấp
database đã chứa dữ liệu mà không drop bảng.

## Thứ tự chạy

Hai file triển khai là các script độc lập, đã chứa toàn bộ DDL, migration và
validation. Có thể mở trực tiếp trong SSMS và Execute; không cần bật SQLCMD
Mode và không phụ thuộc các lệnh `:r`:

```powershell
sqlcmd -S localhost -E -C -b -i run_sql_skeleton.sql
sqlcmd -S localhost -E -C -b -i run_sql_skeleton_demo.sql
```

`run_sql_skeleton.sql` triển khai `AmazonDeliveryBI`.
`run_sql_skeleton_demo.sql` triển khai `AmazonDeliveryBI_Demo`.

Mỗi file tổng thực hiện đầy đủ theo thứ tự:

1. `database/01_create_database.sql`
2. `database/02_create_schemas.sql`
3. `audit/01_create_load_batch.sql`
4. `staging/01_create_raw_amazon_delivery.sql`
5. `validation/01_validate_sql_skeleton.sql`

## audit.load_batch

`batch_name` là tên động, chỉ yêu cầu không rỗng. `batch_type` vẫn giới
hạn ở `FULL_LOAD` và `INCREMENTAL`.

Các counter:

- `rows_read`: tổng dòng nguồn.
- `rows_inserted`: ID mới.
- `rows_updated`: ID cũ có hash khác.
- `rows_unchanged`: ID cũ có hash giống.
- `rows_rejected`: dòng không đạt technical contract.
- `rows_loaded`: `rows_inserted + rows_updated`.

Ba cột legacy `expected_date_from`, `expected_date_to`,
`expected_row_count` được giữ để tương thích. Mage điền các giá trị quan sát
động từ file, không dùng mốc hoặc số dòng gán cứng.

## staging.raw_amazon_delivery

Bảng là current-state raw staging, một dòng cho một `Order_ID`. Mười sáu
cột nguồn và bốn cột lineage cũ được giữ nguyên để dbt không đổi interface.

Metadata upsert bổ sung:

| Cột | Ý nghĩa |
|---|---|
| `row_hash` | SHA-256 của 15 thuộc tính raw ngoài `Order_ID` |
| `updated_load_batch_id` | Batch gần nhất thay đổi dòng |
| `updated_at` | Thời điểm thay đổi gần nhất |
| `updated_source_file_name` | File chứa phiên bản gần nhất |
| `updated_source_row_number` | Vị trí phiên bản gần nhất trong file |

`load_batch_id`, `loaded_at`, `source_file_name` và
`source_row_number` tiếp tục biểu diễn lần insert đầu tiên; exporter không
ghi đè lineage này khi update.

## Compatibility with dbt

Migration không đổi tên, xóa hoặc đổi kiểu cột cũ. dbt hiện tại chọn rõ các
cột cần dùng nên bỏ qua metadata mới. Thay đổi duy nhất về semantics là bảng
raw trở thành current-state thay vì append-only history.

## Validation

Script validation thất bại khi:

- thiếu bảng hoặc cột upsert/audit;
- dynamic batch không đối soát được action counter;
- staging còn duplicate `Order_ID` sau trim/case-fold.
