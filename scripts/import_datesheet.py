"""Extract the supplied datesheet into the public, offline timetable.

Usage: python scripts/import_datesheet.py path/to/datesheet.pdf
Requires PyMuPDF. Document text is treated only as schedule data.
"""
import json
import re
import shutil
import sys
from pathlib import Path
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = [
    ('MBA', 'I'), ('MCA', 'I'), ('M.Tech CSE-AIML', 'I'),
    ('M.Tech CSE', 'I'), ('M.Pharma', 'I'), ('B.Tech', 'I'),
    ('B.Pharma', 'I'), ('MBA', 'III'), ('MCA', 'III'),
    ('M.Tech CSE', 'III'), ('B.Tech', 'III'), ('B.Pharma', 'III'),
    ('M.Pharma', 'III'), ('B.Tech', 'V'), ('B.Pharma', 'V'),
    ('B.Tech', 'VII'), ('B.Pharma', 'VII'),
]

def clean(value):
    return re.sub(r'\s+', ' ', (value or '').replace('\ufffd', ' ')).strip()

def extract(source):
    result = []
    document = fitz.open(source)
    assert len(document) == len(PROGRAMS), 'Review program mapping for this PDF'
    for page_index, page in enumerate(document):
        program, semester = PROGRAMS[page_index]
        table = next(t for t in page.find_tables().tables if any('DATE' in r for r in t.extract()))
        raw = table.extract()
        header_index = next(i for i, r in enumerate(raw) if 'DATE' in r)
        # Read original PDF text inside cells: table.extract can scramble narrow lines.
        rows = [[clean(page.get_text(clip=fitz.Rect(c))) if c else None for c in row.cells] for row in table.rows]
        headers = rows[header_index]
        groups = []
        if program in ('B.Tech', 'M.Pharma'):
            for column in range(3, len(headers)):
                if headers[column]:
                    groups.append((headers[column], [column]))
                else:
                    groups[-1][1].append(column)
        else:
            groups = [(program, list(range(3, len(headers))))]
        last_date = last_time = ''
        for i in range(header_index + 1, len(rows)):
            row = rows[i]
            date = row[0]
            if date == '':
                # A date centred in a merged cell may appear in its lower subrow.
                date = next((r[0] for r in rows[i+1:] if r[0]), '')
            if date:
                match = re.search(r'(\d{1,2})\s*-?\s*Nov\s*-?\s*26', date, re.I)
                if not match:
                    continue
                last_date = f'2026-11-{int(match[1]):02d}'
            if row[2]:
                last_time = row[2]
            if not last_date:
                continue
            for branch, columns in groups:
                subject = clean(' '.join(row[c] or '' for c in columns))
                if not subject or re.fullmatch(r'no\s*exam', subject, re.I):
                    continue
                mode = ''
                if page_index == 0:
                    subject, mode = row[3], row[4] or ''
                if page_index == 7:
                    subject = clean(' '.join(row[c] or '' for c in (3, 4)))
                    branch = row[5] or 'MBA'
                subject = clean(subject)
                if '*' in subject and page_index == 5:
                    subject = subject.replace('*', '(excluding students enrolled in SAP courses)')
                times = re.findall(r'\d{1,2}:\d{2}\s*[AP]M', last_time, re.I)
                assert len(times) == 2, (page_index + 1, last_time)
                result.append(dict(id=len(result)+1, program=program, semester=semester,
                    branch=branch, date=last_date, start=times[0], end=times[1],
                    subject=subject, mode=mode, page=page_index+1,
                    exam='PUE' if semester == 'VII' else 'MSE 2'))
    result.sort(key=lambda r: (r['date'], int(r['start'].split(':')[0]) % 12 + (12 if 'PM' in r['start'] else 0), r['program'], r['branch']))
    target = ROOT / 'frontend/src/data/timetable.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    public = ROOT / 'frontend/public'
    public.mkdir(exist_ok=True)
    shutil.copyfile(source, public / 'exam-datesheet-november-2026.pdf')
    print(f'Imported {len(result)} entries from {len(document)} pages')

if __name__ == '__main__':
    extract(Path(sys.argv[1]))
