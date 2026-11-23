# Giai đoạn 3 — Thay đổi triển khai và bàn giao viết báo cáo

Cập nhật: 23/11/2026. Tài liệu dành cho thành viên tổng hợp báo cáo; mô tả source hiện tại, không thay thế kết quả thực nghiệm trong video.

## 1. Mốc so sánh và cách sử dụng

- Bản trước: source tại `GD2/Source/BI_AI_Project` trong thư mục Mini Project. Đã đối chiếu trực tiếp các thành phần Mage, dbt và AI với bản này.
- Mốc Git trước đợt nối pipeline/metadata/monitoring: `7ccf60f`. Một số phần AI đã có ở mốc Git này nhưng khác source GD2; không mô tả toàn bộ AI là vừa được bổ sung trong lần merge monitoring.
- Bản hiện tại: nhánh `main`, đã tích hợp Mage → dbt, metadata, audit và dashboard ETL Monitoring; hỗ trợ database chính `AmazonDeliveryBI` và database demo riêng.
- Chủ dự án xác nhận đã quay demo thành công. Agent không chạy lại ETL hoặc reset database khi đóng gói. Số liệu thực nghiệm trong báo cáo phải lấy từ video/ảnh/SQL của lần quay, không lấy trạng thái dữ liệu lưu sẵn trong PBIX làm bằng chứng cho mọi lần chạy.

## 2. Tổng hợp khác biệt cần đưa vào báo cáo

| Nội dung | Bản trước / điểm cần cập nhật | Triển khai hiện tại |
|---|---|---|
| Điều phối | Các bước ingest và dbt chưa nối thành một lần thực thi hoàn chỉnh | Hai pipeline Mage đều gọi dbt ở block cuối; không phải chạy dbt tay sau mỗi lần ingest |
| Incremental | Đã có current-state upsert/hash trong bản trước | Giữ cơ chế này, nối đối soát và ghi nhận kết quả tới DDS; không chuyển sang LSET/CSET |
| Lập lịch | Không thể chỉ trình bày thao tác chạy từng block bằng tay | Tạo trigger trên web Mage, cấu hình lịch/thời điểm và source file; trigger chạy toàn bộ pipeline |
| Audit ingestion | Có thống kê batch staging | Giữ `audit.load_batch`; bổ sung `audit.dbt_run` để tách trạng thái ingestion và lần thực thi dbt |
| Monitoring | Chưa có trang giám sát ETL hoàn chỉnh trong bộ dashboard nghiệp vụ | Thêm schema `monitoring`, log run/step/metrics/error và bốn reporting views |
| Power BI | Bốn trang nghiệp vụ | Có thêm trang ETL Monitoring: tổng cộng năm trang |
| Metadata | Tài liệu thiết kế và mô tả chưa phản ánh đầy đủ triển khai cuối | Cập nhật dbt YAML và bộ dictionary, contract, source-to-target, KPI; xem mục 7 |
| SQL khởi tạo | Có thể cần chạy các thành phần riêng | Một script tổng hợp cho mỗi database, bao gồm staging, audit và monitoring; DDS do dbt tạo |
| Kiểm thử/demo | Dữ liệu CSV tĩnh, chạy lại thường không đổi | Có batch hỗn hợp insert/update/unchanged/reject và file sai header để chứng minh các nhánh xử lý |
| AI | Cần kiểm tra khác biệt với bản GD2, tránh chỉ mô tả ý tưởng | Source có ứng dụng Gemini, đọc dữ liệu phân tích từ DDS, xử lý credential và kiểm thử; đọc `ai/README.md` để viết đúng chức năng |

## 3. Kiến trúc và pipeline thực tế

```text
CSV → Mage Loader → Validate → Export/upsert staging → Verify staging
    → build_amazon_delivery_dds → dbt build (models + tests) → đối soát DDS

Trong quá trình thực thi:
    audit.load_batch + audit.dbt_run + monitoring tables
    → monitoring reporting views → Power BI Import → Refresh data

DDS → ứng dụng AI phân tích nghiệp vụ (chạy riêng)
```

