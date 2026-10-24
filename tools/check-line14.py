#!/usr/bin/env python3
"""Validate the line 14 Excel fingerprint, directions, combined GS and HTML/map."""
import json
import re
import hashlib
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))
cfg=read("data/import-config/14.json")
line=read("data/rozklady/linie/14.json")
src=read("data/trips/014.json")
trips=src["trips"]
assert line["line"]==src["line"]=="14"
assert len(trips)==68
assert sum(len(t["stop_times"]) for t in trips)==2289
assert sum(len(t["stop_times"])-1 for t in trips)==2221
assert len(src["route_patterns"])==8
assert Counter((t["direction"],t["service_code"]) for t in trips)=={
  (1,"R"):15,(1,"S"):8,(1,"N"):7,(1,"SW"):4,
  (2,"R"):14,(2,"S"):8,(2,"N"):7,(2,"SW"):5
}
assert Counter((t["direction"],t["variant"]) for t in trips)=={
 (1,"0"):15,(1,"1"):3,(1,"2"):15,(1,"3"):1,
 (2,"0"):17,(2,"1"):2,(2,"2"):13,(2,"3"):2
}
# Independent fingerprint from the uploaded original P.A.M. - Linia 14
# (done).xlsx / Arkusz1, including all stop positions and cached times.
digest=hashlib.sha256(json.dumps([
 [t["trip_id"],[[s["stop_sequence"],s["time"]] for s in t["stop_times"]]]
 for t in trips],separators=(",",":"),ensure_ascii=False
).encode("utf-8")).hexdigest()
assert digest=="2dceb352b81c6be9664f55f71f1182010ce906c382024f66a85919d57e25c0f3",digest

assert [d["slug"] for d in line["directions"]]==["chrzanow","grojec"]
assert [d["name"] for d in line["directions"]]==[
 "Chrzanów Dworzec Autobusowy","Grojec Zajezdnia"]
assert [len(d["route_stops"]) for d in line["directions"]]==[42,44]
assert cfg["directions"]["1"]["variant_symbols"]=={"1":"S","3":"S"}
assert cfg["directions"]["2"]["variant_symbols"]=={"1":"S","2":"G","3":"GS"}
assert cfg["directions"]["1"]["variant_letter_ends"]=={"S":{"stop_id":"0117","occurrence":1}}
assert cfg["directions"]["2"]["variant_letter_ends"]=={
 "G":{"stop_id":"1484","occurrence":1},"S":{"stop_id":"0117","occurrence":1}}
assert line["directions"][1]["variant_destinations"]=={"G":"Sanka Głuchówki"}
assert line["directions"][1]["direction_segments"]==[
 {"from_stop_id":"0334","name":"Grojec Zajezdnia"},
 {"from_stop_id":"1484","name":"Sanka Głuchówki"}]

def tt(direction,sid):
    items=[t for t in direction["timetables"] if t["stop_id"]==sid]
    assert len(items)==1,(direction["name"],sid)
    return items[0]
def letters(t):
    return {v[5:] for vals in t["departures"].values() for v in vals}
d1,d2=line["directions"]
assert "S" in letters(tt(d1,"1164"))
assert letters(tt(d1,"0117"))=={""}
assert "GS" in letters(tt(d2,"0334"))
assert "GS" in letters(tt(d2,"0333"))
assert "G" in letters(tt(d2,"0117"))
assert "GS" not in letters(tt(d2,"0117"))
assert "S" not in letters(tt(d2,"1058"))
assert "G" in letters(tt(d2,"1483"))
assert letters(tt(d2,"1484"))=={""}
assert letters(tt(d2,"1485"))=={""}
assert tt(d1,"0334")["arrival_only"]
assert tt(d2,"1399")["arrival_only"]
assert all(t["variant"] not in ("2","3") or t["stop_times"][0]["stop_id"]=="1399" for t in trips if t["direction"]==1)
assert len([t for t in trips if t["direction"]==1 and t["stop_times"][0]["stop_id"]=="1399"])==16
assert len([t for t in trips if t["direction"]==2 and t["stop_times"][-1]["stop_id"]=="1399"])==15

metadata={}
for file in sorted((ROOT/"data/stops").glob("*.geojson")):
    for f in read(file.relative_to(ROOT))["features"]:
        p=f["properties"]
        metadata[p["stop_id"]]=(p["name"],str(p["platform"]))
DAYS={"R":["workday"],"S":["saturday"],"N":["sunday"],"SW":["holiday"]}
for di,d in enumerate(line["directions"],1):
    ids=[r["stop_id"] for r in d["route_stops"]]
    assert len(ids)==len(set(ids))
    for p,entry in enumerate(d["route_stops"]):
        sid=entry["stop_id"]
        assert (entry["stop_name"],entry["platform"])==metadata[sid],sid
        table=d["timetables"][p]
        assert table["file"]==entry["file"]
        expected={}
        for trip in trips:
            if trip["direction"]!=di:continue
            for stop in trip["stop_times"][:-1]:
                if stop["stop_sequence"]!=p+1:continue
                variant=trip["variant"]
                if di==1:
                    symbol="S" if variant in ("1","3") and p<ids.index("0117") else ""
                else:
                    symbol=(
                        "GS" if variant=="3" else
                        "G" if variant=="2" else
                        "S" if variant=="1" else ""
                    )
                    if p>=ids.index("0117"): symbol=symbol.replace("S","")
                    if p>=ids.index("1484"): symbol=symbol.replace("G","")
                for day in DAYS[trip["service_code"]]:
                    expected.setdefault(day,[]).append(stop["time"]+symbol)
        expected={k:sorted(v) for k,v in expected.items()}
        assert table["departures"]==expected,table["file"]
        f=ROOT/"rozklady"/"14"/entry["file"]
        assert f.is_file(),f
        html=f.read_text(encoding="utf-8")
        heading=(d["name"] if di==1 else
                 ("Sanka Głuchówki" if p>=ids.index("1484") else "Grojec Zajezdnia"))
        assert f'<div class="route-title">Kierunek: {heading}</div>' in html,table["file"]
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,table["file"]
        legend=[x for x in d["legend"] if x in "".join(letters(table))]
        actual=re.findall(r'<div class="legend-row"><span class="symbol">([^<]+)</span>',html)
        assert actual==sorted(legend),(table["file"],actual,legend)
        if table.get("arrival_only"):
            assert "Brak odjazdów tej linii" in html
            assert '<div class="time">' not in html

page=(ROOT/"linie/14.html").read_text(encoding="utf-8")
for d in line["directions"]:
    for stop in d["route_stops"]:
        assert f'../rozklady/14/{stop["file"]}' in page
for sid,conditions in (
 ("0334",("Sanka Głuchówki","Grojec Zajezdnia")),
 ("1484",("Chrzanów Dworzec Autobusowy","Sanka Głuchówki")),
 ("1399",("Chrzanów Dworzec Autobusowy",))
):
    data=read(f"data/odjazdy/{sid}.json")
    departures=[v for v in data["departures"] if v["line"]=="14"]
    assert departures,sid
    assert set(v["display_direction"] for v in departures)==set(conditions),(sid,departures[:3])
assert not any(x["line"]=="14" and x["direction_slug"]=="chrzanow"
               for x in read("data/odjazdy/0334.json")["departures"])
assert not any(x["line"]=="14" and x["direction_slug"]=="grojec"
               for x in read("data/odjazdy/1399.json")["departures"])
print("OK: line14, original 68 trips / 2289 times / 2221 departures, G/S/GS cutoff")
