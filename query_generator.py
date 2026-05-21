"""
Natural language → themes + queries, via Claude API.

Coworker describes their portco in plain English; Claude returns a structured
dict of themes (each with name + queries[]) ready to drop into the scraper.

Requires `ANTHROPIC_API_KEY` in Streamlit Secrets (or env var for the cron).
Setup:
  pip install anthropic
  Add to Streamlit Secrets:  ANTHROPIC_API_KEY = "sk-ant-..."
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


# Pre-built theme categories the user picks from via checkboxes.
# Each carries the guidance Claude uses when generating queries for it.
# Ordered so the default-checked categories come first in the UI.
CATEGORY_DEFINITIONS = {
    "competitive": {
        "label": "Competitive moves — M&A, funding, partnerships",
        "default": True,
        "guidance": (
            "M&A activity, capital raises (seed through IPO), partnerships, executive moves, "
            "product launches by competitors. Mix broad event-language queries (e.g. "
            "'industrial cybersecurity acquisition', 'OT security Series B funding') with "
            "named-competitor queries from the user's specifics."
        ),
    },
    "customer_wins": {
        "label": "Customer wins & deployments",
        "default": True,
        "guidance": (
            "Named-customer wins, deployments, contracts, RFP results. Use event verbs "
            "(selects, deploys, signs, wins, partners with) plus vertical/customer-type "
            "qualifiers."
        ),
    },
    "industry_news": {
        "label": "Industry news & regulatory landscape",
        "default": True,
        "guidance": (
            "General industry news: market developments, demand shifts, infrastructure "
            "investment, major customer/end-market trends, AND the regulatory landscape "
            "(policy direction, agency rule-makings, legislative pushes, enforcement actions, "
            "named regulations, compliance deadlines). Cover both narrative/landscape news "
            "AND discrete regulatory events in one theme. Mix vertical-qualified event "
            "queries with named-policy/named-agency queries (e.g. 'NIS2 directive', 'NERC-CIP "
            "audit', 'FDA 510k', 'CFPB enforcement')."
        ),
    },
    "product_launches": {
        "label": "Product launches & innovation",
        "default": False,
        "guidance": (
            "New product announcements, feature releases, major version updates from "
            "competitors and adjacent players."
        ),
    },
    "geographic": {
        "label": "Geographic / regional coverage",
        "default": False,
        "guidance": (
            "Country- or region-specific news in the industry. Use country names plus "
            "industry qualifiers. If the user specified regions in their specifics, use "
            "those; otherwise default to the largest relevant markets."
        ),
    },
    "talent": {
        "label": "Talent moves (key hires, departures)",
        "default": False,
        "guidance": (
            "Executive hires and departures at competitors and named portco. Use event "
            "verbs (appoints, hires, names CEO, departs, joins) plus role qualifiers."
        ),
    },
    "other": {
        "label": "Other (describe a custom theme)",
        "default": False,
        "guidance": (
            "User-defined theme. The user fills in a dedicated 'Other theme description' "
            "field — read it carefully and build a theme name and 8-15 queries around exactly "
            "that topic. Apply the same principles: broad event queries + named-entity queries, "
            "strong event verbs, avoid market-report phrasing. If the Other-theme description "
            "is empty or doesn't suggest a clear topic, skip this theme entirely."
        ),
    },
}


def category_keys() -> list[str]:
    return list(CATEGORY_DEFINITIONS.keys())


# Structured-output schema returned by Claude
class GeneratedTheme(BaseModel):
    name: str = Field(description="Short theme name (3-7 words). Will be used as a section heading.")
    queries: list[str] = Field(description="8-15 Google News search queries that target this theme.")


class GeneratedConfig(BaseModel):
    title: str = Field(description="Brief title shown at top of the deliverable (e.g. 'AcmeFresh Weekly Brief').")
    subtitle: str = Field(description="Subtitle shown beneath title (e.g. 'Banneker Partners · Fresh produce supply chain market intel').")
    themes: list[GeneratedTheme] = Field(
        description="One theme per enabled category, in priority order (breaches first if enabled, then competitive, then regulation, then others)."
    )


SYSTEM_PROMPT = """You are an analyst at Banneker Partners, a software-focused private equity firm. You build weekly news trackers for portfolio companies and deal targets.