Hai pipeline: `amazon_delivery_full_load` và `amazon_delivery_incremental_load`. Code chính:

- `mage_project/amazon_delivery_loader.py`: lấy nguồn và ngữ cảnh batch.
- `mage_project/amazon_delivery_repository.py`: ghi staging/upsert, giao dịch và thống kê hành động.
- `mage_project/custom/verify_amazon_delivery_batch.py`: kiểm tra kết quả staging.
- `mage_project/custom/build_amazon_delivery_dds.py` và `mage_project/amazon_delivery_dbt.py`: gọi dbt, ghi nhận attempt, đọc artifact và đối soát.
- `etl_monitoring/pipeline_bridge.py`, `runtime.py`: tích hợp log vào luồng chạy.

Phân biệt đúng: trigger là cơ chế kích hoạt theo lịch; pipeline gồm quan hệ phụ thuộc, biến đổi, kiểm tra, ghi dữ liệu và xử lý lỗi. Không viết “ETL chỉ là trigger”.

Full Load hiện dùng cơ chế upsert với toàn bộ file, không tự truncate dữ liệu. Chạy trên staging trống sẽ thêm mới toàn bộ; chạy lại cùng dữ liệu có thể cho unchanged. Không mô tả Full Load là luôn xóa sạch rồi nạp lại.

## 4. Cơ chế incremental và lỗi/rerun

- Đối chiếu khóa `Order_ID` đã chuẩn hóa và hash nội dung raw để quyết định insert/update/unchanged.
- Không có watermark LSET/CSET hoặc CDC từ một hệ thống giao dịch đang phát sinh dữ liệu.
- Dataset nguồn tĩnh có 43.739 dòng, 16 cột, từ 11/02/2022 đến 06/04/2022, có 44 ngày phát sinh dữ liệu. Không gọi đây là ba tháng dữ liệu đầy đủ.
- Cùng file và cùng nội dung: không thêm dòng trùng, ghi nhận unchanged. Các file demo mô phỏng thay đổi nguồn, không phải dữ liệu vận hành mới theo thời gian thực.
- Reject tại Mage và reject tại dbt là hai tầng khác nhau. Dòng bị Mage từ chối không được ghi staging; dòng bị dbt từ chối có thể đã nằm trong staging nhưng không vào fact.
- Sai cấu trúc header làm batch thất bại trước khi export. Có thể không có dòng `audit.load_batch`; vẫn cần xem monitoring để biết lần chạy lỗi.
- dbt lỗi sau khi staging đã commit không có nghĩa toàn pipeline đã rollback. Xem trạng thái riêng và sửa nguyên nhân rồi chạy lại; không khẳng định rollback staging/DDS theo một giao dịch chung.
- Tránh trigger chồng lấn; demo chạy tuần tự. Không khẳng định có snapshot dữ liệu riêng biệt cho từng lần chạy đồng thời.

## 5. Audit và monitoring: mục đích và cấu trúc

| Thành phần | Vai trò |
|---|---|
| `audit.load_batch` | Batch ingestion, nguồn, thời điểm, trạng thái và read/insert/update/unchanged/reject/loaded |
| `audit.dbt_run` | Các attempt dbt theo batch, exit code, thời điểm, lỗi, thư mục artifact/log và tóm tắt kết quả |
| `monitoring.etl_runs` | Lần thực thi pipeline và trạng thái tổng thể |
| `monitoring.etl_step_runs` | Trạng thái, thời gian và attempt từng bước |
| `monitoring.etl_record_metrics` | Chỉ số xử lý theo phạm vi và trạng thái ghi nhận |
| `monitoring.etl_errors` | Sự kiện error/warning gắn với lần chạy và bước |

Bốn view phục vụ Power BI:

1. `monitoring.vw_etl_run_summary`.
2. `monitoring.vw_etl_step_status`.
3. `monitoring.vw_etl_record_metrics`.
4. `monitoring.vw_etl_error_details`.

