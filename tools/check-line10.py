#!/usr/bin/env python3
"""KMMZ line 10: verify revised Arkusz1 fingerprint and published route behavior."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

config=load("data/import-config/10.json")
trips=load("data/trips/010.json")
line=load("data/rozklady/linie/10.json")
assert trips["line"] == line["line"] == "10"
assert len(trips["trips"]) == 13
assert len(trips["route_patterns"]) == 2
assert len(line["directions"]) == 2
assert set(config["directions"]) == {"1","2"}
assert trips["schema_version"] == "kmmz-trips-v1"
assert all(t["variant"]=="0" and t["trip_id"].startswith("010-") for t in trips["trips"])
assert Counter((t["direction"],t["service_code"]) for t in trips["trips"]) == {
    (1,"R"):3,(1,"S"):1,(1,"N"):1,(1,"SW"):1,
    (2,"R"):3,(2,"S"):2,(2,"N"):1,(2,"SW"):1,
}
assert sum(len(t["stop_times"]) for t in trips["trips"]) == 420
assert sum(len(t["stop_times"])-1 for t in trips["trips"]) == 407

# Independent SHA-256 fingerprint calculated from the revised original
# P.A.M. - Linia 10 (1).xlsx, Arkusz1 only: trip IDs, stop positions,
# minute-of-day for every one of the 420 times.
rows = [[t["trip_id"], [[s["stop_sequence"],
        int(s["time"][:2])*60 + int(s["time"][3:])]
        for s in t["stop_times"]]] for t in trips["trips"]]
fingerprint=hashlib.sha256(json.dumps(
    rows, separators=(",",":"), ensure_ascii=False
).encode("utf-8")).hexdigest()
assert fingerprint == "7544682f30702bb84d1a4c411f8ca41f93869f74584b9f2fff6905079a19b11c", fingerprint

routes=[
    "0147 0148 0724 0725 0726 0727 0728 0729 0730 0731 0732 0733 0734 0735 0736 0737 0738 0739 0252 0253 0254 0255 0256 0106 0139 0140 0141 0142 0143 0144 0145 0146 0147".split(),
    "0147 0148 0250 0251 0252 0253 0254 0255 0256 0106 0139 0140 0141 0142 0143 0732 0733 0734 0735 0736 0737 0738 0739 0740 0741 0742 0743 0744 0726 0745 0746 0146 0147".split()
]
expected_segments=[
    [("0147","Bukowno Bór Biskupi OSP"),("0735","Bukowno Dworzec PKP")],
    [("0147","Bukowno Przymiarki"),("0106","Bukowno Dworzec PKP")],
]
metadata={f["properties"]["stop_id"]:f["properties"]
          for f in load("data/stops/bukowno.geojson")["features"]}
days={"R":["workday"],"S":["saturday"],"N":["sunday"],"SW":["holiday"]}
for i,d in enumerate(line["directions"]):
    direction=i+1
    assert d["slug"] == f"okrezna-{direction}"
    assert d["name"] == "Bukowno Dworzec PKP"
    assert d["variant_destinations"] == d["legend"] == {}
    segments=[(s["from_stop_id"],s["name"]) for s in d["direction_segments"]]
    assert segments == expected_segments[i]
    assert config["directions"][str(direction)]["direction_segments"] == d["direction_segments"]
    assert len(d["route_stops"]) == len(d["timetables"]) == 33
    assert [s["stop_id"] for s in d["route_stops"]] == routes[i]
    assert [s["stop_id"] for s in d["timetables"]] == routes[i]
    assert trips["route_patterns"][i] == {
        "route_pattern_id":f"010-{direction}-0",
        "direction":direction, "variant":"0", "stop_ids":routes[i]
    }
    for pos,(stop,tt) in enumerate(zip(d["route_stops"],d["timetables"])):
        assert stop["stop_name"] == metadata[stop["stop_id"]]["name"]
        assert stop["platform"] == str(metadata[stop["stop_id"]]["platform"])
        assert stop["file"] == tt["file"]
        expected={}
        for t in trips["trips"]:
            if t["direction"]!=direction:continue
            for visit in t["stop_times"][:-1]:
                if visit["stop_sequence"]!=pos+1:continue
                for day in days[t["service_code"]]:
                    expected.setdefault(day,[]).append(visit["time"])
        expected={day:sorted(hh) for day,hh in expected.items()}
        assert tt["departures"] == expected, (direction,pos,tt["file"])
        if pos==32:
            assert tt["arrival_only"] is True
            assert tt["file"] == f"0147-okrezna-{direction}-koniec.html"
            assert tt["departures"] == {}
        else:
            assert not tt.get("arrival_only")
        # Actual generated HTML: correct heading and one highlighted
        # occurrence, including dedicated final 0147 with no departures.
        path=ROOT/"rozklady"/"10"/tt["file"]
        assert path.is_file(), path
        html=path.read_text(encoding="utf-8")
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1, tt["file"]
        second_boundary = 13 if direction==1 else 9
        display=(expected_segments[i][0][1] if pos<second_boundary
                 else expected_segments[i][1][1])
        assert f'<div class="route-title">Kierunek: {display}</div>' in html,tt["file"]
        assert "Legenda" not in html and "<sup>W</sup>" not in html, tt["file"]
        if pos==32:assert "Brak odjazdów tej linii" in html
    # The terminal time for every individual trip is preserved in detail
    # JSON only, never as a new stop departure.
    for t in (t for t in trips["trips"] if t["direction"]==direction):
        assert t["stop_times"][-1]["stop_id"]=="0147"

short=[t for t in trips["trips"] if t["trip_id"]=="010-2-0-R-03"]
assert len(short)==1
assert short[0]["stop_times"][0] == {"stop_sequence":10,"stop_id":"0106","time":"17:19"}
assert short[0]["stop_times"][-1] == {"stop_sequence":33,"stop_id":"0147","time":"18:01"}
assert len(short[0]["stop_times"])==24
assert [x for x in trips["trips"] if x["trip_id"]=="010-1-0-R-03"][0]["stop_times"][0]["stop_id"]=="0147"

# 0736 was adjusted by -1 minute in every one of the 13 courses.
assert len([t for t in trips["trips"] if any(v["stop_id"]=="0736" for v in t["stop_times"])]) == 13

routepage=(ROOT/"linie/10.html").read_text(encoding="utf-8")
for direction in (1,2):
    assert routepage.count(f'../rozklady/10/0147-okrezna-{direction}.html') == 1
    assert routepage.count(f'../rozklady/10/0147-okrezna-{direction}-koniec.html') == 1

physical=load("data/odjazdy/0147.json")
entries=[x for x in physical["departures"] if x["line"]=="10"]
assert len(entries)==12
assert not any("-koniec" in e["page"] for e in entries)
assert Counter(e["direction_slug"] for e in entries) == {"okrezna-1":6,"okrezna-2":6}
for e in entries:
    assert e["main_direction"] in {"Bukowno Bór Biskupi OSP","Bukowno Przymiarki"}
mid=load("data/odjazdy/0106.json")
assert len([e for e in mid["departures"] if e["line"]=="10"])==13
print("OK: line 10, 13 trips, revised Excel fingerprint, 420 stop times, 407 real departures.")
print("OK: two directions, segment headings, no variants, separate 0147 terminal pages.")