Your job: take a brief description of a company plus a list of enabled theme categories, then return a structured set of themes and Google News RSS queries that will surface HIGH-SIGNAL NEWS.

# CRITICAL PRINCIPLES

## 1. Optimize for news, NOT market reports.

The Google News RSS we're hitting will return whatever matches the query string. Generic category queries pull market reports from Mordor Intelligence, Grand View Research, MarketsAndMarkets, Gartner, IDC, Statista, Forrester — those are evergreen reports, not news. Avoid query phrasing that primarily returns these.

- BAD: "OT cybersecurity market", "OT cybersecurity trends", "OT cybersecurity industry analysis"
- GOOD: "OT cybersecurity acquisition", "OT cybersecurity Series B", "ICS vendor acquired", "operational technology security funding round"

The test: would a journalist write an article matching this query, or would only an analyst write a report matching it? If the latter, change the query.

## 2. Mix BROAD event-language queries with NARROW named-entity queries.

Every theme needs both, because:
- Broad queries catch deals/incidents involving unknown players. (Most acquisitions don't name the acquirer in the headline.)
- Named queries catch news about specific competitors/regulations/companies the user cares about.

For each theme, aim for ~5-8 broad event queries + ~3-7 named-entity queries = 8-15 total.

Example (competitive theme for an OT cyber portco):
- Broad: "OT cybersecurity acquisition", "industrial cybersecurity Series B", "ICS vendor acquired", "OT security funding round", "operational technology cybersecurity investment", "industrial control system IPO"
- Named: "Claroty funding", "Dragos acquired", "Nozomi Networks IPO", "Armis acquisition", "TXOne raises"

Example (competitive theme for fresh produce SaaS):
- Broad: "produce technology acquisition", "agtech Series B funding", "food supply chain software acquired", "grocery technology IPO", "produce traceability software raises"
- Named: "Afresh funding", "Shelf Engine acquired", "Crisp Series A", "ProducePay raises"

## 3. Use STRONG event verbs.

Real news has real verbs. Use them in queries to filter out evergreen content.

Acquisition/M&A: acquires, acquired, acquisition, buys, merger, merges
Funding: raises, raised, Series A/B/C, IPO, funded, valuation
Launches: launches, unveils, announces, debuts, releases
Regulation: fined, penalty, settles, indicted, sued, enforcement, advisory
Security: breach, attack, hacked, ransomware, exploit, leaked, stolen, vulnerability
Customer: selects, deploys, signs, wins, partners, replaces, adopts
Talent: appoints, hires, joins, departs, resigns, names CEO

## 4. Be specific with regulations and named entities, generic with categories.

- For regulations: name the actual regulation/agency ("NIS2 directive enforcement", "NERC-CIP audit", "FSMA 204 traceability", "CFPB enforcement"), not "regulations" or "compliance"
- For competitors: name them individually as separate queries
- For verticals: use vertical qualifiers ("utility cyberattack", "manufacturing ransomware"), not the bare category

## 5. EVERY query MUST include an industry-anchor term. (Critical.)

Google News RSS does loose token matching — a query like "agtech Series B funding" will return ANY tech-sector Series B story where the words happen to appear nearby. The result: a produce-tech tracker pulls semiconductor or food-delivery M&A news.

To prevent this, every single query — broad event queries AND named-entity queries — must contain at least one tight industry-anchor word or phrase that uniquely identifies this industry. Generic event words (acquisition, Series B, M&A, funding, raises) cannot stand alone.

For each tracker, first pick 2-4 industry-anchor terms from the user's industry description. These are the words a journalist writing about THIS industry would actually use. Then ensure every query contains at least one of them.

- BAD (produce-tech tracker): "agtech Series B funding"  →  "agtech" is too loose; matches drone, livestock, and food-delivery startups
- GOOD: "fresh produce software Series B", "produce traceability funding", "grocery supply chain SaaS raises"

- BAD (OT cyber tracker): "industrial cybersecurity acquisition"  →  the words "industrial" and "cybersecurity" rarely co-occur in actual headlines
- GOOD: "OT cybersecurity acquisition", "ICS security vendor acquired", "operational technology security M&A"

- BAD (healthcare RCM tracker): "RCM acquisition"  →  "RCM" alone is too short, will match unrelated acronyms
- GOOD: "revenue cycle management acquisition", "healthcare RCM acquisition", "medical billing software acquired"

The test for each query: "If I read three loose interpretations of the words in this query, would they all be about the user's industry?" If no, add an anchor term.

## 6. SOFTWARE FOCUS (Banneker-specific). EVERY non-regulatory query must filter for software/tech news.

Banneker Partners invests exclusively in software/tech companies. Every tracker is built for a software portco or software deal target. The user does NOT care about news affecting the physical/operational side of the industry — only the software/tech sub-segment.

Examples of news that should NEVER appear in these trackers:
- "HEB acquires land for new distribution center" — physical grocery operations, not software
- "Fresh produce industry survey group relocates" — corporate-move news, not software
- "Tyson Foods buys poultry farm" — agriculture M&A, not software
- "Hospital system opens new wing" — healthcare facility news, not software

The rule: every query for the COMPETITIVE, CUSTOMER WINS, PRODUCT LAUNCHES, GEOGRAPHIC, TALENT, and OTHER themes must contain a software/tech qualifier. Choose from: "software", "SaaS", "platform", "technology", "tech", "AI", "automation", "digital", "app", or an industry-specific software acronym (RCM, EHR, ERP, CRM, etc.).

EXCEPTION — INDUSTRY NEWS & REGULATORY LANDSCAPE: this single theme covers broader policy, regulation, and industry trends that affect the whole industry, not just software vendors. Queries here may omit the software qualifier when the topic is genuinely industry-wide (a new FDA traceability rule, an EPA mandate, a Congressional hearing). When a regulation is software-relevant, still pair it with software language where natural.

Bad/good pairs (fresh produce software tracker):
- BAD: "HEB acquisition"  →  matches "HEB acquires land", "HEB acquires grocery chain"
- GOOD: "HEB software contract", "HEB selects technology platform", "HEB SaaS deal"

- BAD: "fresh produce acquisition"  →  matches farm acquisitions, distribution-center M&A
- GOOD: "fresh produce software acquisition", "produce SaaS acquired", "grocery tech M&A"

- BAD: "produce industry executive moves"  →  matches plant/warehouse hires
- GOOD: "produce software CEO", "agtech executive hire", "produce SaaS appoints"

For inherently digital industries (cybersecurity, fintech, AI, devops), the industry name itself implies software — you don't need to double up the qualifier. "OT cybersecurity acquisition" is fine without adding "software" because OT cybersecurity is inherently software.

The test for each non-regulatory query: "Would the matching article be about a software company, software product, or technology platform? Or could it be about physical operations, real estate, hiring at a plant, or the underlying physical industry?" Only the former is in scope.

# OUTPUT STRUCTURE

Return one theme per enabled category, in this priority order if applicable:
1. Competitive (M&A, raises, partnerships)
2. Customer wins
3. Industry news & regulatory landscape
4. Other (user-defined custom theme)
5. Product launches
6. Geographic
7. Talent

Each theme should have 8-15 queries. Mix broad event queries with named-entity queries pulled from the user's specifics (if provided).

If the "Other" category is enabled but the Other-theme description is empty, skip that theme — don't fabricate one.

# TITLE/SUBTITLE

- Title: "[Company Name] Weekly Brief"
- Subtitle: "Banneker Partners · [short industry phrase] market intel"

Return ONLY the structured JSON — no preamble, no explanation."""


def _build_user_prompt(company_name: str, industry: str, enabled_categories: list[str], specifics: str, other_description: str = "") -> str:
    enabled_block = "\n".join(
        f"- {key} — {CATEGORY_DEFINITIONS[key]['label']}\n  Guidance: {CATEGORY_DEFINITIONS[key]['guidance']}"
        for key in enabled_categories if key in CATEGORY_DEFINITIONS
    )
    specifics_block = specifics.strip() or "(none provided — use defaults for the industry)"

    other_block = ""
    if "other" in enabled_categories:
        desc = other_description.strip() or "(empty — skip the Other theme entirely)"
        other_block = f"\n\n# OTHER-THEME DESCRIPTION (use this to build the 'Other' theme)\n{desc}"

    return f"""Build a weekly news tracker.

# COMPANY / TRACKER NAME
{company_name}

# INDUSTRY / MARKET
{industry.strip()}

# ENABLED THEME CATEGORIES (one theme per category, in this exact order)
{enabled_block}

# USER-PROVIDED SPECIFICS (incorporate as named-entity queries within the relevant themes)
{specifics_block}{other_block}

Before generating queries:
1. Internally identify 2-4 INDUSTRY-ANCHOR TERMS from the industry description above — the words a journalist actually writing about this industry would use in a headline. USE THE NARROWEST FORM the user gave you, not a broader generalization. "Fresh produce supply chain" must NOT become "food supply chain" or "supply chain"; "OT cybersecurity for utilities" must NOT become "industrial cybersecurity". The narrower form is what the user meant.
2. Identify whether this is an inherently-digital industry (cyber, fintech, AI) or a physical industry with a software sub-segment (food, healthcare, energy, industrials).
3. For physical-industry trackers, pick 1-2 SOFTWARE-QUALIFIER terms (software, SaaS, platform, technology, etc.) that you will pair with the industry anchor.

Every single non-regulatory query must contain BOTH an industry anchor (in its narrowest form) AND (for physical-industry trackers) a software qualifier. If you find yourself writing "HEB acquisition" or "fresh produce M&A" or "food supply chain acquisition", stop and (a) narrow the anchor and (b) add a software qualifier.

ALSO AVOID generic adjacencies — for a fresh-produce-software tracker, "supply chain software acquisition" is too broad (matches Manhattan Associates, Blue Yonder, manufacturing supply chain); needs to be "fresh produce supply chain software acquisition" or "produce traceability software acquisition".

Generate the structured tracker config now. Remember: news-only (avoid market-report queries, earnings posts, IPO tracker listicles), mix broad event queries with named queries, use strong event verbs, every query needs the narrowest industry anchor + software qualifier (except regulatory-landscape queries), 8-15 queries per theme."""


def generate_config(
    company_name: str,
    industry_description: str,
    enabled_categories: list[str],
    specifics: str = "",
    other_description: str = "",
) -> Optional[dict]:
    """Call Claude API to convert structured inputs → themes/queries config.

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

    if not enabled_categories:
        enabled_categories = [k for k, v in CATEGORY_DEFINITIONS.items() if v["default"]]

    user_prompt = _build_user_prompt(company_name, industry_description, enabled_categories, specifics, other_description)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.parse(
            model="claude-sonnet-4-6",
            max_tokens=6000,
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


def revise_config(
    previous_config: dict,
    feedback: str,
    company_name: str,
    industry_description: str,
    enabled_categories: list[str],
    specifics: str = "",
    other_description: str = "",
) -> Optional[dict]:
    """Take an existing generated config + user feedback in plain English, and ask
    Claude to return a revised version. Same return shape as `generate_config`.
    """
    api_key = get_anthropic_key()
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    if not enabled_categories:
        enabled_categories = [k for k, v in CATEGORY_DEFINITIONS.items() if v["default"]]

    base_prompt = _build_user_prompt(company_name, industry_description, enabled_categories, specifics, other_description)

    # Serialize the previous config compactly so Claude can see what to revise.
    prev_themes_text = "\n".join(
        f"## Theme: {t.get('name', '')}\n" + "\n".join(f"- {q}" for q in t.get("queries", []))
        for t in previous_config.get("themes", [])
    )

    revise_prompt = f"""{base_prompt}

# PREVIOUS GENERATED CONFIG
You generated the following themes and queries previously. The user has feedback below — REVISE the config based on their feedback. Keep what's good, change what they're asking you to change. Preserve the same number of themes (one per enabled category) and the same priority ordering. Aim for 8-15 queries per theme.

Title: {previous_config.get('title', '')}
Subtitle: {previous_config.get('subtitle', '')}

{prev_themes_text}

# USER FEEDBACK (apply this to the revision)
{feedback.strip()}

Return the FULL revised config — title, subtitle, all themes, all queries. Apply the user's feedback throughout (not just to one theme). Re-check every query against the rules in your system prompt before returning."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.parse(
            model="claude-sonnet-4-6",
            max_tokens=6000,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": revise_prompt}],
            output_format=GeneratedConfig,
        )
        cfg: GeneratedConfig = response.parsed_output
        return {
            "title": cfg.title,
            "subtitle": cfg.subtitle,
            "themes": [{"name": t.name, "queries": t.queries} for t in cfg.themes],
        }
    except Exception as e:
        print(f"Claude API error during config revision: {e}")
        return None
