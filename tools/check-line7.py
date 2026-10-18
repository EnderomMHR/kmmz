#!/usr/bin/env python3
"""Regression tests for the single-direction circular line 7."""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
line = json.loads((ROOT / "data/rozklady/linie/7.json").read_text(encoding="utf-8"))
trips = json.loads((ROOT / "data/trips/007.json").read_text(encoding="utf-8"))
assert line["line"] == trips["line"] == "7"
assert len(line["directions"]) == 1
assert len(trips["trips"]) == 12
assert len(trips["route_patterns"]) == 1
assert sum(len(t["stop_times"]) for t in trips["trips"]) == 108
assert Counter(t["service_code"] for t in trips["trips"]) == {"R": 7, "S": 5}
direction = line["directions"][0]
assert direction["slug"] == "okrezna"
route = direction["route_stops"]
assert len(route) == 9
assert [(route[0]["stop_id"],route[0]["platform"]),(route[-1]["stop_id"],route[-1]["platform"])] == [("0684","2"),("0334","4")]
assert len({s["stop_id"] for s in route}) == 9
assert direction["timetables"][-1]["departures"] == {}
expected = {}
for t in trips["trips"]:
    assert t["stop_times"][0]["stop_id"] == "0684"
    assert t["stop_times"][-1]["stop_id"] == "0334"
    assert [s["stop_id"] for s in t["stop_times"]] == [x["stop_id"] for x in route]
    values = [int(s["time"][:2])*60 + int(s["time"][3:]) for s in t["stop_times"]]
    assert values == sorted(values) and values[-1] - values[0] == 15
    day = "workday" if t["service_code"] == "R" else "saturday"
    for stop in t["stop_times"][:-1]:
        expected.setdefault((stop["stop_id"],day), []).append(stop["time"])
for table in direction["timetables"]:
    for day in ("workday","saturday","sunday","holiday"):
        assert table["departures"].get(day,[]) == sorted(expected.get((table["stop_id"],day),[])),(table["stop_id"],day)
assert not direction["timetables"][-1]["departures"]
print("OK: line 7 — 12 courses, 9 stops, 108 stop times, 96 departures; terminal only arrival")
