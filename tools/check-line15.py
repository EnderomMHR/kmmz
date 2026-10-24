#!/usr/bin/env python3
"""Line 15: independently audit source and all rendered stop timetable pages."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

cfg=read("data/import-config/15.json")
line=read("data/rozklady/linie/15.json")
detail=read("data/trips/015.json")
trips=detail["trips"]
assert detail["line"]==line["line"]=="15"
assert len(trips)==56
assert len(detail["route_patterns"])==2
assert sum(len(t["stop_times"]) for t in trips)==2996
assert sum(len(t["stop_times"])-1 for t in trips)==2940
assert Counter((t["direction"],t["service_code"]) for t in trips)=={
 (1,"R"):12,(1,"S"):7,(1,"N"):6,(1,"SW"):3,
 (2,"R"):12,(2,"S"):7,(2,"N"):6,(2,"SW"):3,
}
assert all(t["variant"]=="0" for t in trips)
assert cfg=={"directions":{
 "1":{"slug":"oswiecim","name":"Oświęcim Dworzec Fabryczny"},
 "2":{"slug":"jawiszowice","name":"Jawiszowice Jaźnik"}}}

# Independently calculated from the original user-uploaded
# P.A.M. - Linia 15.xlsx / Arkusz1, preserving 56 IDs,
# all 2996 HH:MM cached values and all original stop positions.
fingerprint=hashlib.sha256(json.dumps([
 [t["trip_id"],[[s["stop_sequence"],s["time"]] for s in t["stop_times"]]]
 for t in trips
],separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
assert fingerprint=="18eed9f456760c176e2fcd173fb868952f43aab1291beaa5622325b278ed3449",fingerprint

metadata={}
for path in sorted((ROOT/"data/stops").glob("*.geojson")):
    for f in read(path.relative_to(ROOT))["features"]:
        p=f["properties"]
        metadata[p["stop_id"]]=(p["name"],str(p["platform"]))

days={"R":["workday"],"S":["saturday"],"N":["sunday"],"SW":["holiday"]}
for dno,slug,name,nstops,duration in (
 (1,"oswiecim","Oświęcim Dworzec Fabryczny",54,71),
 (2,"jawiszowice","Jawiszowice Jaźnik",53,68)
):
    d=line["directions"][dno-1]
    assert d["slug"]==slug and d["name"]==name
    assert d["legend"]==d["variant_destinations"]=={}
    assert len(d["route_stops"])==len(d["timetables"])==nstops
    route=d["route_stops"]
    route_ids=[s["stop_id"] for s in route]
    assert len(set(route_ids))==nstops
    assert detail["route_patterns"][dno-1]=={
      "route_pattern_id":f"015-{dno}-0",
      "direction":dno,"variant":"0","stop_ids":route_ids
    }
    courses=[t for t in trips if t["direction"]==dno]
    def minute(v):return int(v[:2])*60+int(v[3:])
    for trip in courses:
        stop_times=trip["stop_times"]
        assert len(stop_times)==nstops
        assert [x["stop_id"] for x in stop_times]==route_ids
        assert [x["stop_sequence"] for x in stop_times]==list(range(1,nstops+1))
        assert minute(stop_times[-1]["time"])-minute(stop_times[0]["time"])==duration
        assert all(minute(a["time"])<=minute(b["time"])
                   for a,b in zip(stop_times,stop_times[1:]))
    for pos,stop in enumerate(route):
        sid=stop["stop_id"]
        assert (stop["stop_name"],stop["platform"])==metadata[sid]
        assert stop["file"]==f"{sid}-{slug}.html"
        timetable=d["timetables"][pos]
        assert timetable["stop_id"]==sid
        assert timetable["stop_name"]==stop["stop_name"]
        assert timetable["platform"]==stop["platform"]
        assert timetable["file"]==stop["file"]
        expected={}
        if pos<nstops-1:
            for trip in courses:
                for day in days[trip["service_code"]]:
                    expected.setdefault(day,[]).append(trip["stop_times"][pos]["time"])
        expected={day:sorted(values) for day,values in expected.items()}
        assert timetable["departures"]==expected,(dno,sid)
        if pos==nstops-1:
            assert timetable["arrival_only"] and not expected
        else:
            assert not timetable.get("arrival_only")
        page=ROOT/"rozklady"/"15"/stop["file"]
        assert page.is_file(),page
        html=page.read_text(encoding="utf-8")
        assert f'<div class="route-title">Kierunek: {name}</div>' in html,page
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,page
        assert 'class="legend"' not in html
        assert '<sup>' not in html
        if pos==nstops-1:
            assert "Brak odjazdów tej linii" in html
            assert '<div class="time">' not in html

route_page=(ROOT/"linie/15.html").read_text(encoding="utf-8")
for d in line["directions"]:
    for stop in d["route_stops"]:
        url=f'../rozklady/15/{stop["file"]}'
        assert route_page.count(url)==1,url

for sid,count,name in (
 ("2627",28,"Oświęcim Dworzec Fabryczny"),
 ("0830",28,"Jawiszowice Jaźnik"),
 ("2553",56,None),
):
    data=read(f"data/odjazdy/{sid}.json")
    departures=[x for x in data["departures"] if x["line"]=="15"]
    assert len(departures)==count,(sid,len(departures))
    assert all(not x["symbols"] for x in departures)
    if name:
        assert all(x["display_direction"]==name for x in departures)
    else:
        assert {x["display_direction"] for x in departures}=={
          "Oświęcim Dworzec Fabryczny","Jawiszowice Jaźnik"
        }

for sid,slug in (("0879","oswiecim"),("2627","jawiszowice")):
    data=read(f"data/odjazdy/{sid}.json")
    assert not any(x["line"]=="15" and x["direction_slug"]==slug
                   for x in data["departures"]),sid
print("OK: line 15 original Excel fingerprint, 56 trips, 2996 stop-times, 2940 departures")
print("OK: no variants, 54/53 stops, endpoints, stop pages and map directions")
