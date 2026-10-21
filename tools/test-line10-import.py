#!/usr/bin/env python3
"""Re-import line 10 with Arkusz1-shaped rows and compare to committed data."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_import",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def read(s):
    return json.loads((ROOT/s).read_text(encoding="utf-8"))
cfg=read("data/import-config/10.json")
detail=read("data/trips/010.json")
line=read("data/rozklady/linie/10.json")
rows=[]
row=1
for d in line["directions"]:
    direction=int(d["slug"][-1])
    selected=[t for t in detail["trips"] if t["direction"]==direction]
    header={0:"ID KURSU"}
    header.update({k+1:t["trip_id"] for k,t in enumerate(selected)})
    rows.append((row,header));row+=1
    for seq,stop in enumerate(d["route_stops"],start=1):
        fields={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for col,t in enumerate(selected,start=1):
            v=next((s for s in t["stop_times"] if s["stop_sequence"]==seq),None)
            if v:fields[col]=v["time"]
        rows.append((row,fields));row+=1
with patch.object(mod,"read_arkusz1",return_value=rows):
    number,reconstructed,retrips=mod.import_file(Path("10.xlsx"),mod.metadata(),cfg)
assert number=="10"
assert retrips == detail, "Importer changed trips / stop-sequences / service codes"
assert reconstructed == line, "Importer changed timetable pages or departures"
print("OK: importer reproduces line 10 from Arkusz1-shaped input including short start 0106.")
