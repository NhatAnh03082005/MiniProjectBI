# Hướng dẫn thành viên 2: Metadata, audit và dashboard giám sát ETL

Ngày giao việc: 21/11/2026. Thời gian thực hiện: 3 ngày.

## 1. Nhiệm vụ và ranh giới công việc

Bạn phụ trách **hoàn thiện metadata, rà soát dữ liệu audit và xây dựng một trang Power BI giám sát kết quả mỗi lần ETL**.

Hiện dự án có 4 trang phân tích nghiệp vụ: Executive Overview, Area & Category detail, Time & Distribution, Operational Drivers. Chưa có trang giám sát ETL. Bạn bổ sung trang thứ 5 tên **ETL Monitoring** vào báo cáo hiện tại, giữ nguyên nội dung 4 trang cũ.

| Hạng mục | Người chịu trách nhiệm |
|---|---|
| Metadata, data dictionary, mô tả dbt | Bạn — thành viên 2 |
| Rà soát audit, SQL/view phục vụ trang giám sát | Bạn — thành viên 2 |
| Trang ETL Monitoring, kết nối audit, DAX và kiểm tra refresh | Bạn — thành viên 2 |
| Trigger/lập lịch và quay video demo | Trưởng nhóm |
| Nối Mage → dbt và tích hợp ghi log trong pipeline | Người phụ trách ETL, thống nhất với trưởng nhóm |
| AI tóm tắt KPI và giải thích nghiệp vụ | Người phụ trách AI |

Bạn được giao bổ sung bảng/query/measure cần thiết trong semantic model để làm trang giám sát. Đây là phạm vi được giao mới; hướng dẫn cũ trong `powerbi/TEAM_WORKFLOW.md` về việc chỉ leader sửa model không ngăn cản phần bổ sung này. Không chỉnh sửa các thành phần nghiệp vụ dùng chung ngoài nhu cầu đã thống nhất.

Không làm trigger, không tự đổi logic upsert, không bổ sung LSET/CET, không thay grain hoặc KPI nghiệp vụ. Không phải xây API hay ứng dụng web.

## 2. Hiểu hệ thống trước khi sửa

Thư mục gốc: `D:\BI\Mini Project\BI_AI_Project`.

Luồng dữ liệu hiện tại:

```text
CSV → Mage đọc/validate/upsert → SQL Server staging + audit.load_batch
    → dbt làm sạch, kiểm tra và dựng Dimension/Fact → Power BI Import
```

Pipeline Mage được kiểm tra trước đây kết thúc ở Verify staging; dbt đang được nối tự động bởi người phụ trách ETL. Luôn kiểm tra lại code mới nhất khi bắt đầu.

Dataset nguồn là một CSV tĩnh. Incremental hiện dùng `Order_ID + row_hash`. Việc mô phỏng các batch mới do người phụ trách ETL chuẩn bị. Không dùng `Order_Date` làm thời gian chạy ETL.

### Thứ tự đọc

Các đường dẫn dưới đây tính từ thư mục gốc dự án.

| Thứ tự | File/thư mục cần đọc | Điều cần ghi lại |
|---|---|---|
| 1 | `README.md`, `project_management/PROJECT_CONTEXT.md`, `BUSINESS_REQUIREMENTS.md` | Bài toán, các lớp dữ liệu, phạm vi |
| 2 | `project_management/DIMENSIONAL_MODEL.md`, `KPI_DICTIONARY.md` | Grain, khóa, Fact/Dimension, định nghĩa KPI và giả định |
| 3 | `project_management/SOURCE_TO_TARGET_MAPPING.md`, `DATA_CONTRACT.md` | Mapping nguồn–đích và quy tắc chất lượng |
| 4 | `sql/staging/01_create_raw_amazon_delivery.sql`, `sql/audit/01_create_load_batch.sql` | Schema hiện có và trường truy vết |
| 5 | `mage_project/amazon_delivery_loader.py`, `amazon_delivery_contract.py`, `amazon_delivery_repository.py` | Cách đọc nguồn, validate, upsert và ghi audit |
| 6 | `mage_project/custom/verify_amazon_delivery_batch.py`, YAML hai pipeline full/incremental | Kiểm tra bộ đếm, thứ tự block và điểm kết thúc pipeline |
| 7 | `dbt_project/models`, `dbt_project/tests`, `dbt_project/dbt_project.yml` | Các lớp biến đổi, tests, rejection và materialization |
| 8 | `powerbi/README.md`, `powerbi/TEAM_WORKFLOW.md`, project Power BI | Cách cộng tác, các bảng/measure đã có |
| 9 | `evidence/final_etl`, `D:\BI\Mini Project\KichBan_Demo_ETL.md` | Bằng chứng cũ và tình huống demo |

