"""
Persistence layer — stores all tracker configs in a single GitHub Gist as JSON.

Setup:
1. Create a Gist on github.com/gists (any visibility, public is fine).
   Add a file named `trackers.json` containing `{}`.
2. Copy the Gist ID (the long hex string in the URL).
3. Create a GitHub Personal Access Token with `gist` scope at
   github.com/settings/tokens.
4. Add both to Streamlit Secrets (App settings -> Secrets):

   GITHUB_GIST_ID = "your_gist_id_here"
   GITHUB_PAT = "your_token_here"

5. Add the same secrets to the GitHub Actions repo (Settings -> Secrets ->
   Actions) for the email cron job.
"""

import json
from typing import Any

import requests
import streamlit as st

FILENAME = "trackers.json"
API_BASE = "https://api.github.com/gists"


def _gist_id() -> str:
    val = st.secrets.get("GITHUB_GIST_ID", "")
    if not val:
        raise RuntimeError(
            "GITHUB_GIST_ID is not set in Streamlit Secrets. See storage.py for setup."
        )
    return val


def _pat() -> str:
    val = st.secrets.get("GITHUB_PAT", "")
    if not val:
        raise RuntimeError(
            "GITHUB_PAT is not set in Streamlit Secrets. See storage.py for setup."
        )
    return val


def _headers() -> dict:
    return {
        "Authorization": f"token {_pat()}",
        "Accept": "application/vnd.github+json",
    }


@st.cache_data(ttl=60, show_spinner=False)
def load_all_configs() -> dict[str, dict]:
    """Read all tracker configs from the Gist. Cached 60s to avoid hammering GitHub."""
    url = f"{API_BASE}/{_gist_id()}"
    r = requests.get(url, headers=_headers(), timeout=15)
    r.raise_for_status()
    files = r.json().get("files", {})
    raw = files.get(FILENAME, {}).get("content", "{}")
    try:
        return json.loads(raw) or {}
    except json.JSONDecodeError:
        return {}


def save_all_configs(configs: dict[str, dict]) -> None:
    """Overwrite the Gist file with the full configs dict."""
    url = f"{API_BASE}/{_gist_id()}"
    body = {"files": {FILENAME: {"content": json.dumps(configs, indent=2, sort_keys=True)}}}
    r = requests.patch(url, headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    load_all_configs.clear()


def get_config(tracker_id: str) -> dict | None:
    return load_all_configs().get(tracker_id)


def upsert_config(tracker_id: str, config: dict) -> None:
    configs = load_all_configs().copy()
    configs[tracker_id] = config
    save_all_configs(configs)


def delete_config(tracker_id: str) -> None:
    configs = load_all_configs().copy()
    configs.pop(tracker_id, None)
    save_all_configs(configs)
