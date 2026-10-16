# Quy ước đặt tên

- Thư mục và file kỹ thuật dùng `lowercase_snake_case`.
- dbt model dùng `lowercase_snake_case`.
- Bảng nguồn dùng tiền tố `raw_`.
- Staging model dùng tiền tố `stg_`.
- Intermediate model dùng tiền tố `int_`.
- Dimension dùng tiền tố `dim_`.
- Fact dùng tiền tố `fact_`.
- Bảng audit hoặc log phải có tên thể hiện rõ mục đích.
- Không hard-code password, credential hoặc API key.
- Secret chỉ được đặt trong `.env`; file này không được commit.
- `.env.example` chỉ chứa tên biến và giá trị trống.
- Tên vật lý cuối cùng của khóa và bảng được xác nhận trong giai đoạn Dimensional Modeling.

Các tài liệu quản lý hiện dùng tên chữ hoa theo cấu trúc project đã thống nhất; quy tắc `lowercase_snake_case` áp dụng cho artefact kỹ thuật được tạo ở các giai đoạn sau.

## Mapping tên cột đã xác nhận

| Raw source | Standardized name |
|---|---|
| Invoice ID | `invoice_id` |
| Customer type | `customer_type` |
| Product line | `product_line` |
| Unit price | `unit_price` |
| Tax 5% | `tax_5_percent` |
| Sales | `sales_amount` |
| Date | `transaction_date` |
| Time | `transaction_time` |
| Payment | `payment_method` |
| gross margin percentage | `gross_margin_percentage` |
| gross income | `gross_income` |
| Rating | `rating` |

- Không đổi tên cột trong raw CSV.
- Việc chuẩn hóa tên được thực hiện trong dbt staging model ở giai đoạn sau.
- Không tạo cột nguồn `Total`; file raw sử dụng `Sales` và tên chuẩn hóa dự kiến là `sales_amount`.
- Tên vật lý cuối cùng của khóa, bảng và các cột dẫn xuất được xác nhận trong Dimensional Modeling.
