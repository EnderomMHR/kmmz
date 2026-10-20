#!/usr/bin/env python3
"""Walidacja importu linii 8: Excel Arkusz1, pętla 0200 i rzeczywiste odjazdy."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

line = read("data/rozklady/linie/8.json")
details = read("data/trips/008.json")
config = read("data/import-config/8.json")
assert line["line"] == details["line"] == "8"
assert details["schema_version"] == "kmmz-trips-v1"
assert set(config["directions"]) == {"1"}
assert set(details["services"]) == {"N", "R", "S", "SW"}
assert len(line["directions"]) == 1
assert len(details["route_patterns"]) == 1
direction = line["directions"][0]
assert direction["slug"] == config["directions"]["1"]["slug"] == "okrezna"
assert direction["name"] == config["directions"]["1"]["name"] == "Olkusz Dworzec PKS"
assert direction["variant_destinations"] == direction["legend"] == {}
expected_segments = [
    {"from_stop_id": "0200", "name": "Olkusz Pomorzany Wzniesienie"},
    {"from_stop_id": "0688", "name": "Olkusz Dworzec PKS"},
]
assert direction["direction_segments"] == expected_segments
assert config["directions"]["1"]["direction_segments"] == expected_segments

ids = [
    "0200", "0228", "0238", "0685", "0686", "0687", "0688", "0689",
    "0690", "0691", "0692", "0693", "0173", "0174", "0199", "0200",
]
offsets = [0, 2, 5, 6, 7, 10, 12, 14, 16, 17, 18, 19, 21, 23, 24, 26]
departures_by_service = {
    "R": "04:41 05:42 07:12 08:29 09:23 11:11 11:58 13:13 14:29 16:00 16:40 18:42 19:15 20:10",
    "S": "05:07 06:45 07:53 09:21 10:03 12:02 12:50 14:14 15:36 16:50 19:31 19:46 21:43",
    "N": "05:28 06:39 08:37 09:27 11:31 12:50 14:11 15:38 17:20 18:26 21:49",
    "SW": "09:27 11:31 12:50 14:11 15:38",
}
days = {"R": ["workday"], "S": ["saturday"], "N": ["sunday"], "SW": ["holiday"]}

def add_minutes(hour, delta):
    h, m = map(int, hour.split(":"))
    t = h * 60 + m + delta
    return f"{t // 60:02d}:{t % 60:02d}"

assert details["route_patterns"] == [{
    "route_pattern_id": "008-1-0", "direction": 1,
    "variant": "0", "stop_ids": ids,
}]
assert [row["stop_id"] for row in direction["route_stops"]] == ids
assert len(direction["route_stops"]) == 16
assert len(direction["timetables"]) == 16
assert [row["stop_id"] for row in direction["timetables"][:-1]] == list(dict.fromkeys(ids))
assert direction["timetables"][-1] == {
    "stop_id": "0200", "stop_name": "Olkusz Dworzec PKS",
    "platform": "0", "file": "0200-okrezna-koniec.html",
    "arrival_only": True, "departures": {},
}
assert direction["route_stops"][-1]["file"] == "0200-okrezna-koniec.html"

expected_trips = [
    (f"008-1-0-{service}-{index:02d}", service, start)
    for service, starts in departures_by_service.items()
    for index, start in enumerate(starts.split(), start=1)
]
assert len(details["trips"]) == len(expected_trips) == 43
for trip, (trip_id, service, start) in zip(details["trips"], expected_trips):
    assert trip["trip_id"] == trip_id
    assert trip["line"] == "8" and trip["direction"] == 1
    assert trip["variant"] == "0" and trip["route_pattern_id"] == "008-1-0"
    assert trip["service_code"] == service
    assert [s["stop_id"] for s in trip["stop_times"]] == ids
    assert [s["stop_sequence"] for s in trip["stop_times"]] == list(range(1, 17))
    assert [s["time"] for s in trip["stop_times"]] == [
        add_minutes(start, offset) for offset in offsets
    ]
    assert trip["stop_times"][0]["stop_id"] == trip["stop_times"][-1]["stop_id"] == "0200"

# Oczekiwane godziny budujemy od nowa z pełnej sekwencji, BEZ ostatniej
# wizyty danego kursu. Ta wizyta to przyjazd, nie odjazd.
expected = defaultdict(lambda: defaultdict(list))
for trip in details["trips"]:
    for stop in trip["stop_times"][:-1]:
        for day in days[trip["service_code"]]:
            expected[stop["stop_id"]][day].append(stop["time"])
total_departures = 0
for item in direction["timetables"]:
    if item.get("arrival_only"):
        assert item["departures"] == {}
        continue
    key = item["stop_id"]
    wanted = expected[key]
    actual = item["departures"]
    assert set(actual) == set(wanted), (key, actual.keys(), wanted.keys())
    for day in wanted:
        assert actual[day] == sorted(wanted[day]), (key, day)
        assert not any(re.search(r"[A-Za-z]$", t) for t in actual[day])
        total_departures += len(actual[day])

assert len(details["trips"]) * len(ids) == 688
assert total_departures == 645
assert all(sum(len(times) for times in t["departures"].values()) == 43
           for t in direction["timetables"] if not t.get("arrival_only"))

# Weryfikacja nazw i peronów na podstawie oficjalnej bazy KMMZ.
geo = read("data/stops/olkusz.geojson")
stop_meta = {f["properties"]["stop_id"]: f["properties"] for f in geo["features"]}
for stop in direction["route_stops"]:
    meta = stop_meta[stop["stop_id"]]
    assert stop["stop_name"] == meta["name"], stop
    assert stop["platform"] == str(meta["platform"]), stop
    expected_file = ("0200-okrezna-koniec.html" if stop is direction["route_stops"][-1]
                     else f'{stop["stop_id"]}-okrezna.html')
    assert stop["file"] == expected_file

# Istniejąca strona przebiegu linii 8 wskazuje na każdy przystanek.
page = (ROOT / "linie/8.html").read_text(encoding="utf-8")
for stop_id in ids:
    assert f"../rozklady/8/{stop_id}-okrezna.html" in page
assert page.count('href="../rozklady/8/0200-okrezna-koniec.html"') == 1
assert page.count('href="../rozklady/8/0200-okrezna.html"') == 1

print("OK: linia 8, 43 kursy (14 R, 13 S, 11 N, 5 SW), 688 czasów, 645 odjazdów.")
print("OK: 16 pozycji, 15 przystanków; 0200 jest początkiem i końcem kursu.")
print("OK: końcowe przyjazdy nie trafiają do odjazdów; wariant wyłącznie 0.")
