# Bối cảnh dự án

## Bối cảnh và mục tiêu

Đây là mini project môn Business Intelligence của nhóm 4 thành viên. Hệ thống BI phân tích hiệu suất giao hàng chặng cuối từ Amazon Delivery Dataset trên Kaggle, hướng đến luồng dữ liệu, mô hình phân tích, dashboard và AI Summary có thể kiểm chứng.

## Dataset hiện hành

| Thuộc tính | Giá trị |
|---|---|
| Dataset | Amazon Delivery Dataset |
| Người đăng Kaggle | Sujal Suthar |
| Nguồn | <https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset> |
| Chủ đề | Hiệu suất giao hàng chặng cuối |
| CSV | `01_data/raw/amazon_delivery.csv` |
| ZIP | `01_data/raw/archive/amazon_delivery_original.zip` |
| Quy mô | 43.739 dòng, 16 cột |
| Khoảng ngày | 2022-02-11 đến 2022-04-06 |
| Active Day | 44 |

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

## Business Baseline đã duyệt

- Data Profiling v2 đã review và đóng; các open decision của profiling đã được chuyển thành quyết định Business/KPI hoặc đầu vào cho MOD/LOAD.
- Grain nghiệp vụ: một dòng đại diện cho một bản ghi giao hàng nguồn duy nhất, nhận diện bởi `Order_ID`; không khẳng định completed delivery.
- Người dùng chính: Delivery Operations Manager.
- Người dùng phụ: Area/Regional Operations Manager và BI Analyst hoặc Data Quality Analyst.
- Có đúng 8 Business Questions và đúng 10 KPI chính.
- Delivery Time dùng phút theo project assumption; metadata Kaggle truy xuất được chưa xác nhận đơn vị.
- Không có SLA hoặc On-time Delivery Rate; Share Above Baseline P90 dùng ngưỡng nội bộ 195 phút.
- Quality rules đã khóa cho missing, rollover, rating, age, categorical values, coordinates, distance và privacy.

## Logical Dimensional Model đã duyệt

- Grain Data Warehouse: một dòng trong `dw.fact_delivery` đại diện cho một bản ghi giao hàng nguồn duy nhất, nhận diện bởi `Order_ID` hợp lệ và duy nhất trong snapshot.
- Một Fact logical: `dw.fact_delivery`; `Order_ID` là degenerate business key.
- Năm Dimension logical: `dw.dim_date`, `dw.dim_delivery_condition`, `dw.dim_vehicle`, `dw.dim_area`, `dw.dim_category`.
- Dimension dùng surrogate key số nguyên; Unknown Member dùng key `0`.
- `dim_date` là dimension tĩnh; các Dimension phân loại dùng SCD Type 1.
- Relationships là Dimension 1 → Fact nhiều, filter một chiều.
- Không tạo `dim_agent`, `dim_time` hoặc Location Dimension từ exact coordinates.

## Nội dung chưa chốt

- Star Schema diagram chi tiết và Source-to-Target Mapping.
- Kiểu dữ liệu vật lý cuối cùng và thuật toán technical key.
- Batch, watermark, idempotency và rerun design chính thức.
- Kiến trúc triển khai và phương án chia sẻ SQL Server.
- Dashboard, AI Summary và LLM provider.

## Trạng thái triển khai

Task 1–6, Handoff và `MOD-01` đã hoàn thành. Task tiếp theo là `MOD-02`. Logical model đã được duyệt nhưng chưa có Fact/Dimension vật lý, Star Schema diagram, pipeline, SQL, dbt model, Power BI hoặc AI component được triển khai.
