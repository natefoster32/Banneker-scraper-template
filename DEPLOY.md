# Banneker Scraper Template — Deploy Guide

End state: One Streamlit app at `banneker-news.streamlit.app` where any Banneker coworker can self-serve their own personalized news tracker in ~4 min. Optional weekly/daily email delivery. All free. Hosted on your accounts.

## What I (Claude) already did

- ✅ Built the full multi-tenant app
- ✅ Created this clean folder at `C:\Claude Test\Banneker-scraper-template\`
- ✅ Initialized a fresh git repo
- ✅ Made the initial commit
- ✅ Verified Python syntax across all files

## What's left for you (~20 min, 4 websites)

Five steps. Direct links provided. Paste the values back to me as you go and I'll keep things moving.

---

### Step 1 — Create the GitHub repo (30 seconds)

Click this link (pre-fills name + description):

**https://github.com/new?name=Banneker-scraper-template&visibility=public&description=Multi-tenant+news+tracker+template+for+Banneker+portco+briefs**

- Don't tick any "Initialize" checkboxes (no README, no .gitignore, no license)
- Click **Create repository**
- Tell me "done" — I'll push the code

---

### Step 2 — Create the Gist that holds all tracker configs (2 minutes)

This is the single source of truth for every coworker's tracker. One Gist, JSON file inside it, all configs go there.

Click here: **https://gist.github.com**

- **Filename:** `trackers.json`
- **Content:** `{}` (literally just an empty JSON object — two curly braces)
- Click **Create secret gist**
- Copy the **Gist ID** from the URL — looks like `https://gist.github.com/natefoster32/<this_long_hex_string>`
- Paste the Gist ID back to me

---

### Step 3 — Create a GitHub Personal Access Token (3 minutes)

The Streamlit app and GitHub Actions both need this to read/write the Gist.

Click here for a pre-scoped token form:

**https://github.com/settings/tokens/new?scopes=gist&description=Banneker+scraper+template+gist**

- Expiration: **1 year** (set a calendar reminder to rotate)
- Click **Generate token**
- Copy the token (starts with `ghp_...`)
- Paste the token back to me — I'll only use it to confirm things work; I won't ever store it

---

### Step 3b — Get an Anthropic API key (3 minutes)

Used to translate natural-language descriptions into themes + Google News queries. Costs ~$0.01-0.03 per tracker creation. A $5 minimum credit lasts essentially forever for this use case (~3,000 tracker creations).

1. Go to **https://console.anthropic.com/settings/keys**
2. Sign in (or sign up) with your Banneker email
3. Click **Create Key** → name `banneker-scraper-template` → copy (starts with `sk-ant-...`)
4. Go to **Billing** → add $5 credit (one-time, prepaid)
5. Paste the API key back to me

---

### Step 4 — Sign up for Resend for email delivery (5 minutes)

Free tier: 3,000 emails/month. No credit card.

1. Go to **https://resend.com/signup**
2. Sign up with your Banneker email
3. For testing immediately, **skip domain verification** — you'll use the built-in `onboarding@resend.dev` as the sender
4. Go to **API Keys** → **Create API Key** → name `banneker-scraper` → permission **Full access** → copy (starts with `re_...`)
5. Paste the API key back to me

(You can add a custom domain like `brief@banneker.com` later — adds 5 min and 3 DNS records.)

---

### Step 5 — Deploy to Streamlit Community Cloud (5 minutes)

After you've completed Steps 1-4 and I've pushed the code, click this link to deploy:

**https://share.streamlit.io/deploy?repository=natefoster32/Banneker-scraper-template&branch=main&mainModule=app.py**

- Sign in with GitHub if prompted
- Verify the form: repo `natefoster32/Banneker-scraper-template`, branch `main`, file `app.py`
- **Custom subdomain:** `banneker-news` (URL becomes `banneker-news.streamlit.app`). If taken, try `banneker-intel` or similar
- Click **Deploy**
- While it builds (~2 min), click **Settings → Secrets** in the Streamlit dashboard, paste this (with your actual values), and save:

   ```toml
   GITHUB_GIST_ID = "paste_your_gist_id"
   GITHUB_PAT = "paste_your_pat"
   RESEND_API_KEY = "paste_your_resend_key"
   RESEND_FROM = "Banneker Brief <onboarding@resend.dev>"
   ANTHROPIC_API_KEY = "paste_your_anthropic_key"
   ```

- Once deployed, paste the live URL back to me

---

### Step 6 (optional) — Wire up the email cron (3 minutes)

If you want weekly emails to actually fire on schedule, the GitHub Actions workflow needs the same secrets.

1. Go to your repo on github.com → **Settings → Secrets and variables → Actions → New repository secret**
2. Add these 5:

   | Name | Value |
   |---|---|
   | `GIST_ID` | your Gist ID |
   | `GIST_PAT` | your GitHub PAT |
   | `RESEND_API_KEY` | your Resend key |
   | `RESEND_FROM` | `Banneker Brief <onboarding@resend.dev>` |
   | `APP_BASE_URL` | `https://banneker-news.streamlit.app` |

3. Workflow is preconfigured to run daily at 11:00 UTC. To test it manually, go to **Actions → Send daily news briefs → Run workflow**

---

## After all steps are done

1. Open `https://banneker-news.streamlit.app` — should show the home page with "Create a new tracker"
2. Click Create → pick **Cybersecurity portco** template → name it "Industrial Defender Weekly Brief" → save
3. Copy the resulting URL → send to Bryan
4. Tell Banneker team: "go to banneker-news.streamlit.app, click Create, pick a template, you'll have your own tracker in 4 min"

---

## Troubleshooting

- **"GITHUB_GIST_ID is not set" error on the live app:** Streamlit Secrets didn't save or app hasn't redeployed. Settings → Secrets → re-save → wait 30 seconds.
- **Gist API 404:** Wrong Gist ID, or PAT missing `gist` scope.
- **Resend 422:** From-address isn't verified. Use `onboarding@resend.dev` until you do domain verification.
- **Cron run silent:** Check Actions log. Most common cause: no tracker has an active email subscription yet, or today's weekday doesn't match the frequency.
