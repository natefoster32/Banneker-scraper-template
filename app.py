"""
Banneker News Tracker — multi-tenant Streamlit app.

Routes (via ?page= and ?id= query params):
  /                    -> home (landing + list of trackers)
  /?page=create        -> create a new tracker
  /?id=<tracker_id>    -> view/run a specific tracker
  /?id=<id>&edit=1     -> edit an existing tracker
"""

import json
import re
import secrets
from datetime import datetime

import streamlit as st

from core import (
    BODY_GREY,
    DARK_GREY,
    DEEP_NAVY,
    ICE_BLUE,
    MID_GREY,
    NAVY,
    PERIWINKLE,
    build_docx_bytes,
    config_hash,
    pick_top_stories,
    scrape_for_config,
)
from core import build_email_html
from email_sender import send_email
from query_generator import CATEGORY_DEFINITIONS, generate_config, get_anthropic_key, revise_config
from storage import delete_config, get_config, load_all_configs, upsert_config

# ---------- Page setup ----------

st.set_page_config(
    page_title="Banneker News Tracker",
    page_icon="📰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(f"""
<style>
  .stApp {{ background: #FFFFFF; }}
  /* Scope the Inter override so Material Icons / Material Symbols fonts on
     icon spans aren't clobbered (they need their own font-family to render
     as glyphs instead of literal text like "_arrow_right"). */
  html, body, .stApp, .stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3,
  .stApp h4, .stApp h5, .stApp h6, .stApp label, .stApp button, .stApp input,
  .stApp textarea, .stApp select, .stApp div[data-testid="stMarkdownContainer"],
  .stApp div[data-testid="stMarkdownContainer"] * {{
    font-family: Inter, Calibri, "Segoe UI", Arial, sans-serif;
  }}
  /* Restore icon fonts on Material Icons / Symbols elements. */
  .material-icons, .material-symbols-outlined, .material-symbols-rounded,
  [class*="material-symbols"], [class*="MuiIcon"], [class*="iconContainer"] *,
  span[data-baseweb="icon"], span[data-baseweb="icon"] * {{
    font-family: 'Material Symbols Outlined', 'Material Icons', 'Material Symbols Rounded' !important;
  }}
  h1, h1 *, h2, h2 *, h3, h3 *,
  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h1 *,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h2 *,
  [data-testid="stMarkdownContainer"] h3,
  [data-testid="stMarkdownContainer"] h3 * {{
    color: {NAVY} !important;
    font-weight: 700 !important;
  }}
  p, li, div, span, label {{ color: {BODY_GREY}; }}
  .block-container {{ padding-top: 2.5rem; padding-bottom: 4rem; max-width: 820px; }}
  .stButton > button {{
    background-color: {NAVY} !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 14px 32px !important;
    border-radius: 4px !important;
    font-size: 15px !important;
    width: 100%;
    box-shadow: 0 2px 6px rgba(24, 31, 100, 0.18);
    transition: all 0.15s ease;
  }}
  .stButton > button:hover {{
    background-color: {DEEP_NAVY} !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 10px rgba(24, 31, 100, 0.25);
    transform: translateY(-1px);
  }}
  .stButton > button p {{ color: #FFFFFF !important; font-weight: 700 !important; }}
  .stDownloadButton > button {{
    background-color: #FFFFFF !important;
    color: {NAVY} !important;
    border: 1.5px solid {NAVY} !important;
    font-weight: 700 !important;
    padding: 10px 22px !important;
    border-radius: 4px !important;
  }}
  .stDownloadButton > button:hover {{ background-color: {ICE_BLUE} !important; }}
  a {{ color: {NAVY} !important; text-decoration: underline; text-decoration-color: rgba(118, 163, 227, 0.5); }}
  a:hover {{ color: {PERIWINKLE} !important; text-decoration-color: {PERIWINKLE}; }}
  .top-news-card a,
  .top-news-card a:link,
  .top-news-card a:visited {{
    color: #FFFFFF !important;
    text-decoration: none !important;
    border-bottom: 1px dotted rgba(255, 255, 255, 0.45) !important;
    font-weight: 600 !important;
  }}
  .top-news-card a:hover {{
    color: {PERIWINKLE} !important;
    border-bottom-color: {PERIWINKLE} !important;
  }}
  #MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; }}
  .stTextInput > div > div > input,
  .stTextArea textarea,
  .stSelectbox > div > div {{
    border-radius: 4px !important;
  }}
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s[:40] or "tracker"


def make_tracker_id(name: str) -> str:
    base = slugify(name)
    existing = load_all_configs()
    candidate = base
    while candidate in existing:
        candidate = f"{base}-{secrets.token_hex(2)}"
    return candidate


def render_footer():
    year = datetime.now().year
    st.markdown(
        f"<div style='margin-top:56px; padding-top:16px; border-top:1px solid {ICE_BLUE}; color:{MID_GREY}; font-size:11px;'>"
        f"(C) {year} Banneker Partners, LLC. All Rights Reserved. Confidential."
        f"</div>",
        unsafe_allow_html=True,
    )


LOGO_PATH = "assets/banneker-logo.png"


def render_masthead(title: str, subtitle: str = "", compact: bool = False):
    # Banneker logo above the navy rule
    logo_width = 130 if compact else 180
    try:
        st.image(LOGO_PATH, width=logo_width)
    except Exception:
        pass

    if compact:
        sub_html = (
            f"<span style='color:{PERIWINKLE}; font-weight:700; font-size:11px; letter-spacing:1.4px; text-transform:uppercase; margin-left:10px; vertical-align:middle;'>{subtitle}</span>"
            if subtitle else ""
        )
        st.markdown(
            f"""
            <div style='border-top:3px solid {NAVY}; padding-top:10px; margin-bottom:6px; margin-top:8px;'></div>
            <h1 style='color:{NAVY}; font-weight:800; font-size:24px; line-height:1.15; margin:0 0 10px 0; letter-spacing:-0.3px;'>{title}{sub_html}</h1>
            """,
            unsafe_allow_html=True,
        )
    else:
        sub_html = (
            f"<div style='color:{PERIWINKLE}; font-weight:700; font-size:13px; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:14px;'>{subtitle}</div>"
            if subtitle else ""
        )
        st.markdown(
            f"""
            <div style='border-top:4px solid {NAVY}; padding-top:18px; margin-bottom:8px; margin-top:14px;'></div>
            <h1 style='color:{NAVY}; font-weight:800; font-size:38px; line-height:1.1; margin:0 0 6px 0; letter-spacing:-0.5px;'>{title}</h1>
            {sub_html}
            """,
            unsafe_allow_html=True,
        )


# ---------- Home ----------

def render_home():
    render_masthead("Banneker News Tracker", "Build your own market intel feed")
    st.markdown(
        f"<div style='color:{BODY_GREY}; font-size:15px; line-height:1.55; margin-bottom:24px; max-width:640px;'>"
        "Personalized weekly news brief for your portco, your patch, or whatever you're tracking. "
        "Takes ~4 minutes to set up. Bookmarkable URL. Optional weekly email straight to your inbox. "
        "Built for Banneker."
        "</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Create a new tracker", type="primary", key="cta_create"):
            st.query_params.update({"page": "create"})
            st.rerun()

    configs = load_all_configs()
    if configs:
        st.markdown(
            f"<div style='margin-top:36px;'><h3 style='color:{NAVY}; margin-bottom:8px;'>Existing trackers</h3></div>",
            unsafe_allow_html=True,
        )
        for tid, cfg in sorted(configs.items(), key=lambda kv: kv[1].get("created_at", "")):
            name = cfg.get("name") or tid
            subtitle = cfg.get("subtitle", "")
            theme_count = len(cfg.get("themes", []))
            url = f"?id={tid}"
            st.markdown(
                f"<div style='margin:10px 0; padding:14px 18px; background:{ICE_BLUE}; border-left:4px solid {NAVY}; border-radius:2px;'>"
                f"<div style='color:{NAVY}; font-weight:700; font-size:16px;'><a href='{url}'>{name}</a></div>"
                f"<div style='color:{DARK_GREY}; font-size:12px; margin-top:2px;'>{subtitle} &middot; {theme_count} themes</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    render_footer()


# ---------- Create ----------

FORM_KEYS = [
    "form_name", "form_industry", "form_specifics", "form_other_description",
    "form_email", "form_frequency", "form_generated_title",
    "form_generated_subtitle", "form_generated_themes",
    "form_generated_anchor_terms", "form_lookback", "form_revise_feedback",
]
FORM_KEYS += [f"form_cat_{k}" for k in CATEGORY_DEFINITIONS.keys()]


def _clear_form_state():
    for k in FORM_KEYS:
        st.session_state.pop(k, None)


def _seed_form_from_existing(cfg: dict):
    st.session_state["form_name"] = cfg.get("name", "")
    st.session_state["form_industry"] = cfg.get("industry_description", "")
    st.session_state["form_specifics"] = cfg.get("specifics", "") or cfg.get("themes_description", "")
    st.session_state["form_other_description"] = cfg.get("other_description", "")
    sub = cfg.get("email_subscription") or {}
    st.session_state["form_email"] = sub.get("email", "")
    st.session_state["form_frequency"] = sub.get("frequency", "none")
    st.session_state["form_generated_title"] = cfg.get("title", "")
    st.session_state["form_generated_subtitle"] = cfg.get("subtitle", "")
    st.session_state["form_generated_themes"] = cfg.get("themes", [])
    st.session_state["form_generated_anchor_terms"] = cfg.get("anchor_terms", [])
    st.session_state["form_lookback"] = cfg.get("lookback_days", 7)
    saved_cats = cfg.get("enabled_categories") or [k for k, v in CATEGORY_DEFINITIONS.items() if v["default"]]
    for cat_key in CATEGORY_DEFINITIONS.keys():
        st.session_state[f"form_cat_{cat_key}"] = cat_key in saved_cats


def render_create(edit_id: str | None = None):
    existing = get_config(edit_id) if edit_id else None
    title_text = "Edit your tracker" if existing else "Create your tracker"
    render_masthead(title_text)

    # Seed state from existing config on first render of edit page
    if existing and "form_name" not in st.session_state:
        _seed_form_from_existing(existing)

    # Default-initialize any missing form keys exactly once.
    # This is required so widgets can use `key=` alone (no `value=`),
    # which avoids Streamlit's value/key collision warnings and rendering glitches.
    _defaults = {
        "form_name": "",
        "form_industry": "",
        "form_specifics": "",
        "form_other_description": "",
        "form_email": "",
        "form_frequency": "none",
        "form_lookback": 14,
        "form_generated_title": "",
        "form_generated_subtitle": "",
    }
    for _k, _default in _defaults.items():
        if _k not in st.session_state:
            st.session_state[_k] = _default
    for _cat_key, _cat_def in CATEGORY_DEFINITIONS.items():
        _sk = f"form_cat_{_cat_key}"
        if _sk not in st.session_state:
            st.session_state[_sk] = _cat_def["default"]

    has_api_key = bool(get_anthropic_key())
    if not has_api_key:
        st.error(
            "Claude API key is not configured. The admin needs to add `ANTHROPIC_API_KEY` "
            "to Streamlit Secrets before this tracker can be generated. Until then, "
            "the form below won't work."
        )

    st.markdown(
        f"<div style='color:{BODY_GREY}; font-size:14px; line-height:1.55; margin-bottom:20px; max-width:640px;'>"
        "Answer three questions about what you want to track. Claude builds the themes and "
        "search queries for you. Takes about 2 minutes."
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Question 1: Company name ---
    st.markdown(f"<h3 style='color:{NAVY}; margin-bottom:4px;'>1. Company name</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{MID_GREY}; font-size:13px; margin-bottom:8px;'>"
        "The portco, deal target, or anything else this tracker is about."
        "</div>",
        unsafe_allow_html=True,
    )
    name = st.text_input(
        "Company name",
        placeholder="e.g., Industrial Defender",
        key="form_name",
        label_visibility="collapsed",
    )

    # --- Question 2: Industry (one line) ---
    st.markdown(f"<h3 style='color:{NAVY}; margin-top:24px; margin-bottom:4px;'>2. Market</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{MID_GREY}; font-size:13px; margin-bottom:8px;'>"
        "What market does this company sell into? (You don't need to say \"software\" — that's implied.) "
        "Be as narrow as you can — \"fresh produce supply chain\" beats \"food supply chain.\""
        "</div>",
        unsafe_allow_html=True,
    )
    industry = st.text_input(
        "Market",
        placeholder="e.g., fresh produce supply chain  ·  OT security for critical infrastructure  ·  medical RCM",
        key="form_industry",
        label_visibility="collapsed",
    )

    # --- Question 3: Theme category checkboxes ---
    st.markdown(f"<h3 style='color:{NAVY}; margin-top:24px; margin-bottom:4px;'>3. What to track</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{MID_GREY}; font-size:13px; margin-bottom:10px;'>"
        "The first three are pre-checked as sensible defaults. Uncheck what you don't need, check what you do. Tick \"Other\" to add a custom theme — a description field will appear."
        "</div>",
        unsafe_allow_html=True,
    )
    enabled_categories: list[str] = []
    for cat_key, cat_def in CATEGORY_DEFINITIONS.items():
        state_key = f"form_cat_{cat_key}"
        checked = st.checkbox(cat_def["label"], key=state_key)
        if checked:
            enabled_categories.append(cat_key)

    # --- Conditional: Other theme description (only when "Other" is checked) ---
    other_description = ""
    if "other" in enabled_categories:
        st.markdown(
            f"<div style='color:{NAVY}; font-size:13px; font-weight:700; margin-top:12px; margin-bottom:4px;'>"
            "Describe your custom \"Other\" theme"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='color:{MID_GREY}; font-size:12px; margin-bottom:6px;'>"
            "One or two sentences on what news you want surfaced. Claude will build a section just for this."
            "</div>",
            unsafe_allow_html=True,
        )
        other_description = st.text_area(
            "Other theme description",
            placeholder="e.g., AI safety regulation and government oversight of frontier AI labs.",
            key="form_other_description",
            height=80,
            label_visibility="collapsed",
        )

    # --- Question 4: Specifics (optional) ---
    st.markdown(f"<h3 style='color:{NAVY}; margin-top:24px; margin-bottom:4px;'>4. Anything special to call out or cover? (optional)</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{MID_GREY}; font-size:13px; margin-bottom:8px;'>"
        "Named competitors, specific regions/countries, named customers, named regulations. "
        "Claude uses these as named-entity queries within the themes above."
        "</div>",
        unsafe_allow_html=True,
    )
    specifics = st.text_area(
        "Specifics",
        placeholder=(
            "e.g., Competitors: Claroty, Dragos, Nozomi Networks, Armis, TXOne. "
            "Regulations: NIS2 directive, NERC-CIP, TSA pipeline directives, CISA advisories. "
            "Regions: Germany, Poland, UK, Italy, Austria, Switzerland."
        ),
        key="form_specifics",
        height=100,
        label_visibility="collapsed",
    )

    # --- Email + frequency ---
    st.markdown(f"<h3 style='color:{NAVY}; margin-top:24px; margin-bottom:4px;'>4. Email me the brief</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{MID_GREY}; font-size:13px; margin-bottom:8px;'>"
        "Optional. Leave email blank to use the web page only, or set frequency to \"Don't email me\"."
        "</div>",
        unsafe_allow_html=True,
    )
    email = st.text_input(
        "Your email",
        placeholder="you@banneker.com",
        key="form_email",
    )
    freq_options = ["none", "weekly_monday", "weekly_friday", "daily"]
    freq_labels = {
        "none": "Don't email me",
        "weekly_monday": "Weekly · Monday",
        "weekly_friday": "Weekly · Friday",
        "daily": "Daily",
    }
    # Defensive: if something corrupted form_frequency, snap it back to a valid value.
    if st.session_state.get("form_frequency") not in freq_options:
        st.session_state["form_frequency"] = "none"
    # Radio (not selectbox) — radios can't be browser-autofilled with email text.
    frequency = st.radio(
        "Frequency",
        options=freq_options,
        format_func=lambda v: freq_labels[v],
        key="form_frequency",
        horizontal=True,
    )

    # --- Generate preview button ---
    st.markdown("---")
    has_generated = "form_generated_themes" in st.session_state and st.session_state["form_generated_themes"]
    generate_label = "Regenerate from descriptions" if has_generated else "Generate my tracker"

    if st.button(generate_label, type="primary", key="generate_btn", disabled=not has_api_key):
        if not name.strip():
            st.error("Company name is required.")
        elif not industry.strip():
            st.error("Industry description is required.")
        elif not enabled_categories:
            st.error("Check at least one category in question 3.")
        else:
            with st.spinner("Claude is building your themes and queries (~10-20 seconds)..."):
                generated = generate_config(name, industry, enabled_categories, specifics, other_description)
            if generated is None:
                st.error(
                    "Generation failed. Check that the Claude API key is set in Streamlit Secrets "
                    "and that the account has credit available."
                )
            else:
                st.session_state["form_generated_title"] = generated["title"]
                st.session_state["form_generated_subtitle"] = generated["subtitle"]
                st.session_state["form_generated_themes"] = generated["themes"]
                st.session_state["form_generated_anchor_terms"] = generated.get("anchor_terms", [])
                # Invalidate preview cache so the new themes get scraped fresh
                for _k in ("preview_cache_key", "preview_grouped", "preview_total"):
                    st.session_state.pop(_k, None)
                st.rerun()

    # --- Preview: sample email + save/revise actions ---
    if has_generated:
        st.markdown(
            f"<div style='margin-top:32px;'><h3 style='color:{NAVY};'>Sample brief preview</h3>"
            f"<div style='color:{MID_GREY}; font-size:13px;'>Here's what this week's email would look like. "
            f"If something's missing or off, edit the inputs above and click Generate again. "
            f"Otherwise click Save below.</div></div>",
            unsafe_allow_html=True,
        )

        gen_title = st.text_input("Brief title", key="form_generated_title")
        gen_subtitle = st.text_input("Subtitle", key="form_generated_subtitle")
        if st.session_state.get("form_lookback") not in [3, 7, 14, 30]:
            st.session_state["form_lookback"] = 7
        lookback = st.selectbox(
            "Lookback window",
            options=[3, 7, 14, 30],
            format_func=lambda d: f"Past {d} days",
            key="form_lookback",
        )

        # Build a temporary config and scrape it. Cache by config hash so we
        # don't re-scrape on every rerun (e.g. clicking inside a text field).
        preview_config = {
            "id": "preview",
            "name": name.strip() or "Preview",
            "title": (st.session_state.get("form_generated_title") or "").strip() or f"{name.strip()} Brief",
            "subtitle": (st.session_state.get("form_generated_subtitle") or "").strip(),
            "themes": st.session_state["form_generated_themes"],
            "anchor_terms": st.session_state.get("form_generated_anchor_terms", []),
            "lookback_days": int(lookback),
            "show_top_news": True,
        }
        preview_key = config_hash(preview_config)
        if st.session_state.get("preview_cache_key") != preview_key:
            with st.spinner("Pulling sample stories (~20-40 seconds)..."):
                try:
                    grouped, total = scrape_for_config(preview_config)
                except Exception as e:
                    st.error(f"Scrape failed: {e}")
                    grouped, total = {}, 0
            st.session_state["preview_grouped"] = grouped
            st.session_state["preview_total"] = total
            st.session_state["preview_cache_key"] = preview_key

        grouped = st.session_state.get("preview_grouped", {})
        total = st.session_state.get("preview_total", 0)
        theme_order = [t["name"] for t in preview_config["themes"] if t.get("name")]
        try:
            email_html = build_email_html(grouped, theme_order, total, preview_config, unsubscribe_url=None)
        except Exception as e:
            email_html = f"<p style='color:#900'>Preview render failed: {e}</p>"

        # Render the email HTML inside an iframe so its inline styles aren't
        # stripped or fought by the page's own CSS.
        import streamlit.components.v1 as components
        components.html(email_html, height=900, scrolling=True)

        st.markdown(
            f"<div style='color:{MID_GREY}; font-size:12px; margin-top:6px;'>"
            f"Preview shows actual stories from Google News for the queries Claude generated. "
            f"{total} stories pulled across {len(theme_order)} themes."
            f"</div>",
            unsafe_allow_html=True,
        )

        # --- Conversational revise loop ---
        st.markdown(
            f"<div style='margin-top:20px;'>"
            f"<div style='color:{NAVY}; font-weight:700; font-size:14px; margin-bottom:4px;'>Not quite right? Tell Claude how to revise.</div>"
            f"<div style='color:{MID_GREY}; font-size:12px; margin-bottom:6px;'>"
            f"e.g. \"focus only on fresh produce, not general food supply chain\", "
            f"\"drop earnings reports\", "
            f"\"add more queries on named LMM produce-software competitors\"."
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        feedback = st.text_area(
            "Revision feedback",
            key="form_revise_feedback",
            placeholder="What's off about the queries? What should Claude change?",
            height=80,
            label_visibility="collapsed",
        )
        if st.button("Revise & regenerate", key="revise_btn"):
            if not feedback.strip():
                st.warning("Type some feedback first.")
            else:
                with st.spinner("Claude is revising your queries (~10-20 seconds)..."):
                    prev = {
                        "title": st.session_state.get("form_generated_title", ""),
                        "subtitle": st.session_state.get("form_generated_subtitle", ""),
                        "themes": st.session_state["form_generated_themes"],
                        "anchor_terms": st.session_state.get("form_generated_anchor_terms", []),
                    }
                    revised = revise_config(
                        previous_config=prev,
                        feedback=feedback,
                        company_name=name,
                        industry_description=industry,
                        enabled_categories=enabled_categories,
                        specifics=specifics,
                        other_description=other_description,
                    )
                if revised is None:
                    st.error("Revision failed. Check the Claude API key / credit and try again.")
                else:
                    st.session_state["form_generated_title"] = revised["title"]
                    st.session_state["form_generated_subtitle"] = revised["subtitle"]
                    st.session_state["form_generated_themes"] = revised["themes"]
                    st.session_state["form_generated_anchor_terms"] = revised.get("anchor_terms", [])
                    st.session_state["form_revise_feedback"] = ""  # clear the field
                    for _k in ("preview_cache_key", "preview_grouped", "preview_total"):
                        st.session_state.pop(_k, None)
                    st.rerun()

        # Power-user fallback: manual theme/query editing
        with st.expander("Advanced: edit themes & queries manually"):
            st.caption(
                "You usually shouldn't need this — if the preview is off, edit the inputs "
                "above and click Generate again. But if you want to hand-tune the queries, you can."
            )
            themes = st.session_state["form_generated_themes"]
            edited_themes = []
            for i, theme in enumerate(themes):
                st.markdown(
                    f"<div style='background:{ICE_BLUE}; padding:8px 12px; border-radius:3px; margin-top:10px; margin-bottom:4px; border-left:3px solid {NAVY};'>"
                    f"<div style='color:{NAVY}; font-weight:700; font-size:11px; letter-spacing:1.2px; text-transform:uppercase;'>Theme {i+1:02d}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                t_name = st.text_input("Theme name", value=theme["name"], key=f"theme_name_{i}",
                                       label_visibility="collapsed")
                t_queries = st.text_area(
                    "Queries (one per line)",
                    value="\n".join(theme["queries"]),
                    key=f"theme_queries_{i}",
                    height=110,
                )
                ctrl_cols = st.columns([1, 1, 1, 5])
                with ctrl_cols[0]:
                    if st.button("↑", key=f"up_{i}", disabled=(i == 0)):
                        themes[i], themes[i-1] = themes[i-1], themes[i]
                        st.session_state["form_generated_themes"] = themes
                        st.session_state.pop("preview_cache_key", None)
                        st.rerun()
                with ctrl_cols[1]:
                    if st.button("↓", key=f"down_{i}", disabled=(i == len(themes) - 1)):
                        themes[i], themes[i+1] = themes[i+1], themes[i]
                        st.session_state["form_generated_themes"] = themes
                        st.session_state.pop("preview_cache_key", None)
                        st.rerun()
                with ctrl_cols[2]:
                    if st.button("Remove", key=f"del_{i}"):
                        themes.pop(i)
                        st.session_state["form_generated_themes"] = themes
                        st.session_state.pop("preview_cache_key", None)
                        st.rerun()
                edited_themes.append({
                    "name": t_name.strip(),
                    "queries": [q.strip() for q in t_queries.split("\n") if q.strip()],
                })
            if st.button("Apply manual edits & refresh preview", key="apply_manual"):
                # Push edited themes back into the generated state so the preview re-scrapes
                valid = [t for t in edited_themes if t["name"] and t["queries"]]
                if valid:
                    st.session_state["form_generated_themes"] = valid
                    st.session_state.pop("preview_cache_key", None)
                    st.rerun()

        st.markdown("---")
        save_cols = st.columns([2, 2, 4])
        with save_cols[0]:
            do_save = st.button("Save tracker" if not existing else "Update tracker",
                                type="primary", key="save_tracker")
        with save_cols[1]:
            if st.button("Discard & start over", key="discard_preview"):
                for _k in ("form_generated_themes", "form_generated_title",
                           "form_generated_subtitle", "form_generated_anchor_terms",
                           "preview_cache_key", "preview_grouped", "preview_total"):
                    st.session_state.pop(_k, None)
                st.rerun()

        if do_save:
            # Source of truth for themes is whatever's in session_state (Claude's output
            # by default, or manual edits if the user applied them).
            themes_to_save = [
                {"name": t.get("name", "").strip(),
                 "queries": [q.strip() for q in t.get("queries", []) if q.strip()]}
                for t in st.session_state["form_generated_themes"]
                if t.get("name") and t.get("queries")
            ]
            if not themes_to_save:
                st.error("Need at least one theme with at least one query.")
                return

            if email.strip() and frequency != "none":
                email_subscription = {
                    "email": email.strip(),
                    "frequency": frequency,
                    "last_sent": (existing or {}).get("email_subscription", {}).get("last_sent")
                                  if existing else None,
                }
            else:
                email_subscription = None

            tracker_id = edit_id or make_tracker_id(name)
            config = {
                "id": tracker_id,
                "name": name.strip(),
                "industry_description": industry.strip(),
                "specifics": specifics.strip(),
                "other_description": other_description.strip(),
                "enabled_categories": enabled_categories,
                "title": gen_title.strip() or f"{name.strip()} Brief",
                "subtitle": gen_subtitle.strip(),
                "anchor_terms": st.session_state.get("form_generated_anchor_terms", []),
                "themes": themes_to_save,
                "lookback_days": int(lookback),
                "show_top_news": True,
                "show_download": True,
                "created_at": (existing or {}).get("created_at") or datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "email_subscription": email_subscription,
            }
            try:
                upsert_config(tracker_id, config)
            except Exception as e:
                st.error(f"Failed to save: {e}")
                return

            _clear_form_state()
            for _k in ("preview_cache_key", "preview_grouped", "preview_total"):
                st.session_state.pop(_k, None)
            st.success("Saved. Redirecting to your tracker...")
            st.query_params.clear()
            st.query_params.update({"id": tracker_id})
            st.rerun()

    render_footer()


# ---------- View ----------

def render_view(tracker_id: str):
    config = get_config(tracker_id)
    if not config:
        st.error(f"Tracker '{tracker_id}' not found.")
        if st.button("← Back to home"):
            st.query_params.clear()
            st.rerun()
        return

    title = config.get("title") or f"{config.get('name', 'News')} Brief"
    subtitle = config.get("subtitle", "")

    render_masthead(title, subtitle, compact=True)

    # Compact status strip — small inline summary, no big paragraph
    sub = config.get("email_subscription") or {}
    if sub:
        sub_status = (
            f"Email: <strong>{sub.get('email', '')}</strong> &middot; "
            f"{ {'weekly_monday': 'Weekly · Monday', 'weekly_friday': 'Weekly · Friday', 'daily': 'Daily'}.get(sub.get('frequency', ''), 'Off') }"
        )
    else:
        sub_status = "Email: <em>not set up</em>"
    st.markdown(
        f"<div style='color:{MID_GREY}; font-size:12px; margin-bottom:12px;'>"
        f"Lookback {config.get('lookback_days', 7)}d &middot; {len(config.get('themes', []))} themes &middot; {sub_status}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Top action row
    cols = st.columns([3, 1, 1, 1, 1])
    with cols[0]:
        go = st.button("Generate this week's brief", type="primary", key="generate")
    with cols[1]:
        if st.button("Edit", key="edit_btn"):
            _clear_form_state()
            st.query_params.clear()
            st.query_params.update({"page": "create", "id": tracker_id})
            st.rerun()
    with cols[2]:
        sub = config.get("email_subscription") or {}
        email_btn_label = "Manage email" if sub else "Email me"
        if st.button(email_btn_label, key="email_btn"):
            st.session_state["show_email_form"] = True
    with cols[3]:
        if st.button("Test email", key="test_email_btn", help="Send the current brief to your inbox now"):
            st.session_state["send_test_email"] = True
    with cols[4]:
        if st.button("← Home", key="home_btn"):
            st.query_params.clear()
            st.rerun()

    # Handle test-email click
    if st.session_state.get("send_test_email"):
        st.session_state["send_test_email"] = False
        sub = config.get("email_subscription") or {}
        recipient = sub.get("email", "")
        if not recipient:
            st.warning("Set up your email first via the 'Email me' button.")
        else:
            with st.spinner(f"Sending a test brief to {recipient}..."):
                grouped, total = scrape_for_config(config)
                theme_order = [t["name"] for t in config.get("themes", []) if t.get("name")]
                html = build_email_html(grouped, theme_order, total, config, unsubscribe_url=None)
                subject = f"[TEST] {title} — {datetime.now().strftime('%b %d, %Y')}"
                ok, info = send_email(recipient, subject, html)
            if ok:
                st.success(f"Sent. Check {recipient}.")
            else:
                st.error(f"Send failed: {info}")

    # Cache-bust on config change
    cfg_hash = config_hash(config)
    cache_key = f"results_{tracker_id}_{cfg_hash}"
    if st.session_state.get("last_cache_key") != cache_key:
        for k in list(st.session_state.keys()):
            if k.startswith("results_") or k == "has_results":
                del st.session_state[k]
        st.session_state["last_cache_key"] = cache_key

    # Email subscribe form
    if st.session_state.get("show_email_form"):
        with st.container():
            st.markdown(
                f"<div style='margin-top:16px; padding:18px; background:{ICE_BLUE}; border-radius:4px; border-left:4px solid {NAVY};'>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='color:{NAVY}; font-weight:700; font-size:14px; margin-bottom:8px;'>Email subscription</div>",
                unsafe_allow_html=True,
            )
            existing_sub = config.get("email_subscription") or {}
            if "sub_email" not in st.session_state:
                st.session_state["sub_email"] = existing_sub.get("email", "")
            sub_freq_options = ["weekly_monday", "weekly_friday", "daily"]
            if st.session_state.get("sub_freq") not in sub_freq_options:
                st.session_state["sub_freq"] = existing_sub.get("frequency", "weekly_monday")
            email = st.text_input(
                "Your email",
                placeholder="you@banneker.com",
                key="sub_email",
            )
            # Radio (not selectbox) — avoids browser autofilling email text into the dropdown.
            freq = st.radio(
                "Frequency",
                options=sub_freq_options,
                format_func=lambda v: {
                    "weekly_monday": "Weekly · Monday morning",
                    "weekly_friday": "Weekly · Friday morning",
                    "daily": "Daily · 6am UTC",
                }[v],
                key="sub_freq",
                horizontal=True,
            )
            cols = st.columns([1, 1, 4])
            with cols[0]:
                if st.button("Save", key="save_sub"):
                    if not email.strip():
                        st.error("Email required.")
                    else:
                        config["email_subscription"] = {
                            "email": email.strip(),
                            "frequency": freq,
                            "last_sent": None,
                        }
                        upsert_config(tracker_id, config)
                        st.session_state["show_email_form"] = False
                        st.success(f"Subscribed. First email lands per the frequency selected.")
                        st.rerun()
            with cols[1]:
                if existing_sub and st.button("Unsubscribe", key="unsub"):
                    config["email_subscription"] = None
                    upsert_config(tracker_id, config)
                    st.session_state["show_email_form"] = False
                    st.success("Unsubscribed.")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Generate / show results
    if go or st.session_state.get(f"has_results_{tracker_id}"):
        if go or cache_key not in st.session_state:
            with st.spinner("Pulling stories from Google News..."):
                grouped, total = scrape_for_config(config)
            st.session_state[cache_key] = (grouped, total)
            st.session_state[f"has_results_{tracker_id}"] = True
            st.session_state[f"generated_at_{tracker_id}"] = datetime.now()
        else:
            grouped, total = st.session_state[cache_key]

        generated = st.session_state[f"generated_at_{tracker_id}"]
        theme_order = [t["name"] for t in config["themes"] if t.get("name")]

        # Date callout
        st.markdown(
            f"""
            <div style='margin-top:24px; padding:18px 22px; background:{ICE_BLUE}; border-left:5px solid {NAVY}; border-radius:2px;'>
              <div style='color:{NAVY}; font-weight:800; font-size:22px; line-height:1.1; margin-bottom:4px;'>{generated.strftime('%B %d, %Y')}</div>
              <div style='color:{DARK_GREY}; font-size:12px; letter-spacing:0.5px; text-transform:uppercase; font-weight:600;'>
                Past {config.get('lookback_days', 7)} days &middot; {total} stories &middot; {len(theme_order)} themes &middot; Source: Google News RSS
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Top news card
        if config.get("show_top_news", True):
            top_picks = pick_top_stories(grouped, theme_order, n=4, lookback_days=config.get("lookback_days", 7))
            if top_picks:
                rows = []
                for i, (it, theme) in enumerate(top_picks, start=1):
                    date = it["published"].strftime("%b %d")
                    theme_short = theme.split(" (")[0]
                    src = (
                        f"<span style='color:rgba(255,255,255,0.6); font-style:italic; font-size:12px;'> &mdash; {it['source']}</span>"
                        if it["source"] else ""
                    )
                    rows.append(
                        f"<div style='margin-bottom:14px; line-height:1.5;'>"
                        f"<span style='color:{PERIWINKLE}; font-weight:800; font-size:13px; margin-right:8px;'>{i:02d}</span>"
                        f"<span style='color:rgba(255,255,255,0.6); font-size:11px; letter-spacing:0.8px; text-transform:uppercase; font-weight:600;'>{theme_short} &middot; {date}</span><br>"
                        f"<a href='{it['link']}' target='_blank' style='font-size:15.5px;'>{it['title']}</a>"
                        f"{src}"
                        f"</div>"
                    )
                st.markdown(
                    f"""
                    <div class='top-news-card' style='margin-top:22px; padding:22px 26px; background:{NAVY}; border-radius:4px;'>
                      <div style='color:{PERIWINKLE}; font-size:11px; letter-spacing:1.8px; text-transform:uppercase; font-weight:700; margin-bottom:14px;'>This week's top news</div>
                      {''.join(rows)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Download button
        if config.get("show_download", True):
            docx_bytes = build_docx_bytes(grouped, theme_order, total, config)
            st.download_button(
                label="Download as Word doc",
                data=docx_bytes,
                file_name=f"{tracker_id}_{generated.strftime('%Y-%m-%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # Themed sections
        for i, theme in enumerate(theme_order):
            items = grouped.get(theme, [])
            st.markdown(
                f"""
                <div style='margin:36px 0 14px 0;'>
                  <div style='color:{PERIWINKLE}; font-size:11px; font-weight:700; letter-spacing:1.8px; text-transform:uppercase; margin-bottom:2px;'>Section {i+1:02d}</div>
                  <h2 style='color:{NAVY}; font-weight:800; font-size:22px; margin:0 0 4px 0; line-height:1.2;'>{theme}</h2>
                  <div style='height:2px; background:{NAVY}; width:48px; margin-top:8px;'></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if not items:
                st.markdown(
                    f"<div style='color:{MID_GREY}; font-style:italic; font-size:13px; margin:8px 0;'>No news in the lookback window.</div>",
                    unsafe_allow_html=True,
                )
                continue
            story_rows = []
            for it in items:
                date = it["published"].strftime("%b %d")
                src = (
                    f" <span style='color:{MID_GREY}; font-style:italic; font-size:12px;'>&mdash; {it['source']}</span>"
                    if it["source"] else ""
                )
                story_rows.append(
                    f"<div style='margin-bottom:10px; line-height:1.45; color:{BODY_GREY}; font-size:14.5px;'>"
                    f"<span style='display:inline-block; min-width:56px; color:{NAVY}; font-weight:700; font-size:13px;'>{date}</span>"
                    f"<a href='{it['link']}' target='_blank' style='color:{NAVY};'>{it['title']}</a>"
                    f"{src}"
                    f"</div>"
                )
            st.markdown("".join(story_rows), unsafe_allow_html=True)

    render_footer()


# ---------- Router ----------

params = st.query_params
page = params.get("page", "")
tracker_id = params.get("id", "")
action = params.get("action", "")
edit_mode = params.get("edit", "") == "1" or (page == "create" and tracker_id)

# Handle one-click unsubscribe from email footer link
if tracker_id and action == "unsubscribe":
    cfg = get_config(tracker_id)
    if cfg:
        old_email = (cfg.get("email_subscription") or {}).get("email", "")
        cfg["email_subscription"] = None
        try:
            upsert_config(tracker_id, cfg)
            render_masthead(cfg.get("title") or "Unsubscribed")
            st.success(f"Unsubscribed {old_email or 'this address'} from {cfg.get('name', 'this tracker')}. You can resubscribe anytime by visiting your tracker and clicking 'Email me'.")
            st.markdown(f"[Open this tracker](?id={tracker_id})")
        except Exception as e:
            st.error(f"Failed to unsubscribe: {e}")
        render_footer()
    else:
        st.error(f"Tracker '{tracker_id}' not found.")
    st.stop()

if page == "create":
    render_create(edit_id=tracker_id if edit_mode else None)
elif tracker_id:
    render_view(tracker_id)
else:
    render_home()
