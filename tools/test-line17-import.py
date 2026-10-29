#!/usr/bin/env python3
"""Round-trip the exact 90 original line 17 trips through the production importer."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_excel17",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

config=load("data/import-config/17.json")
expected_line=load("data/rozklady/linie/17.json")
expected_trips=load("data/trips/017.json")
rows=[]
rno=1
for dno,direction in enumerate(expected_line["directions"],1):
    courses=[t for t in expected_trips["trips"] if t["direction"]==dno]
    columns={0:"ID KURSU",**{i:t["trip_id"] for i,t in enumerate(courses,1)}}
    rows.append((rno,columns))
    rno+=1
    for pos,stop in enumerate(direction["route_stops"],1):
        cells={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for i,t in enumerate(courses,1):
            visit=next((item for item in t["stop_times"]
                        if item["stop_sequence"]==pos),None)
            if visit:
                assert visit["stop_id"]==stop["stop_id"]
                cells[i]=visit["time"]
        rows.append((rno,cells))
        rno+=1

assert len(rows)==60
with patch.object(mod,"read_arkusz1",return_value=rows):
    line_no,actual_line,actual_trips=mod.import_file(
        Path("P.A.M. - Linia 17 (done).xlsx"),mod.metadata(),config
    )
assert line_no=="17"
assert actual_trips==expected_trips, "Trip IDs, original stop sequence, route patterns or times differ"
assert actual_line==expected_line, "Expected Janina/destination variants, timetables, and per-stop letters differ"
print("OK: line 17 — importer roundtrip: 90 trips, 1898 stop-times, 8 patterns, both directions")
