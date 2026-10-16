# Data

## Official Dataset

- **Dataset:** Supermarket Sales.
- **Author:** Fares Ashraf.
- **Source:** Kaggle, <https://www.kaggle.com/datasets/faresashraf1001/supermarket-sales>.
- **License:** Apache 2.0.
- **Version:** 2.
- **Original downloaded file:** `SuperMarket Analysis.csv`.
- **Project CSV:** `raw/supermarket_sales.csv`.
- **Archive ZIP:** `raw/archive/supermarket_sales_faresashraf_v2.zip`.
- **Quy mô:** 1.000 dòng dữ liệu, không tính header; 17 cột.
- **Khoảng thời gian:** 2019-01-01 đến 2019-03-30.
- **SHA-256 CSV:** `C5E0490DA62001D3066A56B3AA9C891C8D3ED42B6C2D09C8CA18B2A409AC93CD`.

## Ý nghĩa thư mục

| Thư mục | Mục đích |
|---|---|
| `raw/` | Lưu dữ liệu nguồn nguyên trạng và thư mục ZIP lưu trữ; không chỉnh sửa file nguồn |
| `full_load/` | Sẽ lưu batch nạp ban đầu được tạo từ bản sao của raw |
| `incremental/` | Sẽ lưu các batch tăng thêm được tạo từ bản sao của raw |
| `rejected/` | Sẽ lưu bản ghi bị từ chối cùng lý do khi pipeline được triển khai |

## Batch baseline

| Batch | Khoảng dữ liệu | Số dòng |
|---|---|---:|
| Full Load | 01/2019 | 352 |
| Incremental 1 | 02/2019 | 303 |
| Incremental 2 | 03/2019, dữ liệu quan sát đến ngày 30 | 345 |

Watermark dự kiến dựa trên Date kết hợp Time. `Invoice ID` được dùng để kiểm tra idempotency và tránh nạp trùng.

## Data Handling Rules

- Không chỉnh sửa, đổi tên, di chuyển hoặc ghi đè file trong `raw/`.
- Chỉ tạo batch Full/Incremental từ bản sao, không cắt trực tiếp raw data.
- Cleaning và standardization được thực hiện qua dbt ở giai đoạn sau.
- Không loại bỏ 9 giao dịch giá trị cao bị IQR gắn cờ khi chưa có bằng chứng là lỗi.
- Rejected records phải kèm lý do và bằng chứng kiểm tra.

## Trạng thái

Dataset Selection và Data Profiling đã hoàn thành. Chưa tạo file batch và chưa triển khai pipeline Mage.ai.
