# Phạm vi dự án

## In scope

- Một dataset Kaggle: Supermarket Sales.
- Một quy trình nghiệp vụ bán hàng.
- Một Fact dự kiến: `fact_sales`.
- Năm Dimension dự kiến: `dim_date`, `dim_branch_location`, `dim_customer_segment`, `dim_product_line`, `dim_payment_method`.
- Chín KPI chính baseline: Total Sales, Total Quantity, Invoice Count, Average Order Value, Weighted Average Unit Price, Total COGS, Average Rating, Average Daily Sales và Monthly Sales Growth có chú thích.
- Ba nhóm người dùng đã xác nhận: Sales/Operations Manager, Branch Manager và BI Analyst.
- Đúng tám Business Questions từ BQ-01 đến BQ-08 theo `BUSINESS_REQUIREMENTS.md`.
- KPI definitions, validation rules và baseline theo `KPI_DICTIONARY.md`.
- Time Period baseline: Morning `10:00-11:59`, Afternoon `12:00-16:59`, Evening `17:00-20:59`.
- Full Load tháng 01/2019 và hai Incremental Load mô phỏng cho tháng 02/2019, tháng 03/2019.
- Data quality checks cơ bản, Staging, Data Warehouse và dbt tests.
- Hai trang Power BI: Overview và Detailed/Diagnostic Analytics.
- AI-generated Summary.
- Báo cáo và video demo.

## Out of scope trong giai đoạn đầu

- Phân tích SKU hoặc sản phẩm chi tiết.
- Customer Lifetime Value, khách hàng cá nhân hoặc hành vi mua lặp lại.
- Phân tích tồn kho, return, discount hoặc chi phí vận hành.
- Machine Learning.
- Dự báo dài hạn hoặc phân tích mùa vụ.
- Chatbot phức tạp.
- Streaming thời gian thực.
- Nhiều Fact không cần thiết.
- Nhiều nguồn dữ liệu ngoài Kaggle.
- Cloud deployment.
- Các chức năng không phục vụ rubric.

## Pending decisions

- Cấu trúc cột chi tiết của Fact và Dimension.
- Surrogate key và Unknown Member.
- SCD strategy.
- Phương án chia sẻ SQL Server cho nhóm.
- LLM provider.
- Màu sắc và phong cách dashboard.
- Thiết kế AI Summary cụ thể.
