# Bối cảnh dự án

## Bối cảnh môn học và mục tiêu

Đây là mini project môn Business Intelligence của nhóm 4 thành viên, với kế hoạch ban đầu 6 ngày. Mục tiêu là xây dựng hệ thống BI tích hợp Generative AI để phân tích hoạt động bán hàng của chuỗi siêu thị.

## Dataset đã xác nhận

- **Tên:** Supermarket Sales.
- **Tác giả:** Fares Ashraf.
- **Nguồn:** <https://www.kaggle.com/datasets/faresashraf1001/supermarket-sales>.
- **File chính:** `01_data/raw/supermarket_sales.csv`.
- **Quy mô:** 1.000 dòng dữ liệu, 17 cột.
- **Khoảng thời gian:** 2019-01-01 đến 2019-03-30.
- **Chủ đề:** phân tích hiệu quả bán hàng của chuỗi siêu thị.

## Grain baseline

Mỗi dòng đại diện cho một bản ghi giao dịch bán hàng duy nhất trong dữ liệu nguồn, được nhận diện bởi `Invoice ID`, phát sinh tại một chi nhánh, vào một thời điểm và gắn với một `Product line`. Dataset không có SKU hoặc chi tiết dòng hóa đơn nên không đủ cơ sở xác định cấu trúc hóa đơn vật lý bên dưới.

## Mô hình dữ liệu baseline

- **Fact dự kiến:** `fact_sales`; `Invoice ID` là degenerate business key.
- **Dimensions dự kiến:** `dim_date`, `dim_branch_location`, `dim_customer_segment`, `dim_product_line`, `dim_payment_method`.
- Không tạo `dim_time`; dự kiến giữ `transaction_time`, `transaction_hour`, `time_period` trong Fact.
- Cấu trúc cột, surrogate key, Unknown Member và quan hệ vật lý được hoàn thiện trong Dimensional Modeling.

## KPI baseline

KPI chính: Total Sales, Total Quantity, Invoice Count, Average Order Value, Weighted Average Unit Price, Total COGS, Average Rating, Average Daily Sales và Monthly Sales Growth có chú thích.

KPI phụ: Total Gross Income và Average Gross Income per Invoice. Không trình bày Gross Income và Tax 5% như hai KPI độc lập; không dùng `gross margin percentage` làm KPI biến động.

Định nghĩa, công thức, quy tắc hiển thị, baseline đối soát và giới hạn diễn giải được chốt tại `00_project_management/KPI_DICTIONARY.md`.

## Business Requirements đã xác nhận

- **Bối cảnh:** phân tích hoạt động bán hàng của chuỗi siêu thị trong snapshot ba tháng để theo dõi quy mô, biến động và nhóm đóng góp; không suy luận nguyên nhân ngoài dữ liệu.
- **Quy trình:** phân tích giao dịch bán hàng tại chuỗi siêu thị theo grain baseline đã chốt.
- **Người dùng:** Sales/Operations Manager là người dùng chính; Branch Manager và BI Analyst là người dùng phụ.
- **Business Questions:** đã chốt đúng 8 câu hỏi từ BQ-01 đến BQ-08, bao phủ tổng quan, xu hướng thời gian, Branch, Product line, Customer segment, Payment, Time Period và Rating.
- **Time Period:** Morning `10:00-11:59`, Afternoon `12:00-16:59`, Evening `17:00-20:59`.

Chi tiết yêu cầu, traceability và acceptance criteria được quản lý tại `00_project_management/BUSINESS_REQUIREMENTS.md`.

## Full Load và Incremental Load baseline

- Full Load 01/2019: 352 dòng.
- Incremental 1 02/2019: 303 dòng.
- Incremental 2 03/2019 đến ngày 30: 345 dòng.
- Watermark dự kiến dựa trên Date kết hợp Time; `Invoice ID` phục vụ kiểm tra idempotency.

## Luồng dữ liệu dự kiến

`Kaggle CSV → Mage.ai → SQL Server staging → dbt → SQL Server dw → Power BI → Generative AI`

## Yêu cầu theo thành phần

- **Mage.ai:** đọc nguồn, kiểm tra dữ liệu, nạp Staging, mô phỏng Full/Incremental Load, logging và hỗ trợ chạy lại.
- **dbt:** làm sạch, chuẩn hóa, tích hợp, xây dựng models, tests, documentation và lineage.
- **Data Warehouse:** ưu tiên SQL Server với các schema `staging`, `dw`, `audit`; thiết kế Star Schema và xử lý surrogate key/Unknown Member sau khi chốt mô hình.
- **Power BI:** semantic model, DAX, hierarchies, Date Dimension và tối thiểu hai trang Overview và Detailed/Diagnostic Analytics.
- **Generative AI:** tạo AI Summary từ KPI đã tính, hạn chế suy diễn và cho phép đối chiếu với dashboard.

## Hạn chế chính

- Chỉ có ba tháng dữ liệu; không đủ phân tích mùa vụ hoặc xu hướng dài hạn.
- Không có SKU, Customer ID, tồn kho, discount, return hoặc chi phí vận hành.
- Không phân tích Customer Lifetime Value hoặc hành vi mua lặp lại.
- Branch và City có hạn chế ngữ nghĩa từ nguồn.
- Không thể xác minh cấu trúc hóa đơn vật lý bên dưới.

## Sản phẩm cuối cùng

Báo cáo PDF; source Mage.ai; source dbt; SQL scripts; thành phần AI; file `.pbix`; dataset và đường dẫn Kaggle; hướng dẫn cấu hình/chạy; video demo end-to-end.

## Trạng thái hiện tại

- Project Setup: Done.
- Dataset Selection: Done.
- Data Profiling: Done.
- Business Context, Business Process và Business Users: Done.
- Business Questions: Done.
- KPI Dictionary: Done.
- Dimensional Modeling: Next; bắt đầu từ MOD-01 - Chốt Star Schema.

Chưa triển khai Mage.ai, dbt, SQL Server, Data Warehouse, Power BI hoặc Generative AI.
