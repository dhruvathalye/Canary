"""Settings you can change WITHOUT touching the main code.

DISCORD_WEBHOOK_URL:
    Paste a Discord webhook URL here to make a phone buzz the instant a decoy
    is triggered. This is the big "wow" moment in the demo.

    How to get one (2 minutes):
      1. In Discord, make a server (or use one you have).
      2. Server Settings -> Integrations -> Webhooks -> New Webhook.
      3. Click "Copy Webhook URL" and paste it between the quotes below.

    If you leave it blank (""), everything still works -- you just won't get
    the Discord buzz. So this is safe to leave empty while developing.
"""

DISCORD_WEBHOOK_URL = ""
