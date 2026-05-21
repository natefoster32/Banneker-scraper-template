"""
Email delivery via Resend. Free tier: 3,000 emails/month, no credit card.

Setup:
1. Sign up at resend.com with your Banneker email
2. Verify your sending domain (or use the free `onboarding@resend.dev` for testing)
3. Get your API key (Settings -> API Keys)
4. Add to Streamlit Secrets AND GitHub Actions secrets:
   RESEND_API_KEY = "re_..."
   RESEND_FROM = "Banneker Brief <brief@yourdomain.com>"  # or onboarding@resend.dev
"""

import os
from typing import Optional

import requests


def get_secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets if available, else env var (for GH Actions)."""
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key, default)


def send_email(to: str, subject: str, html: str, reply_to: Optional[str] = None) -> tuple[bool, str]:
    api_key = get_secret("RESEND_API_KEY")
    from_addr = get_secret("RESEND_FROM", "onboarding@resend.dev")
    if not api_key:
        return False, "RESEND_API_KEY is not set"

    payload = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if r.status_code in (200, 202):
            return True, r.json().get("id", "")
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)
