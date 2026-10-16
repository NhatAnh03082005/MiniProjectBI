# Data Profile - Amazon Delivery Dataset

## 1. Executive Summary

- File được phân tích: `01_data/raw/amazon_delivery.csv`.
- Dataset có 43.739 dòng dữ liệu và 16 cột.
- Dữ liệu bao phủ 44 ngày có bản ghi, từ 2022-02-11 đến 2022-04-06.
- CSV dùng UTF-8 không BOM, dấu phẩy làm delimiter và có header đúng 16 cột.
- `Order_ID` có 43.739 giá trị hợp lệ, duy nhất, không trống, không thừa khoảng trắng và không có collision khi bỏ phân biệt hoa/thường.
- Không có dòng trùng hoàn toàn.
- Có 91 dòng mang chuỗi null-like `NaN` đồng thời ở `Order_Time`, `Weather`, `Traffic`; `Agent_Rating` có 54 giá trị trống.
- `Delivery_Time` parse numeric được 43.739/43.739 dòng, từ 10 đến 270. CSV không chứa đơn vị trong giá trị. Metadata Kaggle truy xuất được không mô tả đơn vị, vì vậy đơn vị cần nhóm xác nhận trước khi chốt KPI.
- `Pickup_Time < Order_Time` ở 828 dòng. Nếu giả định pickup xảy ra ngày kế tiếp, toàn bộ pickup delay hợp lệ và chỉ nhận ba giá trị 5, 10, 15 phút. Đây là giả định chuyển đổi cần nhóm xác nhận.
- Bốn cột tọa độ đều parse numeric và nằm trong miền kỹ thuật latitude/longitude, nhưng có 3.505 store coordinate `(0,0)` và 188 dòng có store coordinate âm tạo khoảng cách Haversine trên 1.000 km. Không tự sửa dấu hoặc thay thế tọa độ.
- Dataset phù hợp hơn cho bài toán BI giao hàng chặng cuối vì có thời gian, điều kiện vận hành, phương tiện, khu vực, category, rating và tọa độ. Rủi ro lớn nhất là provenance, đơn vị `Delivery_Time`, quy tắc rollover và chất lượng tọa độ.

Kết quả này chỉ là profiling. Chưa chốt Business Baseline v2, Fact, Dimension, KPI, SLA hoặc thiết kế tải dữ liệu.

## 2. Dataset Source and Provenance

| Thuộc tính | Kết quả |
|---|---|
| Tên theo người đăng | Amazon Delivery Dataset |
| Người đăng | Sujal Suthar |
| Nguồn | Kaggle: <https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset> |
| Subtitle từ metadata công khai | Analyzing Last-Mile Logistics and Delivery Performance |
| License từ metadata công khai | MIT |
| Ngày metadata ghi nhận cập nhật | 2024-07-02 |
| Bối cảnh dự kiến | Phân tích hiệu suất giao hàng chặng cuối |
| Trạng thái bối cảnh | Định hướng, chưa phải Business Baseline v2 |

Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Chưa có bằng chứng trong project để khẳng định đây là dữ liệu vận hành chính thức của Amazon.

