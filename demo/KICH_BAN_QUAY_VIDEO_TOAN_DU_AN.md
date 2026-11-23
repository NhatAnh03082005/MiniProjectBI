# Kịch bản quay demo dự án BI + ETL Monitoring

Phiên bản: 23/11/2026. Thời lượng dựng mục tiêu: **15 phút**. Quay màn hình và phụ đề tiếng Việt, có thể bổ sung thuyết minh.

## 1. Luồng demo chốt

```text
Tắt trigger cũ → reset AmazonDeliveryBI → chạy bootstrap tổng hợp
→ mở Mage với Monitoring
→ trigger Once: full load CSV gốc
→ SSMS + Power BI nghiệp vụ
→ trigger cron: mixed lần 1 (insert/update/reject/unchanged)
→ cùng trigger tự chạy lần 2 (unchanged, không trùng)
→ tắt cron
→ trigger Once: file sai header
→ SSMS + dashboard Monitoring và lỗi
→ dbt docs/metadata → AI giải thích KPI → kết thúc
```

Chỉ dùng database chính **AmazonDeliveryBI** trên **NHAT-ANH\SQLEXPRESS**, SQL Authentication `sa` cho Mage/dbt. Bộ mixed là dữ liệu mô phỏng, được chủ động thêm vào bản database vừa reset để trình diễn; không gọi đó là dữ liệu mới thật từ Kaggle.

**Các file trong bộ kịch bản chỉ được tạo để bạn chạy tay. Agent không reset database, không bật trigger, không chạy ETL, không gọi AI hoặc refresh Power BI.**

## 2. Chuẩn bị trước khi bấm quay

### Giữ lại giao diện vừa hoàn thiện

- Ctrl+S trong Power BI; sao lưu thư mục Power BI project trước khi reset SQL.
- Mở đúng `powerbi/project/AmazonDeliveryBI.pbip`, không dùng PBIX cũ thiếu thay đổi.
- Parameter Monitoring Server = NHAT-ANH\SQLEXPRESS; Database = AmazonDeliveryBI. Các bảng Fact/Dimension cũng phải đọc cùng instance/database chính.
- Chưa Refresh Power BI trong khoảng database vừa drop và trước khi dbt build thành công. Các thẻ lúc đó có thể là cache cũ, không trình bày là dữ liệu mới.

### Dừng hoạt động cũ

1. Trong web Mage, **Disable/Pause tất cả trigger cũ** của full và incremental; chờ run đang chạy xong.
2. Ctrl+C dừng Mage, dừng app AI, đóng truy vấn đang giữ kết nối database. Power BI có thể đóng sau khi lưu rồi mở lại sau full load.
3. Database reset **không xóa lịch sử trigger/run của Mage**. Tạo trigger mới có tên riêng, ví dụ hậu tố `_take01`; không tái dùng một trigger Once đã chạy vì Once có run history rồi sẽ không tự chạy lại như trigger mới.
4. Pipeline incremental hiện đang lưu biến mặc định `source_file_path = demo/etl_batches/06_bad_header.csv` từ các lần test. Trước khi quay, xóa biến mặc định này ở phần Variables của pipeline hoặc chỉnh lại phù hợp; **mỗi trigger dưới đây vẫn phải truyền rõ file riêng**.

### Quay và dựng

- Quay 1920×1080; phóng Mage/SSMS vừa đủ đọc. Power BI dùng Fit to page, đóng bớt pane chỉnh sửa trước khi quay.
- Mở sẵn các file SQL trong thư mục `demo/video`, một tab cho mỗi file. Chỉ chạy tab đúng cảnh.
- Nhập password/API key trước cảnh cần dùng; không quay nội dung bí mật hoặc cửa sổ credential manager.
- Thời gian chờ lịch/dbt có thể tua nhanh/cắt nối. Giữ lại timestamp, Next run và run history để chứng minh thực sự chạy theo lịch.
- Không bấm Run now rồi chú thích là scheduler tự chạy. Lịch phải tự tạo run khi đến giờ.
- Tắt thông báo cá nhân; tên clip: `S01_intro`, `S02_reset`… để dễ dựng lại theo bảng ở mục 8.

## 3. Reset và tạo lại cấu trúc — chỉ chạy trước full load

### SSMS: xóa database cũ

Mở `demo/video/00_RESET_MAIN_MANUAL.sql`, đọc đúng server/database rồi Execute. Script này **xóa toàn bộ dữ liệu và cấu trúc AmazonDeliveryBI**, không xóa Demo và không xóa metadata Mage. Không chạy lại giữa các cảnh incremental.

