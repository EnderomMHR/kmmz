#!/usr/bin/env python3
"""Recreate line 12 through the unmodified Excel importer, retaining all cells."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_excel12",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

config=load("data/import-config/12.json")
expected_trips=load("data/trips/012.json")
expected_line=load("data/rozklady/linie/12.json")
rows=[]
row=1
for direction in expected_line["directions"]:
    direction_no=1 if direction["slug"]=="metkow" else 2
    courses=[t for t in expected_trips["trips"] if t["direction"]==direction_no]
    header={0:"ID KURSU"}
    header.update({c:t["trip_id"] for c,t in enumerate(courses,1)})
    rows.append((row,header))
    row+=1
    for sequence,stop in enumerate(direction["route_stops"],1):
        cells={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for c,trip in enumerate(courses,1):
            if trip["stop_times"][sequence-1]["stop_sequence"]!=sequence:
                raise AssertionError("Discontinuous course")
            cells[c]=trip["stop_times"][sequence-1]["time"]
        rows.append((row,cells))
        row+=1
with patch.object(mod,"read_arkusz1",return_value=rows):
    number,line,trips=mod.import_file(Path("12.xlsx"),mod.metadata(),config)
assert number=="12"
assert trips==expected_trips, "Importer trip/time mismatch"
assert line==expected_line, "Importer pages and departure mismatch"
print("OK: line 12 importer roundtrip, all routes, all 2723 times, SN/SW days.")
