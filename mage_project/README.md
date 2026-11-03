# Mage.ai — Amazon Delivery ingestion

Hai pipeline `amazon_delivery_full_load` và `amazon_delivery_incremental_load`
đều có bốn block theo thứ tự:

1. **Data loader** đọc một snapshot byte của `data/raw/amazon_delivery.csv`,
   tính checksum SHA-256 và parse dữ liệu nguyên trạng dưới dạng chuỗi từ cùng
   snapshot.
2. **Transformer** kiểm tra dữ liệu đầu vào. Full load kiểm tra số dòng, số cột
   và header. Incremental kiểm tra header, ngày, số dòng của batch và `Order_ID`
   rỗng/trùng trong batch; số dòng nguồn gốc được giữ trong `_source_row_number`.
3. **Data exporter** quản lý checksum, audit, bỏ qua batch đã nạp, kiểm tra
   `Order_ID` đã có trong staging (incremental), ghi raw staging và đối soát
   số dòng trong cùng transaction trước khi đánh dấu `SUCCEEDED`.
4. **Custom verification block** chỉ đọc `audit.load_batch` và
   `staging.raw_amazon_delivery` để xác nhận kết quả `SUCCEEDED` hoặc `SKIPPED`.

`test_sql_server_connection` vẫn là pipeline kiểm tra kết nối riêng. Full load
và ba batch incremental là hai cách nạp thay thế nhau trên cùng dataset.
Không chạy cả hai cách trên một staging đã có dữ liệu. Mage không chuẩn hóa
giá trị nguồn hoặc tạo Fact/Dimension; dbt xử lý sau khi nạp thành công.

Runtime variable `batch_name` của incremental nhận một trong ba giá trị:
`INITIAL_FULL` (6.982 dòng), `INCREMENTAL_01` (30.658 dòng),
`INCREMENTAL_02` (6.099 dòng). Các quy tắc và kỳ vọng được giữ từ loader gốc.
Không có `batch_name` mặc định trong metadata; cần truyền tường minh cho mỗi
lần chạy. Đây là ba batch lịch sử từ cùng một CSV, chưa phải luồng nhận file
mới tự động theo lịch.
Xem `MAGE_TEAM_SETUP.md` ở thư mục dự án để cấu hình môi trường và khởi chạy.
