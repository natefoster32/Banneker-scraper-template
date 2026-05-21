"""
Cron worker — runs daily via GitHub Actions. For each tracker config in the
Gist with an active email subscription whose frequency matches "today",
scrapes, builds the email HTML, sends via Resend, and updates last_sent.

Env vars required (set as GitHub Actions secrets):
  GITHUB_GIST_ID     - the Gist that holds trackers.json
  GITHUB_PAT         - token with `gist` scope
  RESEND_API_KEY     - from resend.com
  RESEND_FROM        - "Banneker Brief <brief@yourdomain.com>" or onboarding@resend.dev
  APP_BASE_URL       - https://your-streamlit-app.streamlit.app  (for unsubscribe links)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent dir to path so we can import core/email_sender
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from core import build_email_html, scrape_for_config


def get_env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        raise RuntimeError(f"{key} is not set")
    return val


def load_configs_from_gist() -> dict:
    gist_id = get_env("GITHUB_GIST_ID")
    pat = get_env("GITHUB_PAT")
    r = requests.get(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"token {pat}", "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    r.raise_for_status()
    content = r.json()["files"].get("trackers.json", {}).get("content", "{}")
    return json.loads(content) or {}


def save_configs_to_gist(configs: dict) -> None:
    gist_id = get_env("GITHUB_GIST_ID")
    pat = get_env("GITHUB_PAT")
    body = {"files": {"trackers.json": {"content": json.dumps(configs, indent=2, sort_keys=True)}}}
    r = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"token {pat}", "Accept": "application/vnd.github+json"},
        json=body,
        timeout=15,
    )
    r.raise_for_status()


def should_send_today(frequency: str, last_sent_iso: str | None, today_utc: datetime) -> bool:
    if frequency == "daily":
        return True
    weekday = today_utc.weekday()  # Mon=0, Sun=6
    if frequency == "weekly_monday" and weekday == 0:
        return True
    if frequency == "weekly_friday" and weekday == 4:
        return True
    return False


def send_via_resend(to: str, subject: str, html: str) -> tuple[bool, str]:
    api_key = get_env("RESEND_API_KEY")
    from_addr = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
    payload = {"from": from_addr, "to": [to], "subject": subject, "html": html}
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if r.status_code in (200, 202):
            return True, r.json().get("id", "")
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def main():
    today_utc = datetime.now(timezone.utc)
    print(f"Cron run at {today_utc.isoformat()} (UTC, weekday={today_utc.weekday()})")

    configs = load_configs_from_gist()
    if not configs:
        print("No configs in Gist. Exiting.")
        return

    app_base = os.environ.get("APP_BASE_URL", "")
    updated = False
    sent_count = 0

    for tracker_id, config in configs.items():
        sub = config.get("email_subscription")
        if not sub or not sub.get("email"):
            continue

        if not should_send_today(sub.get("frequency", "weekly_monday"), sub.get("last_sent"), today_utc):
            continue

        print(f"  -> {tracker_id} ({config.get('name', '?')}) -> {sub['email']}")
        try:
            grouped, total = scrape_for_config(config)
        except Exception as e:
            print(f"     ! scrape failed: {e}")
            continue

        theme_order = [t["name"] for t in config.get("themes", []) if t.get("name")]
        unsubscribe_url = (
            f"{app_base}/?id={tracker_id}&action=unsubscribe" if app_base else None
        )
        html = build_email_html(
            grouped=grouped,
            theme_order=theme_order,
            total=total,
            config=config,
            unsubscribe_url=unsubscribe_url,
        )

        title = config.get("title") or f"{config.get('name', 'News')} Brief"
        subject = f"{title} — {today_utc.strftime('%b %d, %Y')}"

        ok, info = send_via_resend(sub["email"], subject, html)
        if ok:
            print(f"     ✓ sent (id={info})")
            sub["last_sent"] = today_utc.isoformat()
            config["email_subscription"] = sub
            configs[tracker_id] = config
            updated = True
            sent_count += 1
        else:
            print(f"     ! send failed: {info}")

    if updated:
        save_configs_to_gist(configs)
        print(f"Saved updated configs. Sent {sent_count} emails total.")
    else:
        print(f"Nothing to send today. Sent {sent_count} emails.")


if __name__ == "__main__":
    main()
