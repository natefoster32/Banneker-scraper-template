# Banneker Scraper Template

Multi-tenant Streamlit app where any Banneker coworker can spin up a personalized news brief for their portco, deal, or vertical in ~4 minutes. Optional weekly/daily email delivery via Resend. Hosted on Streamlit Community Cloud, $0 to operate.

**Live:** https://banneker-news.streamlit.app (once deployed)

## How it works

- Coworker visits the URL, clicks **Create a new tracker**
- Picks a portco template (Cyber / Healthcare / Fintech / Vertical SaaS / Industrials / Climate) or Blank
- Edits themes and queries to match their actual focus
- Saves → gets a bookmarkable URL
- Optional: clicks **Email me** → enters email + frequency (daily / weekly Monday / weekly Friday) → cron sends it

All configs live in a shared GitHub Gist (`trackers.json`). The Streamlit app and the cron worker both read/write the Gist via a Personal Access Token in Streamlit Secrets and GitHub Actions secrets.

## Architecture

| File | Role |
|---|---|
| `app.py` | Streamlit UI — home, create form, view page, email subscription UI |
| `core.py` | Scraping (Google News RSS), news filter, ranking, DOCX export, email HTML |
| `storage.py` | Gist read/write for tracker configs |
| `templates.py` | 6 portco starter templates + Blank |
| `email_sender.py` | Resend API wrapper |
| `scripts/send_emails.py` | Daily cron worker |
| `.github/workflows/send_emails.yml` | Runs cron at 11:00 UTC daily |

## Setup

See [DEPLOY.md](DEPLOY.md). ~20 minutes one-time across 4 websites.

## Run locally

```bash
pip install -r requirements.txt
# Create .streamlit/secrets.toml with the 4 required secrets
streamlit run app.py
```

## Cost

$0/month indefinitely on free tiers:

- Streamlit Community Cloud (unlimited apps)
- GitHub (Gists, Actions, repo)
- Resend (3,000 emails/month free)

If you ever outgrow free tiers, ~$40/mo for Streamlit Teams + Resend Pro covers significant scale.
