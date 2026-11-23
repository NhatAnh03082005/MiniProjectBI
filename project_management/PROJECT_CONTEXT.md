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
| CSV | `data/raw/amazon_delivery.csv` |
| ZIP | `data/raw/archive/amazon_delivery_original.zip` |
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

## Trạng thái triển khai hiện hành — 22/11/2026

- Có Mage full/incremental current-state upsert theo Order_ID + row_hash, không thêm LSET/CET.
- Cả hai pipeline nối Verify → dbt build (models/tests) → đối soát DDS; auth SQL/Windows theo cấu hình chung.
- Có staging/audit.load_batch và audit.dbt_run; nguồn và phạm vi audit được mô tả trong Data Dictionary, chưa bao phủ mọi lỗi trước exporter.
- dbt có 11 model, 5 Dimension và Fact 33 cột; key-map giữ surrogate keys qua rebuild. Required/range hiện khác một số giả định missing ban đầu.
- Có 4 trang Power BI nghiệp vụ và ứng dụng AI Gemini; trang giám sát/lập lịch là hạng mục riêng, không tự đánh dấu hoàn tất trong task metadata.
- Đã có ảnh kết quả demo do người dùng chạy, không đồng nghĩa task metadata vừa chạy lại hệ thống.
- [Data Dictionary](DATA_DICTIONARY.md), [mapping](SOURCE_TO_TARGET_MAPPING.md), [Data Contract](DATA_CONTRACT.md) và [metadata handoff](../report/METADATA_AUDIT_HANDOFF.md) mô tả triển khai hiện hành. Task board/thiết kế ban đầu giữ làm lịch sử kế hoạch.
