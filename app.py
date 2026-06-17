"""Small Business Deception Network -- main server.

ONE command to run everything:
    python app.py
Then open http://localhost:5000 in your browser.

The whole idea:
  1. You create a "honeytoken" (decoy bait) on the dashboard.
  2. You plant it somewhere (a fake file, a link in an email, a fake login page).
  3. The moment anyone touches it, this server logs WHO and WHEN, shows a
     plain-English action plan, buzzes a phone via Discord, and goes RED.

That's how a small business finds out it's been breached in SECONDS
instead of the industry-average ~200 days.
"""

import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify, redirect, send_from_directory, Response

import db
from config import DISCORD_WEBHOOK_URL

app = Flask(__name__, static_folder="static", static_url_path="")

db.init_db()

TIME_FMT = "%Y-%m-%d %H:%M:%S UTC"


def now_iso():
    return datetime.now(timezone.utc).strftime(TIME_FMT)


def action_plan(token_name, ip, geo):
    """Plain-English guidance for a non-technical owner. Simple + reliable."""
    return (
        f"A decoy ('{token_name}') was accessed from {ip} ({geo}). "
        f"Real staff never touch decoys, so this likely means an intruder is inside.\n"
        f"1. Reset all admin and email passwords now.\n"
        f"2. Disconnect the affected computer from the internet.\n"
        f"3. Contact your IT support and preserve the logs."
    )


DECOY_ROWS = [
    ["Employee", "Role", "Annual Salary", "Email", "Login"],
    ["Sarah Chen", "Office Manager", 68000, "s.chen@company.local", "schen"],
    ["Mike Torres", "Lead Dentist", 142000, "m.torres@company.local", "mtorres"],
    ["Priya Patel", "Hygienist", 61000, "p.patel@company.local", "ppatel"],
    ["James Okoro", "Receptionist", 44000, "j.okoro@company.local", "jokoro"],
]


def make_decoy_file(name):
    """Return (bytes, mimetype) for a believable decoy download.

    - .xlsx -> a REAL Excel file (opens cleanly) if openpyxl is installed
    - everything else (or no openpyxl) -> plain CSV/text that opens cleanly too
    Either way it's harmless bait -- no real sensitive data.
    """
    lower = (name or "").lower()

    if lower.endswith(".xlsx"):
        try:
            import io
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = "Payroll"
            for row in DECOY_ROWS:
                ws.append(row)
            ws.append([])
            ws.append(["NOTE: security decoy - accessed by an unauthorized party."])
            buf = io.BytesIO()
            wb.save(buf)
            return (
                buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            pass  # openpyxl missing -> fall through to plain text below

    # Plain CSV/text fallback (opens fine in Excel/Notepad as .csv or .txt)
    lines = ["CONFIDENTIAL - INTERNAL USE ONLY", f"File: {name}", ""]
    lines += [",".join(str(c) for c in row) for row in DECOY_ROWS]
    lines += ["", "NOTE: security decoy - accessed by an unauthorized party."]
    return ("\r\n".join(lines).encode("utf-8"), "text/csv")


def lookup_geo(ip):
    """Free, no-key IP geolocation. Best-effort -- returns 'Unknown' on failure."""
    if not ip or ip.startswith(("127.", "192.168.", "10.")):
        return "Local network"
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=4)
        d = r.json()
        if d.get("status") == "success":
            return f"{d.get('city', '?')}, {d.get('country', '?')}"
    except Exception:
        pass
    return "Unknown"


def seconds_between(start_iso, end_iso):
    """How long the bait sat planted before it was triggered (the 'dwell time')."""
    try:
        a = datetime.strptime(start_iso, TIME_FMT)
        b = datetime.strptime(end_iso, TIME_FMT)
        return max(0, int((b - a).total_seconds()))
    except Exception:
        return 0


def human_duration(seconds):
    """Turn seconds into '3 seconds', '5 min', '2 hr', '3 days'."""
    if seconds < 60:
        return f"{seconds} sec"
    if seconds < 3600:
        return f"{seconds // 60} min"
    if seconds < 86400:
        return f"{seconds // 3600} hr"
    return f"{seconds // 86400} days"


def send_discord_alert(token_name, ip, geo, when):
    """Buzz a phone via Discord. Silently does nothing if no webhook is set."""
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={
                "content": (
                    f"🚨 **BREACH DETECTED** 🚨\n"
                    f"Decoy **{token_name}** was just touched.\n"
                    f"From `{ip}` ({geo}) at {when}.\n"
                    f"A real intruder is likely inside. Act now."
                )
            },
            timeout=4,
        )
    except Exception:
        pass  # never let an alert failure break the trap


# ---------------------------------------------------------------------------
# Dashboard (served as a static file)
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------------------
# API: create + list tokens, list events, stats  (the dashboard polls these)
# ---------------------------------------------------------------------------

@app.post("/api/tokens")
def api_create_token():
    data = request.get_json(force=True)
    token_id = uuid.uuid4().hex[:12]
    db.create_token(
        token_id=token_id,
        name=data.get("name", "Untitled decoy"),
        kind=data.get("kind", "link"),
        created_at=now_iso(),
        note=data.get("note", ""),
    )
    # The bait URL the team plants. Anyone hitting it triggers the alarm.
    trigger_url = request.host_url.rstrip("/") + "/t/" + token_id
    return jsonify({"id": token_id, "trigger_url": trigger_url})


@app.get("/api/tokens")
def api_list_tokens():
    return jsonify(db.list_tokens())


@app.get("/api/events")
def api_list_events():
    events = db.list_events()
    # Add the dwell-time numbers each alert card shows.
    for e in events:
        secs = seconds_between(e.get("token_created_at", ""), e.get("triggered_at", ""))
        e["dwell_seconds"] = secs
        e["dwell_human"] = human_duration(secs)
    return jsonify(events)


@app.get("/api/stats")
def api_stats():
    """Numbers for the headline bar at the top of the dashboard."""
    tokens = db.list_tokens()
    events = db.list_events()
    return jsonify({
        "decoys_planted": len(tokens),
        "breaches_detected": len(events),
        "industry_avg_days": 204,  # widely-cited average detection time
    })


# ---------------------------------------------------------------------------
# THE TRAP: anyone who touches a decoy hits this endpoint.
# ---------------------------------------------------------------------------

@app.route("/t/<token_id>")
def trigger(token_id):
    token = db.get_token(token_id)
    if not token:
        return "Not found", 404

    # Get the real client IP even behind a proxy/tunnel.
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip = ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "unknown")
    geo = lookup_geo(ip)
    when = now_iso()

    event_id = db.create_event(token_id, when, ip, geo, ua)
    db.set_event_explanation(event_id, action_plan(token["name"], ip, geo))
    send_discord_alert(token["name"], ip, geo, when)

    # What the attacker sees depends on the bait type -- looks innocent to them.
    if token["kind"] == "login":
        return redirect("/fake_login.html?t=" + token_id)
    if token["kind"] == "file":
        # Serve a real file download so the attacker actually gets "something".
        filename = token["name"] or "document.txt"
        data, mimetype = make_decoy_file(filename)
        return Response(
            data,
            mimetype=mimetype,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return ("", 200)  # tracking link / pixel: silent


if __name__ == "__main__":
    print("Deception Network running -> http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
