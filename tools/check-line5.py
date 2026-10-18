#!/usr/bin/env python3
"""Regression checks for line 5 import artifacts; run: python tools/check-line5.py"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tripdata = json.loads((ROOT / "data/trips/005.json").read_text(encoding="utf-8"))
line = json.loads((ROOT / "data/rozklady/linie/5.json").read_text(encoding="utf-8"))
assert tripdata["line"] == line["line"] == "5"
assert len(tripdata["trips"]) == 36
assert sum(len(t["stop_times"]) for t in tripdata["trips"]) == 1296
assert Counter(t["service_code"] for t in tripdata["trips"]) == {"R": 16, "SN": 14, "SW": 6}
assert len(line["directions"]) == 2
assert [len(d["route_stops"]) for d in line["directions"]] == [36, 36]
assert len({s["stop_id"] for t in tripdata["trips"] for s in t["stop_times"]}) == 70
stop_pages = set()
for direction in line["directions"]:
    for stop in direction["route_stops"]:
        assert re.fullmatch(r"\d{4}-(olkusz|slawkow)\.html", stop["file"]), stop
        assert stop["file"] not in stop_pages
        stop_pages.add(stop["file"])
    for table in direction["timetables"]:
        assert table["file"] in stop_pages
        assert set(table["departures"]) == {"workday", "saturday", "sunday", "holiday"}
        for values in table["departures"].values():
            assert values == sorted(values)
for t in tripdata["trips"]:
    assert t["trip_id"].startswith("005-")
    times = [int(st["time"][:2]) * 60 + int(st["time"][3:]) for st in t["stop_times"]]
    assert times == sorted(times)
assert any(t["stop_id"] == "0465" for t in line["directions"][0]["timetables"])
assert any(t["stop_id"] == "0466" for t in line["directions"][1]["timetables"])
print("OK: line 5 trips, departure calendar, stop names, and page references")