Không cần học thuộc toàn bộ code. Sau bước đọc phải giải thích được: mỗi dòng Fact là gì; pipeline ghi audit lúc nào; bộ đếm nào phản ánh ingestion; Power BI đang đọc database nào.

**Lưu ý:** README/task board có thông tin cũ. Đối chiếu với code, schema và kết quả thực tế; không đổi trạng thái thành Done chỉ vì có file.

## 3. Công việc A — Hoàn thiện metadata

Metadata là thông tin mô tả ý nghĩa, nguồn gốc, cấu trúc và cách xử lý dữ liệu. Ưu tiên cập nhật tài liệu hiện có thay vì tạo nhiều tài liệu trùng nhau.

### A1. Data dictionary

Tạo `project_management/DATA_DICTIONARY.md` nếu chưa có tài liệu tương đương. Bao phủ staging, Dimension/Fact, rejection và các bảng audit/control được sử dụng thực tế.

Mỗi bảng ghi: mục đích, grain, khóa chính/ngoại, nguồn và cách cập nhật. Mỗi cột ghi: tên, kiểu dữ liệu, nullable, ý nghĩa, đơn vị, nguồn/quy tắc dẫn xuất và quy tắc chất lượng liên quan.

Ví dụ cần giải thích rõ:

- `Order_ID`: khóa nghiệp vụ phục vụ upsert; kiểm tra cách chuẩn hóa thực tế.
- `row_hash`: dùng nhận diện thay đổi nội dung; ghi rõ những cột tham gia theo code.
- `load_batch_id` và trường cập nhật batch: phân biệt lần tạo với lần sửa bản ghi.
- `delivery_time_minutes`: đơn vị phút là giả định đã chốt của nhóm, không khẳng định nguồn xác nhận.
- Grain `fact_delivery`: bản ghi giao hàng hợp lệ theo quy tắc; không tự diễn giải là giao thành công.

### A2. Mapping và lineage

- Cập nhật `SOURCE_TO_TARGET_MAPPING.md` để phản ánh đúng cột và biến đổi hiện tại.
- Mô tả lineage CSV → staging → staging/intermediate dbt → Dimension/Fact/rejection → Power BI.
- Sửa mô tả raw là "immutable" nếu code thực tế cập nhật current state bằng upsert.
- Ghi đúng fact hiện dựng lại bảng nếu `materialized='table'`; không gọi đó là dbt incremental.
- Chỉ sửa mô tả nghiệp vụ khi đã đối chiếu với người phụ trách; không tự đổi quy tắc để khớp tài liệu.

### A3. dbt documentation

- Bổ sung/sửa descriptions cho model và cột quan trọng trong các file YAML của `dbt_project/models`.
- Ưu tiên khóa, measure, cờ chất lượng, trường lineage và trường có giả định.
- Nếu môi trường cho phép, chạy `dbt docs generate` bằng cấu hình đã thống nhất. Lệnh này kết nối database; kiểm tra target trước khi chạy.
- Lưu bằng chứng docs sinh thành công. Không ghi secret hoặc toàn bộ cấu hình kết nối vào tài liệu.

## 4. Công việc B — Rà soát audit và chốt dữ liệu giám sát

### B1. Hiểu audit hiện có

