#!/usr/bin/env python3
"""
Scrapes the City of Toronto ferry schedule page and writes structured JSON
to data/ferry-schedule.json.

Handles:
- Peak-only ("**") times: these run on weekends and statutory holidays only.
  Each departure time is tagged with a `peakOnly` flag instead of being
  silently merged into the regular schedule.
- Multiple seasons: the site runs a Summer schedule (3 routes), a reduced
  Fall schedule, and a Winter schedule (Ward's Island only). Route count is
  NOT hard-validated at exactly 3 anymore, since that would incorrectly fail
  every day once Fall/Winter schedules take effect.
- Ontario statutory holidays are computed automatically via the `holidays`
  package (no manual list to maintain) for the current and next year, so the
  app can determine "is today a peak day" without needing its own calendar.

Exits with a non-zero status on any failure (network error, zero routes
found, missing data) so the calling GitHub Actions workflow can detect the
failure and send an email alert.
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone

import holidays
import requests
from bs4 import BeautifulSoup

URL = "https://www.toronto.ca/explore-enjoy/toronto-island-ferries/ferry-routes-schedules/"
OUTPUT_PATH = "data/ferry-schedule.json"

# Matched against page headings; curly and straight apostrophes both handled.
KNOWN_DESTINATIONS = ["Centre Island", "Hanlan's Point", "Ward's Island"]


def normalize_apostrophes(text: str) -> str:
    return text.replace("\u2019", "'").replace("\u2018", "'")


def parse_time_cell(raw: str):
    """
    Returns (time_24h, is_peak_only) for a single schedule cell.
    Peak-only trips are marked with a trailing "**" on the page, meaning
    "weekends and holidays" per the page's own footnote text.
    """
    is_peak_only = "**" in raw
    cleaned = raw.replace("*", "").strip()

    if cleaned.lower() == "noon":
        return "12:00", is_peak_only
    if cleaned.lower() == "midnight":
        return "00:00", is_peak_only

    normalized = cleaned.lower().replace(".", "").replace(" ", "")
    match = re.match(r"^(\d{1,2}):(\d{2})(am|pm)$", normalized)
    if not match:
        raise ValueError(f"Unrecognized time format: {raw!r}")

    hour, minute, period = match.groups()
    dt = datetime.strptime(f"{hour}:{minute} {period.upper()}", "%I:%M %p")
    return dt.strftime("%H:%M"), is_peak_only


def parse_schedule_label(soup: BeautifulSoup):
    """Best-effort grab of the season heading, e.g. 'Summer Schedule: May 13 to September 15'."""
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True)
        if "schedule" in text.lower() and any(c.isdigit() for c in text):
            return text
    return None


def parse_routes(soup: BeautifulSoup):
    routes = []
    found_destinations = []

    for heading in soup.find_all(["h2", "h3"]):
        heading_text = normalize_apostrophes(heading.get_text(strip=True))

        matched_destination = next(
            (dest for dest in KNOWN_DESTINATIONS if dest in heading_text), None
        )
        if not matched_destination:
            continue

        table = heading.find_next("table")
        if table is None:
            continue  # heading without a table right after it — not a route section

        departs_city = []
        departs_island = []

        rows = table.find_all("tr")
        for row in rows[1:]:  # skip header row
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            city_raw = cells[0].get_text(strip=True)
            island_raw = cells[1].get_text(strip=True)
            if not city_raw or not island_raw:
                continue

            city_time, city_peak = parse_time_cell(city_raw)
            island_time, island_peak = parse_time_cell(island_raw)
            departs_city.append({"time": city_time, "peakOnly": city_peak})
            departs_island.append({"time": island_time, "peakOnly": island_peak})

        if not departs_city or not departs_island:
            raise ValueError(f"No departure times parsed for {matched_destination}")

        routes.append(
            {
                "destination": matched_destination,
                "departsCity": departs_city,
                "departsIsland": departs_island,
            }
        )
        found_destinations.append(matched_destination)

    if not routes:
        raise ValueError(
            "No routes parsed at all. The page structure may have changed — check the scraper."
        )

    missing = [d for d in KNOWN_DESTINATIONS if d not in found_destinations]
    if missing:
        # Not a failure — this is expected during Fall/Winter when fewer
        # routes run (e.g. Winter only runs Ward's Island).
        print(f"Note: no section found for {missing} (expected if a reduced seasonal schedule is active)")

    return routes


def compute_ontario_holidays():
    """Ontario statutory holidays for this year and next, as ISO date strings."""
    current_year = date.today().year
    on_holidays = holidays.Canada(prov="ON", years=[current_year, current_year + 1])
    return sorted(d.isoformat() for d in on_holidays.keys())


def main():
    response = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; FerryScheduleBot/1.0)"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    routes = parse_routes(soup)
    schedule_label = parse_schedule_label(soup)

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scheduleLabel": schedule_label,
        "holidays": compute_ontario_holidays(),
        "routes": routes,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(routes)} route(s) to {OUTPUT_PATH} (schedule: {schedule_label!r})")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
