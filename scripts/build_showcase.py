"""Export recorded pipeline snapshots and matching HTML / SVG, with no network."""
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from moba_lab.pipeline import KEYS, run_pipeline

ROOT = Path(__file__).resolve().parents[1]
AS_OF = '2026-01-14'


def utc_day(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).date().isoformat()


def build_data(source=None):
    raw_bytes = (ROOT / 'examples/fixture.json').read_bytes()
    source = json.loads(raw_bytes) if source is None else source
    start = min(utc_day(u['signup_at']) for u in source['users'])
    snapshots = {}
    cutoff = date.fromisoformat(start)
    while cutoff <= date.fromisoformat(AS_OF):
        day = cutoff.isoformat()
        metrics = run_pipeline(source, day)
        cohorts = Counter(utc_day(u['signup_at']) for u in {u['user_id']: u for u in source['users']}.values() if utc_day(u['signup_at']) <= day)
        observed = {(r['cohort_date'], r['day_offset']): r for r in metrics['retention']}
        cells = []
        for cohort, count in sorted(cohorts.items()):
            for offset in (1, 7):
                eligible = date.fromisoformat(cohort) + timedelta(days=offset) <= cutoff
                row = observed.get((cohort, offset))
                if eligible and row is None:
                    raise ValueError('observable cohort missing from pipeline')
                cells.append(dict(cohort_date=cohort, day_offset=offset, cohort_users=count,
                                  observable=eligible, retained_users=row['retained_users'] if row else None,
                                  retention_rate=row['retention_rate'] if row else None))
        snapshots[day] = dict(metrics=metrics, retention_cells=cells, users=sum(cohorts.values()))
        cutoff += timedelta(days=1)
    counts = {table: dict(raw=len(rows), unique=len({tuple(r[k] for k in KEYS[table]) for r in rows})) for table, rows in source.items()}
    return dict(synthetic=True, source='examples/fixture.json', source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                as_of_utc=AS_OF, start_utc=start, currency='fictional single currency; 100 cents = 1 unit',
                counts=counts, snapshots=snapshots)


def make_preview(data):
    m = data['snapshots'][AS_OF]['metrics']
    t = lambda x,y,s,size=16,color='#e9eef5': f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(str(s))}</text>'
    rect = lambda x,y,w,h,c: f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{c}"/>'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="880" viewBox="0 0 1440 880" role="img" aria-label="MOBA Analytics Lab synthetic pipeline preview"><style>text{font-family:Arial,sans-serif}</style>', rect(0,0,1440,880,'#0b1220'), t(48,52,'MOBA / ANALYTICS LAB',16,'#68e0c2'), t(48,106,'From raw events to player insight',40), t(48,140,'Recorded synthetic result • UTC observation through 2026-01-14 • Python + DuckDB + SQL',17,'#a7b7cb')]
    values = [('OBSERVED PLAYERS',data['snapshots'][AS_OF]['users']),('LATEST DAU',m['dau'][-1]['dau']),('PLAYER / MATCH FACTS',sum(r['player_matches'] for r in m['hero_stats'])),('REVENUE · CURRENCY UNITS',f"{sum(r['revenue_cents'] for r in m['monetization'])/100:.2f}")]
    for i,(label,value) in enumerate(values):
        x=48+i*342
        parts += [rect(x,174,320,110,'#141f30'),t(x+20,208,label,13,'#a7b7cb'),t(x+20,258,value,36)]
    parts += [rect(48,310,850,270,'#141f30'),t(70,345,'Daily active players',23),t(70,371,f"Distinct login users per UTC day · {len(m['user_day'])} user/day facts",14,'#a7b7cb')]
    points=[]
    for i,r in enumerate(m['dau']):
        x=100+i*55; y=530-r['dau']*13
        parts += [rect(x-12,y,24,530-y,'#285e60'), t(x-7,y-12,r['dau'],13,'#68e0c2')]
        points.append(f'{x},{y}')
    parts += [f'<polyline points="{" ".join(points)}" fill="none" stroke="#68e0c2" stroke-width="3"/>',t(80,555,'JAN 01',12,'#a7b7cb'),t(790,555,'JAN 14',12,'#a7b7cb'),rect(920,310,472,270,'#141f30'),t(942,345,'Exact-day retention',23),t(942,371,'Cohort       D1             D7',15,'#a7b7cb')]
    for i,cohort in enumerate(sorted({r['cohort_date'] for r in m['retention']})):
        y=390+i*42
        parts += [t(943,y+24,cohort[5:],16)]
        for j,offset in enumerate((1,7)):
            r=next(r for r in m['retention'] if r['cohort_date']==cohort and r['day_offset']==offset)
            x=1060+j*135
            parts += [rect(x,y,118,34,'#22564f'),t(x+16,y+23,f"{r['retention_rate']:.0%} ({r['retained_users']}/{r['cohort_users']})",14)]
    parts += [rect(48,602,850,204,'#141f30'),t(70,638,'Hero performance · win rate',23),t(70,665,'One player per match; purchases cannot multiply these facts',14,'#a7b7cb')]
    for i,r in enumerate(m['hero_stats']):
        y=684+i*34
        parts += [t(70,y+19,r['hero'],16),rect(170,y,500*r['win_rate'],22,'#68e0c2'),t(690,y+19,f"{r['win_rate']:.1%} · {r['wins']}/{r['player_matches']}",16)]
    parts += [rect(920,602,472,204,'#141f30'),t(942,638,'Revenue stays in integer cents',23),t(942,675,f"{sum(r['revenue_cents'] for r in m['monetization']):,} cents = {sum(r['revenue_cents'] for r in m['monetization'])/100:.2f} currency units",19,'#ffb85c'),t(942,710,f"{data['counts']['payments']['raw']} raw payments → {sum(r['transactions'] for r in m['monetization'])} distinct transactions",16),t(942,745,'Change observation day to reveal N/A cells.',14,'#a7b7cb'),t(942,771,'N/A means too early to observe, never 0%.',14,'#a7b7cb'),t(48,848,'AI-assisted educational project · Fictional heroes and players · No production or business-impact claim',15,'#a7b7cb'),'</svg>']
    return ''.join(parts)


def main():
    data = build_data()
    (ROOT / 'docs/showcase-data.json').write_text(json.dumps(data, indent=2)+'\n')
    html = (ROOT / 'docs/index.html').read_text()
    payload = json.dumps(data, separators=(',', ':')).replace('<', '\\u003c')
    html = re.sub(r'(<script id="showcase-data" type="application/json">).*?(</script>)', lambda m:m[1]+payload+m[2],html,flags=re.S)
    (ROOT / 'docs/index.html').write_text(html)
    (ROOT / 'docs/assets/showcase.svg').write_text(make_preview(data))
    print(f'Exported {len(data["snapshots"])} actual pipeline snapshots through {AS_OF}')

if __name__ == '__main__':
    main()
