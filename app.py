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
import decoy_data
from config import DISCORD_WEBHOOK_URL

app = Flask(__name__, static_folder="static", static_url_path="")

db.init_db()

TIME_FMT = "%Y-%m-%d %H:%M:%S UTC"


def now_iso():
    return datetime.now(timezone.utc).strftime(TIME_FMT)


def action_plan(token_name, ip, geo, taken=""):
    """Plain-English guidance for a non-technical owner. Simple + reliable."""
    what = f"downloaded '{taken}' from" if taken else "accessed"
    return (
        f"An intruder {what} your decoy '{token_name}' from {ip} ({geo}). "
        f"Real staff never touch decoys, so this almost certainly means someone "
        f"unauthorized is inside your systems.\n"
        f"1. Reset all admin and email passwords now.\n"
        f"2. Disconnect the affected computer from the internet.\n"
        f"3. Contact your IT support and preserve the logs."
    )


def lookup_geo(ip):
    """Free, no-key IP geolocation. Returns a human string that also flags
    VPN / proxy / datacenter IPs (because attackers often hide behind them)."""
    if not ip or ip.startswith(("127.", "192.168.", "10.")):
        return "Local network"
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}"
            "?fields=status,country,city,isp,proxy,hosting",
            timeout=4,
        )
        d = r.json()
        if d.get("status") == "success":
            loc = f"{d.get('city', '?')}, {d.get('country', '?')}"
            isp = d.get("isp", "")
            flag = " · ⚠ likely VPN/proxy" if (d.get("proxy") or d.get("hosting")) else ""
            return f"{loc} · {isp}{flag}"
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
    data = request.get_json(silent=True) or {}
    allowed_kinds = {"file", "login", "link", "portal"}
    token_id = uuid.uuid4().hex[:12]
    name=(data.get("name") or "Untitled decoy").strip()
    kind=(data.get("kind") or "link").strip().lower()
    if kind not in allowed_kinds:
            return jsonify({"error": "invalid kind"}), 400
    db.create_token(
        token_id=token_id,
        name=name,
        kind=kind,
        
        created_at=now_iso(),
        note=data.get("note", ""),
        company=data.get("company", ""),
        location=data.get("location", ""),
        email=data.get("email", ""),
    )
    # The bait URL the team plants. Anyone hitting it triggers the alarm.
    base = request.host_url.rstrip("/")
    path = "/portal/" if data.get("kind") == "portal" else "/t/"
    trigger_url = base + path + token_id
    return jsonify({"id": token_id, "trigger_url": trigger_url})


@app.get("/api/cities")
def api_cities():
    """City list for the location dropdown (drives realistic phone numbers)."""
    return jsonify(decoy_data.CITY_LIST)


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
# THE TRAP: anyone who touches a decoy hits these endpoints.
# ---------------------------------------------------------------------------

def log_breach(token, taken=""):
    """Record the breach: capture WHO/WHERE/WHEN, write the action plan, alert."""
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip = ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "unknown")
    geo = lookup_geo(ip)
    when = now_iso()
    event_id = db.create_event(token["id"], when, ip, geo, ua)
    db.set_event_explanation(event_id, action_plan(token["name"], ip, geo, taken))
    send_discord_alert(token["name"] + (f" / {taken}" if taken else ""), ip, geo, when)


@app.route("/t/<token_id>")
def trigger(token_id):
    token = db.get_token(token_id)
    if not token:
        return "Not found", 404

    # An attacker may be downloading one specific file out of the portal.
    taken = request.args.get("file", "")
    log_breach(token, taken)

    # If a specific file was requested, hand them that real file.
    if taken:
        data, mimetype = decoy_data.build_download(
            taken, token.get("company", ""), token.get("location", "")
        )
        return Response(data, mimetype=mimetype,
                        headers={"Content-Disposition": f'attachment; filename="{taken}"'})

    # Otherwise behave by bait type.
    if token["kind"] == "login":
        return redirect("/fake_login.html?t=" + token_id)
    if token["kind"] == "file":
        filename = token["name"] or "document.csv"
        data, mimetype = decoy_data.build_download(
            filename, token.get("company", ""), token.get("location", "")
        )
        return Response(data, mimetype=mimetype,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    return ("", 200)  # tracking link / pixel: silent


@app.route("/portal/<token_id>")
def portal(token_id):
    """A fake internal company document portal. THIS is what an attacker lands
    on -- a believable file server listing several juicy files to download.
    Loading this page is itself logged as a breach."""
    token = db.get_token(token_id)
    if not token:
        return "Not found", 404

    log_breach(token, "")  # they reached the internal portal
    company = token.get("company") or "Internal"
    rows = "".join(
        f"""<tr>
              <td class="fn">📄 {m['label']}<span>{m['file']}</span></td>
              <td>{m['modified']}</td>
              <td>{m['size']}</td>
              <td><a class="dl" href="/t/{token_id}?file={m['file']}">Download</a></td>
            </tr>"""
        for m in decoy_data.PORTAL_MANIFEST
    )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{company} — Document Portal</title>
<style>
  body{{font-family:Segoe UI,system-ui,sans-serif;background:#f3f4f6;margin:0;color:#1f2937;}}
  .bar{{background:#1e3a8a;color:#fff;padding:16px 28px;font-size:18px;font-weight:600;}}
  .bar small{{display:block;font-size:12px;font-weight:400;opacity:.8;margin-top:2px;}}
  .wrap{{max-width:880px;margin:30px auto;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;}}
  .head{{padding:16px 22px;border-bottom:1px solid #e5e7eb;font-weight:600;}}
  table{{width:100%;border-collapse:collapse;}}
  th,td{{text-align:left;padding:14px 22px;border-bottom:1px solid #f0f0f0;font-size:14px;}}
  th{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#6b7280;}}
  .fn span{{display:block;color:#9ca3af;font-size:12px;}}
  .dl{{background:#1e3a8a;color:#fff;padding:7px 16px;border-radius:6px;text-decoration:none;font-size:13px;}}
  .dl:hover{{background:#1e40af;}}
</style></head><body>
  <div class="bar">{company} — Internal Document Portal
    <small>Confidential · Authorized personnel only</small></div>
  <div class="wrap">
    <div class="head">Shared Documents ({len(decoy_data.PORTAL_MANIFEST)})</div>
    <table>
      <tr><th>Name</th><th>Modified</th><th>Size</th><th></th></tr>
      {rows}
    </table>
  </div>
</body></html>"""


if __name__ == "__main__":
    print("Deception Network running -> http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
