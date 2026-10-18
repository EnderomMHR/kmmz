#!/usr/bin/env python3
"""Regression: terminal arrival times remain in trips, not in departure tables."""
import json
import sys
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
DAYS={"R":["workday"],"S":["saturday"],"N":["sunday"],"SN":["saturday","sunday"],"SW":["holiday"]}

for number in (5,6):
    trip_data=json.loads((ROOT/f"data/trips/{number:03d}.json").read_text(encoding="utf-8"))
    line_data=json.loads((ROOT/f"data/rozklady/linie/{number}.json").read_text(encoding="utf-8"))
    config=json.loads((ROOT/f"data/import-config/{number}.json").read_text(encoding="utf-8"))
    expected={}
    for trip in trip_data["trips"]:
        symbol=config["directions"][str(trip["direction"])].get("variant_symbols",{}).get(trip["variant"],"")
        for point in trip["stop_times"][:-1]:
            key=(trip["direction"],point["stop_id"])
            for day in DAYS[trip["service_code"]]:
                expected.setdefault(key,{}).setdefault(day,[]).append(point["time"]+symbol)
    actual={}
    for dnum,direction in enumerate(line_data["directions"],start=1):
        for table in direction["timetables"]:
            key=(dnum,table["stop_id"])
            actual[key]={day: sorted(values) for day,values in table["departures"].items() if values}
            assert actual[key]=={day: sorted(values) for day,values in expected.get(key,{}).items()},(
                number,key,actual[key],expected.get(key,{}))
    print(f"OK: {number}: {len(trip_data['trips'])} course terminal arrivals excluded")
