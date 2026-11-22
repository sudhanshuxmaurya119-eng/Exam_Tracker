"""Verify supplied-plan lookup with the API offline; requires Vite and Playwright."""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5173/').rstrip('/') + '/'
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
    page.goto(BASE_URL)
    date_values = page.locator('#exam-filter option').evaluate_all('(options) => options.map(option => option.value)')
    assert len(date_values) == len(set(date_values)) == 8
    assert date_values == ['', '2026-11-18', '2026-11-19', '2026-11-20', '2026-11-23', '2026-11-25', '2026-11-26', '2026-11-27']
    assert page.locator('#exam-filter optgroup').count() == 0
    def submit(date, roll, shift=''):
        page.locator('#exam-filter').select_option(date)
        page.locator('#shift-filter').select_option(shift)
        page.locator('#roll-number-input').fill(roll)
        page.get_by_role('button', name='Find My Seat', exact=True).click()
    def search(date, roll, shift=''):
        submit(date, roll, shift)
        expect(page.locator('#supplied-results-heading')).to_be_visible()
    search('2026-11-18', '202401100200093', 'Morning')
    result = page.locator('section[aria-labelledby="supplied-results-heading"]')
    expect(result.get_by_text('E-006', exact=True)).to_be_visible()
    expect(result.get_by_text('Ground Floor', exact=True)).to_be_visible()
    expect(result.get_by_text('Row 1, Column 1', exact=True)).to_be_visible()
    source = result.get_by_role('link', name='View room plan · page 1')
    assert source.get_attribute('href').endswith('2026-11-18-morning-roomwise.pdf#page=1')
    # Third physical seat column skips the first aisle in the PDF.
    search('2026-11-18', '202501100200012', 'Morning')
    expect(result.get_by_text('Row 1, Column 3', exact=True)).to_be_visible()
    # The alternate A/B layout retains empty B seats as actual columns.
    search('2026-11-18', '202510115100020', 'Evening')
    expect(result.get_by_text('B-201', exact=True)).to_be_visible()
    expect(result.get_by_text('Row 1, Column 3', exact=True)).to_be_visible()
    expect(result.get_by_text('Not stated in this plan', exact=True)).to_be_visible()
    search('', '202401100200093')
    assert result.locator('article').count() > 1
    search('2026-11-18', '999999999999999')
    expect(result.get_by_role('heading', name='No matching seat found')).to_be_visible()
    assert page.locator('#seating-plans').count() == 0
    nav = page.get_by_role('navigation', name='Main navigation')
    assert nav.get_by_role('link').count() == 2
    expect(page.locator('footer')).to_contain_text('Made By Sudhanshu')
    # Every updated data source must be reachable by date alone.
    cases = [
        ('2026-11-23', '202501100400038', 'AI201B · Machine Learning Essentials'),
        ('2026-11-19', '202501100400038', 'CS336B · Object Oriented Programming with Java'),
        ('2026-11-19', '2500290310001', 'AI101B · Introduction to AI'),
    ]
    for date, roll, title in cases:
        submit(date, roll)
        expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
    assert page.get_by_role('heading', name='AI201B · Machine Learning Essentials', exact=True).count() == 0
    for filename, date, title in [
        ('cs205b-seating.json', '2026-11-23', 'CS205B seating · 23 November 2026'),
        ('cs302b-seating.json', '2026-11-25', 'CS302B · Advanced Data Structure'),
        ('it107b-seating.json', '2026-11-23', 'IT107B · Artificial Intelligence Essentials'),
        ('el106b-roster.json', '2026-11-20', 'EL106B · Introduction to AI & ML'),
    ]:
        data = json.loads((ROOT / 'frontend/src/data' / filename).read_text(encoding='utf-8'))
        submit(date, next(iter(data)))
        expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
    tracks = json.loads((ROOT / 'frontend/src/data/track-seating.json').read_text(encoding='utf-8'))
    uid = next(uid for uid, seats in tracks.items() if {seat['exam'] for seat in seats} == {'pps','ibm'})
    submit('2026-11-18', uid)
    expect(page.get_by_role('heading', name='Programming for Problem Solving (26IT101ESB)', exact=True)).to_be_visible()
    assert page.get_by_role('heading', name='IBM Track · Web Designing and Cloud Foundations', exact=True).count() == 0
    submit('2026-11-19', uid)
    expect(page.get_by_role('heading', name='IBM Track · Web Designing and Cloud Foundations', exact=True)).to_be_visible()
    assert page.get_by_role('heading', name='Programming for Problem Solving (26IT101ESB)', exact=True).count() == 0
    finals = json.loads((ROOT / 'frontend/src/data/ai201b-final-seating.json').read_text(encoding='utf-8'))
    minor = next(uid for uid, seats in finals.items() if any(seat['session']=='ai201b-minor' for seat in seats))
    submit('2026-11-27', minor, 'Evening')
    expect(page.get_by_role('heading', name='Minor course · Final seating plan', exact=True)).to_be_visible()
    submit('2026-11-27', minor, 'Morning')
    expect(page.get_by_role('button', name='Find My Seat', exact=True)).to_be_enabled()
    assert page.get_by_role('heading', name='Minor course · Final seating plan', exact=True).count() == 0
    university = next(plan for plan in manifest if plan.get('universityBatch') and plan['kind']=='roomwise')
    index = json.loads((ROOT / 'frontend/public' / university['indexUrl']).read_text())
    search(university['date'], index['seats'][0][0], university['shift'])
    expect(result.get_by_text(index['rooms'][0]['room'], exact=True)).to_be_visible()
    search('2026-11-18', '202401100200093', 'Morning')
    for width in (320, 375, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 950})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}px'
        if width in (375, 1440):
            result.scroll_into_view_if_needed()
            page.screenshot(path=str(ROOT / f'tmp/seating-results-{width}.png'))
    for href in ('seating-plans/2026-11-18-morning-roomwise.pdf', 'seating-plans/all-seating-plans-november-2026.zip'):
        response = page.request.get(BASE_URL+href)
        assert response.ok
    # A failed index fetch must show an error, not claim no seat exists.
    page.reload()
    page.route('**/seating-plans/2026-11-18-morning-roomwise.json', lambda route: route.abort())
    page.locator('#exam-filter').select_option('2026-11-18')
    page.locator('#roll-number-input').fill('202401100200093')
    page.get_by_role('button', name='Find My Seat', exact=True).click()
    expect(page.get_by_text('The seating plans could not be loaded. Please check your connection and try again.')).to_be_visible()
    assert not errors, errors
    browser.close()
print(f'PASS: {seat_count} indexed seats, {len(manifest)} PDFs, unique date options, all updated data sources, shifts, failure states, downloads and responsive layouts')