`audit.load_batch` đang có các trường: batch ID/tên/loại, nguồn tệp/checksum, thời gian bắt đầu/kết thúc, trạng thái, các bộ đếm và `error_message`.

Các trạng thái theo DDL hiện có: `STARTED`, `SUCCEEDED`, `FAILED`, `SKIPPED`. Không tự suy ra `SKIPPED` đồng nghĩa không có dữ liệu mới nếu pipeline chưa dùng trạng thái đó như vậy.

Định nghĩa phải kiểm tra lại theo code mới nhất:

| Bộ đếm | Ý nghĩa ở ingestion |
|---|---|
| `rows_read` | Số dòng đầu vào của batch |
| `rows_inserted` | Dòng mới thêm vào staging |
| `rows_updated` | Dòng cũ có nội dung thay đổi được cập nhật |
| `rows_unchanged` | Dòng hợp lệ khớp dữ liệu hiện có |
| `rows_rejected` | Dòng bị loại ở ingestion |
| `rows_loaded` | Inserted + updated; không gồm unchanged |

Với batch **SUCCEEDED**, đối chiếu:

```text
rows_read = rows_inserted + rows_updated + rows_unchanged + rows_rejected
rows_loaded = rows_inserted + rows_updated
```

Không áp cứng hai phương trình cho batch đang chạy hoặc thất bại: bộ đếm có thể chưa hoàn tất hoặc đã rollback.

`error_message` có thể chứa tóm tắt rejection dù batch SUCCEEDED. Phải dùng `status` để xác định thất bại; không coi mọi message khác rỗng là lỗi thất bại.

### B2. Tách ingestion và toàn bộ ETL

**SUCCEEDED trong bảng ingestion không chứng minh dbt đã thành công.** Trang cuối cùng phải phân biệt trạng thái nạp staging và trạng thái dbt/toàn luồng.

Trong ngày 1, thống nhất với người phụ trách ETL hợp đồng dữ liệu tối thiểu:

| Thông tin cần thống nhất | Yêu cầu |
|---|---|
| `run_id` | Một lần chạy toàn luồng; liên kết được các ingestion batch bên trong |
| Trạng thái run | Đang chạy, thành công, thất bại; quy định rõ các bước bắt buộc |
| Thời gian | Bắt đầu/kết thúc run và các bước; thống nhất UTC |
| Ingestion | Liên kết `load_batch_id`, bộ đếm, nguồn tệp |
| dbt | Trạng thái, thời gian, exit code; thống kê models/tests nếu thu thập được |
| Lỗi | Bước lỗi và thông báo an toàn, không chứa secret |
| Không có dữ liệu mới | Quy ước rõ, không nhầm với lỗi discovery hoặc rerun toàn unchanged |

Một run có thể xử lý nhiều tệp/batch. Nếu vậy, không join trực tiếp run với nhiều bảng con rồi SUM vì có thể nhân đôi bộ đếm; tổng hợp mỗi bảng con về grain run trước khi join.

Bạn đề xuất/tạo SQL migration tương thích cho dữ liệu còn thiếu sau khi chốt contract. Người phụ trách ETL tích hợp ghi dữ liệu vào các bảng đó. Không tạo bảng mới trùng chức năng nếu đồng đội đã triển khai.

Phải báo rõ hai khoảng trống hiện cần kiểm tra: audit tạo ở exporter nên có thể bỏ sót lỗi loader; dbt chưa có log toàn luồng trong bảng ingestion. Không tự điền thành công cho dữ liệu thiếu.

### B3. View có cần không?

View là truy vấn SQL đóng gói để Power BI đọc dễ hơn; không bắt buộc và không phải API.