Dashboard đọc các view này qua SQL Server, không cần tạo một API dashboard riêng. Các bộ đếm đưa vào biểu đồ chỉ lấy metric phù hợp và đã commit (`is_chart_eligible`); không lọc bắt buộc tên nguồn phải là `amazon_delivery.csv`.

Khi ingestion thành công: `read = inserted + updated + unchanged + rejected`; `loaded = inserted + updated`. Đây là số liệu ingestion, không đồng nhất với số dòng fact tăng thêm.

## 6. Trang Power BI ETL Monitoring đã hoàn thiện

- Sáu KPI: Total Runs, Success Rate, Successful Runs, Failed Runs, Unfinished Runs, Avg Processing Duration.
- Bốn chỉ số xử lý: Inserted, Updated, Mage Rejected, Unchanged.
- Biểu đồ thời gian thực thi, kết quả thành công/thất bại và bảng trạng thái pipeline Mage/dbt/overall.
- Lịch sử thực thi với mã run, pipeline, source file, trạng thái và thời điểm bắt đầu/kết thúc.
- Errors & Warnings lọc theo run được chọn. Giữ `error_id` để các sự kiện có nội dung giống nhau không bị gộp thành một dòng; `Step Display` rút gọn mã `dbt_node:...`.
- Bộ lọc pipeline/ngày/trạng thái và nhãn database/thời điểm refresh.

Công thức success rate: `successful / (successful + failed)`. Unfinished không nằm trong mẫu số; vì vậy sáu run gồm bốn success, một failed, một unfinished cho 80%, không phải 66,7%.

Chỉ số xử lý là tổng theo ngữ cảnh lọc hiện tại. Khi chọn một run, đối chiếu chỉ số của run đó; khi bỏ chọn, đó có thể là cộng dồn nhiều lần chạy, không phải số bản ghi duy nhất trong database.

SUCCEEDED vẫn có thể kèm WARNING hoặc reject theo quy tắc; ERROR của run khác không được hiện như lỗi của run đang chọn. Số sự kiện warning khác số bản ghi dữ liệu bị loại.

Power BI dùng Import: chạy Mage xong phải Refresh data để nhận kết quả mới. Không tự cập nhật theo thời gian thực. Thời gian chạy hiển thị UTC; nhãn refresh dùng UTC+7 và phản ánh thời điểm Power Query đánh giá truy vấn refresh, không phải thời điểm ETL kết thúc.

Mở `powerbi/project/AmazonDeliveryBI.pbip` để xem source chỉnh sửa hiện hành; PBIX được giữ kèm. Đổi tham số ETL Monitoring Server/Database khi chuyển máy và kiểm tra cả nguồn của các bảng nghiệp vụ cùng trỏ đúng database.

## 7. Metadata và cập nhật thiết kế dữ liệu

Metadata không chỉ là các file Markdown. Có ba phần liên quan:

1. Metadata mô tả trong dbt YAML: bảng, cột, nguồn, test và thông tin nghiệp vụ; hiển thị qua dbt Docs/lineage.
2. Tài liệu quản trị: dictionary, mapping, data contract, KPI và quy tắc diễn giải.
3. Metadata vận hành: nguồn file, batch/run/attempt, thời điểm, trạng thái, số lượng và lỗi lưu trong audit/monitoring.

Nguồn cần đọc để cập nhật báo cáo:

- `project_management/DATA_DICTIONARY.md`: cấu trúc hiện hành; staging 26 cột, fact 33 cột, bảng audit và các model.
- `project_management/SOURCE_TO_TARGET_MAPPING.md`: ánh xạ, biến đổi và lineage.
- `project_management/DATA_CONTRACT.md`: grain, kiểu dữ liệu, quy tắc hợp lệ, rejection và giới hạn.
- `project_management/KPI_DICTIONARY.md`: định nghĩa KPI và ngưỡng phân tích.
- `report/METADATA_AUDIT_HANDOFF.md`: phạm vi thay đổi và giới hạn kiểm chứng của đợt metadata trước.
- `dbt_project/models/{sources,staging,intermediate,marts}/*.yml`: mô tả và test triển khai.

