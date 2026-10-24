#!/usr/bin/env python3
"""Regression: line 13 importer recreates every Excel time and both origins."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_import13",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))
config=read("data/import-config/13.json")
expected_line=read("data/rozklady/linie/13.json")
expected_trips=read("data/trips/013.json")
rows=[]
n=1
for direction_index,d in enumerate(expected_line["directions"],1):
    selected=[t for t in expected_trips["trips"] if t["direction"]==direction_index]
    header={0:"ID KURSU"}
    header.update({col:t["trip_id"] for col,t in enumerate(selected,1)})
    rows.append((n,header)); n+=1
    for pos,stop in enumerate(d["route_stops"],1):
        cells={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for col,t in enumerate(selected,1):
            item=next((x for x in t["stop_times"] if x["stop_sequence"]==pos),None)
            if item:
                cells[col]=item["time"]
        rows.append((n,cells)); n+=1
with patch.object(mod,"read_arkusz1",return_value=rows):
    number,line,trips=mod.import_file(Path("line13.xlsx"),mod.metadata(),config)
assert number=="13"
assert line==expected_line, "Line 13 importer differs from published timetable JSON"
assert trips==expected_trips, "Line 13 importer differs from original 1443 stop-times"
print("OK: line 13 importer roundtrip, 74 trips, 3 route patterns, short starts from 0483.")
