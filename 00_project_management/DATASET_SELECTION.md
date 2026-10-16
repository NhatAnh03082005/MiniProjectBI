# Dataset Selection v2 — Amazon Delivery Dataset

## 1. Thông tin dataset

| Thuộc tính | Giá trị |
|---|---|
| Tên dataset | Amazon Delivery Dataset |
| Người đăng Kaggle | Sujal Suthar |
| Nguồn | <https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset> |
| License | MIT, đã xác minh trong `DATA_PROFILE_AMAZON_DELIVERY.md` |
| Chủ đề | Hiệu suất giao hàng chặng cuối |
| Bối cảnh BI | Hệ thống BI phân tích hiệu suất giao hàng chặng cuối dựa trên Amazon Delivery Dataset từ Kaggle. |
| CSV | `01_data/raw/amazon_delivery.csv` |
| ZIP | `01_data/raw/archive/amazon_delivery_original.zip` |
| Số file raw | 2: một CSV và một ZIP archive |
| Quy mô | 43.739 dòng, không tính header; 16 cột |
| Khoảng ngày | 2022-02-11 đến 2022-04-06 |
| Độ phủ | 44 ngày có dữ liệu trong 3 tháng |
| SHA-256 CSV | `B922DFBDFED11AC2C9508C9E915326364FC95A2D00440B4C3E01E56BFFB6A4ED` |
| SHA-256 ZIP | `0ADD736B4AFD2A616856003CBC736F05AFD02242AC4E3F416F5C07FC53EB25A8` |

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

### 16 cột nguồn

`Order_ID`, `Agent_Age`, `Agent_Rating`, `Store_Latitude`, `Store_Longitude`, `Drop_Latitude`, `Drop_Longitude`, `Order_Date`, `Order_Time`, `Pickup_Time`, `Weather`, `Traffic`, `Vehicle`, `Area`, `Delivery_Time`, `Category`.

## 2. Grain nghiệp vụ

> Một dòng đại diện cho một bản ghi giao hàng nguồn duy nhất, được nhận diện bởi `Order_ID`.

Trong snapshot, 43.739/43.739 dòng có `Order_ID` hợp lệ và duy nhất. Dataset không có delivery status, attempt ID hoặc event history nên không gọi chắc chắn mỗi dòng là completed delivery. Grain Data Warehouse vẫn thuộc MOD-01.

## 3. Chấm điểm lựa chọn

| Tiêu chí | Điểm tối đa | Điểm | Giải thích |
|---|---:|---:|---|
| Có cột ngày/thời gian | 2 | 2,0 | Có Order Date, Order Time, Pickup Time; đã có rule missing và rollover. |
| Có measures/KPI | 2 | 2,0 | Delivery Time, Rating, pickup delay và valid distance. |
| Có nhiều chiều phân tích | 2 | 2,0 | Weather, Traffic, Vehicle, Area, Category và date/time. |
| Có business key | 1 | 1,0 | `Order_ID` hợp lệ và duy nhất 43.739/43.739. |
| Dữ liệu đủ lớn | 1 | 1,0 | 43.739 dòng. |
| Nghiệp vụ đủ rõ | 1 | 0,5 | Last-mile delivery rõ; provenance và đơn vị vẫn cần cảnh báo. |
| Dễ mô phỏng Incremental Load | 1 | 1,0 | Có ba tháng và Date/Time; load design chưa triển khai. |
| **Tổng** | **10** | **9,5** | Phù hợp Business Intelligence trong phạm vi project. |

## 4. Khả năng phân tích

- Date, month, weekday, order hour và time period.
- Weather, Traffic, Vehicle, Area và Category.
- Age group, valid rating group và pickup delay band.
- Haversine Distance trên các dòng đạt quality rule.

Không tạo `dim_agent` chỉ từ Age và Rating. Fact/Dimension vật lý chưa được chốt.

## 5. KPI baseline

Business Baseline có đúng 10 KPI chính: Total Deliveries; Average, Median, P90 và P95 Delivery Time; Average Pickup Delay; Average Valid Delivery Distance; Average Valid Agent Rating; Average Deliveries per Active Day; Share Above Baseline P90.

Delivery Time dùng phút theo project assumption nhưng metadata Kaggle truy xuất được chưa xác nhận đơn vị. Share Above Baseline P90 dùng ngưỡng cố định 195 phút, là ngưỡng thống kê nội bộ chứ không phải SLA. Không tạo On-time Delivery Rate.

## 6. Phương án load đề xuất

| Batch | Khoảng dữ liệu | Số dòng |
|---|---|---:|
| Full Load | 2022-02-11 đến 2022-02-18 | 6.982 |
| Incremental 1 | 2022-03-01 đến 2022-03-31 | 30.658 |
| Incremental 2 | 2022-04-01 đến 2022-04-06 | 6.099 |
| **Tổng** | 2022-02-11 đến 2022-04-06 | **43.739** |

Đây chỉ là phương án đề xuất. Chưa tạo batch, pipeline, watermark hoặc rerun design chính thức.

## 7. Hạn chế

- Tên dataset không chứng minh provenance vận hành chính thức.
- Chỉ có 44 Active Day; không đủ kết luận mùa vụ hoặc xu hướng dài hạn.
- Đơn vị Delivery Time dựa trên project assumption.
- Không có delivery status, attempt ID, Agent ID hoặc SLA.
- Missing, rating 6,0, tuổi dưới 18, categorical whitespace và coordinate anomalies cần quality flags/rules đã khóa.
- Drop coordinate có rủi ro privacy.
- Grocery có phân bố Delivery Time khác biệt nhưng chưa đủ bằng chứng để kết luận nguyên nhân.

## 8. Trạng thái

- Dataset Selection v2: **Done**.
- Data Profiling v2: **Done**.
- Business Baseline v2: **Approved**.
- Dimensional Modeling: **Todo**.

Chưa chốt grain Data Warehouse, tên vật lý Fact/Dimension, Star Schema hoặc Source-to-Target Mapping.
