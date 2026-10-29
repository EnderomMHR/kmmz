#!/usr/bin/env python3
"""Audit line 18 against independent source Excel fingerprint and site output."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

cfg=read("data/import-config/18.json")
line=read("data/rozklady/linie/18.json")
data=read("data/trips/018.json")
trips=data["trips"]
assert line["line"]==data["line"]=="18"
assert len(trips)==96
assert sum(len(t["stop_times"]) for t in trips)==2682
assert sum(len(t["stop_times"])-1 for t in trips)==2586
assert len(data["route_patterns"])==3
assert len(line["directions"])==2
assert Counter((t["direction"],t["service_code"]) for t in trips)=={
    (1,"R"):15,(1,"S"):13,(1,"N"):11,(1,"SW"):9,
    (2,"R"):15,(2,"S"):13,(2,"N"):11,(2,"SW"):9
}
assert Counter((t["direction"],t["variant"]) for t in trips)=={
    (1,"0"):27,(1,"1"):21,(2,"0"):48
}
assert Counter((t["direction"],len(t["stop_times"])) for t in trips)=={
    (1,22):27,(1,39):21,(2,19):27,(2,36):21
}
# Independent SHA-256 from uploaded P.A.M. - Linia 18.xlsx, Arkusz1.
# All 96 original IDs, stop_sequence positions and cached time cells,
# normalized to integer minutes, in original worksheet column order.
fingerprint=hashlib.sha256(json.dumps([
    [t["trip_id"],[[s["stop_sequence"],int(s["time"][:2])*60+int(s["time"][3:])]
    for s in t["stop_times"]]] for t in trips
],separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
assert fingerprint=="47e093ec82f153acfe35cad26c79dc5336b36ff7a4ddc028e403b5053e1386ec",fingerprint

d1,d2=line["directions"]
assert [d["slug"] for d in line["directions"]]==["osiek","olkusz"]
assert [d["name"] for d in line["directions"]]==["Osiek Pętla","Olkusz Dworzec PKS"]
assert [len(d["route_stops"]) for d in line["directions"]]==[39,36]
assert [len(d["timetables"]) for d in line["directions"]]==[39,36]
assert d1["route_stops"][0]["stop_id"]=="0200"
assert d1["route_stops"][21]["stop_id"]=="2054"
assert d1["route_stops"][-1]["stop_id"]=="2075"
assert d2["route_stops"][0]["stop_id"]=="2075"
assert d2["route_stops"][17]["stop_id"]=="2054"
assert d2["route_stops"][-1]["stop_id"]=="0200"
assert cfg["directions"]["1"]["variant_symbols"]=={"1":"Z"}
assert cfg["directions"]["1"]["variant_letter_ends"]=={
    "Z":{"stop_id":"2054","occurrence":1}
}
assert cfg["directions"]["1"]["legend"]=={"Z":"do: Zawada Pętla"}
assert cfg["directions"]["1"]["legend_only_used_symbols"] is True
assert d1["legend_only_used_symbols"] is True
assert d1["legend"]=={"Z":"do: Zawada Pętla"}
assert d1["variant_destinations"]=={"Z":"Zawada Pętla"}
assert cfg["directions"]["1"]["direction_segments"]==d1["direction_segments"]==[
    {"from_stop_id":"0200","name":"Osiek Pętla"},
    {"from_stop_id":"2054","name":"Zawada Pętla"}
]
assert d2["legend"]==d2["variant_destinations"]=={}
assert all(t["variant"]=="0" for t in trips if t["direction"]==2)
assert Counter(t["stop_times"][0]["stop_id"] for t in trips if t["direction"]==2)=={
    "2054":27,"2075":21
}
assert all(t["stop_times"][-1]["stop_id"]=="0200" for t in trips if t["direction"]==2)
assert all(t["stop_times"][-1]["stop_id"]==("2054" if t["variant"]=="0" else "2075")
           for t in trips if t["direction"]==1)

patterns={p["route_pattern_id"]:p for p in data["route_patterns"]}
assert set(patterns)=={"018-1-0","018-1-1","018-2-0"}
for t in trips:
    route=patterns[t["route_pattern_id"]]["stop_ids"]
    visits=t["stop_times"]
    assert [s["stop_id"] for s in visits]==route[-len(visits):]
    assert [s["stop_sequence"] for s in visits]==list(range(visits[0]["stop_sequence"],
                                                             visits[0]["stop_sequence"]+len(visits)))
    assert visits[-1]["stop_sequence"]==(39 if t["direction"]==1 and t["variant"]=="1" else
                                        22 if t["direction"]==1 else 36)
    assert [s["time"] for s in visits]==sorted(s["time"] for s in visits)
    assert all(s["stop_id"]!= "2054" for s in visits) is False

metadata={}
for path in sorted((ROOT/"data/stops").glob("*.geojson")):
    for f in read(path.relative_to(ROOT))["features"]:
        p=f["properties"]
        metadata[p["stop_id"]]=(p["name"],str(p["platform"]))
days={"R":["workday"],"S":["saturday"],"N":["sunday"],"SW":["holiday"]}
for direction,dir_data in enumerate((d1,d2),1):
    for pos,(route,tt) in enumerate(zip(dir_data["route_stops"],dir_data["timetables"])):
        assert route["stop_name"]==metadata[route["stop_id"]][0]
        assert route["platform"]==metadata[route["stop_id"]][1]
        assert route["file"]==tt["file"]
        expected={}
        for t in trips:
            if t["direction"]!=direction:continue
            for visit in t["stop_times"][:-1]:
                if visit["stop_sequence"]!=pos+1:continue
                symbol=("Z" if direction==1 and t["variant"]=="1" and pos<21 else "")
                for day in days[t["service_code"]]:
                    expected.setdefault(day,[]).append(visit["time"]+symbol)
        expected={day:sorted(values) for day,values in expected.items()}
        assert tt["departures"]==expected,(tt["file"],expected,tt["departures"])
        is_terminal=(direction==1 and pos==38) or (direction==2 and pos==35)
        assert bool(tt.get("arrival_only"))==is_terminal,tt["file"]
        path=ROOT/"rozklady"/"18"/tt["file"]
        assert path.is_file(),path
        html=path.read_text(encoding="utf-8")
        heading=("Osiek Pętla" if direction==1 and pos<21
                 else "Zawada Pętla" if direction==1 else "Olkusz Dworzec PKS")
        assert f'<div class="route-title">Kierunek: {heading}</div>' in html,tt["file"]
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,tt["file"]
        assert len(re.findall(r'<div class="time">',html))==sum(
            len(vals) for vals in expected.values()
        ),tt["file"]
        has_z=any(raw.endswith("Z") for vals in expected.values() for raw in vals)
        assert ('<span class="symbol">Z</span>' in html)==has_z,tt["file"]
        assert ('<div class="legend">' in html)==has_z,tt["file"]
        if is_terminal:assert "Brak odjazdów tej linii" in html

def tt(direction,stop_id):
    hit=[x for x in direction["timetables"] if x["stop_id"]==stop_id]
    assert len(hit)==1,stop_id
    return hit[0]
def letters(table):
    return {x[5:] for vals in table["departures"].values() for x in vals}
assert letters(tt(d1,"0200"))=={"","Z"}
assert letters(tt(d1,"2886"))=={"","Z"}
assert letters(tt(d1,"2054"))=={""}
assert len([v for vals in tt(d1,"2054")["departures"].values() for v in vals])==21
assert len([v for vals in tt(d2,"2054")["departures"].values() for v in vals])==48
assert len([v for vals in tt(d2,"2075")["departures"].values() for v in vals])==21

# Map's compact departure data and per-stop switching of informational direction.
for sid,slug,name,n in [
    ("0200","osiek","Osiek Pętla",48),
    ("2054","osiek","Zawada Pętla",21),
    ("2075","olkusz","Olkusz Dworzec PKS",21),
    ("2054","olkusz","Olkusz Dworzec PKS",48),
]:
    data=read(f"data/odjazdy/{sid}.json")
    selection=[x for x in data["departures"]
               if x["line"]=="18" and x["direction_slug"]==slug]
    assert len(selection)==n,(sid,slug,len(selection))
    assert {x["main_direction"] for x in selection}=={name},(sid,slug)
    assert all(x["page"].startswith("rozklady/18/") for x in selection)
    if sid=="0200":
        assert len([x for x in selection if x["symbols"]==["Z"]])==21
        assert len([x for x in selection if x["display_direction"]=="Zawada Pętla"])==21
    if sid=="2054" and slug=="osiek":
        assert all(not x["symbols"] and x["display_direction"]=="Zawada Pętla"
                   for x in selection)
assert not any(x["line"]=="18" and x["direction_slug"]=="osiek"
               for x in read("data/odjazdy/2075.json")["departures"])
assert not any(x["line"]=="18" and x["direction_slug"]=="olkusz"
               for x in read("data/odjazdy/0200.json")["departures"])

# The existing route page has both full paths and their correct timetables.
html=(ROOT/"linie/18.html").read_text(encoding="utf-8")
for d in (d1,d2):
    for s in d["route_stops"]:
        assert f'../rozklady/18/{s["file"]}' in html,s["file"]
print("OK: line 18 original Excel SHA256 / 96 trips / 2682 stop times / 2586 departures")
print("OK: Z variant until Osiek Pętla, 21 Zawada starts, all 75 timetable pages and map")