- Nếu dữ liệu đã gọn trong một bảng, Power BI có thể đọc trực tiếp.
- Nếu cần ghép run/step/batch, tạo view sau khi thống nhất schema.
- Có thể đặt script tại `sql/audit/02_create_monitoring_views.sql` nếu tên chưa được dùng.
- Chạy trên database demo trước; script không xóa dữ liệu và có thể chạy lại.
- Không sửa bootstrap database thật chỉ để thử dashboard.
- Bộ đếm dbt rejection khác ingestion rejection; ghi riêng và không cộng nếu chưa chứng minh được phạm vi.
- Không lấy tổng Fact/rejection hiện tại để gắn làm kết quả lịch sử mọi run. Cần snapshot thực khi chạy; thiếu thì để trống/chưa ghi nhận.

## 5. Công việc C — Xây trang ETL Monitoring trong Power BI

### C1. Chuẩn bị bản làm việc

1. Thống nhất với trưởng nhóm bản Power BI đang dùng làm gốc. Thư mục có nhiều PBIX; không tự chọn theo chữ Final trong tên.
2. Ưu tiên mở `powerbi/project/AmazonDeliveryBI.pbip` nếu đây là bản gốc đã thống nhất.
3. Làm trên branch/bản làm việc riêng. Không ghi đè PBIX của người khác hoặc reset thay đổi đang có.
4. Dùng Power BI Desktop để chỉnh report/model; không tự sinh hoặc sửa tay cấu trúc PBIP/PBIR bằng agent.
5. Thêm trang **ETL Monitoring**, giữ nguyên 4 trang nghiệp vụ.

### C2. Kết nối và mô hình

1. Get Data → SQL Server → chọn đúng server/database demo được giao.
2. Đọc bảng/view audit đã thống nhất. Import là phương án đơn giản, phù hợp cấu hình hiện tại.
3. Kiểm tra kiểu dữ liệu: ID là text hoặc đúng kiểu nguồn; thời gian là datetime; bộ đếm là số nguyên.
4. Bảng audit không nối với `dim_date` nghiệp vụ theo Order_Date. Ngày ETL là thời gian vận hành riêng.
5. Nếu dùng nhiều bảng audit, xác định grain và relationship một–nhiều rõ ràng; không bật lọc hai chiều tùy tiện.
6. Nếu cần slicer ngày chạy, tạo cột ngày chạy hoặc bảng ngày ETL riêng.
7. Đặt tên measure có tiền tố `ETL` để tránh lẫn với KPI giao hàng.
8. Thời gian audit hiện dùng UTC. Giữ cột gốc, thêm giờ hiển thị UTC+7 nếu cần và ghi nhãn rõ.

### C3. Bố cục một trang

Không cần nhiều trang hay biểu đồ phức tạp. Ưu tiên đọc được kết quả từng run.

| Vùng | Nội dung |
|---|---|
| Đầu trang | Tên trang, thời điểm refresh dữ liệu, phạm vi ngày đang lọc |
| Bộ lọc | Ngày chạy, loại batch, trạng thái; run/batch ID để tra cứu |
| Thẻ tổng hợp | Tổng run, thành công, thất bại, đang chạy; tỷ lệ thành công nếu cần |
| Biểu đồ | Thời lượng theo run; insert/update/unchanged/reject theo batch hoặc run |
| Bảng lịch sử | ID, thời gian, loại batch, trạng thái từng bước/toàn luồng, bộ đếm |
| Chi tiết | Tệp nguồn, lỗi/cảnh báo và bước lỗi của run được chọn |

Nếu backend toàn luồng chưa xong, xây bản đầu trên `audit.load_batch`, ghi rõ **Giám sát ingestion** và trạng thái dbt là **Chưa ghi nhận**. Đây là bản trung gian; muốn nhận bàn giao giám sát toàn ETL phải tích hợp log dbt thật.

Quy ước hiển thị:

- Thành công: xanh; thất bại: đỏ; đang chạy: vàng/xanh dương; bỏ qua: xám.
- Thời lượng run kết thúc = finished_at − started_at. Run đang chạy không hiển thị 0 giây như đã hoàn tất.
- Không đổi NULL thành 0 nếu NULL nghĩa là chưa ghi nhận.
- Giữ run lỗi ngay cả khi bộ đếm chưa đầy đủ.
- Card tổng hợp chịu tác động bộ lọc phải có nhãn phù hợp. Nếu dùng card "run mới nhất", chốt rõ mới nhất toàn bộ hay trong phạm vi lọc.
- Rerun có unchanged vẫn là một lần chạy hợp lệ; không tự gắn nhãn thất bại.