Metadata công khai của Kaggle mô tả tổng quát dữ liệu giao hàng nhưng không cung cấp data dictionary có đơn vị của `Delivery_Time`. Một [nghiên cứu thứ cấp dùng cùng dataset](https://dergipark.org.tr/tr/download/article-file/4114868) mô tả miền 10–270 là phút. Vì CSV không chứa đơn vị và metadata nguồn truy xuất được không xác nhận trường này, báo cáo không xem “phút” là quyết định chính thức.

## 3. Files and Checksums

| File | Kích thước | SHA-256 trước phân tích | Đối chiếu dự kiến |
|---|---:|---|---|
| `01_data/raw/amazon_delivery.csv` | 5.971.175 byte | `B922DFBDFED11AC2C9508C9E915326364FC95A2D00440B4C3E01E56BFFB6A4ED` | Khớp |
| `01_data/raw/archive/amazon_delivery_original.zip` | 1.606.558 byte | `0ADD736B4AFD2A616856003CBC736F05AFD02242AC4E3F416F5C07FC53EB25A8` | Khớp |

ZIP chứa một file `amazon_delivery.csv`. Không giải nén lại và không chỉnh sửa CSV/ZIP trong quá trình profiling.

## 4. Technical Structure

| Thuộc tính | Kết quả |
|---|---|
| Encoding | UTF-8 không BOM; đọc strict thành công |
| Dấu phân cách | Dấu phẩy `,` |
| Header | Có |
| Dòng dữ liệu | 43.739, không tính header |
| Số cột | 16 |
| Thứ tự cột | `Order_ID`, `Agent_Age`, `Agent_Rating`, `Store_Latitude`, `Store_Longitude`, `Drop_Latitude`, `Drop_Longitude`, `Order_Date`, `Order_Time`, `Pickup_Time`, `Weather`, `Traffic`, `Vehicle`, `Area`, `Delivery_Time`, `Category` |
| Kiểu đọc ban đầu | Tất cả là chuỗi khi đọc CSV để bảo toàn null-like string và khoảng trắng |

### Năm dòng mẫu giới hạn

`Order_ID` được che một phần và tọa độ được làm tròn ba chữ số chỉ trong bảng minh họa. Raw data không bị thay đổi.

| Order ID | Age | Rating | Store lat/lon | Drop lat/lon | Date | Order/Pickup | Weather | Traffic | Vehicle | Area | Delivery Time | Category |
|---|---:|---:|---|---|---|---|---|---|---|---|---:|---|
| `ialx***618` | 37 | 4.9 | 22.745 / 75.892 | 22.765 / 75.912 | 2022-03-19 | 11:30 / 11:45 | Sunny | High | motorcycle | Urban | 120 | Clothing |
| `akqg***122` | 34 | 4.5 | 12.913 / 77.683 | 13.043 / 77.813 | 2022-03-25 | 19:45 / 19:50 | Stormy | Jam | scooter | Metropolitian | 165 | Electronics |
| `njpu***536` | 23 | 4.4 | 12.914 / 77.678 | 12.924 / 77.688 | 2022-03-19 | 08:30 / 08:45 | Sandstorms | Low | motorcycle | Urban | 130 | Sports |
| `rjto***700` | 38 | 4.7 | 11.004 / 76.976 | 11.054 / 77.026 | 2022-04-05 | 18:00 / 18:10 | Sunny | Medium | motorcycle | Metropolitian | 105 | Cosmetics |
| `zguw***638` | 32 | 4.6 | 12.973 / 80.250 | 13.013 / 80.290 | 2022-03-26 | 13:30 / 13:45 | Cloudy | High | scooter | Metropolitian | 150 | Toys |

## 5. Preliminary Data Dictionary

Tên chuẩn hóa và logical type dưới đây chỉ là đề xuất cho task sau.

| Raw column | Standardized name đề xuất | Source type | Logical type đề xuất | Ý nghĩa dự kiến | Ví dụ | Nullable quan sát | Ghi chú chất lượng |
|---|---|---|---|---|---|---|---|
| `Order_ID` | `order_id` | string | varchar(13) | Mã bản ghi order/delivery nguồn | `ialx566343618` | Không | Duy nhất; chưa phải DW primary key |
| `Agent_Age` | `agent_age` | string | smallint | Tuổi agent theo nguồn | `37` | Không | Có 38 giá trị 15 và 53 giá trị 50; cần xác nhận nghiệp vụ |
| `Agent_Rating` | `agent_rating` | string | decimal(3,1) | Rating agent theo nguồn | `4.9` | Có | 54 trống; có 38 giá trị 1.0 và 53 giá trị 6.0; thang điểm chưa xác nhận |
| `Store_Latitude` | `store_latitude` | string | decimal(10,6) | Latitude điểm store | `22.745049` | Không | 3.505 cặp store `(0,0)`; 188 latitude âm |
| `Store_Longitude` | `store_longitude` | string | decimal(10,6) | Longitude điểm store | `75.892471` | Không | 3.505 cặp store `(0,0)`; 27 longitude âm |
| `Drop_Latitude` | `drop_latitude` | string | decimal(10,6) | Latitude điểm giao | `22.765049` | Không | Không có 0 hoặc giá trị âm |
| `Drop_Longitude` | `drop_longitude` | string | decimal(10,6) | Longitude điểm giao | `75.912471` | Không | Không có 0 hoặc giá trị âm |
| `Order_Date` | `order_date` | string | date | Ngày ghi nhận order | `2022-03-19` | Không | 100% format `YYYY-MM-DD` |
| `Order_Time` | `order_time` | string | time | Giờ order theo nguồn | `11:30:00` | Có | 91 chuỗi `NaN` có khoảng trắng |
| `Pickup_Time` | `pickup_time` | string | time | Giờ pickup theo nguồn | `11:45:00` | Không | 828 giá trị nhỏ hơn Order Time |
| `Weather` | `weather` | string | varchar | Điều kiện thời tiết | `Sunny` | Có | 91 chuỗi `NaN` |
| `Traffic` | `traffic` | string | varchar | Mức traffic | `High` | Có | Mọi dòng có trailing whitespace; 91 chuỗi `NaN` |
| `Vehicle` | `vehicle_type` | string | varchar | Loại phương tiện | `motorcycle` | Không | 40.181 dòng có trailing whitespace |
| `Area` | `area_type` | string | varchar | Nhóm khu vực theo nguồn | `Metropolitian` | Không | 42.601 dòng có trailing whitespace; giữ nguyên lỗi chính tả nguồn |
| `Delivery_Time` | `delivery_time` | string | integer/decimal duration | Thời lượng giao theo nguồn | `120` | Không | Numeric 100%; đơn vị chưa được nguồn xác nhận trong project |
| `Category` | `category` | string | varchar | Category của item/delivery theo nguồn | `Clothing` | Không | 16 giá trị ổn định; ý nghĩa taxonomy cần xác nhận |

## 6. Null and Duplicate Analysis

Null-like string gồm `NaN`, `NA`, `N/A`, `null`, `None`, `Unknown`, `-`, so sánh sau khi trim và bỏ phân biệt hoa/thường.

| Column | Null vật lý | Empty | Whitespace-only | Null-like string | Tỷ lệ thiếu | Nhận xét |
|---|---:|---:|---:|---:|---:|---|
| Order_ID | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |
| Agent_Age | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |
| Agent_Rating | 0 | 54 | 0 | 0 | 0,123% | Thiếu thật dưới dạng chuỗi rỗng |
| Store_Latitude | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ nhưng có giá trị bất thường |
| Store_Longitude | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ nhưng có giá trị bất thường |
| Drop_Latitude | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |
| Drop_Longitude | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |
| Order_Date | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |
| Order_Time | 0 | 0 | 0 | 91 | 0,208% | `NaN` kèm trailing whitespace |
| Pickup_Time | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |
| Weather | 0 | 0 | 0 | 91 | 0,208% | `NaN` là missing marker, không coi là weather hợp lệ |
| Traffic | 0 | 0 | 0 | 91 | 0,208% | `NaN` là missing marker; mọi dòng có trailing whitespace |
| Vehicle | 0 | 0 | 0 | 0 | 0,000% | Có trailing whitespace trên 40.181 dòng |
| Area | 0 | 0 | 0 | 0 | 0,000% | Có trailing whitespace trên 42.601 dòng |
| Delivery_Time | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |
| Category | 0 | 0 | 0 | 0 | 0,000% | Đầy đủ |

91 dòng thiếu `Order_Time`, `Weather`, `Traffic` là cùng một tập bản ghi. Không có dòng nào trong nhóm này đồng thời thiếu `Agent_Rating`. Có 0 dòng trùng hoàn toàn và 0 nhóm dòng trùng.

## 7. Order ID Analysis

| Kiểm tra | Kết quả |
|---|---:|
| Tổng dòng | 43.739 |
| `Order_ID` phân biệt | 43.739 |
| Null/rỗng/null-like | 0 |
| Thừa khoảng trắng | 0 |
| Dòng thuộc ID trùng | 0 |
| ID trùng với dữ liệu khác nhau | 0 |
| Phân biệt sau case-fold | 43.739 |
| Collision do hoa/thường | 0 |
| Độ dài | 13 ký tự trên 43.739/43.739 dòng |
| Pattern | Chữ cái theo sau bởi chữ số trên 43.739/43.739 dòng |

Đề xuất grain nguồn với mức tin cậy cao:

> Một dòng đại diện cho một bản ghi giao hàng duy nhất, được nhận diện bởi `Order_ID`.

Bằng chứng là mỗi dòng có một ID hợp lệ và duy nhất, không có dòng trùng hoặc một ID xuất hiện nhiều lần. Giới hạn: tên `Order_ID` không đủ để chứng minh một order và một delivery luôn là cùng một thực thể nghiệp vụ, hoặc không có retry/attempt ngoài snapshot. `Order_ID` chỉ được đề xuất làm business key của grain nguồn, chưa phải primary key vật lý trong Data Warehouse.

## 8. Date and Time Analysis

### 8.1. Order Date

- 43.739/43.739 giá trị khớp regex và parse thành công theo `YYYY-MM-DD`.
- Min: 2022-02-11; max: 2022-04-06.
- 44 ngày phân biệt, 3 tháng, 1 năm.
- Số dòng mỗi ngày: min 819, max 1.141, mean 994,07.
- Có 11 ngày lịch không có bản ghi: 2022-02-19 đến 2022-02-28 và 2022-03-22. Không đủ bằng chứng để gọi đây là dữ liệu bị thiếu hay ngày không phát sinh.

| Năm | Số dòng |
|---|---:|
| 2022 | 43.739 |

| Tháng | Số dòng |
|---|---:|
| 2022-02 | 6.982 |
| 2022-03 | 30.658 |
| 2022-04 | 6.099 |

| ISO week | Số dòng |
|---|---:|
| 2022-W06 | 2.701 |
| 2022-W07 | 4.281 |
| 2022-W09 | 6.169 |
| 2022-W10 | 7.224 |
| 2022-W11 | 7.092 |
| 2022-W12 | 6.123 |
| 2022-W13 | 7.220 |
| 2022-W14 | 2.929 |

Không có W08 vì khoảng 2022-02-19 đến 2022-02-28 không có bản ghi.

<details>
<summary>Số dòng theo 44 ngày có dữ liệu</summary>

| Date | Rows | Date | Rows |
|---|---:|---|---:|
| 2022-02-11 | 940 | 2022-03-11 | 1.094 |
| 2022-02-12 | 837 | 2022-03-12 | 931 |
| 2022-02-13 | 924 | 2022-03-13 | 1.123 |
| 2022-02-14 | 826 | 2022-03-14 | 931 |
| 2022-02-15 | 904 | 2022-03-15 | 1.141 |
| 2022-02-16 | 827 | 2022-03-16 | 955 |
| 2022-02-17 | 905 | 2022-03-17 | 1.085 |
| 2022-02-18 | 819 | 2022-03-18 | 932 |
| 2022-03-01 | 1.076 | 2022-03-19 | 1.103 |
| 2022-03-02 | 969 | 2022-03-20 | 945 |
| 2022-03-03 | 1.119 | 2022-03-21 | 1.107 |
| 2022-03-04 | 944 | 2022-03-23 | 922 |
| 2022-03-05 | 1.112 | 2022-03-24 | 1.112 |
| 2022-03-06 | 949 | 2022-03-25 | 931 |
| 2022-03-07 | 1.093 | 2022-03-26 | 1.119 |
| 2022-03-08 | 919 | 2022-03-27 | 932 |
| 2022-03-09 | 1.117 | 2022-03-28 | 1.092 |
| 2022-03-10 | 947 | 2022-03-29 | 938 |
| 2022-03-30 | 1.091 | 2022-04-03 | 1.133 |
| 2022-03-31 | 929 | 2022-04-04 | 905 |
| 2022-04-01 | 1.092 | 2022-04-05 | 1.106 |
| 2022-04-02 | 945 | 2022-04-06 | 918 |

</details>

### 8.2. Order Time và Pickup Time

| Kiểm tra | Order Time | Pickup Time |
|---|---:|---:|
| Parse thành công | 43.648 | 43.739 |
| Parse thất bại/missing | 91 | 0 |
| Min | 00:00:00 | 00:00:00 |
| Max | 23:55:00 | 23:55:00 |
| Ngoài miền 24 giờ | 0 | 0 |
| Có giây khác 0 | 0 | 0 |
| Có AM/PM | 0 | 0 |
| Format | 24 giờ `HH:MM:SS` | 24 giờ `HH:MM:SS` |

## 9. Pickup Delay Feasibility

`pickup_delay_minutes = Pickup Timestamp - Order Timestamp` có thể tạo được nếu ghép Date và Time, nhưng cần xử lý qua ngày.

| Kịch bản | Valid | Min | Max | Mean | Median | P90 | P95 | Negative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Ghép cùng ngày, không rollover | 43.648 | -1.435 | 15 | -17,33 | 10 | 15 | 15 | 828 |
| Nếu `Pickup_Time < Order_Time`, cộng một ngày | 43.648 | 5 | 15 | 9,99 | 10 | 15 | 15 | 0 |

Sau rollover giả định: 14.617 dòng có delay 5 phút, 14.490 dòng có 10 phút, 14.541 dòng có 15 phút; không có giá trị trên 180 phút. 91 dòng thiếu `Order_Time` không thể tính.

Quy tắc “khi `Pickup_Time < Order_Time`, pickup thuộc ngày kế tiếp” hợp lý về mặt thời gian nhưng không có pickup date riêng để xác minh. Đây là giả định chuyển đổi cần nhóm xác nhận, không phải sự thật trực tiếp từ nguồn.

## 10. Delivery Time Analysis

| Chỉ số | Kết quả |
|---|---:|
| Parse numeric | 43.739/43.739 |
| Có ký tự đơn vị trong chuỗi | 0 |
| Distinct | 89 |
| Min | 10 |
| Max | 270 |
| Mean | 124,9056 |
| Median | 125 |
| Q1 | 90 |
| Q3 | 160 |
| IQR | 70 |
| P90 | 195 |
| P95 | 215 |
| P99 | 245 |
| Bằng 0 | 0 |
| Âm | 0 |
| IQR bounds | -15 đến 265 |
| IQR outlier | 79 |

Các giá trị xuất hiện nhiều nhất: 130 (1.919 dòng), 125 (1.856), 140 (1.791), 135 (1.787), 145 (1.754), 95 (1.629), 75 (1.620), 90 (1.589), 80 (1.532), 85 (1.523).

Đơn vị của `Delivery_Time` cần được nhóm xác nhận trước khi chốt KPI. Không tạo On-time Delivery Rate vì dataset không có SLA, promised time hoặc expected delivery time.

Nếu dùng ngưỡng thống kê nội bộ để thảo luận, `> P90 (195)` có 4.100 dòng và `> P95 (215)` có 2.086 dòng. Đây không phải tỷ lệ trễ theo nghiệp vụ.

## 11. Agent Analysis

### 11.1. Agent Age

| Chỉ số | Kết quả |
|---|---:|
| Parse numeric | 43.739/43.739 |
| Distinct | 22 |
| Min / Max | 15 / 50 |
| Mean | 29,5671 |
| Median | 30 |
| Q1 / Q3 | 25 / 35 |
| IQR bounds | 10 đến 50 |
| IQR outlier | 0 |
| Bằng 0 / âm | 0 / 0 |

Tuổi 15 xuất hiện 38 lần và tuổi 50 xuất hiện 53 lần; các tuổi còn lại tập trung 20–39. Không tự xóa hoặc thay thế hai nhóm hiếm này. Cần xác nhận tuổi tối thiểu/tối đa hợp lệ theo bối cảnh nghiệp vụ.

### 11.2. Agent Rating

| Chỉ số | Kết quả |
|---|---:|
| Parse numeric | 43.685/43.739 |
| Missing | 54 |
| Distinct numeric | 28 |
| Min / Max | 1,0 / 6,0 |
| Mean | 4,6338 |
| Median | 4,7 |
| Q1 / Q3 | 4,5 / 4,9 |
| IQR bounds | 3,9 đến 5,5 |
| IQR outlier | 1.223 |
| Giá trị 1,0 | 38 |
| Giá trị 6,0 | 53 |

38 dòng tuổi 15 đồng thời có rating 1,0; 53 dòng tuổi 50 đồng thời có rating 6,0. Dữ liệu không đủ để tự khẳng định thang 1–5 hoặc sửa 6,0. IQR gắn cờ nhiều rating thấp nhưng không chứng minh chúng sai.

## 12. Coordinate and Distance Analysis

| Kiểm tra | Kết quả |
|---|---:|
| Bốn tọa độ parse numeric | 43.739/43.739 |
| Latitude ngoài `[-90,90]` | 0 |
| Longitude ngoài `[-180,180]` | 0 |
| Store `(0,0)` | 3.505 |
| Drop `(0,0)` | 0 |
| Store và Drop trùng hoàn toàn | 0 |
| Store coordinate pair phân biệt | 522 |
| Drop coordinate pair phân biệt | 4.367 |
| Store latitude âm | 188 |
| Store longitude âm | 27 |

### Haversine profiling

| Phạm vi | N | Min km | Max km | Mean km | Median km | P90 km | P95 km | IQR outlier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Tất cả dòng | 43.739 | 1,465 | 19.692,702 | 38,562 | 9,220 | 19,363 | 20,071 | 188 |
| Chỉ store/drop có tọa độ dương và store khác `(0,0)` | 40.046 | 1,465 | 20,970 | 9,717 | 9,193 | 19,088 | 19,917 | 0 |

Có đúng 188 khoảng cách trên 50 km, trên 100 km và trên 1.000 km; chúng trùng với nhóm store coordinate âm và tạo giá trị tối đa gần 19.693 km. Không tự đổi dấu tọa độ vì chưa biết quy ước nguồn. Nhóm `(0,0)` cũng không phù hợp để hiển thị như vị trí thực dù khoảng cách số học có thể nhỏ.

`delivery_distance_km` khả thi như derived measure cho profiling, nhưng chỉ nên chính thức hóa sau khi chốt quy tắc loại/flag tọa độ `(0,0)` và tọa độ âm. Tương quan Pearson distance–Delivery Time là -0,0019 trên toàn bộ dữ liệu, nhưng tăng thành 0,2781 trên 40.046 dòng tọa độ dương, khác `(0,0)`. Chênh lệch cho thấy anomaly tọa độ làm sai lệch phân tích.

## 13. Categorical Analysis

Tất cả category được báo cáo sau trim để nhìn rõ giá trị. Không có collision do hoa/thường và không tự hợp nhất category.

### Weather

| Giá trị | Dòng | Tỷ lệ |
|---|---:|---:|
| Fog | 7.440 | 17,01% |
| Stormy | 7.374 | 16,86% |
| Cloudy | 7.288 | 16,66% |
| Sandstorms | 7.245 | 16,56% |
| Windy | 7.223 | 16,51% |
| Sunny | 7.078 | 16,18% |
| `NaN` | 91 | 0,21% |

Accepted values có thể đề xuất là Fog, Stormy, Cloudy, Sandstorms, Windy, Sunny; `NaN` phải xử lý như missing.

### Traffic

| Giá trị | Dòng | Tỷ lệ |
|---|---:|---:|
| Low | 14.999 | 34,29% |
| Jam | 13.725 | 31,38% |
| Medium | 10.628 | 24,30% |
| High | 4.296 | 9,82% |
| `NaN` | 91 | 0,21% |

Mọi raw value của `Traffic` có trailing whitespace. Accepted values có thể đề xuất sau trim là Low, Jam, Medium, High; `NaN` là missing.

### Vehicle

| Giá trị | Dòng | Tỷ lệ |
|---|---:|---:|
| motorcycle | 25.527 | 58,36% |
| scooter | 14.639 | 33,47% |
| van | 3.558 | 8,13% |
| bicycle | 15 | 0,03% |

40.181 raw values có trailing whitespace. `bicycle` là category hiếm nhưng chưa có bằng chứng là lỗi.

### Area

| Giá trị | Dòng | Tỷ lệ |
|---|---:|---:|
| Metropolitian | 32.698 | 74,76% |
| Urban | 9.751 | 22,29% |
| Other | 1.138 | 2,60% |
| Semi-Urban | 152 | 0,35% |

42.601 raw values có trailing whitespace. `Metropolitian` được giữ đúng như nguồn; việc chuẩn hóa chính tả cần quyết định riêng.

### Category

| Giá trị | Dòng | Tỷ lệ |
|---|---:|---:|
| Electronics | 2.849 | 6,51% |
| Books | 2.824 | 6,46% |
| Jewelry | 2.802 | 6,41% |
| Toys | 2.781 | 6,36% |
| Skincare | 2.772 | 6,34% |
| Snacks | 2.770 | 6,33% |
| Outdoors | 2.747 | 6,28% |
| Apparel | 2.726 | 6,23% |
| Sports | 2.719 | 6,22% |
| Grocery | 2.691 | 6,15% |
| Pet Supplies | 2.690 | 6,15% |
| Home | 2.685 | 6,14% |
| Cosmetics | 2.677 | 6,12% |
| Kitchen | 2.673 | 6,11% |
| Clothing | 2.667 | 6,10% |
| Shoes | 2.666 | 6,10% |

Category phân bố khá đều, không có giá trị dưới 1%.

## 14. Numerical and Outlier Analysis

| Trường/measure | Min | Q1 | Median | Q3 | Max | IQR outlier | Nhận xét |
|---|---:|---:|---:|---:|---:|---:|---|
| Agent Age | 15 | 25 | 30 | 35 | 50 | 0 | 15 và 50 hiếm, cần xác nhận nghiệp vụ |
| Agent Rating | 1,0 | 4,5 | 4,7 | 4,9 | 6,0 | 1.223 | 54 missing; thang điểm chưa xác nhận |
| Delivery Time | 10 | 90 | 125 | 160 | 270 | 79 | Đơn vị chưa chốt |
| Pickup Delay, rollover giả định | 5 | 5 | 10 | 15 | 15 | 0 | Phụ thuộc giả định ngày kế tiếp |
| Haversine distance, toàn bộ | 1,465 | 4,663 | 9,220 | 13,682 | 19.692,702 | 188 | Outlier do store coordinate âm |

IQR chỉ là cờ thống kê. Không dòng nào bị xóa hoặc sửa dựa trên các cờ này.

## 15. Relationship and Consistency Analysis

Các bảng dưới đây là mô tả theo nhóm, không chứng minh quan hệ nhân quả. `Delivery_Time` giữ nguyên source unit chưa xác nhận.

### Weather và Traffic

| Nhóm | N | Mean | Median | P90 |
|---|---:|---:|---:|---:|
| Weather - Cloudy | 7.288 | 138,29 | 140 | 210 |
| Weather - Fog | 7.440 | 136,57 | 135 | 210 |
| Weather - Sandstorms | 7.245 | 123,24 | 125 | 185 |
| Weather - Stormy | 7.374 | 123,21 | 125 | 185 |
| Weather - Sunny | 7.078 | 103,66 | 100 | 160 |
| Weather - Windy | 7.223 | 123,66 | 125 | 185 |
| Traffic - High | 4.296 | 129,42 | 135 | 185 |
| Traffic - Jam | 13.725 | 147,76 | 150 | 220 |
| Traffic - Low | 14.999 | 101,35 | 100 | 145 |
| Traffic - Medium | 10.628 | 126,84 | 130 | 190 |

91 dòng null-like có mean 120,67 nhưng không phải category hợp lệ.

### Vehicle và Area

| Nhóm | N | Mean | Median | P90 |
|---|---:|---:|---:|---:|
| Vehicle - bicycle | 15 | 127,00 | 125 | 181 |
| Vehicle - motorcycle | 25.527 | 131,03 | 130 | 205 |
| Vehicle - scooter | 14.639 | 116,36 | 115 | 185 |
| Vehicle - van | 3.558 | 116,14 | 115 | 180 |
| Area - Metropolitian | 32.698 | 129,70 | 130 | 200 |
| Area - Other | 1.138 | 104,46 | 100 | 165 |
| Area - Semi-Urban | 152 | 238,55 | 245 | 269,5 |
| Area - Urban | 9.751 | 109,43 | 105 | 175 |

Nhóm bicycle và Semi-Urban có mẫu nhỏ, nên cần hiển thị N khi so sánh.

### Category

| Category | N | Mean | Median | P90 |
|---|---:|---:|---:|---:|
| Apparel | 2.726 | 132,05 | 130 | 200 |
| Books | 2.824 | 131,02 | 125 | 200 |
| Clothing | 2.667 | 130,48 | 125 | 200 |
| Cosmetics | 2.677 | 132,90 | 130 | 200 |
| Electronics | 2.849 | 130,84 | 125 | 195 |
| Grocery | 2.691 | 26,54 | 26 | 40 |
| Home | 2.685 | 130,96 | 125 | 200 |
| Jewelry | 2.802 | 130,75 | 125 | 199,5 |
| Kitchen | 2.673 | 132,33 | 130 | 195 |
| Outdoors | 2.747 | 131,06 | 125 | 200 |
| Pet Supplies | 2.690 | 131,29 | 130 | 195 |
| Shoes | 2.666 | 131,15 | 130 | 195 |
| Skincare | 2.772 | 132,03 | 130 | 200 |
| Snacks | 2.770 | 131,90 | 130 | 200 |
| Sports | 2.719 | 132,25 | 130 | 195 |
| Toys | 2.781 | 129,40 | 125 | 200 |

Grocery có phân bố rất khác các category còn lại. Đây có thể là logic nguồn hoặc cấu trúc dữ liệu tổng hợp; cần xác nhận trước khi diễn giải.

### Correlation Pearson

| Cặp biến | Correlation |
|---|---:|
| Agent Age và Delivery Time | 0,2546 |
| Agent Rating và Delivery Time | -0,2900 |
| Pickup Delay sau rollover giả định và Delivery Time | -0,0093 |
| Haversine distance và Delivery Time, toàn bộ | -0,0019 |
| Haversine distance và Delivery Time, tọa độ dương/non-zero | 0,2781 |

Các correlation chỉ mô tả đồng biến/nghịch biến tuyến tính trong snapshot. Không kết luận tuổi, rating, thời tiết, traffic hoặc khoảng cách gây ra thay đổi Delivery Time.

## 16. Privacy and Interpretation Risks

- Không có cột tên, email, số điện thoại hoặc địa chỉ văn bản.
- `Order_ID` là mã giao dịch, không phải PII trực tiếp theo cấu trúc quan sát được, nhưng vẫn nên coi là identifier cần hạn chế khi xuất báo cáo chi tiết.
- Drop coordinate có thể đại diện vị trí giao cụ thể. Không nên hiển thị tọa độ chính xác ở mức dòng trên dashboard công khai; nên cân nhắc làm tròn, binning, aggregation hoặc access control.
- Store coordinate `(0,0)` và tọa độ âm cho thấy vị trí có thể đã bị mã hóa, lỗi dấu hoặc có quy ước đặc biệt. Không suy ra vị trí thật.
- Tên dataset không chứng minh provenance vận hành chính thức của Amazon.
- Không dùng thống kê mô tả để khẳng định nguyên nhân hoặc đánh giá hiệu suất cá nhân của agent.

## 17. Proposed Grain

Đề xuất sơ bộ:

> Một dòng đại diện cho một bản ghi giao hàng duy nhất, được nhận diện bởi `Order_ID`.

| Thuộc tính | Đánh giá |
|---|---|
| Mức độ tin cậy | Cao ở mức snapshot nguồn |
| Bằng chứng | 43.739 dòng, 43.739 ID hợp lệ và duy nhất; không duplicate |
| Nhiều lần giao cùng Order ID | Không quan sát thấy trong file |
| Giới hạn | Không có attempt ID, delivery status hoặc event history; không chứng minh order và delivery luôn một-một ngoài snapshot |
| Trạng thái | Đề xuất profiling, chưa chốt modeling |

## 18. Preliminary Fact/Dimension Assessment

| Đối tượng | Đánh giá sơ bộ | Rủi ro/quyết định cần chốt |
|---|---|---|
| `fact_delivery` | Phù hợp làm Fact ứng viên cho một bản ghi giao nguồn | Cần chốt grain, key, measure, đơn vị Delivery Time và xử lý record lỗi |
| `dim_date` | Có căn cứ mạnh từ `Order_Date` | Chưa chốt date range, derived attributes và key |
| `dim_delivery_location` | Có thể gom Area và location attributes | Không có location ID; tọa độ `(0,0)`/âm; precise drop coordinate có rủi ro privacy |
| `dim_delivery_condition` | Có thể là junk dimension cho Weather và Traffic; Area cần đánh giá riêng | 91 missing đồng thời; chưa chốt Unknown Member; tránh tăng cardinality không cần thiết |
| `dim_vehicle` | 4 category ổn định, phù hợp Dimension nhỏ | bicycle chỉ 15 dòng; cần chính sách accepted values |
| `dim_product_category` | 16 category ổn định, có thể phù hợp nếu `Category` thực sự là nhóm sản phẩm | Nguồn chưa cung cấp taxonomy; không gọi là Product/SKU dimension trước khi xác nhận |
| `dim_agent` | Chưa đủ căn cứ | Không có Agent ID; Age/Rating không xác định một agent và có thể thay đổi |

Không có `Agent_ID`, vì vậy `Agent_Age` và `Agent_Rating` nên được cân nhắc giữ trong Fact, tách mini-dimension nếu có nhu cầu rõ ràng, hoặc mô hình khác sau khi hiểu nghiệp vụ. Không được tạo `dim_agent` chỉ từ Age/Rating.

Weather và Traffic có thể vào một junk dimension nhỏ; hai Dimension riêng có thể quá chi tiết cho cardinality hiện tại; giữ trong Fact cũng khả thi. Tọa độ có thể ở Fact để tính distance hoặc trong location structure nếu nhóm chốt business key và privacy rule. Đây đều là phương án, chưa phải quyết định.

## 19. Preliminary KPI Assessment

| KPI/measure | Khả năng | Yêu cầu/cảnh báo |
|---|---|---|
| Total Deliveries | Tính trực tiếp | `DISTINCTCOUNT(Order_ID)`; grain phải được chốt |
| Average Delivery Time | Tính trực tiếp | Numeric đầy đủ nhưng đơn vị chưa xác nhận |
| Median Delivery Time | Tính trực tiếp | Non-additive; đơn vị chưa xác nhận |
| P90 Delivery Time | Tính trực tiếp | 195 source units; không phải SLA |
| P95 Delivery Time | Tính trực tiếp | 215 source units; không phải SLA |
| Average Pickup Delay | Cần derived timestamp | Cần rollover assumption; 91 dòng không tính được |
| Median Pickup Delay | Cần derived timestamp | Cần rollover assumption; median dự kiến 10 phút |
| Average Delivery Distance | Cần derived column | Haversine; phải xử lý/flag tọa độ `(0,0)` và âm |
| Average Agent Rating | Tính trực tiếp có điều kiện | Loại 54 missing; cần xác nhận thang điểm và giá trị 6,0 |
| Delivery Time by Traffic | Tính trực tiếp sau trim | 91 missing; không suy luận nhân quả |
| Delivery Time by Weather | Tính trực tiếp | 91 missing; không suy luận nhân quả |
| Delivery Time by Vehicle | Tính trực tiếp sau trim | bicycle N=15, cần hiển thị sample size |
| Delivery Time by Area | Tính trực tiếp sau trim | Semi-Urban N=152; `Metropolitian` là nhãn nguồn |
| Delivery Time by Category | Tính trực tiếp | Grocery khác biệt mạnh, cần xác nhận logic nguồn |
| Slow Delivery Rate | Cần giả định | Chưa có SLA; có thể dùng ngưỡng nhóm đặt, P90/P95 nội bộ hoặc metadata nếu tìm được |
| On-time Delivery Rate | Không tính được | Không có promised/expected delivery time hoặc SLA |

Không chọn SLA trong profiling. Nếu dùng P90/P95, nhãn phải là “share above internal percentile threshold”, không phải late/on-time rate.

## 20. Full/Incremental Load Recommendation

Phương án sơ bộ dựa trên tháng, chưa tạo file batch:

| Batch | Khoảng ngày | Số dòng | Loại |
|---|---|---:|---|
| Full Load | 2022-02-11 đến 2022-02-18 | 6.982 | Nạp ban đầu |
| Incremental 1 | 2022-03-01 đến 2022-03-31 | 30.658 | Tăng thêm 1 |
| Incremental 2 | 2022-04-01 đến 2022-04-06 | 6.099 | Tăng thêm 2 |
| Tổng | 2022-02-11 đến 2022-04-06 | 43.739 | Đối soát |

- Watermark ứng viên: `Order_Date + Order_Time`; thêm `Order_ID` làm tie-breaker vì nhiều dòng cùng timestamp.
- 91 dòng thiếu `Order_Time` cần chính sách rõ: dùng date-level batch với `Order_ID` để đảm bảo idempotency, hoặc route sang quality handling; không tự đặt giờ giả.
- `Order_ID` dùng để phát hiện duplicate trong batch và với dữ liệu đã nạp.
- Rerun cùng batch phải upsert/skip theo business key đã chốt, không tạo trùng và không xóa lịch sử ngoài phạm vi batch.
- Khoảng ngày không liên tục phải được ghi nhận; không tự sinh record cho ngày không có dữ liệu.

## 21. Dataset Scoring

| Tiêu chí | Điểm tối đa | Điểm | Giải thích |
|---|---:|---:|---|
| Có cột ngày/thời gian | 2 | 2,0 | Có Order Date, Order Time, Pickup Time; có caveat rollover/missing |
| Có measures/KPI | 2 | 2,0 | Delivery Time, Rating, pickup delay và distance có thể phân tích |
| Có nhiều chiều phân tích | 2 | 2,0 | Weather, Traffic, Vehicle, Area, Category, date/time |
| Có business key | 1 | 1,0 | `Order_ID` duy nhất 43.739/43.739 |
| Dữ liệu đủ lớn | 1 | 1,0 | 43.739 dòng |
| Nghiệp vụ đủ rõ | 1 | 0,5 | Last-mile delivery rõ, nhưng provenance, unit và order/delivery semantics chưa chắc chắn |
| Dễ mô phỏng Incremental Load | 1 | 1,0 | Ba tháng và có Date/Time, dù có khoảng ngày trống và 91 time missing |
| **Tổng** | **10** | **9,5** | Phù hợp nếu xử lý các open decision trước baseline v2 |

Dataset đủ tốt để thay thế dataset cũ về độ phức tạp: quy mô lớn hơn, có temporal, geospatial, operational condition và nhiều vấn đề data quality thực tế. Nó phù hợp deadline nếu nhóm giới hạn task tiếp theo ở baseline một Fact, các Dimension có căn cứ và không mở rộng sang ML. Rủi ro lớn nhất là diễn giải quá mức tên Amazon, tự gán đơn vị/SLA, và dùng tọa độ bất thường mà không có quality rule.

## 22. Open Decisions

1. Xác nhận có chấp nhận Amazon Delivery Dataset làm dataset chính thức cho Business Baseline v2 hay không.
2. Xác nhận provenance wording: chỉ dùng tên theo người đăng Kaggle, không gọi là dữ liệu vận hành chính thức của Amazon.
3. Xác nhận đơn vị `Delivery_Time`; bằng chứng thứ cấp gợi ý phút nhưng metadata nguồn truy xuất được chưa nêu đơn vị.
4. Xác nhận grain nghiệp vụ: order record hay completed delivery record; dataset không có delivery status/attempt ID.
5. Xác nhận rollover: `Pickup_Time < Order_Time` nghĩa là pickup ngày kế tiếp.
6. Chốt cách xử lý 91 dòng thiếu đồng thời Order Time/Weather/Traffic và 54 Rating trống.
7. Chốt thang Agent Rating và cách xử lý 53 giá trị 6,0; xác nhận tuổi 15/50.
8. Chốt quality rule cho 3.505 store `(0,0)` và 188 store coordinate âm; không tự sửa dấu.
9. Xác nhận chính sách privacy cho drop coordinate chi tiết.
10. Xác nhận `Area = Metropolitian` giữ nhãn nguồn hay chuẩn hóa thành `Metropolitan` ở staging.
11. Xác nhận ý nghĩa của `Category` và anomaly Grocery có mean Delivery Time 26,54 so với khoảng 129–133 ở hầu hết category khác.
12. Chốt Fact/Dimension, vị trí Weather/Traffic/Area/coordinates và việc không tạo `dim_agent` khi thiếu Agent ID.
13. Chốt KPI baseline v2; không tạo On-time Delivery Rate khi chưa có SLA/expected time.
14. Chốt batch/watermark và quy tắc cho Order Time missing.

## 23. Profiling Conclusion

CSV thực tế khớp checksum dự kiến, có 43.739 dòng, 16 cột và chất lượng khóa tốt. `Order_ID` hỗ trợ đề xuất grain một bản ghi giao nguồn trên mỗi ID. Dataset có tiềm năng phân tích BI cao nhờ ngày giờ, thời lượng, điều kiện giao, phương tiện, area, category, agent attributes và tọa độ.

Các vấn đề chính cần giải quyết trước Business Requirements v2 là đơn vị `Delivery_Time`, 91 dòng null-like, 54 Rating trống, rating 6,0, giả định pickup qua ngày, store coordinate `(0,0)`/âm, privacy của drop coordinate, semantics của Category và provenance. Không có SLA hoặc expected delivery time, nên On-time Delivery Rate không khả thi.

Fact/Dimension và KPI trong tài liệu này chỉ là đánh giá sơ bộ. Không có bảng, pipeline, batch file, Star Schema hoặc semantic model nào được tạo.
