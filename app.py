"""Small Business Deception Network -- main server.

ONE command to run everything:
    python app.py
Then open http://localhost:5000 in your browser.

The whole idea:
  1. You create a "honeytoken" (decoy bait) on the dashboard.
  2. You plant it somewhere (a fake file, a link in an email, a fake login page).
  3. The moment anyone touches it, this server logs WHO and WHEN,
     a local Ollama model explains what it means, and the dashboard goes RED.

That's how a small business finds out it's been breached in SECONDS
instead of the industry-average ~200 days.
"""

import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify, redirect, send_from_directory

import db

app = Flask(__name__, static_folder="static", static_url_path="")


def action_plan(token_name, ip, geo):
    """Plain-English guidance for a non-technical owner. Simple + reliable."""
    return (
        f"A decoy ('{token_name}') was accessed from {ip} ({geo}). "
        f"Real staff never touch decoys, so this likely means an intruder is inside.\n"
        f"1. Reset all admin and email passwords now.\n"
        f"2. Disconnect the affected computer from the internet.\n"
        f"3. Contact your IT support and preserve the logs."
    )

db.init_db()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


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


# ---------------------------------------------------------------------------
# Dashboard (served as a static file)
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------------------
# API: create + list tokens, list events  (the dashboard polls these)
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
    return jsonify(db.list_events())


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

    event_id = db.create_event(token_id, now_iso(), ip, geo, ua)
    db.set_event_explanation(event_id, action_plan(token["name"], ip, geo))

    # What the attacker sees depends on the bait type -- looks innocent to them.
    if token["kind"] == "login":
        return redirect("/static/fake_login.html?t=" + token_id)
    if token["kind"] == "file":
        return ("Downloading...", 200)  # swap for a real decoy file if you like
    return ("", 200)  # tracking link / pixel: silent


if __name__ == "__main__":
    print("Deception Network running -> http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
