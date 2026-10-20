#!/usr/bin/env python3
"""Line 9: precise Excel Arkusz1 fingerprint and generated KMMZ data checks."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

trips = read("data/trips/009.json")
line = read("data/rozklady/linie/9.json")
config = read("data/import-config/9.json")
assert trips["line"] == line["line"] == "9"
assert trips["schema_version"] == "kmmz-trips-v1"
assert set(config["directions"]) == {"1", "2"}
assert len(line["directions"]) == 2
assert len(trips["trips"]) == 50
assert len(trips["route_patterns"]) == 4

# Fingerprint calculated independently directly from P.A.M. - Linia 9.xlsx,
# first worksheet, combining each course ID and its position/time (in min).
excel_rows = [
    [t["trip_id"], [
        [s["stop_sequence"], int(s["time"][:2])*60+int(s["time"][3:])]
        for s in t["stop_times"]]] for t in trips["trips"]
]
fingerprint = hashlib.sha256(
    json.dumps(excel_rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
).hexdigest()
assert fingerprint == "f4121b6c85f6c99bb554f3ab7a013735b946da4ea5ccdae0b7e4dd5f320c1459", fingerprint

counts = Counter((t["direction"], t["variant"], t["service_code"]) for t in trips["trips"])
assert sum(1 for t in trips["trips"] if t["direction"] == 1) == 25
assert sum(1 for t in trips["trips"] if t["direction"] == 2) == 25
assert Counter(t["service_code"] for t in trips["trips"]) == {"R":24, "SN":20, "SW":6}
assert Counter(t["direction"] for t in trips["trips"]) == {1:25, 2:25}
assert Counter(t["variant"] for t in trips["trips"] if t["direction"]==1) == {"0":15,"1":10}
assert Counter(t["variant"] for t in trips["trips"] if t["direction"]==2) == {"0":14,"1":11}
assert sum(len(t["stop_times"]) for t in trips["trips"]) == 1123
assert sum(len(t["stop_times"])-1 for t in trips["trips"]) == 1073

a,b = line["directions"]
assert a["slug"] == "okrezna-1" and b["slug"] == "okrezna-2"
assert [v["from_stop_id"] for v in a["direction_segments"]] == ["0015","0699"]
assert [v["name"] for v in a["direction_segments"]] == ["Jeżówka Świetlica","Wolbrom Nowa PKS"]
assert [v["from_stop_id"] for v in b["direction_segments"]] == ["0001","0711"]
assert [v["name"] for v in b["direction_segments"]] == ["Jeżówka Świetlica","Wolbrom Nowa PKS"]
assert b["variant_destinations"] == {"W":"Wolbrom Pod Lasem"}
assert b["legend"]["W"] == "do: Wolbrom Pod Lasem"
assert config["directions"]["2"]["legend"]["W"] == "do: Wolbrom Pod Lasem"
assert "variant_symbols" not in config["directions"]["1"]
assert config["directions"]["2"]["variant_symbols"] == {"1":"W"}
assert config["directions"]["2"]["variant_symbol_starts"] == {"1":"0711"}
assert config["directions"]["2"]["variant_symbol_ends"] == {"1":{"stop_id":"0001","occurrence":2}}

expected_routes = [
    "0015 0016 0017 0018 0001 0022 0694 0695 0696 0697 0698 0699 0700 0701 0702 0703 0704 0705 0706 0707 0708 0709 0710 0021 0001".split(),
    "0001 0022 0694 0695 0711 0712 0713 0714 0715 0716 0717 0718 0719 0720 0721 0722 0723 0709 0710 0021 0001 0029 0016 0015".split(),
]
geo=read("data/stops/wolbrom.geojson")
meta={f["properties"]["stop_id"]:f["properties"] for f in geo["features"]}
for direction,route in zip(line["directions"], expected_routes):
    assert [r["stop_id"] for r in direction["route_stops"]]==route
    assert len(direction["timetables"])==len(route)
    for stop in direction["route_stops"]:
        assert stop["stop_name"]==meta[stop["stop_id"]]["name"]
        assert stop["platform"]==str(meta[stop["stop_id"]]["platform"])
    assert len(set(s["file"] for s in direction["route_stops"]))==len(route)

assert a["timetables"][-1]["file"]=="0001-okrezna-1-koniec.html"
assert a["timetables"][-1]["arrival_only"] is True
assert a["timetables"][-1]["departures"] == {}
assert b["timetables"][20]["file"]=="0001-okrezna-2-ponownie.html"
assert b["timetables"][20]["stop_id"]=="0001"
assert b["timetables"][20]["departures"]["workday"] == sorted(b["timetables"][20]["departures"]["workday"])
assert b["timetables"][20]["departures"]["workday"] and all(not t.endswith("W") for t in b["timetables"][20]["departures"]["workday"])
assert all(t["direction_override"] == "Wolbrom Pod Lasem" for t in b["timetables"][20:23])
assert all(not value.endswith("W") for table in b["timetables"][20:23]
           for values in table["departures"].values() for value in values)
assert any(t.endswith("W") for t in b["timetables"][19]["departures"]["workday"])
assert b["timetables"][-1]["arrival_only"] is True
assert b["timetables"][-1]["arrival_direction"] == "Wolbrom Pod Lasem"

# Independently reconstruct all timetable positions, excluding each trip's
# last visit, and applying W only after position 0711 of direction 2.
days={"R":["workday"],"SN":["saturday","sunday"],"SW":["holiday"]}
for direction in line["directions"]:
    dirnum=1 if direction["slug"]=="okrezna-1" else 2
    for idx,table in enumerate(direction["timetables"]):
        expected={}
        for trip in trips["trips"]:
            if trip["direction"] != dirnum: continue
            for tm in trip["stop_times"][:-1]:
                if tm["stop_sequence"] != idx+1: continue
                suffix="W" if dirnum==2 and trip["variant"]=="1" and 4 <= idx < 20 else ""
                for day in days[trip["service_code"]]:
                    expected.setdefault(day,[]).append(tm["time"]+suffix)
        expected={k:sorted(v) for k,v in expected.items()}
        assert table["departures"]==expected, (dirnum,idx,table["stop_id"])
        if dirnum==1 or (dirnum==2 and (idx <= 3 or idx >= 20)):
            assert not any(v.endswith("W") for times in table["departures"].values() for v in times)

# Generated HTML and map data (generator runs before this test in Actions)
for direction in line["directions"]:
    for t in direction["timetables"]:
        path=ROOT/"rozklady"/"9"/t["file"]
        assert path.is_file(), str(path)
        txt=path.read_text(encoding="utf-8")
        assert len(re.findall(r'class="stop(?: variant)? current-stop"', txt)) == 1, t["file"]
        if t.get("arrival_only"):
            assert "Brak odjazdów tej linii" in txt
        if t["file"] == "0001-okrezna-2-ponownie.html":
            assert "Kierunek: Wolbrom Pod Lasem" in txt
            assert "07:29" in txt
        if t.get("direction_override"):
            assert "Kierunek: Wolbrom Pod Lasem" in txt
            assert "<sup>W</sup>" not in txt, t["file"]
            assert "Legenda" not in txt, t["file"]
        elif t["file"] == "0711-okrezna-2.html":
            assert "W</strong>" not in txt
            assert "do: Wolbrom Pod Lasem" in txt
            assert "<sup>W</sup>" in txt
        if t["file"] == "0015-okrezna-2.html":
            assert "Kierunek: Wolbrom Pod Lasem" in txt

page=(ROOT/"linie/9.html").read_text(encoding="utf-8")
assert page.count("0001-okrezna-1-koniec.html")==1
assert page.count("0001-okrezna-2-ponownie.html")==1
assert page.count('0001-okrezna-1.html')==1
assert page.count('0001-okrezna-2.html')==1

stop=read("data/odjazdy/0001.json")
line9=[x for x in stop["departures"] if x["line"]=="9"]
assert len(line9) == 85
assert len([x for x in line9 if x["page"].endswith("0001-okrezna-2-ponownie.html")])==15
assert not any(x["page"].endswith("0001-okrezna-1-koniec.html") for x in line9)
assert len([x for x in line9 if x["page"].endswith("0001-okrezna-2-ponownie.html")
            and x["display_direction"] == "Wolbrom Pod Lasem"
            and not x["symbols"]]) == 15
for stop_id in ("0029", "0016"):
    stop_data = read(f"data/odjazdy/{stop_id}.json")
    matches = [x for x in stop_data["departures"] if x["line"] == "9" and
               x["direction_slug"] == "okrezna-2"]
    assert matches and all(x["display_direction"] == "Wolbrom Pod Lasem"
                           and not x["symbols"] for x in matches), stop_id
print("OK: Excel SHA-256, 50 kursów, 1123 godziny, 1073 rzeczywiste odjazdy.")
print("OK: two route directions, repeated 0001, W after 0711, map and HTML pages.")
