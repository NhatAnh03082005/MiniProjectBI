# Business Requirements — Amazon Delivery BI

## 1. Document Control

| Thuộc tính | Giá trị |
|---|---|
| Dataset | Amazon Delivery Dataset |
| Phiên bản baseline | Business Baseline v2 |
| Phạm vi | Phân tích hiệu suất giao hàng chặng cuối |
| Trạng thái | Approved |
| Ngày duyệt | 2026-10-16 |

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

## 2. Bối cảnh

Hệ thống BI phân tích hiệu suất giao hàng chặng cuối trên snapshot Amazon Delivery Dataset từ Kaggle. Dữ liệu có 43.739 bản ghi, 16 cột, từ 2022-02-11 đến 2022-04-06 và chỉ bao phủ 44 ngày có dữ liệu. Kết quả chỉ mô tả snapshot này, không đại diện cho hoạt động vận hành chính thức của Amazon và không đủ để kết luận xu hướng dài hạn hoặc mùa vụ.

## 3. Quy trình nghiệp vụ quan sát được

1. Ghi nhận order bằng `Order_ID`, `Order_Date` và `Order_Time` khi có.
2. Agent đến pickup; `Pickup_Time` được dùng để dẫn xuất pickup delay theo quy tắc rollover đã khóa.
3. Giao từ store đến drop location trong các điều kiện Weather, Traffic, Vehicle và Area do nguồn cung cấp.
4. Ghi nhận `Delivery_Time`, Agent Rating và Category liên quan.

Dataset không có delivery status nên quy trình không tự thêm hoặc khẳng định các trạng thái delivered, cancelled, failed hay returned. Grain phân tích đã chốt:

> Một dòng đại diện cho một bản ghi giao hàng nguồn duy nhất, được nhận diện bởi `Order_ID`.

Không gọi chắc chắn mỗi dòng là completed delivery.

## 4. Người dùng

| Vai trò | Mức độ | Nhu cầu chính |
|---|---|---|
| Delivery Operations Manager | Chính | Theo dõi khối lượng, thời lượng, phân bố và các nhóm vận hành cần xem sâu |
| Area/Regional Operations Manager | Phụ | So sánh mô tả theo Area, Vehicle và điều kiện vận hành |
| BI Analyst hoặc Data Quality Analyst | Phụ | Đối soát KPI, kiểm tra chất lượng, phạm vi mẫu và giới hạn diễn giải |

Không dùng dataset để đánh giá hiệu suất cá nhân vì không có `Agent_ID`.

## 5. Mục tiêu nghiệp vụ

- Theo dõi khối lượng giao hàng.
- Theo dõi thời lượng giao hàng và phân bố bằng average, median, P90 và P95.
- Nhận diện các nhóm có Delivery Time cao hoặc thấp để ưu tiên phân tích mô tả.
- Phân tích theo thời gian, Traffic, Weather, Vehicle, Area và Category.
- Theo dõi pickup delay theo quy tắc rollover.
- Phân tích khoảng cách trên các bản ghi có tọa độ hợp lệ.
- Hỗ trợ kiểm tra missing, rating, tuổi và tọa độ bất thường.
- Cung cấp KPI đã định nghĩa làm đầu vào cho Power BI và AI Summary ở giai đoạn sau.

## 6. Phạm vi và giới hạn

- Không Machine Learning và không dự báo.
- Không phân tích doanh thu, lợi nhuận, chi phí hoặc số lượng sản phẩm.
- Không đánh giá cá nhân agent.
- Không suy luận quan hệ nhân quả từ các khác biệt mô tả hoặc correlation.
- Không tạo On-time Delivery Rate vì không có SLA, promised time hoặc expected delivery time.
- Không dùng từ “late delivery” hoặc “giao trễ”.
- Không hiển thị drop coordinate chính xác ở mức dòng trên dashboard công khai.
- Không kết luận xu hướng dài hạn hoặc mùa vụ từ 44 ngày có dữ liệu.
- Không chốt Star Schema, tên vật lý Fact/Dimension hoặc Source-to-Target Mapping trong tài liệu này.

