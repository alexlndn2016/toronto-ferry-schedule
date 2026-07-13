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

- `scrape_ferry_schedule.py` fetches the schedule page, parses each route
  table (Centre Island, Hanlan's Point, Ward's Island — though not all three
  necessarily run year-round; see below), and writes `data/ferry-schedule.json`.
- **Peak-only trips**: times marked `**` on the page (which the site's own
  footnote defines as running "on weekends and holidays") are tagged with a
  `peakOnly: true` flag per time entry, rather than silently treated as a
  regular trip.
- **Holidays**: Ontario statutory holidays for the current and next year are
  computed automatically via the Python `holidays` package and embedded in
  the JSON as a `holidays` array — no manual list to maintain, and it stays
  correct year to year without code changes.
- **Seasonal route changes**: the City runs a Summer schedule (3 routes), a
  reduced Fall schedule, and a Winter schedule (Ward's Island only). The
  scraper does NOT require exactly 3 routes to succeed — it accepts however
  many route sections it actually finds, and only fails if it finds zero.
- If parsing fails entirely (network error, unexpected page structure, no
  routes found), the script exits with a non-zero status.
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

The app determines "is today a peak day" itself (weekend or a date present
in the `holidays` array) via `PeakDayChecker.swift`, and only includes
`peakOnly` times on days that qualify. This check is re-applied locally
(no network call) once a minute, so it stays correct even if the app is left
open across a midnight boundary.

## If the scrape starts failing

The most likely cause is the City of Toronto changing the page's HTML
structure (different heading tags, table layout, etc.). Check the failed
workflow run's log for the specific error, then adjust
`scrape_ferry_schedule.py` accordingly — the `DESTINATIONS` list and
`parse_schedule()` function are the places to look first.
