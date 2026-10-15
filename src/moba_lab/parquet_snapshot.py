"""Optional local user-day Parquet exercise, not a cloud or lakehouse writer."""
from collections import Counter
from datetime import date
import json
from pathlib import Path
import duckdb


def _day(value):
    if not isinstance(value, str):
        raise ValueError('expected canonical YYYY-MM-DD date')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('expected canonical YYYY-MM-DD date') from exc
    if parsed.isoformat() != value:
        raise ValueError('expected canonical YYYY-MM-DD date')
    return parsed


def export_user_days(rows, output, filter_date):
    """Export a nonempty unique user-day fact to a fresh owned local directory.

    Refuse existing outputs; partial data may remain after failure, without a
    completed summary. No append, directory transaction, fsync or race guarantee.
    """
    filtered_day = _day(filter_date)
    if not isinstance(rows, list) or not rows:
        raise ValueError('expected a nonempty list of user-day facts')
    facts = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'activity_date', 'user_id'}:
            raise ValueError('expected exactly activity_date and user_id')
        day = _day(row['activity_date'])
        user = row['user_id']
        if not isinstance(user, str) or not user.strip():
            raise ValueError('user_id must be a nonblank string')
        fact = (day, user)
        if fact in seen:
            raise ValueError('duplicate user-day fact')
        seen.add(fact)
        facts.append(fact)
    facts.sort()
    expected_counts = Counter(day for day, _ in facts)
    expected_dau = [{'activity_date': day.isoformat(), 'dau': expected_counts[day]}
                    for day in sorted(expected_counts)]
    folder = Path(output).absolute()  # Do not resolve a dangling output symlink.
    folder.mkdir(parents=True, exist_ok=False)
    dataset = folder / 'user_day'
    with duckdb.connect(':memory:') as con:
        con.execute('SET threads=1')
        con.execute('CREATE TABLE user_day(activity_date DATE NOT NULL, user_id VARCHAR NOT NULL)')
        con.executemany('INSERT INTO user_day VALUES (?,?)', facts)
        con.execute('COPY user_day TO ? (FORMAT PARQUET, PARTITION_BY(activity_date), COMPRESSION ZSTD)', [str(dataset)])
        files = sorted(dataset.rglob('*.parquet'))
        paths = [str(path) for path in files]
        actual = con.execute('SELECT activity_date,user_id FROM read_parquet(?,hive_partitioning=true) ORDER BY 1,2', [paths]).fetchall()
        if actual != facts:
            raise ValueError('Parquet full user-day roundtrip mismatch')
        dau_rows = con.execute('SELECT activity_date,count(*) FROM read_parquet(?,hive_partitioning=true) GROUP BY 1 ORDER BY 1', [paths]).fetchall()
        dau = [{'activity_date': day.isoformat(), 'dau': count} for day,count in dau_rows]
        if dau != expected_dau:
            raise ValueError('Parquet DAU mismatch')
        query = 'SELECT user_id FROM read_parquet(?,hive_partitioning=true) WHERE activity_date=?::DATE'
        filtered = [row[0] for row in con.execute(query + ' ORDER BY 1', [paths, filtered_day]).fetchall()]
        expected_filtered = [user for day,user in facts if day == filtered_day]
        if filtered != expected_filtered:
            raise ValueError('Parquet date-filter mismatch')
        plan = con.execute('EXPLAIN ' + query, [paths, filtered_day]).fetchone()[1]
        result = {'scope': 'local user-day Parquet snapshot experiment', 'duckdb_version': duckdb.__version__,
                  'rows': len(actual), 'partition_count': len({path.parent for path in files}),
                  'files': [str(path.relative_to(folder)) for path in files], 'dau': dau,
                  'full_rows_equal': True, 'filter_date': filter_date,
                  'filtered_user_ids': filtered, 'explain': plan.replace(str(folder), '<snapshot>')}
    # Publish only a complete summary, after checks and connection close.
    temporary = folder / '.summary.json.tmp'
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(folder / 'summary.json')
    return result
