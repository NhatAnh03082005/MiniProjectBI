# KPI Dictionary — Amazon Delivery BI

## 1. Quy ước chung

- Grain nghiệp vụ: một dòng đại diện cho một bản ghi giao hàng nguồn duy nhất, nhận diện bởi `Order_ID`.
- Tên bảng vật lý chưa được chốt; DAX dưới đây là pseudocode và dùng tên trường logic.
- `Delivery_Time` hiển thị bằng phút theo project assumption có dẫn nguồn thứ cấp; metadata Kaggle truy xuất được chưa xác nhận đơn vị.
- KPI phải phản hồi filter context hợp lệ của Date, Traffic, Weather, Vehicle, Area, Category và các nhóm dẫn xuất, trừ khi định nghĩa ghi khác.
- Dataset không có measure semi-additive vì chỉ chứa bản ghi sự kiện nguồn, không chứa balance hoặc periodic snapshot.
- Không cộng Average, Median, Percentile, Rating, Distance hoặc Rate giữa các nhóm; phải tính lại trên tập dòng trong filter context.
- Không có KPI doanh thu, lợi nhuận, chi phí hoặc số lượng sản phẩm.
- Không có On-time Delivery Rate.

## 2. Mười KPI chính

### KPI-01 — Total Deliveries

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Đo khối lượng bản ghi giao hàng nguồn có business key hợp lệ |
| Business Question | BQ-01, BQ-02, BQ-04, BQ-05, BQ-06 |
| Định nghĩa | Số `Order_ID` phân biệt và hợp lệ trong filter context |
| Công thức nghiệp vụ | `DISTINCTCOUNT(Order_ID)` |
| DAX dự kiến | `Total Deliveries := DISTINCTCOUNT([Order_ID])` |
| Numerator | Không áp dụng |
| Denominator | Không áp dụng |
| Filter context | Toàn bộ slicer và chiều phân tích hợp lệ |
| Include | Mọi bản ghi có `Order_ID` hợp lệ, kể cả khi thiếu context vận hành hoặc rating |
| Exclude | `Order_ID` null/rỗng hoặc duplicate theo chính sách load tương lai |
| Đơn vị | Delivery record |
| Aggregation behavior | Distinct count; tính lại theo context |
| Additive classification | Additive count trên các nhóm không giao nhau |
| Baseline dự kiến | 43.739 |
| Data quality warning | Grain là source delivery record, không khẳng định completed delivery |
| Dashboard | Overview; mọi trang phân tích nhóm |

### KPI-02 — Average Delivery Time

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Đo thời lượng giao trung bình |
| Business Question | BQ-01, BQ-02, BQ-03, BQ-04, BQ-05, BQ-06 |
| Định nghĩa | Trung bình `Delivery_Time` numeric trong filter context |
| Công thức nghiệp vụ | `SUM(Delivery_Time) / COUNT(valid Delivery_Time)` |
| DAX dự kiến | `Average Delivery Time := AVERAGE([Delivery_Time])` |
| Numerator | Tổng `Delivery_Time` hợp lệ |
| Denominator | Số dòng có `Delivery_Time` hợp lệ |
| Filter context | Date và toàn bộ chiều phân tích hợp lệ |
| Include | Toàn bộ giá trị numeric 10–270, gồm 79 IQR outlier |
| Exclude | Null hoặc không numeric nếu xuất hiện ở lần nạp sau |
| Đơn vị | Phút theo project assumption |
| Aggregation behavior | Tính lại từ numerator/denominator, không cộng các average |
| Additive classification | Non-additive |
| Baseline dự kiến | 124,91 phút |
| Data quality warning | Metadata Kaggle chưa xác nhận đơn vị; IQR flag không phải lỗi |
| Dashboard | Overview; Time; Conditions; Category |

