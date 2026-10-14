import argparse
import csv
from html import escape
import json
from pathlib import Path
from .fixtures import generate_fixture
from .pipeline import METRICS, run_pipeline


def write_reports(metrics, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    sections = []
    for name, fields in METRICS.items():
        rows = metrics[name]
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        head = "".join(f"<th>{escape(f)}</th>" for f in fields)
        body = "".join("<tr>" + "".join(f"<td>{escape(str(row[f]))}</td>" for f in fields) + "</tr>" for row in rows)
        sections.append(f"<section><h2>{escape(name)}</h2><p><a href='{name}.csv'>CSV</a> · {len(rows)} rows</p><div><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>")
    (output / "index.html").write_text("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Synthetic MOBA analytics</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#17253c;background:#f4f7fb}section{background:white;padding:20px;margin:20px 0;border-radius:12px}div{overflow:auto}table{border-collapse:collapse;font-size:14px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}a{color:#245cc1}</style><h1>Synthetic MOBA analytics</h1><p>AI-assisted personal educational lab. UTC dates; exact-day D1/D7 retention includes observable cohorts only. DAU means login activity. All values are fictional.</p>" + "".join(sections) + "</html>", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Synthetic MOBA analytics lab")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=7)
    run = sub.add_parser("run")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--as-of", required=True, help="last fully observed UTC day, YYYY-MM-DD")
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            data = generate_fixture(args.seed)
            args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({k: len(v) for k, v in data.items()}, sort_keys=True))
        else:
            metrics = run_pipeline(json.loads(args.input.read_text(encoding="utf-8")), args.as_of)
            write_reports(metrics, args.output)
            (args.output / "run.json").write_text(json.dumps({"as_of_utc": args.as_of, "synthetic": True, "rows": {k: len(v) for k, v in metrics.items()}}, indent=2) + "\n")
            print(json.dumps({k: len(v) for k, v in metrics.items()}, sort_keys=True))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
