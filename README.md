# Toronto Ferry Schedule Scraper

Scrapes the City of Toronto's ferry schedule page daily and publishes the
result as JSON, for the app to fetch.

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

Once pushed, the JSON is available at: main/data/ferry-schedule.json