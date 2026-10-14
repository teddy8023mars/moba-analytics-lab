# Metrics and input contract

All dates below are **UTC calendar dates**. `--as-of YYYY-MM-DD` is an inclusive, caller-declared complete observation day. Timezone-aware input timestamps normalize to UTC. Future events are ignored in metrics; future users are omitted from cohorts. Invalid input fails even if the invalid event would be outside the window.

| Export | Grain | Definition |
|---|---|---|
| `user_day` | One user / login date | At least one login on that UTC day. Does not infer activity from matches or payments. |
| `dau` | One observed login date | Number of distinct login users. Dates without logins are absent, not zero-filled. |
| `retention` | Signup date / offset (1 or 7) | Denominator: registered users on signup date, including users without a login. Numerator: users with a login on signup date + offset. Rate = numerator / denominator. Cohort-offset pairs beyond as-of are absent. |
| `hero_stats` | Hero | `player_matches`: participant appearances. `distinct_matches`: unique matches with that hero. `wins`: winning appearances. `win_rate`: wins / appearances. Kills, deaths, assists: totals. Multiple players selecting the same hero in a match count separately. |
| `player_stats` | Player | Participant appearances, winning appearances and kill/death/assist totals. Only users with an observed match appear. |
| `monetization` | Payment date | Deduplicated transactions, distinct paying users, gross fictional revenue in cents, ARPPU = revenue cents / distinct paying users. Payments are independent of login activity; no conversion-rate claim is made. |

Rates are fractions from 0 to 1, not percentages. No rounding is applied in CSV. ARPPU is a floating division of integer cent totals, not a rounded currency amount. Zero-cent transactions are allowed and their users count as paying users under this transaction-based definition.

Hand-checkable test fixture: a and b sign up January 1. a logs in January 2 and January 8; b's `2026-01-02T00:30:00+08:00` login falls on January 1 UTC. Therefore January 1 cohort D1 and D7 are both 1 / 2 at an observation end of January 8. c signs up January 8 and is absent from both retention rows. a makes 100-cent and 200-cent payments but plays one match: revenue is 300 cents, hero appearance count remains 1.

## JSON table contract

All five table names must exist and contain lists. Fields must match exactly; unknown or missing fields fail. Empty lists are supported. IDs and heroes must be nonempty strings; whitespace-only strings fail. IDs are case-sensitive. Integer counters must be nonnegative, booleans must be booleans, and match duration must be positive. Integer fields fit DuckDB's declared signed 32-bit integer range, or signed 64-bit range for payment cents.

| Table | Identity | Required fields |
|---|---|---|
| users | user_id | user_id, signup_at |
| logins | event_id | event_id, user_id, occurred_at |
| matches | match_id | match_id, started_at, duration_seconds |
| participants | match_id + user_id | match_id, user_id, hero, won, kills, deaths, assists |
| payments | payment_id | payment_id, user_id, occurred_at, amount_cents |

Timestamp fields require ISO 8601 with explicit timezone, such as `2026-01-01T12:00:00Z` or `2026-01-01T20:00:00+08:00`. Exact repeats after normalization deduplicate. Different payloads sharing an identity are errors. All login/payment/participant users must exist. Participants must reference a known match; their match start must not predate signup. Login and payment times must not predate signup.

CLI success exits 0. Invalid JSON, contract, observation date or file access exits 2 with a diagnostic. Unexpected database/runtime failures are not relabeled as quality failures. The lab does not infer data completeness from the presence or absence of events.
