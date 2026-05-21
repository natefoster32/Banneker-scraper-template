"""
Natural language → themes + queries, via Claude API.

Coworker describes their portco in plain English; Claude returns a structured
dict of themes (each with name + queries[]) ready to drop into the scraper.

Requires `ANTHROPIC_API_KEY` in Streamlit Secrets (or env var for the cron).
Setup:
  pip install anthropic
  Add to Streamlit Secrets:  ANTHROPIC_API_KEY = "sk-ant-..."

Cost: ~$0.01-0.03 per tracker creation (one-time per user). With Claude's
prompt caching enabled, the long system prompt is cached on 2nd+ creations.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field


def get_anthropic_key() -> str:
    """Pull API key from Streamlit secrets if available, else env var."""
    try:
        import streamlit as st
        val = st.secrets.get("ANTHROPIC_API_KEY", "")
        if val:
            return val
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "")


# Structured-output schema returned by Claude
class GeneratedTheme(BaseModel):
    name: str = Field(description="Short theme name (3-7 words). Will be used as a section heading.")
    queries: list[str] = Field(description="6-12 Google News search queries that target this theme.")


class GeneratedConfig(BaseModel):
    title: str = Field(description="Brief title shown at top of the deliverable (e.g. 'AcmeFresh Weekly Brief').")
    subtitle: str = Field(description="Subtitle shown beneath title (e.g. 'Banneker Partners · Fresh produce supply chain market intel').")
    themes: list[GeneratedTheme] = Field(
        description="5-7 themes organized in priority order (most actionable first, typically breaches/incidents then competitive/M&A then regulatory)."
    )


SYSTEM_PROMPT = """You are an analyst at Banneker Partners, a software-focused private equity firm. You build weekly news trackers for portfolio companies and deal targets.

Your job: take a brief description of a company and what their team cares about, then return a structured set of themes and Google News RSS queries that will surface high-signal news.

Rules for queries:
- Each query is what you'd type into Google News (3-8 words). Be specific.
- Avoid generic queries like "cybersecurity" or "healthcare news" — they pull too much noise.
- Prefer specific phrases ("NIS2 directive enforcement", "FDA 510k clearance"), named competitors, named regulations, and event-language (acquires, raises, breach, fined, recall, partnership).
- Include 2-3 queries per major sub-area within a theme so coverage is robust to phrasing variation.
- For competitive themes, include the company itself plus 3-5 named competitors.
- For regulatory themes, name the specific regulations / agencies (e.g. "NERC-CIP audit", "CMS reimbursement rule", "CFPB enforcement").
- For breach/incident themes (always include one if industrial / fintech / cyber / data-heavy), include event keywords and named verticals.

Rules for themes:
- 5-7 themes total.
- Order them by signal value to a busy PE-portco operator: most actionable first.
- Typical priority order: Breaches/Incidents → Competitive (M&A, raises) → Regulation → Customer/Market dynamics → Geographic.
- Each theme name should be short and concrete (3-7 words).

Rules for title/subtitle:
- Title: "[Company Name] Weekly Brief" unless context suggests otherwise.
- Subtitle: "Banneker Partners · [short industry phrase] market intel".

Return ONLY the structured JSON — no preamble, no explanation."""


def generate_config(company_name: str, industry_description: str, themes_description: str) -> Optional[dict]:
    """Call Claude API to convert natural language → themes/queries config.

    Returns a dict with keys {title, subtitle, themes}, or None if the call fails.
    `themes` is a list of {name, queries[]}.
    """
    api_key = get_anthropic_key()
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    user_prompt = f"""Build a weekly news tracker for the following:

Company / tracker name: {company_name}

Industry and market the company operates in:
{industry_description.strip()}

Themes the team specifically wants tracked (regions, competitors, regulatory topics, etc.):
{themes_description.strip()}

Generate the structured tracker config now."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.parse(
            model="claude-opus-4-7",
            max_tokens=4000,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
            output_format=GeneratedConfig,
        )

        cfg: GeneratedConfig = response.parsed_output
        return {
            "title": cfg.title,
            "subtitle": cfg.subtitle,
            "themes": [{"name": t.name, "queries": t.queries} for t in cfg.themes],
        }
    except Exception as e:
        print(f"Claude API error during config generation: {e}")
        return None
