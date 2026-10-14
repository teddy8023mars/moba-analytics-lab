"""Validated synthetic events -> UTC SQL marts, entirely in memory."""
from datetime import date, datetime, timezone
from importlib.resources import files
import duckdb
from time import perf_counter

SCHEMAS = {
    "users": [("user_id", "VARCHAR"), ("signup_at", "TIMESTAMPTZ")],
    "logins": [("event_id", "VARCHAR"), ("user_id", "VARCHAR"), ("occurred_at", "TIMESTAMPTZ")],
    "matches": [("match_id", "VARCHAR"), ("started_at", "TIMESTAMPTZ"), ("duration_seconds", "INTEGER")],
    "participants": [("match_id", "VARCHAR"), ("user_id", "VARCHAR"), ("hero", "VARCHAR"), ("won", "BOOLEAN"), ("kills", "INTEGER"), ("deaths", "INTEGER"), ("assists", "INTEGER")],
    "payments": [("payment_id", "VARCHAR"), ("user_id", "VARCHAR"), ("occurred_at", "TIMESTAMPTZ"), ("amount_cents", "BIGINT")],
}
KEYS = {"users": ("user_id",), "logins": ("event_id",), "matches": ("match_id",), "participants": ("match_id", "user_id"), "payments": ("payment_id",)}
METRICS = {
    "user_day": ("activity_date", "user_id"), "dau": ("activity_date", "dau"),
    "retention": ("cohort_date", "day_offset", "cohort_users", "retained_users", "retention_rate"),
    "hero_stats": ("hero", "player_matches", "distinct_matches", "wins", "win_rate", "kills", "deaths", "assists"),
    "player_stats": ("user_id", "player_matches", "wins", "kills", "deaths", "assists"),
    "monetization": ("payment_date", "transactions", "paying_users", "revenue_cents", "arppu_cents"),
}


def _validated(data):
    if not isinstance(data, dict) or set(data) != set(SCHEMAS):
        raise ValueError("input must contain exactly users, logins, matches, participants, payments")
    clean = {}
    for table, schema in SCHEMAS.items():
        if not isinstance(data[table], list):
            raise ValueError(f"{table}: expected a list")
        unique = {}
        for record in data[table]:
            if not isinstance(record, dict) or set(record) != {f for f, _ in schema}:
                raise ValueError(f"{table}: unexpected or missing fields")
            values = []
            for field, kind in schema:
                value = record[field]
                if kind == "TIMESTAMPTZ":
                    try:
                        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        if value.tzinfo is None or value.utcoffset() is None:
                            raise ValueError("timezone required")
                        value = value.astimezone(timezone.utc)
                    except (ValueError, TypeError, AttributeError) as exc:
                        raise ValueError(f"{table}.{field}: timezone-aware ISO timestamp required") from exc
                elif kind == "VARCHAR":
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"{table}.{field}: nonempty string required")
                elif kind == "BOOLEAN":
                    if type(value) is not bool:
                        raise ValueError(f"{table}.{field}: boolean required")
                else:
                    limit = 2**63 - 1 if kind == "BIGINT" else 2**31 - 1
                    if type(value) is not int or not 0 <= value <= limit:
                        raise ValueError(f"{table}.{field}: nonnegative bounded integer required")
                    if field == "duration_seconds" and value == 0:
                        raise ValueError("match duration must be positive")
                values.append(value)
            normalized = dict(zip((f for f, _ in schema), values))
            key = tuple(normalized[k] for k in KEYS[table])
            if key in unique and unique[key] != normalized:
                raise ValueError(f"{table}: conflicting duplicate identity {key}")
            unique[key] = normalized
        clean[table] = list(unique.values())
    users = {r["user_id"]: r["signup_at"] for r in clean["users"]}
    matches = {r["match_id"]: r["started_at"] for r in clean["matches"]}
    for table in ("logins", "payments", "participants"):
        for row in clean[table]:
            if row["user_id"] not in users:
                raise ValueError(f"{table}: unknown user")
            if table == "participants":
                if row["match_id"] not in matches:
                    raise ValueError("participants: unknown match")
                at = matches[row["match_id"]]
            else:
                at = row["occurred_at"]
            if at < users[row["user_id"]]:
                raise ValueError(f"{table}: event before signup")
    return clean


def run_pipeline(data: dict, as_of: str, *, timings: dict | None = None) -> dict[str, list[dict]]:
    """as_of declares the last fully observed UTC day (inclusive).

    Optional timings is replaced only after a successful full rebuild, including
    connection close. Values are wall-clock seconds, not isolated CPU/SQL time.
    """
    if timings is not None and not isinstance(timings, dict):
        raise ValueError("timings must be a dict or None")
    stages = {}
    started = previous = perf_counter() if timings is not None else 0

    def mark(stage):
        nonlocal previous
        if timings is not None:
            now = perf_counter()
            stages[stage] = now - previous
            previous = now
    try:
        cutoff = date.fromisoformat(as_of)
        if cutoff.isoformat() != as_of:
            raise ValueError("canonical date required")
    except (ValueError, TypeError) as exc:
        raise ValueError("as-of must be YYYY-MM-DD") from exc
    clean = _validated(data)
    mark("validation")
    with duckdb.connect(":memory:") as con:
        con.execute("SET TimeZone='UTC'")
        con.execute("CREATE TABLE observation(as_of DATE)")
        con.execute("INSERT INTO observation VALUES (?)", [cutoff])
        mark("connection_setup")
        # Keep raw copies; staging SQL deduplicates exact repeats. Validation above
        # rejects conflicts rather than choosing an arbitrary winning version.
        for table, schema in SCHEMAS.items():
            con.execute(f"CREATE TABLE raw_{table} ({', '.join(f'{f} {t}' for f, t in schema)})")
            rows = clean[table]
            if rows:
                # The input may contain exact duplicates; expand normalized copies
                # to preserve raw cardinality without re-parsing timestamps.
                by_key = {tuple(r[k] for k in KEYS[table]): r for r in rows}
                raw = [by_key[tuple(r[k] for k in KEYS[table])] for r in data[table]]
                con.executemany(f"INSERT INTO raw_{table} VALUES ({','.join('?' for _ in schema)})",
                                [tuple(r[f] for f, _ in schema) for r in raw])
        mark("raw_load")
        con.execute(files("moba_lab").joinpath("models.sql").read_text())
        mark("sql_models")
        result = {}
        for name in METRICS:
            cursor = con.execute(f"SELECT * FROM {name} ORDER BY 1, 2")
            columns = [c[0] for c in cursor.description]
            result[name] = [dict(zip(columns, (v.isoformat() if isinstance(v, date) else v for v in row))) for row in cursor.fetchall()]
        mark("result_fetch")
    mark("connection_close")
    if timings is not None:
        stages["total"] = previous - started
        timings.clear()
        timings.update(stages)
    return result
