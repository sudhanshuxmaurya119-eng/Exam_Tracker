"""Import PDF plans from a supplied ZIP. Never execute document content.

Usage: python scripts/import_seating_plans.py path/to/plans.zip
Requires PyMuPDF. Roll matches come from individual roomwise table cells,
never from consolidated roll ranges (which can contain gaps).
"""
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
import pymupdf as fitz
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'frontend/public/seating-plans'

def clean(text):
    return re.sub(r'\s+', ' ', text).strip()

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')

def import_plans(source):
    PUBLIC.mkdir(parents=True, exist_ok=True)
    manifest = []
    with ZipFile(source) as archive:
        for item in archive.infolist():
            if not item.filename.lower().endswith('.pdf'):
                continue
            payload = archive.read(item)
            doc = fitz.open(stream=payload, filetype='pdf')
            text = clean(doc[0].get_text())
            # Read the displayed date, not the frequently reused filename suffix.
            date_match = re.search(r'\b(\d{1,2})\s+(?:NOVEMBER|Nov\.?)\s+2026\b', text, re.I)
            assert date_match, item.filename
            day = int(date_match[1])
            shift = 'Morning' if 'MORNING' in text.upper() else 'Evening'
            assert shift.upper() in text.upper(), item.filename
            kind = 'roomwise' if item.filename.startswith('ROOMWISE') else 'consolidated'
            slug = f'2026-11-{day:02d}-{shift.lower()}-{kind}'
            assert not any(m['id'] == slug for m in manifest), slug
            (PUBLIC / f'{slug}.pdf').write_bytes(payload)
            entry = dict(id=slug, date=f'2026-11-{day:02d}', shift=shift, kind=kind,
                url=f'seating-plans/{slug}.pdf', pages=len(doc), originalName=item.filename)
            if kind == 'roomwise':
                rooms, seats, seen = [], [], set()
                for page_number, page in enumerate(doc, 1):
                    page_text = clean(page.get_text())
                    room_match = re.search(r'(?:Room Name\s*:|ROOM NO\s*:)\s*([A-Z]+\s*-\s*\d+[A-Z]?)', page_text, re.I)
                    assert room_match, (item.filename, page_number, 'Missing room')
                    room = re.sub(r'\s+', '', room_match[1]).upper()
                    building_match = re.search(r'Building Name\s*:\s*(\S+)', page_text, re.I)
                    floor_match = re.search(r'Floor Name\s*:\s*(.*?)\s*Room Name', page_text, re.I)
                    rooms.append(dict(room=room, building=building_match[1] if building_match else room.split('-')[0],
                        floor=floor_match[1] if floor_match else '', page=page_number))
                    count_before = len(seats)
                    source_rolls = Counter()
                    for table in page.find_tables().tables:
                        rows = table.extract()
                        if not any(re.search(r'(?<!\d)\d{15}(?!\d)', re.sub(r'\s+', '', cell or '')) for row in rows for cell in row):
                            continue
                        source_rolls.update(re.findall(r'20\d{13}', re.sub(r'\s+', '', page.get_text(clip=fitz.Rect(table.bbox)))))
                        # Generated layouts have two seat columns then an aisle.
                        # The alternate A/B layout has ten actual seat columns.
                        standard = 'Room Name' in page_text
                        columns = [c for c in range(table.col_count) if not (standard and c % 3 == 2)]
                        row_number = 0
                        for row in rows:
                            if not any(re.search(r'(?<!\d)\d{15}(?!\d)', re.sub(r'\s+', '', cell or '')) for cell in row):
                                # Empty physical rows still count; these tables have no header.
                                row_number += 1
                                continue
                            row_number += 1
                            for column_number, c in enumerate(columns, 1):
                                value = re.sub(r'\s+', '', row[c] or '')
                                rolls = re.findall(r'(?<!\d)\d{15}(?!\d)', value)
                                assert len(rolls) <= 1, (slug, page_number, row_number, c)
                                for roll in rolls:
                                    key = (roll, page_number, row_number, column_number)
                                    assert key not in seen, key
                                    seen.add(key)
                                    seats.append([roll, len(rooms)-1, row_number, column_number])
                    assert len(seats) > count_before, (slug, page_number, 'No seats parsed')
                    parsed_rolls = Counter(s[0] for s in seats[count_before:])
                    assert source_rolls == parsed_rolls, (slug, page_number, 'Roll coverage mismatch', source_rolls-parsed_rolls, parsed_rolls-source_rolls)
                write_json(PUBLIC / f'{slug}.json', dict(rooms=rooms, seats=seats))
                entry.update(indexUrl=f'seating-plans/{slug}.json', seatCount=len(seats))
                print(f'{slug}: {len(seats)} seats / {len(rooms)} rooms', flush=True)
            manifest.append(entry)
    manifest.sort(key=lambda m: (m['date'], m['shift'] != 'Morning', m['kind']))
    target = ROOT / 'frontend/src/data/seating-plans.json'
    write_json(target, manifest)
    shutil.copyfile(source, PUBLIC / 'all-seating-plans-november-2026.zip')
    print(f'Imported {len(manifest)} documents', flush=True)

if __name__ == '__main__':
    import_plans(Path(sys.argv[1]))
