# Toronto Ferry Schedule Scraper

Scrapes the City of Toronto's ferry schedule page daily and publishes the
result as JSON, for the iOS app to fetch.

## Setup

1. Create a new GitHub repository and push this folder's contents to it.
2. Repo → Settings → Secrets and variables → Actions → add these secrets:
   - `MAIL_USERNAME` — a Gmail address to send failure alerts from
   - `MAIL_PASSWORD` — a Gmail **App Password** (not your normal password).
     Requires 2-factor auth enabled on the Google account, then generate one
     at https://myaccount.google.com/apppasswords
   - `ALERT_EMAIL` — where the failure alert should be sent (can be the same
     address as `MAIL_USERNAME`)
3. That's it — the workflow in `.github/workflows/update-schedule.yml` runs
   automatically every day at 9:00 UTC, and can also be triggered manually
   from the repo's **Actions** tab ("Run workflow").

## What it does

- `scrape_ferry_schedule.py` fetches the schedule page, parses the three
  route tables (Centre Island, Hanlan's Point, Ward's Island), and writes
  `data/ferry-schedule.json`.
- If parsing fails for any reason (network error, unexpected page structure,
  missing data), the script exits with a non-zero status.
- The workflow detects that failure and emails you via
  `dawidd6/action-send-mail`, linking directly to the failed run's log.
- On success, the updated JSON is committed back to the repo automatically.

## Consuming the data

Once pushed, the JSON is available at:

```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO_NAME/main/data/ferry-schedule.json
```

Update `ScheduleService.swift` in the iOS app with your actual username/repo
name at that URL.

## If the scrape starts failing

The most likely cause is the City of Toronto changing the page's HTML
structure (different heading tags, table layout, etc.). Check the failed
workflow run's log for the specific error, then adjust
`scrape_ferry_schedule.py` accordingly — the `DESTINATIONS` list and
`parse_schedule()` function are the places to look first.
