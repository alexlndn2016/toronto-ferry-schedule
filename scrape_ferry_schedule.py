#!/usr/bin/env python3
"""
Scrapes the City of Toronto ferry schedule page and writes structured JSON
to data/ferry-schedule.json.

Exits with a non-zero status on any failure (network error, unexpected page
structure, missing data) so the calling GitHub Actions workflow can detect
the failure and send an email alert.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

URL = "https://www.toronto.ca/explore-enjoy/toronto-island-ferries/ferry-routes-schedules/"
OUTPUT_PATH = "data/ferry-schedule.json"

# Matched against page headings; curly and straight apostrophes both handled.
DESTINATIONS = ["Centre Island", "Hanlan's Point", "Ward's Island"]


def normalize_time(raw: str) -> str:
    """Converts strings like '8:00 a.m.', '12:20 p.m.**', or 'Noon' into 24-hour HH:MM."""
    raw = raw.strip().replace("*", "").strip()

    if raw.lower() == "noon":
        return "12:00"
    if raw.lower() == "midnight":
        return "00:00"

    cleaned = raw.lower().replace(".", "").replace(" ", "")
    match = re.match(r"^(\d{1,2}):(\d{2})(am|pm)$", cleaned)
    if not match:
        raise ValueError(f"Unrecognized time format: {raw!r}")

    hour, minute, period = match.groups()
    dt = datetime.strptime(f"{hour}:{minute} {period.upper()}", "%I:%M %p")
    return dt.strftime("%H:%M")


def normalize_apostrophes(text: str) -> str:
    return text.replace("\u2019", "'").replace("\u2018", "'")


def parse_schedule(html: str):
    soup = BeautifulSoup(html, "html.parser")
    routes = []

    for heading in soup.find_all(["h2", "h3"]):
        heading_text = normalize_apostrophes(heading.get_text(strip=True))

        matched_destination = next(
            (dest for dest in DESTINATIONS if dest in heading_text), None
        )
        if not matched_destination:
            continue

        table = heading.find_next("table")
        if table is None:
            raise ValueError(f"No table found after heading '{heading_text}'")

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
            departs_city.append(normalize_time(city_raw))
            departs_island.append(normalize_time(island_raw))

        if not departs_city or not departs_island:
            raise ValueError(f"No departure times parsed for {matched_destination}")

        routes.append(
            {
                "destination": matched_destination,
                "departsCity": departs_city,
                "departsIsland": departs_island,
            }
        )

    if len(routes) != len(DESTINATIONS):
        raise ValueError(
            f"Expected {len(DESTINATIONS)} routes, found {len(routes)}. "
            "The page structure may have changed — check the scraper."
        )

    return routes


def main():
    response = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; FerryScheduleBot/1.0)"},
    )
    response.raise_for_status()

    routes = parse_schedule(response.text)

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "routes": routes,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(routes)} routes to {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