### KPI-03 — Median Delivery Time

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Mô tả trung tâm phân bố ít nhạy với giá trị cực trị |
| Business Question | BQ-01, BQ-03, BQ-04, BQ-05, BQ-06 |
| Định nghĩa | Percentile 0,5 của `Delivery_Time` hợp lệ |
| Công thức nghiệp vụ | `PERCENTILE_CONT(0.5)` |
| DAX dự kiến | `Median Delivery Time := MEDIAN([Delivery_Time])` |
| Numerator | Không áp dụng |
| Denominator | Tập `Delivery_Time` hợp lệ |
| Filter context | Tính lại trong context hiện tại |
| Include | Giá trị numeric 10–270 |
| Exclude | Null hoặc không numeric |
| Đơn vị | Phút theo project assumption |
| Aggregation behavior | Percentile tính lại trên tập dòng; không cộng median |
| Additive classification | Non-additive |
| Baseline dự kiến | 125 phút |
| Data quality warning | Không suy ra SLA từ median |
| Dashboard | Overview; Distribution; group diagnostics |

### KPI-04 — P90 Delivery Time

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Mô tả mức mà 90% quan sát có Delivery Time nhỏ hơn hoặc bằng |
| Business Question | BQ-01, BQ-03, BQ-04, BQ-05, BQ-06 |
| Định nghĩa | Percentile 0,90 của `Delivery_Time` hợp lệ |
| Công thức nghiệp vụ | `PERCENTILE_CONT(0.90)` |
| DAX dự kiến | `P90 Delivery Time := PERCENTILEX.INC(CurrentRows, [Delivery_Time], 0.90)` |
| Numerator | Không áp dụng |
| Denominator | Tập `Delivery_Time` hợp lệ |
| Filter context | Tính lại theo context; baseline toàn dataset được khóa riêng ở 195 |
| Include | Giá trị numeric 10–270 |
| Exclude | Null hoặc không numeric |
| Đơn vị | Phút theo project assumption |
| Aggregation behavior | Percentile tính lại trên tập dòng |
| Additive classification | Non-additive |
| Baseline dự kiến | 195 phút |
| Data quality warning | Không phải SLA; không gọi là ngưỡng giao trễ |
| Dashboard | Overview; Distribution; group diagnostics |

### KPI-05 — P95 Delivery Time

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Theo dõi phần đuôi trên của phân bố Delivery Time |
| Business Question | BQ-01, BQ-03 |
| Định nghĩa | Percentile 0,95 của `Delivery_Time` hợp lệ |
| Công thức nghiệp vụ | `PERCENTILE_CONT(0.95)` |
| DAX dự kiến | `P95 Delivery Time := PERCENTILEX.INC(CurrentRows, [Delivery_Time], 0.95)` |
| Numerator | Không áp dụng |
| Denominator | Tập `Delivery_Time` hợp lệ |
| Filter context | Tính lại trong context hiện tại |
| Include | Giá trị numeric 10–270 |
| Exclude | Null hoặc không numeric |
| Đơn vị | Phút theo project assumption |
| Aggregation behavior | Percentile tính lại trên tập dòng |
| Additive classification | Non-additive |
| Baseline dự kiến | 215 phút |
| Data quality warning | Không phải SLA; sample size cần hiển thị khi phân nhóm nhỏ |
| Dashboard | Overview; Distribution |

### KPI-06 — Average Pickup Delay

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Đo khoảng thời gian trung bình từ order đến pickup theo quy tắc project |
| Business Question | BQ-08 |
| Định nghĩa | Trung bình `pickup_delay_minutes` sau rollover |
| Công thức nghiệp vụ | `AVG(pickup_timestamp - order_timestamp)`; cộng một ngày nếu Pickup Time nhỏ hơn Order Time |
| DAX dự kiến | `Average Pickup Delay := AVERAGE([pickup_delay_minutes])` |
| Numerator | Tổng pickup delay hợp lệ |
| Denominator | Số dòng tính được pickup delay |
| Filter context | Date và các nhóm giao hàng hợp lệ |
| Include | Dòng có đủ Order Date, Order Time và Pickup Time |
| Exclude | 91 dòng thiếu Order Time; không tự đặt giờ |
| Đơn vị | Phút |
| Aggregation behavior | Tính lại từ các dòng hợp lệ |
| Additive classification | Non-additive |
| Baseline dự kiến | Khoảng 9,99 phút |
| Data quality warning | Phụ thuộc giả định pickup qua ngày khi Pickup Time nhỏ hơn Order Time |
| Dashboard | Agent Attributes & Data Quality; Time Analysis |

