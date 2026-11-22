# Bàn giao metadata và audit — 22/11/2026

## 1. Phạm vi hoàn thành

Task này chỉ cập nhật tài liệu, descriptions và meta dbt. Không đổi SQL model, DDL, business rules, pipeline, DAX, AI logic hoặc dashboard; không chạy ETL/dbt build và không kết nối database.

| Đầu ra | Đường dẫn / mục đích |
|---|---|
| Data Dictionary | `project_management/DATA_DICTIONARY.md`: staging 26 cột, load_batch 18 cột, dbt_run 9 cột, 11 model dbt và 4 key-map |
| Mapping/lineage | `project_management/SOURCE_TO_TARGET_MAPPING.md`: đủ 16 cột nguồn, derived fields, Mermaid luồng mới |
| Data Contract | `project_management/DATA_CONTRACT.md`: interface triển khai, auth, batch/attempt, null/warning/retry và giới hạn |
| KPI metadata | `project_management/KPI_DICTIONARY.md`: trace 10 KPI → DAX thực tế → AI key, phạm vi Fact, BLANK/NULL |
| dbt metadata | 4 YAML trong models/sources, staging, intermediate, marts; đủ mô tả mọi cột đã đối chiếu |
| Điểm truy cập | README, PROJECT_CONTEXT và dbt README cập nhật; thiết kế/handoff cũ được đánh dấu là lịch sử |
| Ghi nhận hiện trạng | DECISION_LOG: phân biệt mô tả code với phê duyệt nghiệp vụ |

Không tự đổi các task kỹ thuật còn Todo thành Done. Không tạo source/model giả để nối audit vào lineage dbt: audit do Mage ghi, quan hệ được giải thích trong dictionary/mapping.

## 2. Các sai lệch đã xử lý trong metadata

1. **Immutable raw → current-state upsert.** Giữ nguyên chuỗi của phiên bản hiện hành, không giữ mọi phiên bản dòng trong staging.
2. **Fact 31 → 33 cột.** Hai cột distance_outlier_flag và distance_status đã có trong code/model, không được task này thêm mới.
3. **Source 21 → 26 cột.** Bổ sung năm trường hash/update vào metadata nguồn.
4. **Missing/rating.** Rule hiện tại required giờ/rating và reject thiếu/ngoài miền. Thiết kế cũ muốn giữ chúng trong Fact; đã ghi khác biệt, không thay rule.
5. **Khoảng cách.** Haversine >50 vẫn giữ, cờ valid=0 và status/band giải thích; không tự biến mọi outlier thành NULL/Unknown.
6. **Kiểu lịch.** DATEPART/UNION tạo INT; không coi tinyint/smallint thiết kế là DDL đã quan sát.
7. **Lineage.** Fact.loaded_at/load_batch_id/source_file_name là insert staging đầu, không phải thời gian/batch dựng DDS mới nhất. updated_* staging cũng được khởi tạo ở insert.
8. **Audit.** Tách ingestion SUCCEEDED, dbt attempt và trạng thái toàn ETL; missing log không phải SUCCESS. Không cộng counter sau join 1:n hoặc lấy Fact hiện tại làm lịch sử.
9. **KPI.** Số profiling nguồn không phải số kỳ vọng Fact; DAX hiện count bằng SUM(delivery_count), AI tính tương ứng trên grain hợp lệ. DAX BLANK và tỷ lệ coverage được phân biệt với 0.
10. **Archive/auth.** Không khẳng định loader tự archive mọi input; auth runner SQL/Windows theo cấu hình chung, không ép Windows khi nhóm dùng sa.

## 3. Nguồn bằng chứng và mức kiểm chứng

- Đọc source code, DDL và TMDL hiện tại trong repo.
- Catalog có sẵn `dbt_project/target/catalog.json`, generated_at 13/11/2026: dùng đối chiếu danh sách cột và kiểu cơ sở với SQL; không coi đó là catalog live vừa sinh.
- Manifest có sẵn dùng đối chiếu schema/materialization, số model và test definitions. Metadata mới trong YAML chưa tự cập nhật manifest/catalog cũ.
- Người dùng đã cung cấp ảnh 5 run thành công. Task này chỉ đọc thêm summary.json cục bộ của những run đó (nếu còn), không chạy lại hay tự tạo bằng chứng runtime.
- Kết quả kiểm tra tĩnh và bản tóm tắt log được ghi ở `evidence/metadata/verification.json`; không chứa password/connection string/profile runtime.

Chưa kiểm chứng trong task này: schema live, nullable/độ dài chuỗi SQL suy ra trên server hiện tại, SQL extended properties mới, render giao diện dbt docs và số liệu Power BI/AI trên database đang chạy. Đã ghi rõ kiểu suy ra/logic thay vì bịa precision hoặc constraint vật lý.

## 4. Cách đọc audit cho người làm dashboard

