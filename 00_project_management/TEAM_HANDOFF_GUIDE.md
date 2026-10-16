# Team Handoff Guide — Business Baseline hiện hành

## 1. Project Overview

Project xây dựng hệ thống Business Intelligence tích hợp Generative AI để phân tích hiệu suất giao hàng chặng cuối. Kiến trúc dự kiến: `Kaggle CSV → Mage.ai → SQL Server staging → dbt → SQL Server dw → Power BI → Generative AI`; chưa có thành phần kỹ thuật nào được triển khai.

- Dataset: Amazon Delivery Dataset, người đăng Kaggle Sujal Suthar.
- Nguồn: <https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset>.
- Quy mô: 43.739 dòng, 16 cột.
- Khoảng ngày: 2022-02-11 đến 2022-04-06; 44 Active Day.

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

Business Baseline đã được duyệt. Task tiếp theo là Dimensional Modeling; chưa chốt tên vật lý Fact/Dimension, Star Schema hoặc Mapping.

## 2. Những gì đã hoàn thành

| Task | Kết quả |
|---|---|
| SET-01 | Cấu trúc project và tài liệu quản lý |
| DAT-03 | Dataset Selection v2 |
| DAT-04 | Amazon Delivery Data Profiling v2 đã review và đóng |
| BUS-04 | Business context, process, users, scope và rules |
| BUS-05 | Đúng 8 Business Questions và traceability |
| KPI-02 | Đúng 10 KPI chính và diagnostic measures |
| HOF-02 | Team Handoff Guide cho baseline hiện hành và task thiết kế tiếp theo |

## 3. File bắt buộc phải đọc

Đọc theo đúng thứ tự:

1. `README.md`
2. `00_project_management/PROJECT_CONTEXT.md`
3. `00_project_management/PROJECT_SCOPE.md`
4. `00_project_management/DATASET_SELECTION.md`
5. `00_project_management/DATA_PROFILE_AMAZON_DELIVERY.md`
6. `00_project_management/BUSINESS_REQUIREMENTS.md`
7. `00_project_management/KPI_DICTIONARY.md`
8. `00_project_management/DECISION_LOG.md`
9. `00_project_management/NAMING_CONVENTIONS.md`
10. `00_project_management/TASK_BOARD.md`

## 4. Quyết định đã khóa

- Dataset và provenance warning nêu trên.
- Grain: một dòng là một bản ghi giao hàng nguồn duy nhất, nhận diện bởi `Order_ID`; không khẳng định completed delivery.
- `Order_ID` là business key nguồn trong snapshot.
- Delivery Time dùng phút theo project assumption; metadata Kaggle truy xuất được chưa xác nhận đơn vị.
- Pickup rollover: Pickup Time nhỏ hơn Order Time thì pickup thuộc ngày kế tiếp; thiếu Order Time thì delay null.
- Missing policy: trim, chuẩn hóa null-like thành SQL `NULL`, không xóa cả record; categorical missing có thể là `Unknown`.
- Rating hợp lệ 1,0–5,0; null giữ null; 6,0 giữ raw, flag và loại khỏi average.
- Không xóa tuổi 15/50; tuổi dưới 18 gắn flag; phân tích nhóm tuổi kèm sample size.
- Haversine Distance chỉ hợp lệ khi đủ tọa độ, store khác `(0,0)` và distance ≤ 50 km; không sửa dấu.
- Không công khai drop coordinate chính xác ở mức dòng.
- Trim Weather, Traffic, Vehicle, Area; chuẩn hóa `Metropolitian` thành `Metropolitan` ở transformation và bảo toàn raw.
- Giữ Grocery và Delivery Time nguồn; chỉ cảnh báo phân bố khác biệt, không kết luận nguyên nhân.
- Không tạo On-time Delivery Rate; dùng Share Above Baseline P90 với ngưỡng cố định 195 phút và nhãn thống kê nội bộ.
- Có đúng 8 Business Questions và đúng 10 KPI chính.
- Dataset không có semi-additive measure.
- Không tạo `dim_agent` khi thiếu `Agent_ID`.