Các điểm dễ viết sai: `load_batch_id/loaded_at` thể hiện lần insert ban đầu; `updated_*` theo lần cập nhật gần nhất. Current-state staging không phải lịch sử bất biến từng phiên bản. Giữ outlier thống kê theo quy tắc triển khai; ngưỡng P90 baseline 195 phút không phải SLA. Không bổ sung KPI tài chính hoặc on-time rate khi nguồn thiếu căn cứ.

dbt Docs được tạo bằng `dbt docs generate` rồi phục vụ bằng `dbt docs serve`, có cấu hình kết nối hợp lệ. Đây là bước tạo tài liệu riêng; không phải chạy lại toàn bộ ETL.

## 8. Triển khai database chính và môi trường

- Python 3.11, SQL Server/SQL Express, ODBC Driver 18, Power BI Desktop.
- Cài project với phần phụ thuộc Mage từ `pyproject.toml`; dbt dùng `dbt_project/requirements.txt`, AI có `ai/requirements.txt`.
- Mở `sql/run_sql_skeleton.sql` trong SSMS để tạo/bổ sung cấu trúc cho `AmazonDeliveryBI`. Script đã gộp audit và monitoring, không cần SQLCMD Mode. Không chạy thêm các bộ monitoring cũ một cách tùy ý.
- Database demo dùng riêng `sql/run_sql_skeleton_demo.sql`; không trộn lịch sử giữa hai database.
- Fact/Dimension do dbt tạo, không có sẵn chỉ nhờ chạy SQL skeleton. Muốn quay trạng thái dashboard trống sau reset: chuẩn bị DDS bằng dbt build trên staging trống trước khi ghi hình; các dimension lịch/Unknown có thể vẫn có dòng.
- Khởi động trên máy quay:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\demo\start_etl_demo.ps1 `
  -Server 'NHAT-ANH\SQLEXPRESS' -Database 'AmazonDeliveryBI' `
  -Authentication sql -User sa -Monitoring
