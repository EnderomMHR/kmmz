#!/usr/bin/env python3
"""KMMZ line 11: independently check the Excel times and rendered output."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))
cfg = read("data/import-config/11.json")
detail = read("data/trips/011.json")
line = read("data/rozklady/linie/11.json")
assert detail["line"] == line["line"] == "11"
assert len(detail["trips"]) == 84
assert sum(len(t["stop_times"]) for t in detail["trips"]) == 3254
assert sum(len(t["stop_times"])-1 for t in detail["trips"]) == 3170
assert Counter((t["direction"], t["service_code"]) for t in detail["trips"]) == {
 (1,"R"):17, (1,"S"):13,(1,"N"):8,(1,"SW"):4,
 (2,"R"):17, (2,"S"):13,(2,"N"):8,(2,"SW"):4,
}
assert Counter((t["direction"],t["variant"]) for t in detail["trips"]) == {
 (1,"0"):21,(1,"1"):5,(1,"2"):4,(1,"3"):12,(2,"0"):25,(2,"1"):17
}
# SHA-256 of the corrected Excel's Arkusz1 content: all trip IDs, original
# stop positions (including skipped rows), and all 3254 HH:MM cell values.
# Computed independently from P.A.M. - Linia 11.xlsx.
fingerprint=hashlib.sha256(json.dumps([
  [t["trip_id"], [[s["stop_sequence"],s["time"]] for s in t["stop_times"]]]
  for t in detail["trips"]
], separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
assert fingerprint == "143aa2936481c7450a69892f4ce3fc46ba38a1e9a16f95815ae5af07f86713c9", fingerprint
assert not any(t["trip_id"]=="011-1-2-R-03" for t in detail["trips"])
assert len([t for t in detail["trips"] if t["trip_id"]=="011-1-1-R-03"]) == 1
assert len(line["directions"]) == 2
d1,d2=line["directions"]
assert (d1["slug"],d2["slug"]) == ("tarnawa","olkusz")
assert (d1["name"],d2["name"]) == ("Tarnawa Podlas","Olkusz Dworzec PKS")
assert len(d1["route_stops"]) == len(d1["timetables"]) == 44
assert len(d2["route_stops"]) == len(d2["timetables"]) == 45
assert cfg["directions"]["1"]["variant_symbols"] == {"1":"Z","2":"P","3":"PZ"}
assert cfg["directions"]["2"]["variant_symbols"] == {"1":"Z"}
assert d1["legend"] == {"P":"do: Poręba Laskowska","Z":"przez: Zagórowa"}
assert d2["legend"] == {"Z":"przez: Zagórowa"}
assert d1["variant_destinations"]["P"] == "Poręba Laskowska"
assert d1["direction_segments"] == [
    {"from_stop_id":"0200","name":"Tarnawa Podlas"},
    {"from_stop_id":"0755","name":"Poręba Laskowska"}
]
assert d1["legend_only_used_symbols"] and d2["legend_only_used_symbols"]

def timetable(direction, sid):
    matches=[t for t in direction["timetables"] if t["stop_id"] == sid]
    assert len(matches)==1,sid
    return matches[0]

def suffixes(t):
    return {s[5:] for values in t["departures"].values() for s in values}
assert "PZ" in suffixes(timetable(d1,"0200"))
assert "PZ" in suffixes(timetable(d1,"0777"))
assert "Z" in suffixes(timetable(d1,"0777"))
assert "P" in suffixes(timetable(d1,"0770"))
assert "PZ" not in suffixes(timetable(d1,"0770"))
assert "Z" not in "".join(suffixes(timetable(d1,"0770")))
assert suffixes(timetable(d1,"0755")) == {""}
for sid in ("0755","0752","0751","0749"):
    assert suffixes(timetable(d1,sid)) == {""}, sid
assert timetable(d1,"0747")["arrival_only"]
assert not timetable(d1,"0747")["departures"]
assert timetable(d2,"0200")["arrival_only"]
assert not timetable(d2,"0200")["departures"]
assert "Z" in suffixes(timetable(d2,"0766"))
assert suffixes(timetable(d2,"0770")) == {""}
assert "Z" not in "".join(suffixes(timetable(d2,"0769")))

# Pages and displayed destinations (per occurrence; no artificial arrivals).
checks=[
    (d1,"0200","Kierunek: Tarnawa Podlas","PZ",("P","Z")),
    (d1,"0777","Kierunek: Tarnawa Podlas","PZ",("P","Z")),
    (d1,"0770","Kierunek: Tarnawa Podlas","P",("P",)),
    (d1,"0755","Kierunek: Poręba Laskowska",None,()),
    (d1,"0752","Kierunek: Poręba Laskowska",None,()),
    (d1,"0747","Kierunek: Poręba Laskowska",None,()),
    (d2,"0756","Kierunek: Olkusz Dworzec PKS","Z",("Z",)),
    (d2,"0766","Kierunek: Olkusz Dworzec PKS","Z",("Z",)),
    (d2,"0770","Kierunek: Olkusz Dworzec PKS",None,()),
    (d2,"0200","Kierunek: Olkusz Dworzec PKS",None,()),
]
for direction,sid,heading,suffix,letters in checks:
    t=timetable(direction,sid)
    path=ROOT/"rozklady"/"11"/t["file"]
    assert path.is_file(),path
    html=path.read_text(encoding="utf-8")
    assert f'<div class="route-title">{heading}</div>' in html, t["file"]
    assert len(re.findall(r'class="stop(?: variant)? current-stop"',html))==1,t["file"]
    if suffix:
        assert f"<sup>{suffix}</sup>" in html,t["file"]
    legends=re.findall(r'<div class="legend-row"><span class="symbol">([^<]+)</span>',html)
    assert legends==list(letters),(t["file"],legends)
    if t.get("arrival_only"):
        assert "Brak odjazdów tej linii" in html
        assert '<div class="time">' not in html

route=(ROOT/"linie/11.html").read_text(encoding="utf-8")
for direction in (d1,d2):
    for s in direction["route_stops"]:
        assert f'../rozklady/11/{s["file"]}' in route, s["file"]
assert 'href="../11/' not in route

physical=read("data/odjazdy/0200.json")
departures=[x for x in physical["departures"] if x["line"]=="11"]
assert len(departures)==42
assert not any(x["page"].endswith("0200-olkusz.html") for x in departures)
assert any(x["display_direction"] == "Poręba Laskowska"
           and x["symbols"]==["P","Z"] for x in departures)
assert any(x["display_direction"] == "Tarnawa Podlas"
           and x["symbols"]==["Z"] for x in departures)
for sid in ("0755","0752","0751","0749"):
    output=read(f"data/odjazdy/{sid}.json")
    dep=[x for x in output["departures"] if x["line"]=="11"]
    assert dep and all(x["display_direction"]=="Poręba Laskowska"
                      and x["symbols"]==[] for x in dep),sid
print("OK: Line 11, 84 trips, corrected Excel fingerprint, 3170 departures")
print("OK: PZ sorted, Z ends at the detour, P ends after Tarnawa, Poręba destination")
