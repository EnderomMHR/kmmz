#!/usr/bin/env python3
"""Verify line 17 Excel fingerprint, route variants, correct HTML and map departures."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

config=load("data/import-config/17.json")
line=load("data/rozklady/linie/17.json")
detail=load("data/trips/017.json")
trips=detail["trips"]
assert line["line"]==detail["line"]=="17"
assert len(trips)==90
assert sum(len(t["stop_times"]) for t in trips)==1898
assert sum(len(t["stop_times"])-1 for t in trips)==1808
assert len(detail["route_patterns"])==8
assert len(line["directions"])==2
assert Counter((t["direction"],t["service_code"]) for t in trips)=={
    (1,"R"):19,(1,"S"):10,(1,"N"):9,(1,"SW"):7,
    (2,"R"):19,(2,"S"):10,(2,"N"):9,(2,"SW"):7
}
assert Counter((t["direction"],t["variant"]) for t in trips)=={
    (1,"0"):9,(1,"1"):10,(1,"2"):18,(1,"3"):8,
    (2,"0"):14,(2,"1"):17,(2,"2"):12,(2,"3"):2
}
# Source file P.A.M. - Linia 17 (done).xlsx / Arkusz1.
# The hash was calculated directly from the uploaded workbook, not this JSON.
digest=hashlib.sha256(json.dumps([
    [t["trip_id"],[[s["stop_sequence"],s["time"]] for s in t["stop_times"]]]
    for t in trips
],separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
assert digest=="d5a88ac6acfd14a6a2b7245dce00d63cfd49c900b6eb9052e016e265b99a7ad7",digest

d1,d2=line["directions"]
assert [d["slug"] for d in line["directions"]]==["chrzanow","metkow"]
assert [d["name"] for d in line["directions"]]==[
    "Chrzanów Dworzec Autobusowy","Mętków Mały"
]
assert len(d1["route_stops"])==len(d2["route_stops"])==29
assert d1["route_stops"][0]["stop_id"]=="0311"
assert d1["route_stops"][-1]["stop_id"]=="0334"
assert d2["route_stops"][0]["stop_id"]=="0095"
assert d2["route_stops"][-1]["stop_id"]=="0311"
assert config["directions"]["1"]["variant_symbols"]=={"1":"J","2":"L","3":"JL"}
assert config["directions"]["2"]["variant_symbols"]=={"1":"J","2":"K","3":"JK"}
assert config["directions"]["1"]["variant_letter_ends"]=={
    "J":{"stop_id":"0105","occurrence":1},
    "L":{"stop_id":"0107","occurrence":1}
}
assert config["directions"]["2"]["variant_letter_ends"]=={
    "J":{"stop_id":"0105","occurrence":1},
    "K":{"stop_id":"0320","occurrence":1}
}
assert all(d["legend_only_used_symbols"] for d in (d1,d2))
assert all(d["variant_destinations"]=={
    "L":"Libiąż Dworzec Autobusowy"
} if d is d1 else d["variant_destinations"]=={
    "K":"Żarki Kadetów Koniec"
} for d in (d1,d2))
assert d1["legend"]=={
    "J":"przez: Libiąż Kopalnia Janina",
    "L":"do: Libiąż Dworzec Autobusowy"
}
assert d2["legend"]=={
    "J":"przez: Libiąż Kopalnia Janina",
    "K":"do: Żarki Kadetów Koniec"
}
for d in (d1,d2):
    assert [s["stop_id"] for s in d["route_stops"]].count("0105")==1
    assert next(s for s in d["route_stops"] if s["stop_id"]=="0105")["variant"] is True
    assert all(s["stop_id"]!= "0105" or s.get("variant") for s in d["route_stops"])
    assert d["timetables"][-1]["arrival_only"] is True
    assert d["timetables"][-1]["departures"]=={}

def tt(direction,stopid):
    found=[t for t in direction["timetables"] if t["stop_id"]==stopid]
    assert len(found)==1, (direction["name"],stopid)
    return found[0]
def symbols(t):
    return {raw[5:] for values in t["departures"].values() for raw in values}

# Janina and shortened termini: independent letters disappear at the stop
# they describe. The next stop lists ONLY still-relevant symbols.
assert {"J","L","JL"} & symbols(tt(d1,"0311"))
assert "JL" in symbols(tt(d1,"0320"))
assert "J" not in symbols(tt(d1,"0105"))
assert "L" in symbols(tt(d1,"0105"))
assert symbols(tt(d1,"0107"))=={""}
assert symbols(tt(d1,"0108"))=={""}

assert "JK" in symbols(tt(d2,"0104"))
assert "J" not in symbols(tt(d2,"0105"))
assert "K" in symbols(tt(d2,"0105"))
assert "K" in symbols(tt(d2,"0345"))
assert symbols(tt(d2,"0320"))=={""}
assert symbols(tt(d2,"0346"))=={""}

# Validate route pattern suffix behavior and no artificial departures at
# short-course destinations, including the original Excel shortened starts.
patterns={p["route_pattern_id"]:p for p in detail["route_patterns"]}
assert len(patterns)==8
for trip in trips:
    row=trip["stop_times"]
    expected=patterns[trip["route_pattern_id"]]["stop_ids"]
    assert [s["stop_id"] for s in row]==expected[-len(row):]
    assert [s["stop_sequence"] for s in row]==sorted(s["stop_sequence"] for s in row)
    assert len(row)>=2
    assert row[0]["stop_sequence"]>=1
    assert [s["time"] for s in row]==sorted(s["time"] for s in row)
    if trip["direction"]==1 and trip["variant"] in ("2","3"):
        assert row[-1]["stop_id"]=="0107"
    if trip["direction"]==2 and trip["variant"] in ("2","3"):
        assert row[-1]["stop_id"]=="0320"
    if trip["direction"]==1 and trip["variant"] in ("1","3"):
        assert any(s["stop_id"]=="0105" for s in row)
    if trip["direction"]==2 and trip["variant"] in ("1","3"):
        assert any(s["stop_id"]=="0105" for s in row)
    if trip["variant"] in ("0","2"):
        assert all(s["stop_id"]!="0105" for s in row)

# Inspect every newly generated timetable page, with exact time suffixes
# and no unnecessary legend after the variant ends.
for d in (d1,d2):
    for s in d["timetables"]:
        f=ROOT/"rozklady"/"17"/s["file"]
        assert f.is_file(),f
        html=f.read_text(encoding="utf-8")
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,s["file"]
        assert len(re.findall(r'<div class="time">',html))==sum(
            len(x) for x in s["departures"].values()
        ),s["file"]
        suffix=set("".join(symbols(s)))
        expected_legend={letter for letter in d["legend"] if letter in suffix}
        for letter in d["legend"]:
            has_legend=f'<span class="symbol">{letter}</span>' in html
            assert has_legend==(letter in expected_legend),(s["file"],letter,expected_legend)
        assert ('<div class="legend">' in html)==bool(expected_legend),s["file"]

# On the map the shortened lines must still be associated with their
# destination (not the main route), and the terminal arrival creates no departure.
for sid,slug,term in [
    ("0311","chrzanow","Libiąż Dworzec Autobusowy"),
    ("0107","chrzanow","Chrzanów Dworzec Autobusowy"),
    ("0095","metkow","Żarki Kadetów Koniec"),
    ("0320","metkow","Mętków Mały"),
]:
    data=load(f"data/odjazdy/{sid}.json")
    matches=[x for x in data["departures"] if x["line"]=="17" and
             x["direction_slug"]==slug]
    assert matches, (sid,slug)
    assert all(x["page"]!=f"rozklady/17/{tt(d1 if slug=='chrzanow' else d2, '0334' if slug=='chrzanow' else '0311')['file']}" for x in matches)
    if sid in ("0311","0095"):
        assert any(x["display_direction"]==term for x in matches),(sid,term)

route_html=(ROOT/"linie/17.html").read_text(encoding="utf-8")
for d in (d1,d2):
    for s in d["route_stops"]:
        assert f'../rozklady/17/{s["file"]}' in route_html
assert route_html.count('href="../rozklady/17/0105-chrzanow.html"')==1
assert route_html.count('href="../rozklady/17/0105-metkow.html"')==1

print("OK: line 17 Excel SHA256 / 90 trips / 1898 stop times / 1808 scheduled departures")
print("OK: J,L,JL and J,K,JK letters / 2 termini / shortened starts / rendered pages and map")