## 5. Task tiếp theo

- `MOD-01`: chốt grain Data Warehouse, Fact, Dimension, keys và relationships.
- `MOD-02`: vẽ Star Schema sau khi MOD-01 được duyệt.
- `MAP-01`: tạo Source-to-Target Mapping sau khi mô hình được chốt.
- `LOAD-01`: thiết kế Full/Incremental Load, watermark, idempotency và rerun.
- `ARC-01`: chốt kiến trúc và phương án chia sẻ SQL Server.

Tất cả task trên vẫn **Todo**. Không tự đánh dấu Done trước review và bằng chứng.

## 6. Gợi ý phân công

- Trưởng nhóm: review mô hình, kiến trúc và quyết định cuối.
- Thành viên 2: LOAD-01 và yêu cầu Mage.ai.
- Thành viên 3: MOD-01, MOD-02 và MAP-01.
- Thành viên 4: kiểm tra KPI traceability và chuẩn bị yêu cầu Power BI.
- Mọi thay đổi Business Baseline phải được trưởng nhóm review và ghi Decision Log.

## 7. Quy tắc không được vi phạm

- Không sửa, đổi tên hoặc ghi đè raw; không đổi checksum.
- Không tự tạo SLA, On-time Rate hoặc dùng ngôn ngữ “giao trễ”.
- Không gọi dataset là dữ liệu vận hành chính thức của Amazon.
- Không sửa tọa độ âm bằng cách đổi dấu hoặc thay raw coordinate.
- Không loại outlier tùy tiện.
- Không công khai drop coordinate chi tiết.
- Không tạo `dim_agent`.
- Không đổi định nghĩa KPI mà không cập nhật Decision Log và tài liệu traceability.
- Không đánh dấu task chưa kiểm thử là Done.
- Không đưa secret, `.env`, credential, runtime file hoặc dữ liệu tạm vào Git.

## 8. Git workflow

1. Pull trước khi làm.
2. Tạo branch theo task; không làm trực tiếp trên `main`.
3. Commit nhỏ, nội dung rõ và chỉ gồm file thuộc task.
4. Không commit `.env`, credential, runtime artefact hoặc dữ liệu tạm.
5. Chạy `git status --short` trước và sau.
6. Chỉ merge sau review.

## 9. Definition of Done cho Task 7–9

| Task | Đầu ra bắt buộc | Kiểm tra bắt buộc | Bằng chứng bàn giao |
|---|---|---|---|
| MOD-01/MOD-02 | Grain DW, danh sách Fact/Dimension, keys, relationships và sơ đồ Star Schema | Trace đủ 8 BQ/10 KPI; không tạo agent dimension; không mâu thuẫn grain nguồn | Tài liệu quyết định, sơ đồ, review note và cập nhật Task Board/Decision Log |
| MAP-01 | Mapping đủ 16 cột nguồn, derived fields, data type, null/quality handling và target hợp lệ | Mapping coverage 16/16; rules cho rollover, rating, categorical và distance; raw không đổi | Mapping file, checklist coverage và review note |
| LOAD-01 | Thiết kế Full/Incremental, watermark, tie-breaker, idempotency, rerun và rejected handling | Tổng batch đối soát 43.739; xử lý Order Time missing; không tạo batch vật lý trong bước thiết kế nếu chưa được phép | Design document, test scenarios, expected reconciliation và review note |

Không chuyển sang Mage.ai/dbt/SQL trước khi các đầu ra thiết kế liên quan được duyệt.

## 10. Hướng dẫn báo cáo

Mỗi thành viên phải báo cáo:

- File đã đọc.
- File đã tạo hoặc sửa.
- Quyết định baseline đã tuân thủ.
- Kiểm tra đã chạy.
- Kết quả và bằng chứng.
- Vấn đề còn mở.
- Task vẫn giữ trạng thái hiện tại nếu chưa được người có trách nhiệm review; không tự chuyển task.
