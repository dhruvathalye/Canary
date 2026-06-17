# 🛡️ Small Business Deception Network

Small businesses get breached and **don't notice for ~200 days**. We make it
**seconds**. You plant fake bait ("honeytokens") around the business — a decoy
`payroll.xlsx`, a fake admin login, a tracking link. Real staff never touch
them, so the moment one is triggered, it's almost certainly an intruder. We log
**who/when/where**, show a plain-English action plan, and the dashboard goes **RED**.

## Run it (1 command)

```bash
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>.

## 30-second demo script

1. On the dashboard, create a decoy named `Q3_payroll.xlsx`.
2. Copy its trigger URL.
3. Paste it in a browser (or `curl` it) — this plays the "attacker."
4. Watch the dashboard flip to a red **BREACH DETECTED** card within 2 seconds,
   then the AI action-plan fills in.

> Pitch line: *"The breach still happened — but they knew in seconds instead of
> 200 days. That's the difference between an incident and a catastrophe."*

## How the code is split (4 people)

| File | Owner | What it does |
|---|---|---|
| `app.py` | **A** | Flask server: create/list tokens, the `/t/<id>` trap, geo lookup |
| `db.py` | **A** | SQLite storage (tokens + events). One file, no setup. |
| `static/index.html` | **B** | The live dashboard (plant bait + red alert feed) |
| `static/fake_login.html` + decoy content | **C** | The bait types attackers see |
| deploy + demo laptop + slides | **D** | Deploy, rehearse, pitch |

## Agree on this first (the API contract)

- `POST /api/tokens` `{name, kind}` → `{id, trigger_url}`
- `GET /api/tokens` → list of bait
- `GET /api/events` → list of breach alerts (newest first)
- `GET /t/<id>` → the trap (logs the hit, fires the alert)

As long as these stay the same, everyone can work in parallel.
