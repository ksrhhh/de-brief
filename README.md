# Debate Briefing Pipeline

Automated daily + weekly BP debate briefings, emailed to you and archived
in this repo.

## How it works

```
GitHub Actions (cron)
  → fetch.py        pulls all RSS feeds in sources.yaml, writes raw_stories.json
  → synthesize.py   sends raw stories to Claude API, gets back a debate-framed
                     briefing (background, clash, motions, underlying principle)
  → send_email.py   emails the briefing via Resend
  → commits the briefing .md file into briefings/ for permanent archive
```

Daily runs pull the last 24 hours; weekly pulls the last 7 days and asks Claude
to synthesize across the whole week rather than just listing more stories.

## ⚠️ Important: what's verified and what isn't yet

I built and tested this pipeline's logic, but **I could not run a live end-to-end
test against the real news feeds** — the sandbox I built this in only has network
access to developer package registries (pypi, npm, GitHub), not general websites.
I confirmed the BBC feed URL is correct and returns real, current articles by
fetching it through a different tool, but I could not test the others
(Economist, FT, WSJ, NYT, Bloomberg, CFR, Seeking Alpha, SCOTUSblog, UN) the same
way before you deploy this.

**This is not a blocker** — GitHub Actions runners have normal, unrestricted
internet access, so the pipeline will work once it's actually running there.
But it does mean: **the first real run is also the first real test.** A few
feed URLs in `sources.yaml` are marked with `notes:` saying "verify exact path
on first run" — these are the ones most likely to have shifted (Bloomberg, WSJ,
Seeking Alpha, CFR all rotate their feed paths periodically). If a source comes
back with 0 stories repeatedly, check the Actions log for that source's `[WARN]`
line, then search "`<source name>` rss feed url 2026" to find the current path
and update `sources.yaml` — no code changes needed, just edit the URL.

I'd recommend running the daily workflow manually (via "Run workflow" in the
Actions tab — see below) once after setup, checking the output, and fixing any
dead feed URLs before turning on the schedule for real.

## Setup steps

### 1. Create the GitHub repo

Create a new repo (can be private) and push these files to it.

### 2. Get an Anthropic API key

Go to [console.anthropic.com](https://console.anthropic.com), create an API
key, and add a small balance (a few dollars covers months of daily + weekly
runs — each run is one API call with a few thousand tokens of input).

### 3. Set up Resend

1. Sign up at [resend.com](https://resend.com) (free tier: 100 emails/day, 3,000/month — far more than you need)
2. **Verify a sending domain.** This is the one part of setup that isn't pure
   copy-paste: Resend requires you to add a few DNS records (TXT/MX) to a
   domain you control to prove you own it, so your emails don't land in spam.
   - If you own a personal domain already, use a subdomain like
     `briefing.yourdomain.com`.
   - If you don't own a domain, Resend's own docs cover registering a cheap
     one (often <$15/year) — see
     [resend.com/docs/dashboard/domains/introduction](https://resend.com/docs/dashboard/domains/introduction).
3. Get your Resend API key from the dashboard.

### 4. Add GitHub repo secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add all of these:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | from console.anthropic.com |
| `RESEND_API_KEY` | from resend.com dashboard |
| `BRIEFING_FROM_EMAIL` | e.g. `briefing@briefing.yourdomain.com` (must match your verified domain) |
| `BRIEFING_TO_EMAIL` | your real inbox |

### 5. Adjust the schedule (optional)

The cron times in `.github/workflows/daily.yml` and `weekly.yml` are in UTC.
`0 6 * * *` means 6:00 AM UTC daily. To convert to your local time, search
"6am UTC to [your timezone]" — or just pick a UTC hour that lands wherever you
want it locally and accept it'll shift by an hour around daylight saving.

### 6. Test it manually before trusting the schedule

Go to the **Actions** tab in your repo → select "Daily Debate Briefing" →
**Run workflow** → Run. Watch the log. Check:
- Did most sources return stories (not all `[WARN] 0 entries`)?
- Did synthesize.py produce reasonable output? (check the committed file under `briefings/`)
- Did the email actually arrive?

Fix any dead feed URLs in `sources.yaml` (see note above), commit, and re-run
until it looks right. Then trust the schedule.

## Editing sources later

Just edit `sources.yaml` — add, remove, or fix a `feed_url` line. No code
changes needed for ordinary source-list maintenance. The `access` field
(`full` / `teaser` / `summary`) just tells the system how much depth to expect
from that source; it doesn't change fetch behavior, only documents what's
realistic from each one.

## On Economist paywall access

You have a personal Economist subscription, but the automated pipeline runs
headlessly (no browser, no your-login-cookie) and can't authenticate as you —
Economist's paywall is also fairly bot-resistant, so even attempting
session-cookie automation would be fragile and likely break often. Practical
upshot: the briefing will flag Economist stories using the free teaser/headline
only. When a flagged item looks high-value, click through yourself on your
phone/browser where you're already logged in for the full piece.

## Cost estimate

- **Anthropic API:** ~$0.01–0.05 per daily run, similar for weekly (varies with
  story volume) → well under $5/month total.
- **Resend:** free tier covers this easily (1 email/day + 1/week ≈ 35/month vs.
  3,000/month free allowance).
- **GitHub Actions:** free tier covers this easily (2 short runs/week vs.
  2,000 free minutes/month for private repos, unlimited for public).
- **Domain (if needed for Resend):** ~$10-15/year, one-time-ish setup cost.

## Files

```
sources.yaml          — edit this to add/remove/fix sources
fetch.py               — pulls RSS feeds, no API calls, no API key needed
synthesize.py          — calls Claude API, contains the debate-framing prompt
send_email.py          — calls Resend API
requirements.txt       — Python deps
.github/workflows/
  daily.yml            — cron + manual trigger for daily briefing
  weekly.yml           — cron + manual trigger for weekly deep dive
briefings/             — auto-committed archive, one .md file per run
```