### C4. Gợi ý DAX cho bản ingestion đầu tiên

Ví dụ dưới dùng bảng Power BI tên `ETL Batch`, mỗi dòng là một `load_batch_id`. Đổi tên theo model thật. Khi chuyển sang run toàn luồng phải dùng grain run, không tái sử dụng số batch làm số run.

```dax
ETL Ingestion Batches = DISTINCTCOUNT('ETL Batch'[load_batch_id])

ETL Successful Batches =
CALCULATE(
    [ETL Ingestion Batches],
    KEEPFILTERS('ETL Batch'[status] = "SUCCEEDED")
)

ETL Failed Batches =
CALCULATE(
    [ETL Ingestion Batches],
    KEEPFILTERS('ETL Batch'[status] = "FAILED")
)

ETL Rows Inserted = SUM('ETL Batch'[rows_inserted])
ETL Rows Updated = SUM('ETL Batch'[rows_updated])
ETL Rows Unchanged = SUM('ETL Batch'[rows_unchanged])
ETL Rows Rejected = SUM('ETL Batch'[rows_rejected])
```

Đây là ví dụ measure riêng biệt, nhập từng measure trong Desktop. Với dữ liệu lỗi/đang chạy, ghi rõ counters là kết quả đã ghi nhận, không khẳng định là dữ liệu đã commit. Không cần sao chép toàn bộ ví dụ nếu view/model cuối đã cung cấp chỉ số tương đương.

### C5. Refresh — bắt buộc hiểu đúng

Power BI hiện dùng Import. ETL chạy xong không tự làm trang đang mở có dữ liệu mới.

- Trong giai đoạn phát triển, Refresh thủ công rồi đối chiếu SQL là hợp lệ.
- Thống nhất với trưởng nhóm cách refresh khi demo: thủ công và nói rõ, hoặc tự động nếu được yêu cầu/đã triển khai.
- Hiển thị thời điểm refresh thật của mô hình/query, không dùng đồng hồ hiện tại để giả làm thời điểm refresh.
- Trang Import phản ánh trạng thái tại lần refresh gần nhất, không phải giám sát trực tiếp liên tục.
- Không tự nhận đã có auto-refresh chỉ vì đã cấu hình trigger Mage.

## 6. Kiểm thử cùng trưởng nhóm/người phụ trách ETL

Không tự xóa/reset database hiện tại. Dùng database demo và batch do người phụ trách chuẩn bị. Không thêm dữ liệu giả vào audit production để trang đẹp hơn.

| Tình huống | Điều phải kiểm tra |
|---|---|
| Full load baseline | Batch/run xuất hiện, bộ đếm và trạng thái khớp SQL |
| Incremental có đơn mới | Insert tăng đúng; thay đổi Fact kiểm tra riêng sau dbt |
| Incremental có cập nhật | Update khớp; không coi update là tăng số dòng Fact |
| Dòng bị loại | Rejection hiển thị đúng tầng; batch có warning không tự thành FAILED |
| Rerun cùng file | Có run/batch mới nếu thực sự xử lý; unchanged hoặc skipped theo cơ chế đã chốt |
| Loader lỗi/thiếu file | Log run thất bại xuất hiện sau khi backend tích hợp; thiếu log phải báo chưa đạt |
| Ingestion thành công, dbt lỗi | Toàn luồng không được báo thành công; xem được bước dbt lỗi |
| Chưa có dữ liệu audit | Trang không lỗi, thông báo chưa có dữ liệu phù hợp |
| Lần chạy mới | Lịch sử cũ vẫn còn, slicer và số tổng không bị nhân đôi |
| Sau refresh | Dữ liệu khớp SQL; cả 4 trang nghiệp vụ vẫn hoạt động |

