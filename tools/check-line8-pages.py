#!/usr/bin/env python3
"""Regression: line 8 loop stop highlight, passenger directions, popup stop data."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def json_file(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

detail = json_file("data/trips/008.json")
line = json_file("data/rozklady/linie/8.json")
direction = line["directions"][0]
ids = [s["stop_id"] for s in direction["route_stops"]]
unique_ids = list(dict.fromkeys(ids))
assert ids[0] == ids[-1] == "0200"
assert len(ids) == 16 and len(unique_ids) == 15
first_part = ["0200", "0228", "0238", "0685", "0686", "0687"]
second_part = ["0688", "0689", "0690", "0691", "0692", "0693", "0173", "0174", "0199"]
assert unique_ids == first_part + second_part

# Check the actual generated timetable HTML for each stop, including the
# breakpoint between 0687 (Pomorzany) and 0688 (Dworzec PKS).
for stop_id in unique_ids:
    wanted = ("Olkusz Pomorzany Wzniesienie"
              if stop_id in first_part else "Olkusz Dworzec PKS")
    html = (ROOT / f"rozklady/8/{stop_id}-okrezna.html").read_text(encoding="utf-8")
    assert f'<div class="route-title">Kierunek: {wanted}</div>' in html, stop_id
    # Only the selected occurrence is current, not both occurrences of 0200.
    assert html.count('class="stop current-stop"') == 1, stop_id
    highlighted = re.findall(r'<a class="stop current-stop"[^>]*>([^<]+)</a>', html)
    assert len(highlighted) == 1 and highlighted[0].startswith(stop_id + " "), (stop_id, highlighted)

start_html = (ROOT / "rozklady/8/0200-okrezna.html").read_text(encoding="utf-8")
assert start_html.count("0200 Olkusz Dworzec PKS (0)</a>") == 2
assert start_html.count('class="stop current-stop"') == 1

# Physical stop popup reads data/odjazdy/0200.json. A line is offered only
# when it has genuine departures (not just a terminal arrival).
day_map = {"R": "workday", "S": "saturday", "N": "sunday", "SW": "holiday"}
expected = defaultdict(Counter)
for trip in detail["trips"]:
    for stop in trip["stop_times"][:-1]:
        expected[stop["stop_id"]][(day_map[trip["service_code"]], stop["time"])] += 1

for stop_id in unique_ids:
    stop_data = json_file(f"data/odjazdy/{stop_id}.json")
    line8 = [entry for entry in stop_data["departures"] if entry["line"] == "8"]
    actual = Counter((entry["day_type"], entry["time"]) for entry in line8)
    assert actual == expected[stop_id], (stop_id, actual - expected[stop_id], expected[stop_id] - actual)
    expected_direction = ("Olkusz Pomorzany Wzniesienie" if stop_id in first_part
                          else "Olkusz Dworzec PKS")
    assert all(entry["display_direction"] == expected_direction
               and entry["main_direction"] == expected_direction for entry in line8), stop_id
    served = [entry for entry in stop_data["served_lines"] if entry["line"] == "8"]
    assert len(served) == 1, (stop_id, served)
    assert served[0]["main_direction"] == expected_direction, (stop_id, served)
    assert served[0]["page"] == f"rozklady/8/{stop_id}-okrezna.html"
    assert len(line8) == 43, (stop_id, len(line8))

# Check the JS avoids stale cached odjazdy data in popup and sidebar.
map_js = (ROOT / "js/mapa.js").read_text(encoding="utf-8")
assert map_js.count('fetch(`data/odjazdy/${stopId}.json`, { cache: "no-store" })') == 2
map_html = (ROOT / "mapa.html").read_text(encoding="utf-8")
assert '<script src="js/mapa.js?v=20261020-stop-data"></script>' in map_html
print("OK: line 8 stop headings, one highlight, all 15 map stops, 43 departures each.")
print("OK: map direction breakpoint 0687/0688, cache refresh for stop popup/sidebar.")
