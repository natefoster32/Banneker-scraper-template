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
from email_sender import send_email
from storage import delete_config, get_config, load_all_configs, upsert_config
from templates import TEMPLATES, get_template, get_template_names

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
  html, body, [class*="css"], [class*="st-"] {{
    font-family: Inter, Calibri, "Segoe UI", Arial, sans-serif !important;
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


def render_masthead(title: str, subtitle: str = ""):
    sub_html = (
        f"<div style='color:{PERIWINKLE}; font-weight:700; font-size:13px; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:14px;'>{subtitle}</div>"
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div style='border-top:4px solid {NAVY}; padding-top:18px; margin-bottom:8px;'></div>
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

def _init_form_state(template_name: str | None = None, existing_config: dict | None = None):
    if existing_config:
        st.session_state["form_themes"] = existing_config.get("themes", [])
        st.session_state["form_name"] = existing_config.get("name", "")
        st.session_state["form_subtitle"] = existing_config.get("subtitle", "")
        st.session_state["form_title"] = existing_config.get("title", "")
        st.session_state["form_lookback"] = existing_config.get("lookback_days", 7)
        st.session_state["form_show_top_news"] = existing_config.get("show_top_news", True)
        st.session_state["form_show_download"] = existing_config.get("show_download", True)
        return
    if template_name:
        tmpl = get_template(template_name)
        st.session_state["form_themes"] = [
            {"name": t["name"], "queries": list(t["queries"])} for t in tmpl["themes"]
        ]
    else:
        st.session_state.setdefault("form_themes", [{"name": "", "queries": []}])
    st.session_state.setdefault("form_name", "")
    st.session_state.setdefault("form_subtitle", "Banneker Partners · Market Intel")
    st.session_state.setdefault("form_title", "")
    st.session_state.setdefault("form_lookback", 7)
    st.session_state.setdefault("form_show_top_news", True)
    st.session_state.setdefault("form_show_download", True)


def render_create(edit_id: str | None = None):
    existing = get_config(edit_id) if edit_id else None
    title_text = "Edit tracker" if existing else "Create your tracker"
    render_masthead(title_text)

    # Initialize form state
    if "form_themes" not in st.session_state:
        if existing:
            _init_form_state(existing_config=existing)
        else:
            _init_form_state(template_name="Cybersecurity portco")

    # Template picker (only on create, not edit)
    if not existing:
        st.markdown(
            f"<div style='color:{BODY_GREY}; font-size:14px; margin-bottom:8px;'>"
            "Pick a starter template, then edit themes and queries to fit your portco."
            "</div>",
            unsafe_allow_html=True,
        )
        template_names = get_template_names()
        chosen = st.selectbox(
            "Starter template",
            options=template_names,
            index=0,
            help="Loads pre-filled themes and queries. You'll edit them next.",
            key="template_picker",
        )
        if st.button("Load template", key="load_tmpl"):
            _init_form_state(template_name=chosen)
            st.rerun()
        st.markdown(
            f"<div style='color:{MID_GREY}; font-size:12px; font-style:italic; margin-bottom:24px;'>"
            f"{TEMPLATES.get(chosen, {}).get('description', '')}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

    # Basics
    st.markdown(f"<h3 style='color:{NAVY}; margin-bottom:8px;'>Basics</h3>", unsafe_allow_html=True)
    name = st.text_input(
        "Tracker name *",
        value=st.session_state.get("form_name", ""),
        placeholder="e.g., Industrial Defender weekly brief",
        key="form_name",
    )
    title_field = st.text_input(
        "Brief title (shown at top of the brief)",
        value=st.session_state.get("form_title", ""),
        placeholder="Defaults to '[Tracker Name] Brief'",
        key="form_title",
    )
    subtitle = st.text_input(
        "Subtitle / tagline",
        value=st.session_state.get("form_subtitle", ""),
        placeholder="e.g., Banneker Partners · OT cybersecurity market intel",
        key="form_subtitle",
    )

    cols = st.columns(3)
    with cols[0]:
        lookback = st.selectbox(
            "Lookback window",
            options=[3, 7, 14, 30],
            index=[3, 7, 14, 30].index(st.session_state.get("form_lookback", 7)),
            format_func=lambda d: f"Past {d} days",
            key="form_lookback",
        )
    with cols[1]:
        show_top = st.checkbox(
            "Show top-news card",
            value=st.session_state.get("form_show_top_news", True),
            key="form_show_top_news",
        )
    with cols[2]:
        show_dl = st.checkbox(
            "Show Word download",
            value=st.session_state.get("form_show_download", True),
            key="form_show_download",
        )

    # Themes editor
    st.markdown(f"<h3 style='color:{NAVY}; margin-top:32px; margin-bottom:8px;'>Themes &amp; queries</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{BODY_GREY}; font-size:13px; margin-bottom:16px;'>"
        "Each theme becomes a section in your brief. Queries within a theme are run against Google News "
        "RSS. Be specific (e.g., 'NIS2 directive', not 'cybersecurity rules'). 3-10 queries per theme works "
        "well; more queries = wider coverage but slower scrape."
        "</div>",
        unsafe_allow_html=True,
    )

    themes = st.session_state["form_themes"]
    new_themes = []
    for i, theme in enumerate(themes):
        with st.container():
            st.markdown(
                f"<div style='background:{ICE_BLUE}; padding:14px 16px; border-radius:4px; margin-bottom:6px; border-left:4px solid {NAVY};'>"
                f"<div style='color:{NAVY}; font-weight:700; font-size:12px; letter-spacing:1.2px; text-transform:uppercase;'>Theme {i+1:02d}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            theme_name = st.text_input(
                f"Theme name",
                value=theme.get("name", ""),
                placeholder="e.g., Breaches & incidents",
                key=f"theme_name_{i}",
            )
            queries_text = "\n".join(theme.get("queries", []))
            queries_input = st.text_area(
                f"Queries (one per line)",
                value=queries_text,
                placeholder="e.g.\nNIS2 directive\nCyber Resilience Act\nDORA cybersecurity",
                key=f"theme_queries_{i}",
                height=120,
            )
            cols = st.columns([1, 1, 6])
            with cols[0]:
                if st.button("↑", key=f"up_{i}", help="Move up", disabled=(i == 0)):
                    themes[i], themes[i-1] = themes[i-1], themes[i]
                    st.session_state["form_themes"] = themes
                    st.rerun()
            with cols[1]:
                if st.button("↓", key=f"down_{i}", help="Move down", disabled=(i == len(themes) - 1)):
                    themes[i], themes[i+1] = themes[i+1], themes[i]
                    st.session_state["form_themes"] = themes
                    st.rerun()
            with cols[2]:
                if st.button("Remove this theme", key=f"del_{i}"):
                    themes.pop(i)
                    st.session_state["form_themes"] = themes
                    st.rerun()

            new_themes.append({
                "name": theme_name.strip(),
                "queries": [q.strip() for q in queries_input.split("\n") if q.strip()],
            })

    if st.button("+ Add another theme", key="add_theme"):
        themes.append({"name": "", "queries": []})
        st.session_state["form_themes"] = themes
        st.rerun()

    # Save
    st.markdown("---")
    if st.button("Save tracker" if not existing else "Update tracker", type="primary", key="save_tracker"):
        if not name.strip():
            st.error("Tracker name is required.")
            return
        valid_themes = [t for t in new_themes if t["name"] and t["queries"]]
        if not valid_themes:
            st.error("Add at least one theme with at least one query.")
            return

        tracker_id = edit_id or make_tracker_id(name)
        config = {
            "id": tracker_id,
            "name": name.strip(),
            "title": title_field.strip() or f"{name.strip()} Brief",
            "subtitle": subtitle.strip(),
            "themes": valid_themes,
            "lookback_days": int(lookback),
            "show_top_news": bool(show_top),
            "show_download": bool(show_dl),
            "created_at": (existing or {}).get("created_at") or datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "email_subscription": (existing or {}).get("email_subscription"),
        }
        try:
            upsert_config(tracker_id, config)
        except Exception as e:
            st.error(f"Failed to save: {e}")
            return

        # Clear form state
        for k in [
            "form_themes", "form_name", "form_subtitle", "form_title",
            "form_lookback", "form_show_top_news", "form_show_download",
        ]:
            st.session_state.pop(k, None)

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

    render_masthead(title, subtitle)

    st.markdown(
        f"<div style='color:{BODY_GREY}; font-size:14px; line-height:1.5; margin-bottom:20px; max-width:640px;'>"
        f"Click the button to pull the last {config.get('lookback_days', 7)} days of news across "
        f"{len(config.get('themes', []))} themes. Fresh every click."
        f"</div>",
        unsafe_allow_html=True,
    )

    # Top action row
    cols = st.columns([3, 1, 1, 1])
    with cols[0]:
        go = st.button("Generate this week's brief", type="primary", key="generate")
    with cols[1]:
        if st.button("Edit", key="edit_btn"):
            st.query_params.clear()
            st.query_params.update({"page": "create", "id": tracker_id})
            st.rerun()
    with cols[2]:
        if st.button("Email me", key="email_btn"):
            st.session_state["show_email_form"] = True
    with cols[3]:
        if st.button("← Home", key="home_btn"):
            st.query_params.clear()
            st.rerun()

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
            email = st.text_input(
                "Your email",
                value=existing_sub.get("email", ""),
                placeholder="you@banneker.com",
                key="sub_email",
            )
            freq = st.selectbox(
                "Frequency",
                options=["weekly_monday", "weekly_friday", "daily"],
                index=["weekly_monday", "weekly_friday", "daily"].index(
                    existing_sub.get("frequency", "weekly_monday")
                ),
                format_func=lambda v: {
                    "weekly_monday": "Weekly · Monday morning",
                    "weekly_friday": "Weekly · Friday morning",
                    "daily": "Daily · 6am UTC",
                }[v],
                key="sub_freq",
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
edit_mode = params.get("edit", "") == "1" or (page == "create" and tracker_id)

if page == "create":
    render_create(edit_id=tracker_id if edit_mode else None)
elif tracker_id:
    render_view(tracker_id)
else:
    render_home()
