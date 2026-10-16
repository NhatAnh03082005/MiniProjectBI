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
- Secret chỉ đặt trong `.env`; `.env` không được commit.
- `.env.example` chỉ chứa tên biến và giá trị trống.
- Raw giữ nguyên tên cột và giá trị nguồn; không đổi tên, sửa hoặc ghi đè raw.
- Tên vật lý cuối cùng của bảng, khóa, cột chuẩn hóa và cột dẫn xuất chỉ được chốt trong MOD-01/MAP-01.

## Tên cột raw hiện hành

`Order_ID`, `Agent_Age`, `Agent_Rating`, `Store_Latitude`, `Store_Longitude`, `Drop_Latitude`, `Drop_Longitude`, `Order_Date`, `Order_Time`, `Pickup_Time`, `Weather`, `Traffic`, `Vehicle`, `Area`, `Delivery_Time`, `Category`.

## Tên logic đã khóa cho rule/KPI

- `pickup_delay_minutes`: chênh lệch phút sau khi áp dụng pickup rollover.
- `delivery_distance_km`: Haversine Distance, không thay raw coordinates.
- `valid_distance_flag`: đạt rule đủ tọa độ, store khác `(0,0)` và distance ≤ 50 km.
- `valid_rating_flag`: Agent Rating trong khoảng 1,0–5,0.
- `underage_agent_flag`: Agent Age dưới 18.
- `Metropolitan`: giá trị chuẩn hóa của raw `Metropolitian` ở lớp transformation.

Các tên logic không chốt tên bảng vật lý. Không tạo `dim_agent` khi không có `Agent_ID`.