## 7. Business Questions

Tám câu hỏi dưới đây mang tính mô tả/chẩn đoán và không khẳng định nhân quả.

1. **BQ-01:** Tổng khối lượng giao hàng và các chỉ số thời lượng giao hàng chính trong phạm vi dữ liệu là bao nhiêu?
2. **BQ-02:** Khối lượng và thời lượng giao hàng biến động như thế nào theo ngày, tháng, ngày trong tuần và khung giờ?
3. **BQ-03:** Phân bố Delivery Time như thế nào, bao gồm median, P90, P95 và tỷ lệ vượt ngưỡng P90 baseline?
4. **BQ-04:** Delivery Time khác nhau như thế nào giữa các mức Traffic và Weather?
5. **BQ-05:** Delivery Time khác nhau như thế nào theo Vehicle và Area?
6. **BQ-06:** Delivery Time khác nhau như thế nào theo Category, đặc biệt đối với nhóm Grocery?
7. **BQ-07:** Trên các bản ghi có tọa độ hợp lệ, khoảng cách giao hàng liên hệ mô tả như thế nào với Delivery Time?
8. **BQ-08:** Agent Rating, nhóm tuổi và Pickup Delay khác nhau như thế nào giữa các nhóm giao hàng, đồng thời có những vấn đề chất lượng dữ liệu nào cần lưu ý?

## 8. Quy tắc dữ liệu đã khóa

### 8.1. Provenance và grain

- Chỉ dùng tên dataset do người đăng Kaggle cung cấp; không tuyên bố đây là dữ liệu vận hành chính thức.
- `Order_ID` là business key nguồn trong snapshot: 43.739 giá trị hợp lệ và duy nhất.
- Grain nghiệp vụ là một bản ghi giao hàng nguồn trên mỗi `Order_ID`; không khẳng định completed delivery.

### 8.2. Delivery Time

- Project hiển thị `Delivery_Time` bằng phút theo giả định có dẫn nguồn thứ cấp; metadata Kaggle truy xuất được chưa xác nhận đơn vị.
- Giữ toàn bộ giá trị numeric từ 10 đến 270.
- Không loại 79 IQR outlier chỉ vì bị gắn cờ thống kê.
- Ngưỡng P90 baseline cố định là 195 phút; đây là ngưỡng thống kê nội bộ, không phải SLA.

### 8.3. Pickup Delay

- `pickup_delay_minutes = pickup_timestamp - order_timestamp`.
- Nếu `Pickup_Time >= Order_Time`, pickup dùng cùng `Order_Date`.
- Nếu `Pickup_Time < Order_Time`, cộng một ngày cho pickup.
- 91 dòng thiếu Order Time có pickup delay bằng null; không tự đặt giờ thay thế.

### 8.4. Missing values

- Trim chuỗi trước khi kiểm tra.
- Chuỗi `NaN`, rỗng hoặc null-like được chuẩn hóa thành SQL `NULL` tại lớp transformation.
- Không xóa toàn bộ bản ghi chỉ vì thiếu Weather, Traffic, Order Time hoặc Rating.
- Missing categorical có thể hiển thị là `Unknown` khi phân tích.
- Total Deliveries vẫn gồm mọi bản ghi có `Order_ID` hợp lệ.

### 8.5. Agent Rating và Agent Age

- Rating hợp lệ của project nằm trong khoảng 1,0–5,0.
- 54 rating thiếu được giữ null.
- 53 rating bằng 6,0 được giữ trong raw, gắn quality flag và loại khỏi Average Valid Agent Rating.
- 38 rating bằng 1,0 được giữ vì hợp lệ.
- Không xóa tuổi 15 hoặc 50 khỏi raw; tuổi dưới 18 gắn quality flag, tuổi 50 không bị xem là lỗi.
- Phân tích nhóm tuổi phải kèm sample size.
- Không tạo `dim_agent` chỉ từ Age và Rating.

### 8.6. Coordinates và Distance