```

Script hỏi mật khẩu, dùng chung đích SQL/auth cho Mage và dbt; không lưu mật khẩu vào source. Đọc thêm `demo/HUONG_DAN_MONITORING_DATABASE_CHINH.md`. Môi trường PRIMARY cần marker `APPROVED_PRIMARY`; mã tích hợp kiểm tra đích kết nối, không được bỏ qua guard để chữa lỗi cấu hình.

Lịch trigger thuộc môi trường Mage đang chạy, không coi source nộp là bản sao lịch sử hay lịch đã bật của máy quay. Tạo lại trigger trên máy mới; override `source_file_path` cho từng ca kiểm thử. Mặc định pipeline incremental được đưa về file gốc sau demo để không tự đọc file sai header.

## 9. Kịch bản thực nghiệm để viết phần kết quả

Các số sau là kỳ vọng cho đúng trình tự quay đã thống nhất; đối chiếu video trước khi chép vào báo cáo.

| Ca chạy | Kết quả ingestion kỳ vọng | Staging / Fact sau chạy |
|---|---|---|
| Ban đầu | Chưa có run; dữ liệu nghiệp vụ trống | 0 / 0 nếu DDS đã chuẩn bị |
| Full Load file gốc | Insert 43.739 | 43.739 / 43.594 |
| Incremental file gốc | Unchanged 43.739; insert/update 0 | 43.739 / 43.594 |
| Incremental `04_mixed.csv` | Insert 2, update 2, unchanged 2, Mage reject 2 | 43.741 / 43.596 |
| Incremental `06_bad_header.csv` | FAILED ở validate, các bước sau không chạy | Giữ 43.741 / 43.596 |

Snapshot gốc: staging 43.739 = fact 43.594 + 145 mã bị dbt loại. 145 là số bản ghi distinct bị loại, không phải số cảnh báo hay tổng dòng log lỗi.

Nếu chỉ có bốn run trên, tổng quan là ba success, một failed, không unfinished, success rate 75%. Bộ đếm ingestion cộng dồn: inserted 43.741, updated 2, Mage rejected 2, unchanged 43.741. Nếu video có run/rerun khác, phải tính lại từ dữ liệu thực tế.

## 10. Các phần báo cáo và hình cần sửa

1. Kiến trúc: vẽ lại liên kết Mage gọi dbt, nhánh audit/monitoring → Power BI; AI là ứng dụng phân tích riêng.
2. ETL: giải thích upsert/hash, nguồn tĩnh và batch mô phỏng; phân biệt orchestration với scheduling.
3. Cơ sở dữ liệu: bổ sung schema audit/monitoring và trạng thái; cập nhật sơ đồ DDS/cột theo dictionary hiện hành.
4. Dashboard: giữ bốn trang nghiệp vụ, thêm trang thứ năm và ví dụ chọn run để xem chi tiết lỗi.
5. Metadata: trình bày cách tạo/quản lý và một ví dụ bảng/cột/test/lineage; không cần chép toàn bộ dictionary vào nội dung chính.
6. AI: đồng bộ với ứng dụng và `ai/README.md`, mô tả nguồn DDS và cách kiểm chứng kết quả; không khẳng định pipeline tự gọi AI hoặc AI đã giải thích lỗi ETL nếu chưa có chức năng đó.
7. Thực nghiệm: ảnh lịch trigger, run thành công, unchanged, mixed, sai header; SQL đối chiếu và dashboard sau refresh, dbt Docs và metadata.
8. Giới hạn: dữ liệu tĩnh, mô phỏng incremental, refresh Power BI thủ công, không CDC/LSET/CSET, không rollback toàn cục, không coi warning là thất bại mặc định.

Ảnh hiện hành ở `report/figures/`, gồm `star-schema.png`, `luong_anh_xa_du_lieu_moi.png`, `mage.png`. Hai ảnh cũ đã bị thay thế/xóa; sửa link hình trong báo cáo thay vì giữ tên cũ.

Các hướng dẫn cũ có câu “chưa triển khai/chưa chạy end-to-end” phản ánh thời điểm viết; không dùng làm kết luận hiện tại. Tương tự, kịch bản/SRT cũ trong `demo/` có thể khác thứ tự quay cuối cùng; video thực tế là căn cứ cho phần kết quả.

## 11. Bản source nộp

Source được sao chép sang `D:\BI\Mini Project\GiaiDoan3\2\Source`, giữ các thư mục thành phần ở cấp gốc như repository. Không di chuyển/xóa bản làm việc.

Giữ code, SQL, dữ liệu nguồn và batch demo, Power BI PBIP/PBIX, tài liệu và test. Không kèm `.git`, môi trường ảo, cache Power BI, database Mage cục bộ, log runtime, dbt target/packages hoặc mật khẩu/API key. `dbt_project/profiles.yml` cục bộ không được nộp; tạo lại từ `profiles.yml.example` với biến môi trường trên máy chạy.

Đây là bản source có thể tái triển khai, không phải bản backup database hay môi trường đã cài sẵn. Người nhận cần cài thư viện, cấu hình SQL, tạo cấu trúc, chạy pipeline và refresh báo cáo.

## 12. Kiểm tra trước khi bàn giao source

Ngày 23/11/2026: kiểm tra cú pháp/định dạng 43 file Python, 111 JSON và 10 YAML trong tập source Git đều đọc được; bảy unit test hợp đồng dữ liệu Mage và 62 unit test AI không cần kết nối thật đều đạt. Kiểm thử giao diện `ai.tests.test_app` chưa chạy được vì môi trường `.venv` hiện tại thiếu Streamlit; cần môi trường AI theo `ai/requirements.txt` để chạy phần này. Không chạy lại test kết nối SQL, ETL, dbt build hoặc gọi Gemini thật trong lần đóng gói.
