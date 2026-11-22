# Demo

- **Mục đích:** chuẩn bị và lưu tài nguyên demo toàn bộ quy trình.
- **Loại file:** kịch bản, checklist và bản ghi video.
- **Phụ trách dự kiến:** cả nhóm; trưởng nhóm điều phối.
- **Trạng thái:** đã có source nối Mage → dbt và batch demo; chờ kiểm thử tay/ghi hình.

Xem [hướng dẫn Mage → dbt và batch demo](HUONG_DAN_MAGE_DBT_DEMO.md).

- `start_etl_demo.ps1`: thiết lập môi trường rồi mở Mage, không chạy/reset ETL.
- `prepare_etl_batches.py`: tạo CSV demo và kết quả ingestion dự kiến, không kết nối SQL.
- `etl_batches/`: baseline, incremental, mixed, rerun và file lỗi.
- `inspect_etl_results.sql`: truy vấn chỉ đọc để đối chiếu sau khi chạy.
