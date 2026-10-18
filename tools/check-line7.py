#!/usr/bin/env python3
"""Regression tests for the single-direction circular line 7."""
import json
import importlib.util
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
assert direction["direction_segments"] == [
    {"from_stop_id": "0684", "name": "Chrzanów Fablok"},
    {"from_stop_id": "0682", "name": "Chrzanów Dworzec Autobusowy"},
]
config = json.loads((ROOT / "data/import-config/7.json").read_text(encoding="utf-8"))
assert config["directions"]["1"]["direction_segments"] == direction["direction_segments"]
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

# Test wspólnego mechanizmu; granica może wypadać na dowolnym przystanku.
spec = importlib.util.spec_from_file_location("kmmz_generate_rozklady", ROOT / "tools/generate-rozklady.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
expected_names = {
    "0684": "Chrzanów Fablok",
    "0096": "Chrzanów Fablok",
    "0352": "Chrzanów Fablok",
    "0332": "Chrzanów Fablok",
    "0681": "Chrzanów Fablok",
    "0682": "Chrzanów Dworzec Autobusowy",
    "0683": "Chrzanów Dworzec Autobusowy",
    "0333": "Chrzanów Dworzec Autobusowy",
    "0334": "Chrzanów Dworzec Autobusowy",
}
for stop_id, name in expected_names.items():
    assert generator.get_stop_direction_name(direction, stop_id) == name, stop_id

alternative = dict(direction)
alternative["direction_segments"] = [
    {"from_stop_id": "0684", "name": "Pierwsza czesc"},
    {"from_stop_id": "0352", "name": "Druga czesc"},
]
assert generator.get_stop_direction_name(alternative, "0096") == "Pierwsza czesc"
assert generator.get_stop_direction_name(alternative, "0352") == "Druga czesc"
assert generator.get_stop_direction_name(direction, "0352") == "Chrzanów Fablok"

try:
    generator.get_stop_direction_name({**direction, "direction_segments": [
        {"from_stop_id": "0684", "name": "Początek"},
        {"from_stop_id": "9999", "name": "Błędny próg"},
    ]}, "0682")
except ValueError:
    pass
else:
    raise AssertionError("Nieznany przystanek graniczny powinien być błędem")

generated = generator.build_departures_from_line_files([ROOT / "data/rozklady/linie/7.json"])
for stop_id, name in expected_names.items():
    entries = generated[stop_id]["departures"]
    served = list(generated[stop_id]["served_lines"].values())
    if stop_id == "0334":
        assert not entries and not served
    else:
        assert entries and len(served) == 1
        assert served[0]["main_direction"] == name
        assert all(e["main_direction"] == name and e["display_direction"] == name for e in entries)

print("OK: line 7 — kierunki zależne od ID, niezależne progi, mapy i strony przystanków")

