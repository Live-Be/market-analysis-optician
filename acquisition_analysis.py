import csv
from pathlib import Path

INPUT_FILE = Path('analysis_optiker_opticians_enriched.csv')
OUTPUT_FILE = Path('top10_takeover_candidates.csv')
REPORT_FILE = Path('top10_takeover_candidates.md')

CHAIN_KEYWORDS = [
    'apollo', 'fielmann', 'hartlauer', 'pearle', 'ace & tate', 'abele', 'aktiv optik',
    'kind', 'pro optik', 'eyes and more', 'mister spex', 'smarteyes'
]


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def looks_like_chain(name, website, is_chain_flag):
    if str(is_chain_flag).strip().lower() == 'true':
        return True
    hay = f"{name or ''} {website or ''}".lower()
    return any(k in hay for k in CHAIN_KEYWORDS)


def normalize(value, minimum, maximum, invert=False):
    if value is None:
        return 0.0
    if maximum == minimum:
        return 1.0
    scaled = (value - minimum) / (maximum - minimum)
    return 1.0 - scaled if invert else scaled


rows = []
with INPUT_FILE.open(newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['dist_to_kufstein_km'] = to_float(row.get('dist_to_kufstein_km'))
        row['competitors_within_10km'] = to_int(row.get('competitors_within_10km'))
        row['nearest_competitor_km'] = to_float(row.get('nearest_competitor_km'))
        rows.append(row)

candidates = []
seen = set()
for r in rows:
    name = (r.get('name') or '').strip()
    if not name:
        continue
    if looks_like_chain(name, r.get('website'), r.get('is_chain')):
        continue
    if r['dist_to_kufstein_km'] is None or r['competitors_within_10km'] is None or r['nearest_competitor_km'] is None:
        continue

    key = (name.lower(), (r.get('city') or '').strip().lower(), (r.get('street') or '').strip().lower(), (r.get('housenumber') or '').strip().lower())
    if key in seen:
        continue
    seen.add(key)
    candidates.append(r)

nearest_vals = [r['nearest_competitor_km'] for r in candidates]
comp_vals = [r['competitors_within_10km'] for r in candidates]
kuf_vals = [r['dist_to_kufstein_km'] for r in candidates]

for r in candidates:
    nearest_score = normalize(r['nearest_competitor_km'], min(nearest_vals), max(nearest_vals), invert=False)
    density_score = normalize(r['competitors_within_10km'], min(comp_vals), max(comp_vals), invert=True)
    kufstein_score = normalize(r['dist_to_kufstein_km'], min(kuf_vals), max(kuf_vals), invert=True)
    r['score_total'] = round(0.40 * nearest_score + 0.35 * density_score + 0.25 * kufstein_score, 4)

candidates.sort(key=lambda r: r['score_total'], reverse=True)
top10 = candidates[:10]

with OUTPUT_FILE.open('w', newline='', encoding='utf-8') as f:
    fields = [
        'rank', 'name', 'city', 'street', 'housenumber', 'postcode',
        'nearest_competitor_km', 'competitors_within_10km', 'dist_to_kufstein_km', 'score_total', 'website', 'phone'
    ]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for i, r in enumerate(top10, start=1):
        w.writerow({
            'rank': i,
            'name': r.get('name', ''),
            'city': r.get('city', ''),
            'street': r.get('street', ''),
            'housenumber': r.get('housenumber', ''),
            'postcode': r.get('postcode', ''),
            'nearest_competitor_km': f"{r['nearest_competitor_km']:.2f}",
            'competitors_within_10km': r['competitors_within_10km'],
            'dist_to_kufstein_km': f"{r['dist_to_kufstein_km']:.2f}",
            'score_total': f"{r['score_total']:.4f}",
            'website': r.get('website', ''),
            'phone': r.get('phone', ''),
        })

with REPORT_FILE.open('w', encoding='utf-8') as f:
    f.write('# Top 10 Übernahmekandidaten (Optikgeschäfte)\n\n')
    f.write('Kriterien: großer Abstand zum nächsten Konkurrenzoptiker, geringe Optikerdichte im 10-km-Radius, keine Ketten, kurze Distanz nach Kufstein.\n\n')
    f.write('| Rang | Name | Ort | Nächster Konkurrent (km) | Optiker im 10km-Radius | Distanz nach Kufstein (km) | Score |\n')
    f.write('|---:|---|---|---:|---:|---:|---:|\n')
    for i, r in enumerate(top10, start=1):
        f.write(
            f"| {i} | {r.get('name','')} | {r.get('city','')} | {r['nearest_competitor_km']:.2f} | {r['competitors_within_10km']} | {r['dist_to_kufstein_km']:.2f} | {r['score_total']:.4f} |\\n"
        )

print(f'Created {OUTPUT_FILE} and {REPORT_FILE} with {len(top10)} entries from {len(candidates)} independent candidates.')
