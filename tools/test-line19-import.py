#!/usr/bin/env python3
"""Reimport line 19's 59 courses with both directions and 12 route patterns.

The rows mirror the exact Arkusz1 stop-grid geometry from the user's XLSX.
"""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_import19", ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

config=load("data/import-config/19.json")
line=load("data/rozklady/linie/19.json")
detail=load("data/trips/019.json")
rows=[]
n=1
for dno,direction in enumerate(line["directions"],1):
    selected=[t for t in detail["trips"] if t["direction"]==dno]
    assert len(selected)==(29 if dno==1 else 30)
    rows.append((n,{0:"ID KURSU",**{col:t["trip_id"] for col,t in enumerate(selected,1)}}))
    n+=1
    for pos,stop in enumerate(direction["route_stops"],1):
        cells={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for col,trip in enumerate(selected,1):
            present=next((v for v in trip["stop_times"] if v["stop_sequence"]==pos),None)
            if present:
                assert present["stop_id"]==stop["stop_id"]
                cells[col]=present["time"]
        rows.append((n,cells))
        n+=1

assert len(rows)==53 # 2 headers, 25 + 26 stop rows
with patch.object(mod,"read_arkusz1",return_value=rows):
    no,actual_line,actual_trips=mod.import_file(
        Path("P.A.M. - Linia 19 (done).xlsx"),mod.metadata(),config
    )
assert no=="19"
assert actual_trips==detail,"Original trip IDs, patterns, sequences or times disagree with production importer"
assert actual_line==line,"Produced timetables, H/P/V cutoff letters or stop names disagree"
print("OK: line 19 importer roundtrip: 59 trips, 1351 times, 12 patterns, correct variants")
