# Decision Log

| Decision ID | Ngày | Quyết định | Lý do | Người xác nhận | Trạng thái |
|---|---|---|---|---|---|
| DEC-001 | Chưa ghi nhận | Nhóm gồm 4 người | Theo bối cảnh dự án | Nhóm | Đã xác nhận |
| DEC-002 | Chưa ghi nhận | Thời gian thực hiện còn 6 ngày | Theo bối cảnh dự án | Nhóm | Đã xác nhận |
| DEC-003 | Chưa ghi nhận | Kiến trúc dự kiến gồm Mage.ai, database, dbt, Power BI và Generative AI | Đáp ứng luồng BI được yêu cầu | Nhóm | Đã xác nhận |
| DEC-004 | Chưa ghi nhận | Ưu tiên SQL Server | Yêu cầu chi tiết chỉ rõ Staging và Data Warehouse trên SQL Server | Nhóm | Đã xác nhận |
| DEC-005 | Chưa ghi nhận | Chưa chọn dataset | Được thay thế bởi DEC-007 | Nhóm | Superseded |
| DEC-006 | Chưa ghi nhận | Chưa chốt grain, Fact, Dimension và KPI | Được thay thế bởi DEC-010, DEC-011, DEC-012 và DEC-014 | Nhóm | Superseded |
| DEC-007 | 2026-10-16 | Chọn dataset Supermarket Sales của Fares Ashraf | Phù hợp phân tích đa chiều, KPI và mô phỏng incremental load | Nhóm | Đã xác nhận |
| DEC-008 | 2026-10-16 | Sử dụng file `01_data/raw/supermarket_sales.csv` và giữ ZIP trong thư mục archive | Xác định một nguồn CSV chính thức để phân tích | Nhóm | Đã xác nhận |
| DEC-009 | 2026-10-16 | Giữ nguyên raw data với SHA-256 `C5E0490DA62001D3066A56B3AA9C891C8D3ED42B6C2D09C8CA18B2A409AC93CD` | Bảo đảm khả năng đối soát và tái lập | Nhóm | Đã xác nhận |
| DEC-010 | 2026-10-16 | Giữ `Sales` trong raw, dự kiến chuẩn hóa thành `sales_amount`; không tạo cột nguồn `Total` | File nguồn không có `Total`; `Sales` là tổng giá trị bán hàng gồm thuế | Nhóm | Đã xác nhận |
| DEC-011 | 2026-10-16 | Grain là một bản ghi giao dịch nguồn trên mỗi `Invoice ID` | 1.000 dòng có 1.000 ID duy nhất; không đủ dữ liệu xác minh hóa đơn vật lý | Nhóm | Đã xác nhận |
| DEC-012 | 2026-10-16 | Sử dụng một Fact baseline là `fact_sales`; `Invoice ID` là degenerate business key | Phù hợp quy trình bán hàng và grain nguồn | Nhóm | Đã xác nhận |
| DEC-013 | 2026-10-16 | Sử dụng năm Dimension baseline: `dim_date`, `dim_branch_location`, `dim_customer_segment`, `dim_product_line`, `dim_payment_method` | Các chiều có căn cứ trực tiếp trong dữ liệu | Nhóm | Đã xác nhận |
| DEC-014 | 2026-10-16 | Không tạo `dim_time`; giữ `transaction_time`, dự kiến thêm `transaction_hour`, `time_period` trong Fact | Phạm vi hiện tại không cần Dimension thời gian trong ngày riêng | Nhóm | Đã xác nhận |
| DEC-015 | 2026-10-16 | Weighted Average Unit Price dùng `SUM(cogs) / SUM(Quantity)` | Công thức `cogs = Unit price × Quantity` đạt 1.000/1.000 dòng | Nhóm | Đã xác nhận |
| DEC-016 | 2026-10-16 | Không dùng `gross margin percentage` làm KPI biến động; không trình bày Gross Income và Tax như hai KPI độc lập | Gross margin percentage cố định; Gross Income bằng Tax 5% | Nhóm | Đã xác nhận |
| DEC-017 | 2026-10-16 | Chia Full Load và Incremental Load theo 01/2019, 02/2019 và 03/2019 | Ba tháng liên tiếp có 352, 303 và 345 dòng | Nhóm | Đã xác nhận |
| DEC-018 | 2026-10-16 | Giữ lại 9 giao dịch giá trị cao bị IQR gắn cờ | Các dòng đạt miền giá trị và công thức nghiệp vụ, chưa có bằng chứng là lỗi | Nhóm | Đã xác nhận |
| DEC-019 | 2026-10-16 | Ưu tiên SQL Server với các schema `staging`, `dw`, `audit` | Phù hợp yêu cầu đề bài và phân tách vùng dữ liệu | Nhóm | Đã xác nhận |
| DEC-020 | 2026-10-16 | Chốt bối cảnh BI là phân tích hoạt động bán hàng của chuỗi siêu thị trong snapshot ba tháng | Hỗ trợ theo dõi quy mô, biến động và nhóm đóng góp mà không suy luận nguyên nhân ngoài dữ liệu | Nhóm | Đã xác nhận |
| DEC-021 | 2026-10-16 | Chốt quy trình nghiệp vụ là phân tích giao dịch bán hàng tại chuỗi siêu thị theo grain baseline | Bám sát các trường và phạm vi đã xác minh trong nguồn | Nhóm | Đã xác nhận |
| DEC-022 | 2026-10-16 | Chốt Sales/Operations Manager là người dùng chính; Branch Manager và BI Analyst là người dùng phụ | Bao phủ nhu cầu quản lý tổng quan, theo dõi chi nhánh và kiểm tra số liệu | Nhóm | Đã xác nhận |
| DEC-023 | 2026-10-16 | Chốt đúng 8 Business Questions từ BQ-01 đến BQ-08 trong `BUSINESS_REQUIREMENTS.md` | Các câu hỏi có thể trả lời bằng dữ liệu và bao phủ các chiều phân tích chính | Nhóm | Đã xác nhận |
| DEC-024 | 2026-10-16 | Chốt KPI baseline gồm 9 KPI chính, 2 KPI hỗ trợ và 1 chỉ số chẩn đoán trong `KPI_DICTIONARY.md` | Chuẩn hóa công thức, filter context, kiểm tra và giới hạn diễn giải trước khi mô hình hóa | Nhóm | Đã xác nhận |
| DEC-025 | 2026-10-16 | Chốt Time Period: Morning `10:00-11:59`, Afternoon `12:00-16:59`, Evening `17:00-20:59` | Phân nhóm toàn bộ miền giờ quan sát thành ba khoảng không chồng lấn | Nhóm | Đã xác nhận |
| DEC-026 | 2026-10-16 | Không gắn ký hiệu tiền tệ cụ thể cho KPI tiền tệ | Dataset chưa xác nhận đơn vị tiền tệ | Nhóm | Đã xác nhận |

Các quyết định mới chỉ được thêm khi nhóm xác nhận; lịch sử được giữ lại và đánh dấu `Superseded` khi có quyết định thay thế.
