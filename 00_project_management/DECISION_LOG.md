# Decision Log

| Decision ID | Ngày | Quyết định | Lý do | Người xác nhận | Trạng thái |
|---|---|---|---|---|---|
| DEC-001 | Chưa ghi nhận | Nhóm gồm 4 người | Theo bối cảnh dự án | Nhóm | Đã xác nhận |
| DEC-002 | Chưa ghi nhận | Thời gian thực hiện còn 6 ngày tại thời điểm lập kế hoạch | Theo bối cảnh dự án | Nhóm | Đã xác nhận |
| DEC-003 | Chưa ghi nhận | Kiến trúc dự kiến gồm Mage.ai, database, dbt, Power BI và Generative AI | Đáp ứng luồng BI được yêu cầu | Nhóm | Đã xác nhận |
| DEC-004 | Chưa ghi nhận | Ưu tiên SQL Server | Yêu cầu chi tiết chỉ rõ Staging và Data Warehouse trên SQL Server | Nhóm | Đã xác nhận |
| DEC-019 | 2026-10-16 | Ưu tiên SQL Server với schema `staging`, `dw`, `audit` | Tách vùng dữ liệu và audit; chưa triển khai | Nhóm | Đã xác nhận |
| DEC-029 | 2026-10-16 | Chọn Amazon Delivery Dataset làm dataset chính thức hiện tại | Đạt 9,5/10 theo tiêu chí lựa chọn và phù hợp bài toán BI | Nhóm | Đã xác nhận |
| DEC-030 | 2026-10-16 | Bối cảnh hiện hành là phân tích hiệu suất giao hàng chặng cuối | Bám sát các trường và phạm vi dữ liệu | Nhóm | Đã xác nhận |
| DEC-031 | 2026-10-16 | Dùng tuyên bố provenance: “Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.” | Tránh diễn giải tên dataset vượt quá bằng chứng nguồn | Nhóm | Đã xác nhận |
| DEC-032 | 2026-10-16 | Giữ nguyên `amazon_delivery.csv` và `amazon_delivery_original.zip` với checksum đã ghi nhận | Bảo toàn raw và khả năng đối soát | Nhóm | Đã xác nhận |
| DEC-033 | 2026-10-16 | Chưa chốt grain Data Warehouse, Fact, Dimension, KPI, SLA và quality rules | Trạng thái trước Business Baseline | Nhóm | Superseded một phần bởi DEC-035–DEC-050; phần DW/Fact/Dimension vẫn mở |
| DEC-034 | 2026-10-16 | Phê duyệt `DATA_PROFILE_AMAZON_DELIVERY.md` làm baseline phân tích | Profiling đã review; open decisions được chuyển sang baseline và task thiết kế | Nhóm | Đã xác nhận |
| DEC-035 | 2026-10-16 | Grain nghiệp vụ là một bản ghi giao hàng nguồn duy nhất trên mỗi `Order_ID`; không khẳng định completed delivery | Dataset không có delivery status hoặc attempt history | Nhóm | Đã xác nhận |
| DEC-036 | 2026-10-16 | Hiển thị Delivery Time bằng phút theo project assumption và ghi rõ metadata Kaggle chưa xác nhận đơn vị | Dẫn nguồn thứ cấp hỗ trợ giả định nhưng metadata truy xuất được chưa đủ | Nhóm | Đã xác nhận |
| DEC-037 | 2026-10-16 | Pickup Time nhỏ hơn Order Time được xử lý là ngày kế tiếp; thiếu Order Time thì pickup delay null | Tạo timestamp nhất quán mà không đặt giờ giả | Nhóm | Đã xác nhận |
| DEC-038 | 2026-10-16 | Trim chuỗi, chuẩn hóa null-like thành SQL `NULL`, không xóa cả record chỉ vì thiếu context/rating | Bảo toàn Total Deliveries và xử lý missing minh bạch | Nhóm | Đã xác nhận |
| DEC-039 | 2026-10-16 | Rating hợp lệ là 1,0–5,0; 6,0 giữ raw, gắn flag và loại khỏi average; null giữ null | Phân biệt raw preservation với analytic validity | Nhóm | Đã xác nhận |
| DEC-040 | 2026-10-16 | Không xóa tuổi 15/50; tuổi dưới 18 gắn flag; phân tích nhóm tuổi kèm sample size | Không tự sửa dữ liệu khi chưa có bằng chứng nghiệp vụ | Nhóm | Đã xác nhận |
| DEC-041 | 2026-10-16 | Valid distance cần đủ tọa độ, store khác `(0,0)` và Haversine ≤ 50 km; không sửa dấu | Loại anomaly khỏi KPI bằng quality rule, không thay raw | Nhóm | Đã xác nhận |
| DEC-042 | 2026-10-16 | Không hiển thị drop coordinate chính xác ở mức dòng trên dashboard công khai | Giảm rủi ro privacy của vị trí giao hàng | Nhóm | Đã xác nhận |
| DEC-043 | 2026-10-16 | Trim Weather/Traffic/Vehicle/Area và chuẩn hóa `Metropolitian` thành `Metropolitan` ở transformation, bảo toàn raw | Chuẩn hóa phân tích mà vẫn truy vết nguồn | Nhóm | Đã xác nhận |
| DEC-044 | 2026-10-16 | Giữ Grocery và Delivery Time nguồn; cảnh báo phân bố khác biệt nhưng không kết luận nguyên nhân | Chưa có bằng chứng để sửa hoặc loại dữ liệu | Nhóm | Đã xác nhận |
| DEC-045 | 2026-10-16 | Không tạo On-time Delivery Rate hoặc metric “giao trễ” | Dataset không có SLA, promised time hoặc expected time | Nhóm | Đã xác nhận |
| DEC-046 | 2026-10-16 | Dùng Share Above Baseline P90 với ngưỡng cố định 195 phút | Cung cấp ngưỡng thống kê nội bộ, không phải SLA | Nhóm | Đã xác nhận |
| DEC-047 | 2026-10-16 | Chốt đúng 8 Business Questions mô tả/chẩn đoán | Bao phủ volume, time, distribution, conditions, category, distance và data quality | Nhóm | Đã xác nhận |
| DEC-048 | 2026-10-16 | Chốt đúng 10 KPI chính trong KPI Dictionary | Chuẩn hóa công thức, context, baseline và cảnh báo | Nhóm | Đã xác nhận |
| DEC-049 | 2026-10-16 | Dataset không có measure semi-additive | Nguồn chỉ có event records, không có balance hoặc snapshot | Nhóm | Đã xác nhận |
| DEC-050 | 2026-10-16 | Business Baseline được duyệt để chuyển sang Dimensional Modeling | Profiling, Requirements, 8 BQ, 10 KPI và handoff đã hoàn thành | Nhóm | Đã xác nhận |

Không renumber Decision ID. Quyết định kiến trúc không đồng nghĩa thành phần kỹ thuật đã được triển khai.
