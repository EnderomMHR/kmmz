#!/usr/bin/env python3
"""Line 19 regression: exact Excel source, H/P/V letters, HTML and map data."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

config=load("data/import-config/19.json")
line=load("data/rozklady/linie/19.json")
src=load("data/trips/019.json")
trips=src["trips"]
assert src["line"]==line["line"]=="19"
assert src["schema_version"]=="kmmz-trips-v1"
assert len(trips)==59
assert sum(len(t["stop_times"]) for t in trips)==1351
assert sum(len(t["stop_times"])-1 for t in trips)==1292
assert len(src["route_patterns"])==12
assert len(line["directions"])==2
assert Counter((t["direction"],t["service_code"]) for t in trips)=={
    (1,"R"):12,(1,"SN"):10,(1,"SW"):7,
    (2,"R"):12,(2,"SN"):10,(2,"SW"):8
}
assert Counter((t["direction"],t["variant"]) for t in trips)=={
    (1,"0"):5,(1,"1"):6,(1,"2"):6,(1,"3"):4,
    (1,"4"):1,(1,"5"):2,(1,"6"):4,(1,"7"):1,
    (2,"0"):10,(2,"1"):9,(2,"2"):10,(2,"3"):1
}
# Independently calculated against the *uploaded* XLSX's Arkusz1:
# all 59 original IDs, physical row positions, and 1351 cached times in
# integer minutes. No other sheet's contents are used.
fingerprint=hashlib.sha256(json.dumps([
    [t["trip_id"],[[s["stop_sequence"],int(s["time"][:2])*60+int(s["time"][3:])]
    for s in t["stop_times"]]] for t in trips
],separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
assert fingerprint=="a18d76f057557da46cc3e0fb43b166153e946ab118c57ceddae13b0cc9460b6a",fingerprint

d1,d2=line["directions"]
assert [d["slug"] for d in (d1,d2)]==["psary","chrzanow"]
assert [d["name"] for d in (d1,d2)]==["Psary Centrum","Chrzanów Osiedle Młodości Witosa"]
assert [len(d["route_stops"]) for d in (d1,d2)]==[25,26]
assert [len(d["timetables"]) for d in (d1,d2)]==[25,26]
assert config["directions"]["1"]["variant_symbols"]=={
    "1":"V","2":"H","3":"P","4":"HP","5":"HV","6":"PV","7":"HPV"
}
assert config["directions"]["2"]["variant_symbols"]=={
    "1":"V","2":"H","3":"HV"
}
assert config["directions"]["1"]["variant_letter_ends"]=={
    "V":{"stop_id":"0119","occurrence":1},
    "H":{"stop_id":"1026","occurrence":1},
    "P":{"stop_id":"1168","occurrence":1}
}
assert config["directions"]["2"]["variant_letter_ends"]=={
    "H":{"stop_id":"1026","occurrence":1},
    "V":{"stop_id":"0092","occurrence":1}
}
assert d1["direction_segments"]==[
    {"from_stop_id":"1079","name":"Psary Centrum"},
    {"from_stop_id":"1168","name":"Psary Ostra Góra"}
]
assert d1["variant_destinations"]=={"P":"Psary Ostra Góra"}
assert d2["variant_destinations"]=={}
assert d1["legend"]=={
    "H":"przez: Trzebinia Harcerska Przychodnia",
    "P":"do: Psary Ostra Góra",
    "V":"przez: Chrzanów Valeo, z pominięciem: Trzebinia Berezka"
}
assert d2["legend"]=={
    "H":"przez: Trzebinia Harcerska Przychodnia",
    "V":"przez: Chrzanów Valeo, z pominięciem: Trzebinia Berezka"
}
assert all(d["legend_only_used_symbols"] is True for d in (d1,d2))
assert d1["route_stops"][0]["stop_id"]=="1079"
assert d1["route_stops"][-1]["stop_id"]=="1166"
assert d2["route_stops"][0]["stop_id"]=="1165"
assert d2["route_stops"][-1]["stop_id"]=="1082"
assert all(d["timetables"][-1]["arrival_only"] and
           not d["timetables"][-1]["departures"] for d in (d1,d2))

patterns={p["route_pattern_id"]:p for p in src["route_patterns"]}
assert len(patterns)==12
for t in trips:
    ss=t["stop_times"]
    assert [s["time"] for s in ss]==sorted(s["time"] for s in ss)
    assert [s["stop_sequence"] for s in ss]==sorted(s["stop_sequence"] for s in ss)
    pattern=patterns[t["route_pattern_id"]]["stop_ids"]
    assert [s["stop_id"] for s in ss]==pattern[-len(ss):],t["trip_id"]
    ids={s["stop_id"] for s in ss}
    if t["direction"]==1:
        labels=config["directions"]["1"]["variant_symbols"].get(t["variant"],"")
        assert ("0119" in ids)==("V" in labels)
        assert ("0120" in ids)==("V" not in labels)
        assert ("1026" in ids)==("H" in labels)
        assert (ss[-1]["stop_id"]=="1166")==("P" in labels)
    else:
        labels=config["directions"]["2"]["variant_symbols"].get(t["variant"],"")
        assert ("0092" in ids)==("V" in labels)
        assert ("0091" in ids)==("V" not in labels)
        assert ("1026" in ids)==("H" in labels)
        assert ss[0]["stop_id"] in ("1165","1168")
        assert ss[-1]["stop_id"]=="1082"

assert Counter(t["stop_times"][0]["stop_id"] for t in trips if t["direction"]==2)=={
    "1165":11,"1168":19
}
assert Counter(t["stop_times"][-1]["stop_id"] for t in trips if t["direction"]==1)=={
    "1168":19,"1166":10
}

def tt(direction,sid):
    items=[x for x in direction["timetables"] if x["stop_id"]==sid]
    assert len(items)==1,(direction["name"],sid)
    return items[0]
def letters(t):
    return set("".join(s[5:] for v in t["departures"].values() for s in v))
def departures(t):
    return sum(len(v) for v in t["departures"].values())

assert letters(tt(d1,"1079"))=={"H","P","V"}
assert "V" not in letters(tt(d1,"0119"))
assert "V" not in letters(tt(d1,"0120"))
assert "H" not in letters(tt(d1,"1026"))
assert "H" not in letters(tt(d1,"0123"))
assert "P" in letters(tt(d1,"1304"))
assert letters(tt(d1,"1168"))==set()
assert departures(tt(d1,"1168"))==13  # 10 P courses, 3 SN expanded for both weekend days
assert departures(tt(d1,"1166"))==0
assert "H" in letters(tt(d2,"0088"))
assert "H" not in letters(tt(d2,"1026"))
assert "V" not in letters(tt(d2,"0092"))
assert letters(tt(d2,"0397"))==set()
assert departures(tt(d2,"1082"))==0

# Check the canonical site route links, all generated pages, used legends,
# correct displayed destination from Psary Centrum, and no fake termini.
routepage=(ROOT/"linie/19.html").read_text(encoding="utf-8")
for direction,d in enumerate((d1,d2),1):
    for idx,(route,table) in enumerate(zip(d["route_stops"],d["timetables"])):
        assert f'../rozklady/19/{route["file"]}' in routepage
        assert route["file"]==table["file"]
        expected=(
            "Psary Ostra Góra" if direction==1 and idx>=23
            else "Psary Centrum" if direction==1
            else "Chrzanów Osiedle Młodości Witosa"
        )
        html=(ROOT/"rozklady"/"19"/table["file"]).read_text(encoding="utf-8")
        assert f'<div class="route-title">Kierunek: {expected}</div>' in html,table["file"]
        assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,table["file"]
        assert len(re.findall(r'<div class="time">',html))==departures(table),table["file"]
        used=letters(table)
        for letter in d["legend"]:
            assert (f'<span class="symbol">{letter}</span>' in html)==(letter in used),(
                table["file"],letter
            )
        assert ('<div class="legend">' in html)==bool(used),table["file"]

# Map must show only real departures. 'P' changes displayed destination
# towards Ostra Góra; at the splitting point 1168 the name is direct.
for sid,slug in (
    ("1079","psary"),("1168","psary"),("1165","chrzanow"),
    ("1168","chrzanow"),("1026","psary"),("1026","chrzanow"),
    ("0119","psary"),("0092","chrzanow")
):
    all_stops=load(f"data/odjazdy/{sid}.json")["departures"]
    actual=[x for x in all_stops if x["line"]=="19" and x["direction_slug"]==slug]
    d=d1 if slug=="psary" else d2
    timetable=tt(d,sid)
    assert len(actual)==departures(timetable),(sid,slug,len(actual))
    assert all(x["page"]==f'rozklady/19/{timetable["file"]}' for x in actual)
    if sid=="1079":
        assert any(x["display_direction"]=="Psary Ostra Góra" and
                   "P" in x["symbols"] for x in actual)
    if sid=="1168" and slug=="psary":
        assert actual
        assert all(x["display_direction"]=="Psary Ostra Góra" and
                   x["main_direction"]=="Psary Ostra Góra" and
                   not x["symbols"] for x in actual)
    if sid in ("0119","0092"):
        assert all("V" not in x["symbols"] for x in actual)

print("OK: line 19 original Excel SHA256, 59 courses, 1351 times, 12 technical patterns")
print("OK: H/P/V combinations, used-only legends, 51 HTML pages and map departures")
