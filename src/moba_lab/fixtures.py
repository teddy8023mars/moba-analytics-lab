"""Tiny fictional MOBA events. No real players, heroes or business metrics."""
from datetime import datetime, timedelta, timezone
import random


def generate_fixture(seed: int = 7) -> dict:
    rng = random.Random(seed)
    data = {k: [] for k in ("users", "logins", "matches", "participants", "payments")}
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    stamp = lambda d: d.isoformat().replace("+00:00", "Z")
    for n in range(12):
        user = f"u{n:02d}"; signup = start + timedelta(days=n // 3)
        data["users"].append({"user_id": user, "signup_at": stamp(signup)})
        for day in range((signup - start).days, 14):
            if rng.random() < 0.6:
                data["logins"].append({"event_id": f"l{n}-{day}", "user_id": user,
                                       "occurred_at": stamp(start + timedelta(days=day, hours=9))})
        if n % 3 == 0:
            data["payments"].append({"payment_id": f"p{n}", "user_id": user,
                "occurred_at": stamp(signup + timedelta(days=1, hours=14)), "amount_cents": rng.choice([199, 499, 999])})
    for day in range(4, 14):
        match = f"m{day}"; players = rng.sample(data["users"], 4)
        data["matches"].append({"match_id": match, "started_at": stamp(start + timedelta(days=day, hours=12)), "duration_seconds": rng.randint(600, 1800)})
        for i, user in enumerate(players):
            data["participants"].append({"match_id": match, "user_id": user["user_id"],
                "hero": rng.choice(["Ember", "Tide", "Stone"]), "won": i < 2,
                "kills": rng.randint(0, 12), "deaths": rng.randint(0, 10), "assists": rng.randint(0, 20)})
    data["logins"].append(dict(data["logins"][0]))
    data["payments"].append(dict(data["payments"][0]))
    return data
