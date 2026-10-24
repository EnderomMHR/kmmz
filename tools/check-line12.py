#!/usr/bin/env python3
"""Check line 12 independently against the uploaded Excel and generated site."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))
cfg=load("data/import-config/12.json")
detail=load("data/trips/012.json")
line=load("data/rozklady/linie/12.json")
assert detail["line"]==line["line"]=="12"
assert len(detail["trips"])==45
assert len(detail["route_patterns"])==2
assert len(line["directions"])==2
assert cfg=={"directions":{
    "1":{"slug":"metkow","name":"Mętków Mały"},
    "2":{"slug":"jawiszowice","name":"Jawiszowice Kółko"}}}
assert Counter((t["direction"],t["service_code"]) for t in detail["trips"])=={
    (1,"R"):13,(1,"SN"):7,(1,"SW"):3,
    (2,"R"):13,(2,"SN"):6,(2,"SW"):3}
assert all(t["variant"]=="0" for t in detail["trips"])
assert all(t["route_pattern_id"]==f'012-{t["direction"]}-0' for t in detail["trips"])
assert sum(len(t["stop_times"]) for t in detail["trips"])==2723
assert sum(len(t["stop_times"])-1 for t in detail["trips"])==2678
# Independently computed from 'P.A.M. - Linia 12.xlsx' Arkusz1, converting
# Excel serial times to whole minutes, preserving every source stop position.
fingerprint=hashlib.sha256(json.dumps([
 [t["trip_id"],[[s["stop_sequence"],s["time"]] for s in t["stop_times"]]]
 for t in detail["trips"]],separators=(",",":"),ensure_ascii=False
).encode("utf-8")).hexdigest()
assert fingerprint=="26e0818b9dd7dfd3a6e4f6ec93ce0489c6c221ebf384ea7287b4efbefa9c5a2e",fingerprint

metadata={}
for fn in (ROOT/"data/stops").glob("*.geojson"):
    for f in load(fn.relative_to(ROOT))["features"]:
        p=f["properties"]
        metadata[p["stop_id"]]=(p["name"],str(p["platform"]))
days={"R":["workday"],"SN":["saturday","sunday"],"SW":["holiday"]}
for direction,expected_name,slug,stops_num,duration in [
 (1,"Mętków Mały","metkow",61,95),
 (2,"Jawiszowice Kółko","jawiszowice",60,94)
]:
    d=line["directions"][direction-1]
    assert d["name"]==expected_name and d["slug"]==slug
    assert d["legend"]==d["variant_destinations"]=={}
    assert len(d["route_stops"])==len(d["timetables"])==stops_num
    ids=[s["stop_id"] for s in d["route_stops"]]
    assert detail["route_patterns"][direction-1]=={
      "route_pattern_id":f"012-{direction}-0",
      "direction":direction,"variant":"0","stop_ids":ids
    }
    course=[t for t in detail["trips"] if t["direction"]==direction]
    for trip in course:
        assert len(trip["stop_times"])==stops_num
        assert [s["stop_id"] for s in trip["stop_times"]]==ids
        assert all(s["stop_sequence"]==i+1 for i,s in enumerate(trip["stop_times"]))
        mins=lambda s: int(s[:2])*60+int(s[3:])
        assert mins(trip["stop_times"][-1]["time"])-mins(trip["stop_times"][0]["time"])==duration
    for i,(route,timetable) in enumerate(zip(d["route_stops"],d["timetables"])):
        sid=route["stop_id"]
        assert (route["stop_name"],route["platform"])==metadata[sid]
        assert timetable["stop_id"]==sid
        assert timetable["file"]==route["file"]==f"{sid}-{slug}.html"
        assert timetable["stop_name"]==route["stop_name"]
        assert timetable["platform"]==route["platform"]
        expect={}
        if i<stops_num-1:
            for trip in course:
                for day in days[trip["service_code"]]:
                    expect.setdefault(day,[]).append(trip["stop_times"][i]["time"])
        expect={day:sorted(values) for day,values in expect.items()}
        assert timetable["departures"]==expect,(sid,slug)
        if i==stops_num-1:
            assert timetable.get("arrival_only") is True
            assert timetable["departures"]=={}
        else:assert not timetable.get("arrival_only")
        path=ROOT/"rozklady"/"12"/route["file"]
        assert path.is_file(),path
        html=path.read_text(encoding="utf-8")
        assert f'<div class="route-title">Kierunek: {expected_name}</div>' in html,path
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,path
        assert 'class="legend"' not in html
        assert '<sup>' not in html
        if i==stops_num-1:
            assert "Brak odjazdów tej linii" in html
            assert '<div class="time">' not in html

route_page=(ROOT/"linie/12.html").read_text(encoding="utf-8")
for d in line["directions"]:
    for s in d["route_stops"]:
        assert f'../rozklady/12/{s["file"]}' in route_page
        assert route_page.count(f'../rozklady/12/{s["file"]}')==1
for sid,expected_count in [("2568",30),("0311",28),("2553",58)]:
    output=load(f"data/odjazdy/{sid}.json")
    departures=[x for x in output["departures"] if x["line"]=="12"]
    assert len(departures)==expected_count,(sid,len(departures))
    assert all(x["symbols"]==[] and x["display_direction"] in
        ("Mętków Mały","Jawiszowice Kółko") for x in departures)
    assert not any(x["page"] in ("rozklady/12/0311-metkow.html",
                                 "rozklady/12/2557-jawiszowice.html")
                   for x in departures)
for sid in ("0311","2557"):
    data=load(f"data/odjazdy/{sid}.json")
    departures=[x for x in data["departures"] if x["line"]=="12"]
    if sid=="2557":assert not departures
    else:assert len(departures)==28  # initial Mętków only; arriving is not departure
print("OK: line 12 original Excel fingerprint, 45 courses, 2723 stop-times, 2678 real departures")
print("OK: no variants, 61+60 route positions, weekends SN, terminal arrivals filtered")