- Không sửa dấu, không thay thế tọa độ raw.
- `delivery_distance_km` được tính bằng công thức Haversine.
- `valid_distance_flag = true` chỉ khi đủ bốn tọa độ, store coordinate khác `(0,0)` và Haversine Distance không vượt 50 km.
- Tọa độ âm tạo khoảng cách bất thường bị loại khỏi KPI distance thông qua quality rule, không bị sửa.
- Dự kiến có 40.046 dòng hợp lệ cho distance.
- Không hiển thị drop coordinate chính xác ở mức dòng trên dashboard công khai; chỉ dùng aggregation, binning, làm tròn phù hợp hoặc access control.

### 8.7. Categorical values

- Trim whitespace cho Weather, Traffic, Vehicle và Area.
- Chuẩn hóa raw value `Metropolitian` thành `Metropolitan` tại lớp transformation và vẫn bảo toàn raw value để truy vết.
- Giữ Category `Grocery`; không tự sửa Delivery Time của nhóm này.
- Grocery có phân bố Delivery Time khác biệt; chưa đủ bằng chứng để kết luận nguyên nhân.

### 8.8. SLA và ngưỡng nội bộ

- Không tạo On-time Delivery Rate hoặc metric “giao trễ”.
- Dùng `Share Above Baseline P90` với ngưỡng cố định 195 phút.
- Chỉ số này là tỷ lệ vượt ngưỡng thống kê nội bộ, không phải SLA.

## 9. Traceability

| Business Question | KPI/measure hỗ trợ | Chiều phân tích | Dashboard dự kiến | Cảnh báo diễn giải |
|---|---|---|---|---|
| BQ-01 | KPI-01, KPI-02, KPI-03, KPI-04, KPI-05 | Date và slicer chung | Overview | Snapshot 44 ngày; đơn vị phút là project assumption |
| BQ-02 | KPI-01, KPI-02, KPI-09 | Date, month, weekday, order hour, time period | Overview; Time Analysis | Active Day khác Calendar Day; không suy luận mùa vụ |
| BQ-03 | KPI-02, KPI-03, KPI-04, KPI-05, KPI-10 | Delivery Time bins, Date | Overview; Distribution | KPI-10 không phải SLA hoặc late rate |
| BQ-04 | KPI-01, KPI-02, KPI-03, KPI-04 | Traffic, Weather | Operational Conditions | Missing hiển thị Unknown; không suy luận nhân quả |
| BQ-05 | KPI-01, KPI-02, KPI-03, KPI-04 | Vehicle, Area | Operational Conditions | Hiển thị sample size; trim và chuẩn hóa Area |
| BQ-06 | KPI-01, KPI-02, KPI-03, KPI-04 | Category | Category Analysis | Grocery khác biệt nhưng không được tự sửa hoặc kết luận nguyên nhân |
| BQ-07 | KPI-07; Delivery Time; offline correlation | Distance band, Date, Area | Distance Analysis | Chỉ dùng valid distance; correlation không phải KPI hay quan hệ nhân quả |
| BQ-08 | KPI-06, KPI-08; diagnostic quality measures | Rating band, age group, pickup delay band | Agent Attributes & Data Quality | Không đánh giá cá nhân; loại rating 6,0 khỏi average; 91 pickup delay null |

## 10. Acceptance Criteria

- Có đúng 8 Business Questions và mỗi câu có ít nhất một KPI hoặc measure hỗ trợ.
- Không có KPI tài chính.
- Không có On-time Delivery Rate; ngưỡng 195 phút được ghi rõ là baseline thống kê nội bộ.
- Có quality rule cho missing, pickup rollover, rating, tuổi, categorical values và coordinates/distance.
- Có provenance warning và privacy warning cho drop coordinates.
- Các câu hỏi chỉ mang tính mô tả/chẩn đoán, không khẳng định nhân quả.
- Tài liệu không triển khai Star Schema, Mapping, pipeline, SQL, Power BI hoặc AI component.
- Business Baseline được phê duyệt để chuyển sang Dimensional Modeling, nhưng chưa thực hiện MOD-01.
