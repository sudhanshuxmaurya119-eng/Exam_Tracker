# Supplied November 2026 plans

The student portal includes the 22 PDFs from the supplied ZIP and a roll-number
lookup for all 13 roomwise plans. The notice covers the requested student groups
and 18–27 November 2026. The supplied video is a UI reference; its September
exam dates are not imported.

## Updating the assets

Install PyMuPDF in the Python environment, then run from the project root:

```powershell
python scripts/import_seating_plans.py 'path/to/plans.zip'
```

The importer writes the PDF files, original ZIP, and compact per-plan seat indexes
to `frontend/public/seating-plans/`, plus the manifest in
`frontend/src/data/seating-plans.json`. Vite includes these assets in its build.
It validates the source document date instead of relying on filename suffixes.
The importer checks each page's indexed roll numbers against text in its grid.

The current import contains 15,349 seat entries across 231 roomwise pages.
Lookup uses exact full 15-digit roll numbers, never consolidated roll ranges.
Consolidated PDFs remain available as original documents; four evening sessions
have no supplied consolidated PDF and are labelled accordingly.

Row positions count from the top of the source grid, and columns from the left,
excluding the blank aisle columns in the generated layout. The alternate A/B
layout retains both A and B seat columns, including empty seats. These are grid
coordinates, not institution-assigned seat numbers. Every result links to its
original PDF page. Floors are shown only when explicitly stated in the source.

## Runtime and checks

The default seat search queries the supplied roomwise plans. A specific plan or
shift can narrow the search. Other database-backed examinations remain selectable
when published by the backend. Supplied-plan indexes load on demand and do not
require the backend. A failed index request shows an error and permits retry.

With Vite running on port 5173, install Playwright for Python and Microsoft Edge,
then run:

```powershell
python scripts/verify_supplied_seating.py
python scripts/verify_timetable.py
```

These checks cover both PDF layouts, exact-roll matches, missing records, failed
index requests, document links, filters, and widths from 320px to 1440px.
The existing timetable remains independently searchable.
