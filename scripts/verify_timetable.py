"""Browser smoke check; run with Vite on localhost:5173 and Playwright installed."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    # The PDF timetable must remain usable with the seat lookup backend offline.
    page.route('**/api/v1/**', lambda route: route.abort())
    page.goto('http://127.0.0.1:5173/timetable')
    section = page.locator('#exam-timetable')
    section.get_by_label('Programme', exact=True).select_option('B.Tech')
    section.get_by_label('Semester', exact=True).select_option('I')
    section.get_by_label('Branch / Specialisation', exact=True).select_option('CSE')
    assert section.locator('tbody tr').count() == 8
    section.get_by_label('Search timetable', exact=True).fill('26MA101BSL')
    assert section.locator('tbody tr').count() == 1
    assert section.locator('tbody time').get_attribute('datetime') == '2026-11-25'
    section.get_by_label('Exam date', exact=True).select_option('2026-11-18')
    assert section.get_by_text('No exams match your filters').is_visible()
    section.get_by_role('button', name='Clear filters').click()
    assert section.locator('tbody tr').count() == 403
    section.get_by_label('Search timetable', exact=True).fill('26MA101BSL')
    for width in (320, 375, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 950})
        section.scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}px'
        if width < 768:
            assert section.locator('article').first.is_visible()
            assert not section.locator('table').is_visible()
        else:
            assert section.locator('table').is_visible()
        if width in (375, 1440):
            page.screenshot(path=str(ROOT / f'tmp/timetable-{width}.png'))
    response = page.request.get('http://127.0.0.1:5173/exam-datesheet-november-2026.pdf')
    assert response.ok and response.body().startswith(b'%PDF')
    assert not errors, errors
    browser.close()
print('PASS: filters, search, reset, empty state, PDF, offline timetable, and 320/375/768/1440px layouts')
