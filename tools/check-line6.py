#!/usr/bin/env python3
"""Verify line 6 timetable and destination-letter semantics."""
import json
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
trips = json.loads((ROOT / "data/trips/006.json").read_text(encoding="utf-8"))
line = json.loads((ROOT / "data/rozklady/linie/6.json").read_text(encoding="utf-8"))
assert trips["line"] == line["line"] == "6"
assert len(trips["trips"]) == 78
assert len(trips["route_patterns"]) == 8
assert sum(len(t["stop_times"]) for t in trips["trips"]) == 1832
assert Counter(t["service_code"] for t in trips["trips"]) == {"R":28,"S":22,"N":18,"SW":10}
assert len({s["stop_id"] for t in trips["trips"] for s in t["stop_times"]}) == 65
assert [len(d["route_stops"]) for d in line["directions"]] == [34,34]
assert line["directions"][0]["legend"] == {"Z": "do: Oświęcim Park Zasole"}
assert line["directions"][1]["legend"] == {"O": "do: Oświęcim Dąbrowskiego Kościół"}
ends = {(1,"0"):"0649",(1,"1"):"0633",(1,"2"):"0649",(1,"3"):"0633",
        (2,"0"):"0616",(2,"1"):"0669",(2,"2"):"0669",(2,"3"):"0616"}
for trip in trips["trips"]:
    assert trip["stop_times"][-1]["stop_id"] == ends[trip["direction"],trip["variant"]]
    t = [int(x["time"][:2])*60+int(x["time"][3:]) for x in trip["stop_times"]]
    assert t == sorted(t), trip["trip_id"]
for index, direction in enumerate(line["directions"]):
    suffix = "Z" if index == 0 else "O"
    for table in direction["timetables"]:
        for departures in table["departures"].values():
            assert departures == sorted(departures)
            assert all(not d[-1].isalpha() or d.endswith(suffix) for d in departures)
    if index == 0:
        assert all(not x.endswith("Z") for x in direction["timetables"][-1]["departures"].get("workday",[]))
    else:
        assert all(not x.endswith("O") for x in direction["timetables"][-1]["departures"].get("workday",[]))
print("OK: Line 6 trips, route pattern stops, destination symbols, departure days")
