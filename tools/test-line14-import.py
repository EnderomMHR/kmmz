#!/usr/bin/env python3
"""Re-import full line 14 using Arkusz1-shaped rows from original stop-times."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_excel14",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

cfg=read("data/import-config/14.json")
line=read("data/rozklady/linie/14.json")
trips=read("data/trips/014.json")
rows=[];number=1
for d in line["directions"]:
    direction=1 if d["slug"]=="chrzanow" else 2
    selected=[t for t in trips["trips"] if t["direction"]==direction]
    header={0:"ID KURSU"}
    header.update({c:t["trip_id"] for c,t in enumerate(selected,1)})
    rows.append((number,header));number+=1
    for pos,s in enumerate(d["route_stops"],1):
        cells={0:f'{s["stop_id"]}{s["stop_name"]} ({s["platform"]})'}
        for c,t in enumerate(selected,1):
            item=next((x for x in t["stop_times"] if x["stop_sequence"]==pos),None)
            if item:cells[c]=item["time"]
        rows.append((number,cells));number+=1
with patch.object(mod,"read_arkusz1",return_value=rows):
    n,actual_line,actual_trips=mod.import_file(Path("P.A.M. - Linia 14 (done).xlsx"),mod.metadata(),cfg)
assert n=="14"
assert actual_trips==trips, "Course IDs, original stop positions, or times differ"
assert actual_line==line, "G/S symbol cutoffs, direction segments, routes, or departure values differ"
print("OK: line14 full importer roundtrip, 68 courses, 2289 stop times, independent G+S letters")
