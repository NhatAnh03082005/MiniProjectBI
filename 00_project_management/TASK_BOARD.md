# Task Board

| ID | Giai đoạn | Công việc | Người phụ trách | Đầu vào | Đầu ra cần bàn giao | Deadline | Trạng thái | Vướng mắc |
|---|---|---|---|---|---|---|---|---|
| SET-01 | Project setup | Tạo cấu trúc project | Trưởng nhóm | Yêu cầu đề bài | Cấu trúc thư mục và tài liệu khởi tạo | Ngày 1 | Done | Không |
| DAT-03 | Dataset selection | Chọn Amazon Delivery Dataset và đồng bộ tài liệu | Cả nhóm, trưởng nhóm điều phối | Tiêu chí lựa chọn | `DATASET_SELECTION.md` | Ngày 1 | Done | Không |
| DAT-04 | Data profiling | Review và close Amazon Delivery Data Profiling v2 | Trưởng nhóm | Amazon raw và báo cáo profiling | `DATA_PROFILE_AMAZON_DELIVERY.md` được duyệt | Ngày 1 | Done | Không; các quyết định nghiệp vụ đã được chuyển sang BUS/KPI/MOD/LOAD |
| BUS-04 | Business requirements | Chốt context, process, users, scope và data rules | Trưởng nhóm | Profiling đã duyệt | `BUSINESS_REQUIREMENTS.md` | Ngày 2 | Done | Không |
| BUS-05 | Business questions | Chốt đúng 8 Business Questions và traceability | Trưởng nhóm + thành viên 4 | BUS-04 | 8 BQ và traceability | Ngày 2 | Done | Không |
| KPI-02 | KPI baseline | Chốt đúng 10 KPI chính và diagnostic measures | Trưởng nhóm + thành viên 4 | BUS-04, BUS-05 | `KPI_DICTIONARY.md` | Ngày 2 | Done | Không |
| HOF-02 | Project coordination | Team Handoff Guide cho Business Baseline hiện hành và các task thiết kế tiếp theo | Trưởng nhóm | Baseline đã duyệt | `TEAM_HANDOFF_GUIDE.md` | Ngày 2 | Done | Không |
| MOD-01 | Dimensional modeling | Chốt grain DW, Fact, Dimension, keys và relationships | Trưởng nhóm + thành viên 3 | Requirements và KPI Dictionary | Thiết kế mô hình được duyệt | Ngày 2 | Todo | Chưa bắt đầu |
| MOD-02 | Dimensional modeling | Vẽ Star Schema | Thành viên 3 | MOD-01 | Sơ đồ mô hình có khóa và quan hệ | Ngày 2 | Todo | Phụ thuộc MOD-01 |
| MAP-01 | Data mapping | Tạo Source-to-Target Mapping | Thành viên 3 | Profile và Star Schema | Mapping đủ 16 cột và derived fields | Ngày 2 | Todo | Phụ thuộc MOD-01 |
| LOAD-01 | Full/Incremental design | Thiết kế batch, watermark, idempotency và rerun | Thành viên 2 | Batch proposal và mapping | Load design được duyệt | Ngày 2 | Todo | Phụ thuộc MAP-01 |
| ARC-01 | Architecture confirmation | Chốt kiến trúc và phương án chia sẻ SQL Server | Trưởng nhóm + cả nhóm | Yêu cầu kỹ thuật và mô hình | Architecture decision | Ngày 2 | Todo | Chưa chốt database dùng chung |
| MAG-01 | Mage.ai | Xây dựng pipeline, kiểm tra và logging | Thành viên 2 | LOAD-01, ARC-01 | Pipeline và bằng chứng | Ngày 3 | Todo | Phụ thuộc thiết kế |
| DBT-01 | dbt | Xây dựng models, tests và documentation | Thành viên 3 | Staging và Star Schema | dbt project, tests, docs, lineage | Ngày 4 | Todo | Phụ thuộc MOD/MAP/MAG |
| DWH-01 | Data Warehouse | Tạo và nạp Data Warehouse | Thành viên 3 | dbt models và kiến trúc | Fact/Dimension được nạp và đối soát | Ngày 4 | Todo | Phụ thuộc DBT-01 |
| PBI-01 | Power BI | Tạo semantic model và dashboard | Thành viên 4 | DWH và KPI Dictionary | `.pbix`, DAX và dashboard | Ngày 5 | Todo | Phụ thuộc DWH-01 |
| AI-01 | Generative AI | Tạo AI Summary có thể kiểm chứng | Trưởng nhóm | KPI đã tính | AI component và tests | Ngày 5 | Todo | Phụ thuộc PBI-01 |
| RPT-01 | Report | Tổng hợp báo cáo | Trưởng nhóm, cả nhóm | Bằng chứng triển khai | Báo cáo PDF | Ngày 6 | Todo | Phụ thuộc triển khai |
| VID-01 | Video demo | Chuẩn bị kịch bản và ghi demo | Cả nhóm | Hệ thống hoàn chỉnh | Video end-to-end | Ngày 6 | Todo | Phụ thuộc E2E-01 |
| E2E-01 | End-to-end testing | Kiểm thử toàn bộ luồng và thu thập bằng chứng | Trưởng nhóm + cả nhóm | Các thành phần tích hợp | Biên bản và bằng chứng | Ngày 6 | Todo | Phụ thuộc MAG/DBT/DWH/PBI/AI |
| SUB-01 | Final submission | Kiểm tra và đóng gói bài nộp | Trưởng nhóm | Toàn bộ deliverables | Gói nộp cuối | Ngày 6 | Todo | Phụ thuộc RPT/VID/E2E |

> Có đúng 7 task Done: SET-01, DAT-03, DAT-04, BUS-04, BUS-05, KPI-02 và HOF-02. Mọi task từ MOD-01 trở đi vẫn Todo; không có task kỹ thuật nào Done.