1. `audit.load_batch` là grain ingestion batch; có thể filter theo batch_type, source_file_name, started_at và status.
2. `audit.dbt_run` là attempt; một batch có nhiều attempt. Chọn attempt mới nhất cho summary batch hoặc hiển thị từng attempt, không SUM ingestion counters sau join 1:n.
3. Ingestion FAILED hoặc dbt FAILED → lần xử lý tương ứng thất bại. Ingestion SUCCEEDED và attempt SUCCEEDED → đủ bằng chứng bước dbt/đối soát đã đạt. Ingestion SUCCEEDED nhưng không có attempt → chưa ghi nhận, không tự là thành công.
4. `result_summary` chứa test counts và snapshot số dòng khi tới được bước đó. SQL JSON_VALUE trả text/NULL; chuyển kiểu số có kiểm soát và không mặc định mọi NULL thành 0.
5. `rows_loaded=inserted+updated`; update không tự làm số dòng Fact tăng. Rejected Mage và rejected dbt có phạm vi khác nhau.
6. Thời lượng ingestion và dbt riêng biệt; audit ingestion bắt đầu ở exporter, không được gọi là thời lượng từ trigger. NULL finished_at hoặc STARTED cũ cần cảnh báo chưa hoàn tất/chưa rõ, chưa có heartbeat tự động.
7. Thời gian nguồn vận hành là UTC, có thể tạo cột UTC+7 để hiển thị. Ngày nghiệp vụ của dim_date không phải ngày chạy ETL.
8. Power BI Import cần refresh và hiển thị thời điểm refresh thật. Chưa xây trang Monitoring trong task này.

## 5. Tạo tài liệu dbt khi vận hành sẵn sàng

Descriptions nằm trong YAML và có hiệu lực với lần parse/docs tiếp theo. Sửa YAML không tự thay comment/extended properties trên SQL Server. Không chạy dbt build chỉ để đọc tài liệu trong task này.

Nếu dùng profile cá nhân `dbt_project/profiles.yml` với env vars như template, người vận hành tự thiết lập SQL authentication trong terminal. Ví dụ server/database demo đã dùng:

```powershell
Set-Location 'D:\BI\Mini Project\BI_AI_Project'
$env:DBT_SQLSERVER_SERVER = 'NHAT-ANH\SQLEXPRESS'
$env:DBT_SQLSERVER_DATABASE = 'AmazonDeliveryBI_Demo'
$env:DBT_SQLSERVER_DRIVER = 'ODBC Driver 18 for SQL Server'
$env:DBT_SQLSERVER_PORT = '1433'
$env:DBT_SQLSERVER_USER = 'sa'
$metadataPassword = Read-Host 'Nhap mat khau SQL Server' -AsSecureString
$metadataCredential = [System.Management.Automation.PSCredential]::new('sa', $metadataPassword)
$env:DBT_SQLSERVER_PASSWORD = $metadataCredential.GetNetworkCredential().Password
try {
    & '.\.venv\Scripts\dbt.exe' docs generate --project-dir dbt_project --profiles-dir dbt_project
} finally {
    Remove-Item Env:DBT_SQLSERVER_PASSWORD -ErrorAction SilentlyContinue
}
```

Kiểm tra profile dev đúng auth/database/schema trước khi dùng; không commit hoặc in giá trị credential. Lệnh docs cần kết nối để lấy catalog, không phải lệnh nạp lại CSV hoặc materialize Fact. Task này **không chạy** lệnh trên.

Sau khi generate thành công:

```powershell
.\.venv\Scripts\dbt.exe docs serve --project-dir dbt_project --profiles-dir dbt_project --port 8080
```

Kiểm tra documentation và lineage tại địa chỉ terminal báo; catalog/manifest/index.html sinh dưới target theo cấu hình. Không đổi hoặc giả cập nhật thời gian catalog cũ để trình bày là mới.

## 6. Hạng mục còn thuộc người phụ trách khác

- Xác nhận nghiệp vụ về required/rating so với thiết kế ban đầu; không cần sửa code nếu nhóm chấp nhận triển khai hiện tại, nhưng phải hiểu khác biệt.
- Nếu cần giám sát mọi trigger/loader error, bổ sung run-start/heartbeat và liên kết batch riêng; audit hiện chưa bao phủ toàn bộ các lỗi sớm.
- Lập lịch, dashboard Monitoring, refresh tự động, quay video và runtime nghiệm thu là công việc riêng.
- Nếu thay schema/rule/KPI sau này, cập nhật dictionary, mapping, dbt descriptions và DAX/AI traceability cùng lúc; không giữ số demo làm hằng số.

Task metadata có thể bàn giao ở mức source/documentation đã kiểm tra tĩnh. Những mục runtime bên trên được để rõ chưa chạy, không dùng chúng để khẳng định end-to-end vừa được nghiệm thu lại.
