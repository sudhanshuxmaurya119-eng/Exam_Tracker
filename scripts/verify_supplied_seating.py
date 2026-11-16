"""Verify supplied-plan lookup with the API offline; requires Vite and Playwright."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'frontend/src/data/seating-plans.json').read_text(encoding='utf-8'))
assert len(manifest) == 46
assert sum(p['kind'] == 'roomwise' for p in manifest) == 25
seat_count = 0
for plan in manifest:
    assert (ROOT / 'frontend/public' / plan['url']).read_bytes().startswith(b'%PDF')
    if plan['kind'] != 'roomwise':
        continue
    index = json.loads((ROOT / 'frontend/public' / plan['indexUrl']).read_text(encoding='utf-8'))
    assert len(index['seats']) == plan['seatCount']
    assert len(index['rooms']) == plan['pages']
    seat_count += len(index['seats'])
    for roll, room, row, column in index['seats']:
        assert roll.isdigit() and len(roll) == (16 if plan.get('universityBatch') else 15)
        assert 0 <= room < len(index['rooms']) and row > 0 and column > 0

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/api/v1/**', lambda route: route.abort())
    page.goto('http://127.0.0.1:5173/')
    def search(plan, roll):
        page.locator('#exam-filter').select_option(plan)
        page.locator('#roll-number-input').fill(roll)
        page.get_by_role('button', name='Find My Seat', exact=True).click()
        expect(page.locator('#supplied-results-heading')).to_be_visible()
    search('plan:2026-11-18-morning-roomwise', '202401100200093')
    result = page.locator('section[aria-labelledby="supplied-results-heading"]')
    expect(result.get_by_text('E-006', exact=True)).to_be_visible()
    expect(result.get_by_text('Ground Floor', exact=True)).to_be_visible()
    expect(result.get_by_text('Row 1, Column 1', exact=True)).to_be_visible()
    source = result.get_by_role('link', name='View room plan · page 1')
    assert source.get_attribute('href').endswith('2026-11-18-morning-roomwise.pdf#page=1')
    # Third physical seat column skips the first aisle in the PDF.
    search('plan:2026-11-18-morning-roomwise', '202501100200012')
    expect(result.get_by_text('Row 1, Column 3', exact=True)).to_be_visible()
    # The alternate A/B layout retains empty B seats as actual columns.
    search('plan:2026-11-18-evening-roomwise', '202510115100020')
    expect(result.get_by_text('B-201', exact=True)).to_be_visible()
    expect(result.get_by_text('Row 1, Column 3', exact=True)).to_be_visible()
    expect(result.get_by_text('Not stated in this plan', exact=True)).to_be_visible()
    search('', '202401100200093')
    assert result.locator('article').count() > 1
    search('plan:2026-11-18-morning-roomwise', '999999999999999')
    expect(result.get_by_role('heading', name='No matching seat found')).to_be_visible()
    assert page.locator('#seating-plans').count() == 0
    nav = page.get_by_role('navigation', name='Main navigation')
    assert nav.get_by_role('link').count() == 2
    expect(page.locator('footer')).to_contain_text('Made By Sudhanshu')
    search('plan:2026-11-18-morning-roomwise', '202401100200093')
    for width in (320, 375, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 950})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}px'
        if width in (375, 1440):
            result.scroll_into_view_if_needed()
            page.screenshot(path=str(ROOT / f'tmp/seating-results-{width}.png'))
    for href in ('seating-plans/2026-11-18-morning-roomwise.pdf', 'seating-plans/all-seating-plans-november-2026.zip'):
        response = page.request.get(f'http://127.0.0.1:5173/{href}')
        assert response.ok
    # A failed index fetch must show an error, not claim no seat exists.
    page.reload()
    page.route('**/seating-plans/2026-11-18-morning-roomwise.json', lambda route: route.abort())
    page.locator('#exam-filter').select_option('plan:2026-11-18-morning-roomwise')
    page.locator('#roll-number-input').fill('202401100200093')
    page.get_by_role('button', name='Find My Seat', exact=True).click()
    expect(page.get_by_text('The seating plans could not be loaded. Please check your connection and try again.')).to_be_visible()
    assert not errors, errors
    browser.close()
print(f'PASS: {seat_count} indexed seats, 22 PDFs, exact-roll lookup, both grid layouts, filters, failure states, downloads and responsive layouts')
