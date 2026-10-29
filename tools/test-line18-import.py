#!/usr/bin/env python3
"""Replay 96 line 18 courses in the production importer (Arkusz1-shaped data)."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_excel18",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

config=read("data/import-config/18.json")
line=read("data/rozklady/linie/18.json")
detail=read("data/trips/018.json")
rows=[]
row_no=1
for dno,d in enumerate(line["directions"],1):
    courses=[t for t in detail["trips"] if t["direction"]==dno]
    assert len(courses)==48
    rows.append((row_no,{0:"ID KURSU",**{i:t["trip_id"] for i,t in enumerate(courses,1)}}))
    row_no+=1
    for pos,stop in enumerate(d["route_stops"],1):
        cells={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for col,trip in enumerate(courses,1):
            visit=next((v for v in trip["stop_times"] if v["stop_sequence"]==pos),None)
            if visit:
                assert visit["stop_id"]==stop["stop_id"]
                cells[col]=visit["time"]
        rows.append((row_no,cells))
        row_no+=1

with patch.object(mod,"read_arkusz1",return_value=rows):
    line_no,actual_line,actual_trips=mod.import_file(
        Path("P.A.M. - Linia 18.xlsx"),mod.metadata(),config
    )
assert line_no=="18"
assert actual_trips==detail,"Course IDs, stop patterns, and all Excel stop-times must match"
assert actual_line==line,"Generated timetable pages, Z labels or directions must match"
print("OK: line 18 reimported 96 courses, 2682 stop-times, 3 patterns, 2 directions")
