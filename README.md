# Business Intelligence System for Last-Mile Delivery Analysis with Generative AI

## Mục tiêu

Xây dựng hệ thống Business Intelligence tích hợp Generative AI để phân tích hiệu suất giao hàng chặng cuối từ dữ liệu nguồn đến dashboard và AI Summary có thể kiểm chứng.

## Dataset

- **Tên:** Amazon Delivery Dataset.
- **Người đăng Kaggle:** Sujal Suthar.
- **Nguồn:** <https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset>.
- **License:** MIT, theo metadata đã xác minh trong báo cáo profiling.
- **Quy mô:** 43.739 dòng, 16 cột.
- **Khoảng thời gian:** 2022-02-11 đến 2022-04-06; 44 ngày có dữ liệu.
- **Chủ đề:** phân tích hiệu suất giao hàng chặng cuối.

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

## Tài liệu hiện hành

- [Thay đổi Giai đoạn 3 và hướng dẫn cập nhật báo cáo](report/GIAI_DOAN_3_THAY_DOI_VA_TRIEN_KHAI.md)
- [Data Dictionary hiện hành](project_management/DATA_DICTIONARY.md)
- [Mapping và lineage hiện hành](project_management/SOURCE_TO_TARGET_MAPPING.md)
- [Data Contract hiện hành](project_management/DATA_CONTRACT.md)
- [Bàn giao metadata và giới hạn kiểm chứng](report/METADATA_AUDIT_HANDOFF.md)

- [Chạy và cấu hình AI với Gemini sau khi pull source](ai/README.md): yêu cầu môi trường, DDS, nhập API key trên giao diện, demo và xử lý lỗi.
- [Dataset Selection](project_management/DATASET_SELECTION.md)
- [Data Profile](project_management/DATA_PROFILE_AMAZON_DELIVERY.md)
- [Business Requirements](project_management/BUSINESS_REQUIREMENTS.md)
- [KPI Dictionary](project_management/KPI_DICTIONARY.md)
- [Approved Dimensional Model](project_management/DIMENSIONAL_MODEL.md)
- [Team Handoff Guide](project_management/TEAM_HANDOFF_GUIDE.md)
- [Task Board](project_management/TASK_BOARD.md)
- [Decision Log](project_management/DECISION_LOG.md)

## Business Baseline

- Grain nghiệp vụ: một dòng là một bản ghi giao hàng nguồn duy nhất, nhận diện bởi `Order_ID`; không khẳng định completed delivery.
- Đúng 8 Business Questions mang tính mô tả/chẩn đoán.
- Đúng 10 KPI chính, không có KPI tài chính và không có On-time Delivery Rate.
- Delivery Time dùng phút theo project assumption; metadata Kaggle truy xuất được chưa xác nhận đơn vị.
- Share Above Baseline P90 dùng ngưỡng thống kê nội bộ cố định 195 phút, không phải SLA.
- Quy tắc triển khai lấy từ `dbt_project/dbt_project.yml`; khác biệt với thiết kế ban đầu về hard rejection được ghi rõ trong Data Contract/KPI Dictionary.

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Project Setup | Done |
| Dataset Selection v2 | Done |
| Data Profiling v2 | Done |
| Business Requirements v2 | Done |
| Business Questions v2 | Done |
| KPI Dictionary v2 | Done |
| Team Handoff v2 | Done |
| Logical Dimensional Model — MOD-01 | Approved / Done |
| Star Schema diagram — MOD-02 | Có tại `report/figures/star-schema.png` |
| ETL, DDS và Power BI | Có source triển khai và project Power BI; xem hướng dẫn từng thành phần |
| AI-Assisted Analytics — mục 3.5 | Ứng dụng Gemini chạy cục bộ; xem [hướng dẫn AI](ai/README.md) |

Mage ingestion đã hỗ trợ dynamic batch, raw row hash, current-state upsert và audit action counters; SQL bootstrap/migration và dbt regression được kiểm thử cục bộ. Mage đã nối dbt build/đối soát DDS và audit.dbt_run; xem demo/HUONG_DAN_MAGE_DBT_DEMO.md. Task board cũ là kế hoạch lịch sử, không thay thế trạng thái kiểm chứng trong metadata handoff.

## Cấu trúc thư mục

- `project_management`: tài liệu quản lý và quyết định.
- `data`: dữ liệu raw, full load, incremental và rejected.
- `sql`: script database, staging, warehouse và audit.
- `mage_project`: mã nguồn và kiểm thử Mage.ai.
- `dbt_project`: models, tests, macros, seeds và snapshots dbt.
- `powerbi`: PBIX, DAX, mockup và theme.
- `ai`: ứng dụng Gemini, script cài/chạy, hướng dẫn và kiểm thử; API key nhập trên giao diện.
- `report`: nội dung, hình và tài liệu tham khảo của báo cáo.
- `evidence`: bằng chứng kiểm thử theo từng thành phần.
- `demo`: kịch bản và bản ghi demo.
- `config`: ví dụ cấu hình không chứa bí mật.
