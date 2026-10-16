# Business Intelligence System for Supermarket Sales Analysis with Generative AI

## Mục tiêu

Xây dựng hệ thống Business Intelligence tích hợp Generative AI để phân tích hiệu quả bán hàng của chuỗi siêu thị, từ dữ liệu nguồn đến dashboard và bản tóm tắt KPI có thể kiểm chứng.

## Dataset

- **Tên:** Supermarket Sales.
- **Tác giả:** Fares Ashraf.
- **Nguồn:** <https://www.kaggle.com/datasets/faresashraf1001/supermarket-sales>.
- **Quy mô:** 1.000 dòng dữ liệu, 17 cột.
- **Khoảng thời gian:** 2019-01-01 đến 2019-03-30.
- **Bài toán:** phân tích hiệu quả bán hàng của chuỗi siêu thị theo thời gian, chi nhánh, phân khúc khách hàng, ngành hàng và phương thức thanh toán.

## Kiến trúc dự kiến

`Kaggle CSV → Mage.ai → SQL Server staging → dbt → SQL Server dw → Power BI → Generative AI`

## Công nghệ dự kiến

- Kaggle cho nguồn dữ liệu.
- Mage.ai cho data ingestion, Full Load và Incremental Load mô phỏng.
- SQL Server cho Staging, Data Warehouse và audit.
- dbt cho làm sạch, biến đổi, kiểm thử và tài liệu hóa.
- Power BI cho semantic model và dashboard.
- Python kết nối LLM API cho AI Summary.

## Grain và mô hình baseline

Mỗi dòng đại diện cho một bản ghi giao dịch bán hàng duy nhất trong dữ liệu nguồn, được nhận diện bởi `Invoice ID`, phát sinh tại một chi nhánh, vào một thời điểm và gắn với một `Product line`. Dataset không có SKU hoặc chi tiết dòng hóa đơn nên không đủ cơ sở xác định cấu trúc hóa đơn vật lý bên dưới.

- **Fact dự kiến:** `fact_sales`; `Invoice ID` là degenerate business key.
- **Dimensions dự kiến:** `dim_date`, `dim_branch_location`, `dim_customer_segment`, `dim_product_line`, `dim_payment_method`.
- Không tạo `dim_time`; dự kiến giữ `transaction_time`, `transaction_hour`, `time_period` trong Fact.

## KPI baseline

KPI chính: Total Sales, Total Quantity, Invoice Count, Average Order Value, Weighted Average Unit Price, Total COGS, Average Rating, Average Daily Sales và Monthly Sales Growth có chú thích.

KPI phụ: Total Gross Income và Average Gross Income per Invoice. Không trình bày Gross Income và Tax 5% như hai KPI độc lập; không dùng `gross margin percentage` làm KPI biến động.

Yêu cầu nghiệp vụ và tám Business Questions được quản lý tại `00_project_management/BUSINESS_REQUIREMENTS.md`; định nghĩa KPI chi tiết được quản lý tại `00_project_management/KPI_DICTIONARY.md`.

## Cấu trúc thư mục

- `00_project_management`: tài liệu quản lý và quyết định.
- `01_data`: dữ liệu raw, full load, incremental và rejected.
- `02_sql`: script database, staging, warehouse và audit.
- `03_mage`: mã nguồn và kiểm thử Mage.ai.
- `04_dbt`: models, tests, macros, seeds và snapshots dbt.
- `05_powerbi`: PBIX, DAX, mockup và theme.
- `06_ai`: mã nguồn, prompt, test và input mẫu cho AI.
- `07_report`: nội dung, hình và tài liệu tham khảo của báo cáo.
- `08_evidence`: bằng chứng kiểm thử theo từng thành phần.
- `09_demo`: kịch bản và bản ghi demo.
- `config`: ví dụ cấu hình không chứa bí mật.

## Sản phẩm cần nộp

1. Báo cáo PDF.
2. Source code Mage.ai.
3. Source code dbt.
4. SQL scripts.
5. Thành phần tích hợp AI.
6. File Power BI `.pbix`.
7. Dataset và đường dẫn Kaggle.
8. Hướng dẫn cấu hình và chạy hệ thống.
9. Video demo toàn bộ quy trình.

## Trạng thái hiện tại

- Giai đoạn 1–6: Done.
- Business Baseline v1: Locked.
- Task tiếp theo: `MOD-01` - Chốt Star Schema.

Chưa triển khai Mage.ai, dbt, SQL Server, Data Warehouse, Power BI hoặc Generative AI.

## Team Handoff

Thành viên mới hoặc thành viên phụ trách Giai đoạn 7–9 phải đọc:

- [Team Handoff Guide](00_project_management/TEAM_HANDOFF_GUIDE.md)

## Hạn chế dữ liệu chính

- Chỉ có ba tháng dữ liệu; không đủ cơ sở phân tích mùa vụ hoặc xu hướng dài hạn.
- Không có SKU, Customer ID, tồn kho, discount, return hoặc chi phí vận hành.
- Không phân tích Customer Lifetime Value hoặc hành vi mua lặp lại.
- Branch và City ánh xạ một-một nhưng có hạn chế ngữ nghĩa từ nguồn.
- Không thể xác minh cấu trúc hóa đơn vật lý bên dưới.

## Quyết định còn chờ

Cấu trúc cột chi tiết của Fact/Dimension; surrogate key và Unknown Member; SCD strategy; phương án chia sẻ SQL Server; LLM provider; màu sắc/phong cách dashboard; thiết kế AI Summary cụ thể.

## Cách cập nhật công việc

Mỗi thành viên cập nhật `00_project_management/TASK_BOARD.md` khi bắt đầu hoặc hoàn tất công việc, ghi quyết định đã được nhóm xác nhận vào `DECISION_LOG.md`, và không đưa secret vào repository.
