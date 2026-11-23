"""Generate deterministic demo inputs only. Never connects to SQL or runs ETL."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mage_project.amazon_delivery_contract import SOURCE_COLUMNS, compute_raw_row_hash


def write_csv(folder: Path, name: str, rows: list[dict], columns=None) -> Path:
    path = folder / name
    with path.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=columns or SOURCE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def expected_counts(rows: list[dict], state: dict) -> dict:
    counters = dict(rows_read=len(rows), rows_inserted=0, rows_updated=0,
                    rows_unchanged=0, rows_rejected=0)
    for row in rows:
        key = row['Order_ID'].strip().casefold()
        try:
            datetime.strptime(row['Order_Date'], '%Y-%m-%d')
            valid_date = True
        except ValueError:
            valid_date = False
        if key in ('', 'nan', 'null', 'none', 'n/a', 'na', '-') or len(key) > 32 or not valid_date:
            counters['rows_rejected'] += 1
            continue
        digest = compute_raw_row_hash([row[c] for c in SOURCE_COLUMNS if c != 'Order_ID'])
        action = ('rows_inserted' if key not in state else
                  'rows_unchanged' if state[key] == digest else 'rows_updated')
        counters[action] += 1
        state[key] = digest
    counters['rows_loaded'] = counters['rows_inserted'] + counters['rows_updated']
    counters['staging_total_after'] = len(state)
    return counters


def main() -> None:
    folder = ROOT / 'demo' / 'etl_batches'
    folder.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'data/raw/amazon_delivery.csv'
    with source.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != SOURCE_COLUMNS:
            raise ValueError('Header CSV gốc không khớp source contract.')
        records = list(reader)
    records.sort(key=lambda row: (row['Order_Date'], row['Order_ID']))
    keys = [row['Order_ID'].strip().casefold() for row in records]
    if len(keys) != len(set(keys)):
        raise ValueError('Nguồn có Order_ID trùng; cần rà soát trước khi chia batch.')
    baseline = [r for r in records if r['Order_Date'] <= '2022-03-01']
    next_batch = [r for r in records if '2022-03-01' < r['Order_Date'] <= '2022-03-20']
    remaining = [r for r in records if r['Order_Date'] > '2022-03-20']
    if not all((baseline, next_batch, remaining)):
        raise ValueError('Dataset không còn phù hợp ba khoảng ngày demo đã định nghĩa.')
    # These four rows are explicitly synthetic. Keep valid source dates within
    # the existing dim_date calendar; no future dates or new business rules.
    template = dict(zip(SOURCE_COLUMNS, [
        'seminar3_new_001', '30', '4.5', '12.91', '77.68', '12.92', '77.69',
        '2022-04-06', '10:00:00', '10:10:00', 'Sunny', 'Low ', 'motorcycle ',
        'Urban ', '120', 'Clothing']))
    for key in ('seminar3_new_001', 'seminar3_new_002', 'seminar3_bad_date'):
        if key in keys:
            raise ValueError(f'ID mô phỏng trùng nguồn: {key}')
    inserted = [template.copy(), {**template, 'Order_ID': 'seminar3_new_002', 'Delivery_Time': '130'}]
    changed = []
    for original in baseline[:2]:
        value = original['Delivery_Time']
        replacement = '150' if value != '150' else '151'
        changed.append({**original, 'Delivery_Time': replacement})
    unchanged = [dict(r) for r in baseline[2:4]]
    invalid = [{**template, 'Order_ID': ''},
               {**template, 'Order_ID': 'seminar3_bad_date', 'Order_Date': '2022-02-30'}]
    mixed = inserted + changed + unchanged + invalid
    sequence = [
        ('01_baseline.csv', 'FULL_LOAD', baseline),
        ('02_incremental.csv', 'INCREMENTAL', next_batch),
        ('03_incremental.csv', 'INCREMENTAL', remaining),
        ('04_mixed.csv', 'INCREMENTAL', mixed),
        ('05_rerun.csv', 'INCREMENTAL', mixed),
    ]
    state, manifest = {}, []
    for name, kind, rows in sequence:
        path = write_csv(folder, name, rows)
        manifest.append({
            'file': path.relative_to(ROOT).as_posix(), 'batch_type': kind,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'expected_ingestion': expected_counts(rows, state),
        })
    # Failed files are NOT included in the successful simulated state above.
    write_csv(folder, '06_bad_header.csv', [{'Order_ID': 'bad_header', 'Delivery_Time': '120'}],
              columns=['Order_ID', 'Delivery_Time'])
    write_csv(folder, '07_duplicate_id.csv', [inserted[0], inserted[0]])
    output = {
        'source': source.relative_to(ROOT).as_posix(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'source_rows': len(records),
        'precondition': 'Fresh empty demo database; run files 01..05 exactly once in order.',
        'synthetic_updates': [{'Order_ID': r['Order_ID'], 'Delivery_Time': r['Delivery_Time']}
                              for r in changed],
        'runs': manifest,
        'failure_files': ['06_bad_header.csv', '07_duplicate_id.csv'],
        'note': 'These are calculated ingestion expectations, not database test results. '
                'dbt rejection is separate. Rerun keeps the two invalid rows rejected.',
    }
    (folder / 'expected_results.json').write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Generated {folder}; source unchanged; no database commands executed.')
    for run in manifest:
        print(run['file'], run['expected_ingestion'])


if __name__ == '__main__':
    main()