### KPI-07 — Average Valid Delivery Distance

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Đo khoảng cách Haversine trung bình trên các tọa độ đạt quality rule |
| Business Question | BQ-07 |
| Định nghĩa | Trung bình `delivery_distance_km` khi `valid_distance_flag = true` |
| Công thức nghiệp vụ | `AVG(Haversine(store, drop))` trên dòng đủ tọa độ, store khác `(0,0)`, distance ≤ 50 km |
| DAX dự kiến | `Average Valid Delivery Distance := CALCULATE(AVERAGE([delivery_distance_km]), [valid_distance_flag] = TRUE)` |
| Numerator | Tổng Haversine Distance của dòng hợp lệ |
| Denominator | Số dòng hợp lệ cho distance |
| Filter context | Date, Area, Category và nhóm phân tích được phép |
| Include | Dự kiến 40.046 dòng đạt quality rule |
| Exclude | Thiếu tọa độ, store `(0,0)`, distance > 50 km; tọa độ âm bất thường bị loại qua rule, không sửa dấu |
| Đơn vị | km |
| Aggregation behavior | Tính lại từ numerator/denominator |
| Additive classification | Non-additive |
| Baseline dự kiến | Khoảng 9,72 km |
| Data quality warning | Không hiển thị drop coordinate chính xác ở mức dòng công khai |
| Dashboard | Distance Analysis |

### KPI-08 — Average Valid Agent Rating

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Mô tả rating trung bình trên miền hợp lệ của project |
| Business Question | BQ-08 |
| Định nghĩa | Trung bình Agent Rating từ 1,0 đến 5,0 |
| Công thức nghiệp vụ | `AVG(Agent_Rating WHERE rating BETWEEN 1.0 AND 5.0)` |
| DAX dự kiến | `Average Valid Agent Rating := CALCULATE(AVERAGE([Agent_Rating]), [Agent_Rating] >= 1, [Agent_Rating] <= 5)` |
| Numerator | Tổng 43.632 rating hợp lệ |
| Denominator | 43.632 dòng có rating từ 1,0 đến 5,0 |
| Filter context | Date và nhóm phân tích; không dùng để xếp hạng cá nhân |
| Include | Rating 1,0–5,0, gồm 38 giá trị 1,0 |
| Exclude | 54 null và 53 giá trị 6,0 |
| Đơn vị | Rating point |
| Aggregation behavior | Tính lại trên dòng hợp lệ; không cộng average |
| Additive classification | Non-additive |
| Baseline dự kiến | Khoảng 4,63 |
| Data quality warning | Không có `Agent_ID`; 6,0 được giữ raw và gắn quality flag |
| Dashboard | Agent Attributes & Data Quality |

### KPI-09 — Average Deliveries per Active Day

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Đo khối lượng bình quân trên ngày thực sự có bản ghi |
| Business Question | BQ-02 |
| Định nghĩa | Total Deliveries chia số `Order_Date` phân biệt có dữ liệu trong context |
| Công thức nghiệp vụ | `Total Deliveries / DISTINCTCOUNT(Order_Date có dữ liệu)` |
| DAX dự kiến | `Average Deliveries per Active Day := DIVIDE([Total Deliveries], DISTINCTCOUNT([Order_Date]))` |
| Numerator | Total Deliveries |
| Denominator | Số Active Day trong filter context |
| Filter context | Phản hồi Date và các bộ lọc nhóm; ngày chỉ được đếm khi có record thuộc context |
| Include | Ngày có ít nhất một `Order_ID` hợp lệ trong context |
| Exclude | Calendar Day không có dữ liệu |
| Đơn vị | Delivery record / Active Day |
| Aggregation behavior | Ratio tính lại từ numerator/denominator |
| Additive classification | Non-additive |
| Baseline dự kiến | Khoảng 994,07 trên 44 Active Day |
| Data quality warning | Phải gọi là Active Day, không phải Calendar Day |
| Dashboard | Overview; Time Analysis |

