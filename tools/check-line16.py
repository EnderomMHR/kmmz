#!/usr/bin/env python3
"""Audit line 16 against the original Excel course/time fingerprint and site output."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))
config=read("data/import-config/16.json")
line=read("data/rozklady/linie/16.json")
detail=read("data/trips/016.json")
trips=detail["trips"]

assert line["line"]==detail["line"]=="16"
assert detail["schema_version"]=="kmmz-trips-v1"
assert len(line["directions"])==1
assert len(trips)==47
assert Counter(t["service_code"] for t in trips)=={"R":16,"S":14,"N":11,"SW":6}
assert all(t["direction"]==1 and t["variant"]=="0" for t in trips)
assert all(t["trip_id"].startswith("016-1-0-") for t in trips)
assert sum(len(t["stop_times"]) for t in trips)==752
assert sum(len(t["stop_times"])-1 for t in trips)==705
assert len(detail["route_patterns"])==1

# Independently calculated from the user-uploaded P.A.M. - Linia 16.xlsx
# / Arkusz1; covers all 47 course IDs, sequence positions and 752 HH:MM
# cached values (as whole minutes since midnight).
source_rows=[
 [trip["trip_id"], [[stop["stop_sequence"],
    int(stop["time"][:2])*60+int(stop["time"][3:])]
    for stop in trip["stop_times"]]]
 for trip in trips
]
fingerprint=hashlib.sha256(json.dumps(
    source_rows, separators=(",",":"),ensure_ascii=False
).encode("utf-8")).hexdigest()
assert fingerprint=="c3909757b1d6b265ec1ee67666d0db4a6668d90fc3dc8a22ec8b6a7ad93f5883",fingerprint

ids="0200 0202 2451 2463 2453 2461 2455 2459 2457 2465 2466 2509 2458 0174 0199 0200".split()
offsets=[0,2,4,5,6,7,8,9,10,13,14,15,16,20,21,23]
expected_segments=[
    {"from_stop_id":"0200","name":"Olkusz Jasna Skrzyżowanie"},
    {"from_stop_id":"2451","name":"Olkusz Dworzec PKS"}
]
cfg=config["directions"]["1"]
assert cfg=={
    "slug":"okrezna",
    "name":"Olkusz Dworzec PKS",
    "direction_segments":expected_segments
}

d=line["directions"][0]
assert d["slug"]=="okrezna"
assert d["name"]=="Olkusz Dworzec PKS"
assert d["direction_segments"]==expected_segments
assert d["legend"]==d["variant_destinations"]=={}
assert len(d["route_stops"])==len(d["timetables"])==16
assert [s["stop_id"] for s in d["route_stops"]]==ids
assert [s["stop_id"] for s in d["timetables"]]==ids
assert d["route_stops"][0]["file"]=="0200-okrezna.html"
assert d["route_stops"][-1]["file"]=="0200-okrezna-koniec.html"
assert detail["route_patterns"]==[{
    "route_pattern_id":"016-1-0",
    "direction":1,
    "variant":"0",
    "stop_ids":ids
}]
meta={f["properties"]["stop_id"]:f["properties"]
      for f in read("data/stops/olkusz.geojson")["features"]}
days={"R":["workday"],"S":["saturday"],"N":["sunday"],"SW":["holiday"]}
def minute(s):return int(s[:2])*60+int(s[3:])

for course in trips:
    visits=course["stop_times"]
    assert [s["stop_id"] for s in visits]==ids
    assert [s["stop_sequence"] for s in visits]==list(range(1,17))
    assert [minute(s["time"])-minute(visits[0]["time"]) for s in visits]==offsets

for pos,(route,tt) in enumerate(zip(d["route_stops"],d["timetables"])):
    sid=route["stop_id"]
    assert route["stop_name"]==meta[sid]["name"]
    assert route["platform"]==str(meta[sid]["platform"])
    assert route["file"]==tt["file"]
    assert (tt["stop_name"],tt["platform"])==(route["stop_name"],route["platform"])
    expected={}
    if pos<15:
        for trip in trips:
            for day in days[trip["service_code"]]:
                expected.setdefault(day,[]).append(trip["stop_times"][pos]["time"])
    expected={day:sorted(values) for day,values in expected.items()}
    assert tt["departures"]==expected,tt["file"]
    assert tt.get("arrival_only",False)==(pos==15)
    page=ROOT/"rozklady"/"16"/tt["file"]
    assert page.is_file(),page
    html=page.read_text(encoding="utf-8")
    heading="Olkusz Jasna Skrzyżowanie" if pos<=1 else "Olkusz Dworzec PKS"
    assert f'<div class="route-title">Kierunek: {heading}</div>' in html, tt["file"]
    assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,tt["file"]
    assert "Legenda" not in html,tt["file"]
    assert "<sup>" not in html,tt["file"]
    if pos==15:
        assert "Brak odjazdów tej linii" in html
        assert '<div class="time">' not in html

route_page=(ROOT/"linie/16.html").read_text(encoding="utf-8")
assert route_page.count('../rozklady/16/0200-okrezna.html')==1
assert route_page.count('../rozklady/16/0200-okrezna-koniec.html')==1
for s in d["route_stops"]:
    assert f'../rozklady/16/{s["file"]}' in route_page

for sid,destination in (
    ("0200","Olkusz Jasna Skrzyżowanie"),
    ("0202","Olkusz Jasna Skrzyżowanie"),
    ("2451","Olkusz Dworzec PKS"),
    ("2465","Olkusz Dworzec PKS"),
    ("0199","Olkusz Dworzec PKS")
):
    data=read(f"data/odjazdy/{sid}.json")
    selected=[x for x in data["departures"] if x["line"]=="16"]
    assert len(selected)==47,(sid,len(selected))
    assert all(x["display_direction"]==destination and
               x["main_direction"]==destination for x in selected),sid
    assert all(x["direction_slug"]=="okrezna" and not x["symbols"] for x in selected)
    assert not any(x["page"]=="rozklady/16/0200-okrezna-koniec.html" for x in selected)

start_page=(ROOT/"rozklady/16/0200-okrezna.html").read_text(encoding="utf-8")
end_page=(ROOT/"rozklady/16/0200-okrezna-koniec.html").read_text(encoding="utf-8")
assert '<div class="route-title">Kierunek: Olkusz Jasna Skrzyżowanie</div>' in start_page
assert '<div class="route-title">Kierunek: Olkusz Dworzec PKS</div>' in end_page
assert start_page!=end_page
assert d["timetables"][-1]["departures"]=={}
print("OK: line 16 original Excel SHA256, 47 trips/752 times/705 departures")
print("OK: first 0200 and final 0200 distinct; segment switch after 0202, map and pages")