Với mỗi tình huống lưu: ID, đầu vào, kỳ vọng, kết quả thực tế, ảnh/query đối chiếu và kết luận. Không coi log cũ là kết quả vừa kiểm thử.

Nếu SQL Server/Mage hoặc Power BI chưa chạy được, hoàn thành phần độc lập và ghi rõ kiểm tra nào chưa thực hiện; không đánh dấu toàn bộ Done.

## 7. Lịch làm việc 3 ngày

| Mốc | Công việc và checkpoint |
|---|---|
| Ngày 1 — buổi đầu | Đọc luồng, kiểm tra schema, thống nhất database/PBIP gốc và contract audit với người phụ trách ETL |
| Ngày 1 — buổi sau | Hoàn thiện dictionary bản đầu, SQL đọc audit; dựng trang Monitoring với dữ liệu thật sẵn có |
| Ngày 2 — buổi đầu | Cập nhật mapping/dbt descriptions; hoàn thiện model, measure và giao diện |
| Ngày 2 — buổi sau | Kết nối log toàn luồng mới; chạy thử cùng người phụ trách; đối chiếu SQL–Power BI |
| Ngày 3 — buổi đầu | Sửa lỗi, kiểm tra refresh và 4 trang cũ; chốt tài liệu/ảnh/bằng chứng |
| Ngày 3 — buổi sau | Bàn giao bản ổn định cho trưởng nhóm quay video; hỗ trợ giải thích chỉ số và xử lý lỗi |

Cuối ngày 2 phải có trang chạy được. Nếu log toàn luồng chưa sẵn sàng, báo ngay để trưởng nhóm xử lý phần tích hợp; không chờ đến ngày 3.

## 8. Đầu ra và tiêu chí bàn giao

### File bàn giao

- `project_management/DATA_DICTIONARY.md` và các tài liệu mapping đã cập nhật.
- YAML descriptions dbt đã sửa; bằng chứng docs nếu đã chạy.
- SQL migration/view cần thiết và truy vấn đối soát, kèm database mục tiêu và thứ tự chạy.
- PBIP có trang thứ 5; PBIX cuối được xuất bằng Desktop từ bản đã thống nhất, không ghi đè bản của người khác.
- `powerbi/specifications/ETL_MONITORING.md`: nguồn dữ liệu, grain, measure, bộ lọc, trạng thái và cách refresh.
- `evidence/etl_monitoring/`: ảnh và biên bản kiểm tra thật; ẩn thông tin nhạy cảm.
- `report/ETL_MONITORING_HANDOFF.md`: cách mở/chạy, phần đã hoàn thành, phần chờ tích hợp và các giới hạn.

Tên thư mục/file mới là đề xuất, có thể dùng tên tương đương nếu dự án đã có quy ước. Tránh tạo hai bản cùng mục đích.

### Checklist trước khi báo hoàn thành

- [ ] Metadata khớp code/schema, giả định được ghi rõ.
- [ ] Đã sửa các mô tả cũ về raw/upsert và materialization nếu có.
- [ ] Trang ETL Monitoring tồn tại, 4 trang cũ vẫn hoạt động.
- [ ] Audit grain và liên kết run–batch rõ, không nhân đôi số đếm.
- [ ] Phân biệt ingestion thành công với toàn ETL thành công.
- [ ] dbt lỗi và lỗi sớm được kiểm tra hoặc liệt kê rõ là chưa tích hợp.
- [ ] Bộ đếm, thời gian, warning/error và dữ liệu NULL được hiển thị đúng.
- [ ] Có bằng chứng SQL đối chiếu với Power BI sau refresh.
- [ ] Không xóa lịch sử, không thay cơ chế incremental, không làm lộ secret.
- [ ] Đã bàn giao phần báo cáo và ảnh để trưởng nhóm quay video; bạn không phải quay video hoặc cấu hình trigger.

Mục tiêu là một trang giám sát có số liệu đáng tin cậy và metadata đúng, không phải xây lại hệ thống ETL.
