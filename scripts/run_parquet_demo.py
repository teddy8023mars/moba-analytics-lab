"""Run a local synthetic Parquet snapshot; every run requires a fresh directory."""
import argparse
from collections import Counter
import json
from pathlib import Path
import duckdb
from moba_lab.fixtures import generate_fixture
from moba_lab.parquet_snapshot import export_user_days
from moba_lab.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        metrics = run_pipeline(generate_fixture(7), '2026-01-14')
        if len(metrics['user_day']) != 101 or len(metrics['dau']) != 14:
            raise ValueError('synthetic seed7 expected totals mismatch')
        counts = Counter(row['activity_date'] for row in metrics['user_day'])
        expected_dau = [{'activity_date': day, 'dau': counts[day]} for day in sorted(counts)]
        if expected_dau != metrics['dau']:
            raise ValueError('canonical DAU disagrees with user-day source')
        result = export_user_days(metrics['user_day'], args.output, '2026-01-08')
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, duckdb.Error) as exc:
        parser.exit(2, f'Parquet demo failed: {exc}\n')


if __name__ == '__main__':
    main()