### KPI-10 — Share Above Baseline P90

| Thuộc tính | Định nghĩa |
|---|---|
| Mục đích | Theo dõi tỷ trọng Delivery Time vượt ngưỡng thống kê baseline cố định |
| Business Question | BQ-03 |
| Định nghĩa | Tỷ lệ delivery có `Delivery_Time > 195` trên delivery có Delivery Time hợp lệ |
| Công thức nghiệp vụ | `COUNT(Delivery_Time > 195) / COUNT(valid Delivery_Time)` |
| DAX dự kiến | `Share Above Baseline P90 := DIVIDE(CALCULATE(COUNTROWS(CurrentRows), [Delivery_Time] > 195), COUNT([Delivery_Time]))` |
| Numerator | 4.100 dòng vượt 195 phút trong baseline |
| Denominator | 43.739 dòng có Delivery Time hợp lệ trong baseline |
| Filter context | Numerator và denominator cùng context; ngưỡng luôn cố định 195 phút |
| Include | Delivery Time numeric |
| Exclude | Null hoặc không numeric nếu có ở lần nạp sau |
| Đơn vị | Percentage |
| Aggregation behavior | Ratio tính lại từ numerator/denominator; không cộng tỷ lệ |
| Additive classification | Non-additive ratio |
| Baseline dự kiến | Khoảng 9,37% |
| Data quality warning | Ngưỡng thống kê nội bộ, không phải SLA; không gọi là late rate hoặc tỷ lệ giao trễ |
| Dashboard | Overview; Distribution |

## 3. Supporting diagnostic measures

Các measure sau hỗ trợ kiểm tra nhưng không tính vào 10 KPI chính:

| Measure | Định nghĩa |
|---|---|
| Records Missing Operational Context | Số dòng thiếu sau chuẩn hóa Order Time, Weather hoặc Traffic |
| Records Missing Rating | Số dòng Agent Rating null; baseline 54 |
| Invalid Rating Count | Số dòng rating ngoài 1,0–5,0; baseline 53 giá trị 6,0 |
| Invalid Store Coordinate Count | Số dòng store `(0,0)` hoặc không đạt distance rule, báo cáo theo loại lỗi |
| Valid Distance Coverage | Số/tỷ lệ dòng có `valid_distance_flag = true`; dự kiến 40.046/43.739 |
| Delivery Count by Group | Sample size đi kèm mọi breakdown |
| Offline Correlation | Chỉ dùng trong phân tích diagnostic ngoài dashboard KPI; không phải KPI và không chứng minh nhân quả |

## 4. Validation rules

- KPI-01 baseline phải bằng 43.739 khi không lọc.
- KPI-03, KPI-04 và KPI-05 lần lượt đối soát 125, 195 và 215 phút trên toàn dataset.
- KPI-06 loại đúng 91 dòng thiếu Order Time khỏi mẫu số.
- KPI-07 dùng đúng 40.046 dòng theo quality rule hiện hành và không sửa dấu tọa độ.
- KPI-08 dùng 43.632 rating hợp lệ, loại 54 null và 53 giá trị 6,0.
- KPI-09 dùng `DISTINCTCOUNT(Order_Date)` trong context, không dùng Date Dimension để đếm ngày không có giao dịch của nhóm.
- KPI-10 dùng ngưỡng cố định 195 phút ở mọi filter context.
- Mọi breakdown phải cho phép kiểm tra sample size; nhóm nhỏ không được diễn giải quá mức.