### SSMS: tạo cấu trúc mới

Mở và Execute toàn bộ **`sql/run_sql_skeleton.sql`**. File tổng hợp đã có staging, audit.load_batch, audit.dbt_run và bảng/procedure/view Monitoring; không cần chạy thêm ba script Monitoring riêng.

Chạy `demo/video/01_CHECK_EMPTY.sql`. Kỳ vọng:

- Database AmazonDeliveryBI trên đúng server.
- Staging = 0, ingestion batches = 0, dbt attempts = 0, Monitoring runs = 0.
- Marker APPROVED_PRIMARY; có schema/tables/views Monitoring.
- Chưa có Fact/Dimension sau reset là bình thường: chúng do dbt tạo trong pipeline.

## 4. Lệnh khởi động và mốc giờ

### Terminal 1: Mage

```powershell
Set-Location 'D:\BI\Mini Project\BI_AI_Project'
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\demo\start_etl_demo.ps1 `
  -Server 'NHAT-ANH\SQLEXPRESS' `
  -Database 'AmazonDeliveryBI' `
  -Authentication sql -User sa -Monitoring
```

Nhập password sa, giữ terminal mở. Mở http://localhost:6789. Script không tự chạy ETL; các trigger sẽ thực hiện việc đó.

### Terminal phụ: xem giờ dùng đặt lịch

```powershell
Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
[DateTimeOffset]::UtcNow.ToString('yyyy-MM-dd HH:mm:ss')
[DateTimeOffset]::UtcNow.AddMinutes(2).ToString('yyyy-MM-dd HH:mm:ss')
```

Ba dòng lần lượt là giờ máy, UTC và UTC + 2 phút. Bangkok/Việt Nam = UTC+7. Không đổi giờ hệ điều hành để ép trigger chạy.

## 5. Tạo trigger trên web Mage

Tên nút có thể hơi khác theo phiên bản; các trường cốt lõi là Trigger type, Frequency/Interval, Start time, Variables và Enabled/Active.

### Trigger A — full load một lần, theo giờ hẹn

1. Chọn pipeline **amazon_delivery_full_load**.
2. Mở **Triggers → Add/New trigger → Schedule**.
3. Name: `video_full_once_take01` (đổi hậu tố nếu quay lại).
4. Frequency/Interval: **Once / @once**.
5. Start date/time: một thời điểm **2–3 phút trong tương lai**. Kiểm tra nhãn timezone của UI; nếu UI là UTC dùng UTC, nếu UI đã hiển thị giờ local thì dùng local. Bản OSS đang cài lưu và so lịch theo UTC; không mặc định mọi ô ngày/giờ là UTC+7.
6. Variables của trigger:

```json
{"source_file_path":"data/raw/amazon_delivery.csv"}
```

7. Save và Enable/Active. Chụp cấu hình, Next run/start time. **Không bấm Run now**.
8. Chờ đến giờ, quay Run history tự xuất hiện và 5 block chạy: Loader → Validate → Export → Verify → build_amazon_delivery_dds.
9. Chờ cả dbt và reconciliation thành công; Disable trigger sau cảnh dù Once chỉ chạy một lần.
10. Chạy SQL `02_CHECK_RUNS.sql`, rồi `03_CHECK_DDS.sql`.

### Trigger B — lịch incremental lặp, chạy đúng hai lần

Chỉ tạo/bật sau full load đã hoàn tất. Tắt mọi trigger khác để tránh chạy chồng.

1. Pipeline: **amazon_delivery_incremental_load**.
2. Triggers → Add trigger → Schedule; name `video_incremental_cron_take01`.
3. Frequency: Custom/Cron.
4. Cron:

```text
*/10 * * * *
```

Nghĩa là chạy ở các phút 00/10/20/30/40/50, **không phải đúng 10 phút sau khi bấm Save**. Chọn Start time tương lai và xem Next run. Nếu có tùy chọn tạo run bù/initial run cho quá khứ, tắt để không sinh thêm run ngoài kịch bản.

5. Variables:

```json
{"source_file_path":"demo/etl_batches/04_mixed.csv"}
```

6. Save/Enable và chờ scheduler chạy lần đầu. Quay đủ trạng thái thành công; chạy SQL 02, 03, 04 và Refresh Power BI.
7. Giữ **cùng trigger/cùng file**, để cron chạy lần thứ hai. Lần này sáu dòng hợp lệ trở thành unchanged, hai dòng lỗi vẫn reject. Không cần đổi sang 05_rerun.csv vì file 04 và 05 có nội dung giống nhau.
8. Ngay khi lần thứ hai đã được scheduler tạo, Disable trigger để chặn lần thứ ba; không Cancel run đang thực thi. Nếu giao diện Disable có cảnh báo hủy run, chờ run hoàn tất rồi Disable ngay, trước mốc cron tiếp theo.
9. Chờ lần thứ hai hoàn tất, đối chiếu SQL và dashboard. Nếu một lần chạy vượt 10 phút thì dừng lịch và tăng interval lên 15/20 phút trước khi tiếp tục; không để các pipeline ghi cùng DB chồng nhau.

### Trigger C — lỗi header theo lịch một lần

1. Xác nhận trigger B đã Disabled và run trước đã kết thúc.
2. Trên incremental tạo Schedule mới: `video_bad_header_once_take01`.
3. Frequency Once; Start time tương lai 2–3 phút.
4. Variables:

```json
{"source_file_path":"demo/etl_batches/06_bad_header.csv"}
```

5. Enable, chờ scheduler tự chạy. Kỳ vọng FAILED ở validation, dbt/warehouse không chạy.
6. Chạy SQL 02 rồi 05; Refresh Power BI, chọn đúng dòng FAILED để xem lỗi.
7. Disable trigger khi quay xong. Nếu trạng thái SQL còn STARTED dù Mage đã kết thúc, cần xử lý logging trước khi ghi cảnh kết luận; không chỉnh dữ liệu audit bằng tay để tạo kết quả đẹp.

Tham khảo chính thức về Schedule/Once/cron và variables: https://www.mage.ai/academy/01/5-3-schedule-trigger và https://www.mage.ai/academy/01/5-2-run-settings. Các lựa chọn nâng cao có thể khác bản OSS cài trên máy.

## 6. Kết quả mong đợi để đối chiếu

Điều kiện: reset sạch, đúng file nguồn hiện tại, đúng 4 run do lịch tạo; không Execute block/run phụ khi quay.

| Run | Source | Ingestion read / insert / update / unchanged / reject | Current staging / Fact / dbt rejected |
|---|---|---|---|
| A Full | CSV gốc | 43739 / 43739 / 0 / 0 / 0 | 43739 / 43594 / 145 |
| B Cron lần 1 | 04_mixed.csv | 8 / 2 / 2 / 2 / 2 | 43741 / 43596 / 145 |
| B Cron lần 2 | Cùng 04_mixed.csv | 8 / 0 / 0 / 6 / 2 | 43741 / 43596 / 145 |
| C Header lỗi | 06_bad_header.csv | Không có export committed; validation thất bại | Không thay đổi DDS |

Hai ID mới: seminar3_new_001, seminar3_new_002. Hai ID sửa thời lượng: abwe493376570 và acnn902187983, Delivery_Time mới = 150. Không thay ngày nghiệp vụ tương lai.

Dashboard cuối, **không chọn riêng run**, slicer All và đã Refresh:

| Thẻ | Kỳ vọng |
|---|---:|
| Total runs | 4 |
| Successful | 3 |
| Failed | 1 |
| Unfinished | 0 |
| Success rate | 75% |
| Inserted | 43741 |
| Updated | 2 |
| Mage rejected | 4 |
| Unchanged | 8 |

Avg duration lấy giá trị đo thật, không gán cứng. Với cấu hình hiện tại thường có warning dbt về 145 rejected ở mỗi build thành công và warning kỹ thuật ở mixed/rerun; xem SQL event_count thay vì giả định luôn đúng số dòng warning nếu code hoặc input đổi.

Phân biệt: Mage reject trước staging; dbt reject từ staging; error records có thể nhiều hơn distinct rejected rows. Rejected card là số cộng dồn qua run, không phải số lỗi duy nhất trong nguồn.

## 7. Cách đối chiếu Power BI và quay đủ dự án

Sau mỗi run hoàn tất:

1. SSMS 02 xem parent/status và ingestion/dbt audit; 03 đối soát DDS; 04 kiểm tra ID khi có mixed/rerun.
2. Power BI **Refresh data**, đợi xong, kiểm tra timestamp refresh.
3. Mở ETL Monitoring, slicer All. Chọn một dòng để xem bộ đếm/lỗi của run đó; nếu tổng quan cũng bị tương tác thì bỏ chọn trước khi đọc số tổng cuối.
4. Bảng Errors & Warnings cần error_id không summarize để không gộp các event cùng nội dung. Bảng đang lọc theo run sẽ không hiển thị lỗi header khi chọn run mixed thành công; warning trên run thành công là hợp lệ.
5. Chuyển 4 trang nghiệp vụ: Overview (khối lượng/mean/P90), Time & Distribution (ngày/giờ), Operational Drivers (Traffic/Weather), Area & Category. Chỉ chọn 1–2 tương tác tiêu biểu, nói đúng dữ liệu mô tả, không suy luận nhân quả.

### dbt docs và metadata

Chuẩn bị terminal riêng, từ root repo. Nếu profile cá nhân dùng env DBT_SQLSERVER_* như template:

```powershell
Set-Location 'D:\BI\Mini Project\BI_AI_Project'
$env:DBT_SQLSERVER_SERVER = 'NHAT-ANH\SQLEXPRESS'
$env:DBT_SQLSERVER_DATABASE = 'AmazonDeliveryBI'
$env:DBT_SQLSERVER_DRIVER = 'ODBC Driver 18 for SQL Server'
$env:DBT_SQLSERVER_PORT = '1433'
$env:DBT_SQLSERVER_USER = 'sa'
$videoPassword = Read-Host 'Nhap mat khau SQL Server' -AsSecureString
$videoCredential = [System.Management.Automation.PSCredential]::new('sa', $videoPassword)
$env:DBT_SQLSERVER_PASSWORD = $videoCredential.GetNetworkCredential().Password
try {
    & '.\.venv\Scripts\dbt.exe' docs generate --project-dir dbt_project --profiles-dir dbt_project
} finally {
    Remove-Item Env:DBT_SQLSERVER_PASSWORD -ErrorAction SilentlyContinue
}
& '.\.venv\Scripts\dbt.exe' docs serve --project-dir dbt_project --profiles-dir dbt_project --port 8080
```

Thực hiện generate sau khi DDS đã có và pipeline đang nghỉ; serve mở http://localhost:8080. Quay lineage, fact_delivery description và 1–2 cột; lineage dbt không tự vẽ scheduler/Mage. Không chạy dbt build riêng vì pipeline đã chạy.

### AI — đoạn cuối của demo toàn dự án

Terminal khác:

```powershell
Set-Location 'D:\BI\Mini Project\BI_AI_Project'
powershell -NoProfile -ExecutionPolicy Bypass -File .\ai\run.ps1
```

Nếu lần đầu chưa cài, chạy `-Install` trước lúc quay, không dành video cho cài thư viện. Mở http://127.0.0.1:8501, tải lại DDS sau khi ETL kết thúc, chọn cùng database/phạm vi với Power BI.

**AI hiện dùng Windows Authentication, không dùng ô sa của launcher Mage.** Kiểm tra trước khi quay tài khoản Windows của app đọc được DDS. Nếu chưa kết nối được, giải quyết quyền/cấu hình trước; đừng quay lỗi kết nối rồi tuyên bố AI hoạt động. Task kịch bản này không sửa auth hoặc cấp quyền cho AI.

Nhập Gemini key ở ngoài cảnh quay, dùng model đã thử thành công; không gán cứng model mới. Quay: KPI → tạo summary → mở dẫn chứng → hỏi "Trong phạm vi hiện tại, nhóm Traffic nào có thời gian giao trung bình cao hơn và số liệu nào hỗ trợ nhận xét?". Đối chiếu cùng filter ở Power BI; không gọi traffic là nguyên nhân đã được chứng minh, 195 phút không phải SLA.

## 8. Timeline dựng 15 phút và phụ đề

Thời gian là **timeline video sau dựng**, không phải thời gian chờ thật của scheduler. Import `demo/video/PHU_DE_DEMO_15_PHUT.srt` vào CapCut/Premiere/DaVinci rồi dịch/rút cue theo clip thực tế.

| Clip | Timeline | Cảnh quay / thao tác | Bằng chứng cần giữ trên hình |
|---|---|---|---|
| S01 | 00:00–00:35 | Tiêu đề + cấu trúc dự án/luồng | CSV → Mage → dbt → DDS → Power BI/AI |
| S02 | 00:35–01:10 | Dừng trigger cũ, chạy 00_RESET_MAIN_MANUAL.sql | Đúng tên server/database; không hiện password |
| S03 | 01:10–01:45 | Chạy bootstrap + SQL 01 | 4 counter 0, marker PRIMARY, schema Monitoring |
| S04 | 01:45–02:15 | Khởi động Mage -Monitoring, mở web | Database AmazonDeliveryBI, 5 block |
| S05 | 02:15–02:45 | CSV nguồn, pipeline graph, snapshot/mapping | 16 cột, validation, audit, dbt cuối |
| S06 | 02:45–03:30 | Tạo trigger A Once, giờ tương lai, variables rõ | Active + start time/Next run; không bấm Run now |
| S07 | 03:30–04:15 | Chờ scheduler tự tạo run; tua nhanh block chạy | Run ID, timestamp, dbt/reconciliation thành công |
| S08 | 04:15–05:00 | SSMS SQL 02 + 03 | 43739 insert; 43739 = 43594 + 145 |
| S09 | 05:00–05:45 | Refresh BI, Overview và các trang nghiệp vụ | 43594 bản ghi Fact, không phải 43739 raw |
| S10 | 05:45–06:30 | Trigger B cron */10, variable 04_mixed | Lịch lặp và Next run thực |
| S11 | 06:30–07:15 | Cron lần đầu tự chạy, xem Output | 2 insert/2 update/2 unchanged/2 reject |
| S12 | 07:15–08:00 | SQL 04 + 03, BI refresh nhanh | Hai ID mới và hai đơn được sửa; DDS cân bằng |
| S13 | 08:00–08:45 | Cron lần hai tự chạy cùng file; Disable lịch | 0 insert/update, 6 unchanged, 2 reject; không run thứ ba |
| S14 | 08:45–09:30 | SQL 02/04, so hai lần cron | Hai ID mới vẫn chỉ có một bản ghi mỗi ID |
| S15 | 09:30–10:15 | Refresh BI Monitoring, chọn từng run | Số dòng và file đúng với SQL, warning đúng run |
| S16 | 10:15–11:00 | Trigger C Once sai header | Biến file 06, lịch hẹn tương lai |
| S17 | 11:00–11:45 | Run FAILED, SQL 02 + 05 | Sai 2/16 cột, dbt không chạy, không thêm dữ liệu |
| S18 | 11:45–12:30 | Refresh BI, xem FAILED rồi bỏ chọn | 4 run/3 thành công/1 lỗi/75%; lỗi đúng run |
| S19 | 12:30–13:15 | dbt docs graph + metadata + audit | Nguồn gốc, grain, description, snapshot mỗi attempt |
| S20 | 13:15–14:30 | AI summary/giải thích/dẫn chứng | Đúng database/filter, không lộ key |
| S21 | 14:30–15:00 | Tổng kết kết quả, trigger Disabled | Lịch, ETL, kiểm soát chất lượng, BI và AI có bằng chứng |

## 9. Nếu lúc quay khác dự kiến

- **Tự chạy thêm lần:** Disable ngay, dùng số liệu thật; số tổng không còn 4. Có thể quay lại từ reset nếu muốn giữ kịch bản chuẩn, không sửa/xóa từng log để làm giả lịch sử.
- **Trigger chưa chạy:** kiểm tra Active, giờ UTC/local, start/next run, scheduler có chạy không; không bấm Run now rồi giữ phụ đề "tự chạy theo lịch".
- **Power BI không đổi:** Refresh data, đúng parameter MAIN, bỏ chọn run/filter; cache preview trong Power Query không phải dữ liệu report đã refresh.
- **dbt WARN:** mở warning thực và giải thích rejection, không cắt cảnh để giấu cảnh báo chất lượng có chủ đích.
- **Lỗi header còn STARTED:** sửa/đối soát logging trước khi kết luận. Một run chưa kết thúc không phải FAILED và không được tính vào mẫu số success rate.
- **Mất commit acknowledgement/IN_DOUBT:** dừng demo retry và đối soát witness; không chạy lại DML tùy tiện.
- **AI lỗi key/quota:** giữ cảnh đã quay thành công với bằng chứng thật hoặc xử lý trước khi quay tiếp; không thay ảnh giả hoặc gán summary viết tay là output LLM.

## 10. Checklist xuất video

- [ ] Đã lưu đầy đủ project Power BI vừa chỉnh trước reset.
- [ ] Chỉ trigger tự chạy trong các cảnh lập lịch; có Next run/run history/timestamps.
- [ ] Không có trigger active khi ghi kết thúc hoặc khi reset lại.
- [ ] SSMS và Power BI cùng database/filter; số liệu tổng và per-run phân biệt rõ.
- [ ] Có full, insert/update/reject/unchanged, lỗi và rerun không trùng.
- [ ] Phân biệt raw/Fact/rejection, Mage/dbt rejection, warning/error, UTC/UTC+7.
- [ ] Có metadata/lineage và AI evidence cho bản demo toàn dự án.
- [ ] Không lộ password, Gemini key, notification hoặc credential manager.
- [ ] Phụ đề khớp thời điểm clip thực tế; có chú thích tua nhanh/cắt thời gian chờ.
- [ ] Không ghi "E2E PASS" nếu các cảnh chưa thực sự chạy và đối chiếu.
