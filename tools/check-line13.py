#!/usr/bin/env python3
"""Independently check line 13 Excel and HTML/map output, including provisional H."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))
detail=read("data/trips/013.json")
line=read("data/rozklady/linie/13.json")
config=read("data/import-config/13.json")
trips=detail["trips"]
assert detail["line"]==line["line"]=="13"
assert len(trips)==74
assert sum(len(t["stop_times"]) for t in trips)==1443
assert sum(len(t["stop_times"])-1 for t in trips)==1369
assert Counter((t["direction"],t["service_code"]) for t in trips)=={
 (1,"R"):13,(1,"S"):11,(1,"N"):8,(1,"SW"):6,
 (2,"R"):13,(2,"S"):10,(2,"N"):8,(2,"SW"):5
}
assert Counter((t["direction"],t["variant"]) for t in trips)=={
 (1,"0"):27,(1,"1"):11,(2,"0"):36
}
assert config["directions"]["1"]["variant_symbols"]=={"1":"H"}
assert config["directions"]["1"]["variant_symbol_ends"]=={"1":{"stop_id":"0449","occurrence":1}}
assert config["directions"]["1"]["variant_destinations"]=={"H":"Hutki Pętla"}
assert config["directions"]["2"]=={"slug":"groniec","name":"Sławków Groniec Świerkowa"}
assert [d["name"] for d in line["directions"]]==["Sławków ZWM","Sławków Groniec Świerkowa"]

# Fingerprint calculated from P.A.M. - Linia 13.xlsx, Arkusz1. It covers all
# original course IDs, stop positions and numeric cached minute-precision times.
digest=hashlib.sha256(json.dumps([
 [t["trip_id"],[[x["stop_sequence"],x["time"]] for x in t["stop_times"]]]
 for t in trips],separators=(",",":"),ensure_ascii=False
).encode("utf-8")).hexdigest()
assert digest=="32d645c0c544e45ec5e3441a11f80249298dc052b447694b4a0a504dbcd28796",digest

assert len(detail["route_patterns"])==3
assert [(p["route_pattern_id"],len(p["stop_ids"])) for p in detail["route_patterns"]]==[
    ("013-1-1",33),("013-1-0",14),("013-2-0",32)
]
DAYS={"R":["workday"],"S":["saturday"],"N":["sunday"],"SW":["holiday"]}
geo={}
for fn in (ROOT/"data/stops").glob("*.geojson"):
    for f in read(fn.relative_to(ROOT))["features"]:
        meta=f["properties"]
        geo[meta["stop_id"]]=(meta["name"],str(meta["platform"]))

def timetable(d,sid):
    x=[tt for tt in d["timetables"] if tt["stop_id"]==sid]
    assert len(x)==1,sid
    return x[0]
def chars(tt):
    return {value[5:] for times in tt["departures"].values() for value in times}

for di,d in enumerate(line["directions"],1):
    ids=[s["stop_id"] for s in d["route_stops"]]
    assert len(ids)==(33 if di==1 else 32)
    courses=[t for t in trips if t["direction"]==di]
    for tt,s in zip(d["timetables"],d["route_stops"]):
        assert tt["stop_id"]==s["stop_id"] and tt["file"]==s["file"]
        assert (tt["stop_name"],tt["platform"])==geo[s["stop_id"]]
        pos=ids.index(s["stop_id"])+1
        expected={}
        for t in courses:
            for visit in t["stop_times"][:-1]:
                if visit["stop_sequence"]==pos:
                    suffix="H" if di==1 and t["variant"]=="1" and pos<14 else ""
                    for day in DAYS[t["service_code"]]:
                        expected.setdefault(day,[]).append(visit["time"]+suffix)
        expected={k:sorted(v) for k,v in expected.items()}
        assert tt["departures"]==expected,tt["file"]
        f=ROOT/"rozklady"/"13"/tt["file"]
        assert f.is_file(),f
        page=f.read_text(encoding="utf-8")
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',page))==1,tt["file"]
        heading=(
          ("Sławków ZWM" if pos<14 else "Hutki Pętla")
          if di==1 else "Sławków Groniec Świerkowa"
        )
        assert f'<div class="route-title">Kierunek: {heading}</div>' in page,tt["file"]
        if tt.get("arrival_only"):
            assert not tt["departures"]
            assert "Brak odjazdów tej linii" in page
            assert '<div class="time">' not in page
        if di==1 and pos<14:
            if "H" in chars(tt):
                assert "<sup>H</sup>" in page
                assert 'class="legend-row"' in page
        else:
            assert "<sup>H</sup>" not in page
            assert 'class="legend"' not in page
assert len([t for t in trips if t["direction"]==2 and
  t["stop_times"][0]["stop_id"]=="0168"])==11
assert len([t for t in trips if t["direction"]==2 and
  t["stop_times"][0]["stop_id"]=="0483"])==25
d1,d2=line["directions"]
assert chars(timetable(d1,"0448"))=={"","H"}
assert chars(timetable(d1,"0449"))=={""}
assert timetable(d1,"0449")["direction_override"]=="Hutki Pętla"
assert timetable(d1,"0168")["arrival_only"]
assert timetable(d1,"0168")["arrival_direction"]=="Hutki Pętla"
assert timetable(d2,"2769")["arrival_only"]
assert all(s=="" for s in chars(timetable(d2,"0483")))
routepage=(ROOT/"linie/13.html").read_text(encoding="utf-8")
for d in line["directions"]:
    for s in d["route_stops"]:
        assert f'../rozklady/13/{s["file"]}' in routepage
for sid,count,destination in [
    ("2769",38,"Hutki Pętla"),
    ("0168",11,"Sławków Groniec Świerkowa"),
    ("0449",11,"Hutki Pętla"),
    ("0483",36,"Sławków Groniec Świerkowa")
]:
    data=read(f"data/odjazdy/{sid}.json")
    matches=[r for r in data["departures"] if r["line"]=="13"]
    assert len(matches)==count,(sid,len(matches),count)
    assert any(v["display_direction"]==destination for v in matches),sid
assert not any(r["line"]=="13" and r["direction_slug"]=="zwm"
    for r in read("data/odjazdy/0168.json")["departures"])
assert not any(r["line"]=="13" and r["direction_slug"]=="groniec"
    for r in read("data/odjazdy/2769.json")["departures"])
print("OK: line 13 Excel fingerprint, 74 trips, 1443 times, 1369 departures.")
print("OK: ZWM/Hutki variant boundary, Groniec short starts, map and pages.")
