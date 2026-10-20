#!/usr/bin/env python3
"""Regression: importer rebuilds line 9 exact visits and conditional W flags."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("importexcel",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cfg=json.loads((ROOT/"data/import-config/9.json").read_text(encoding="utf-8"))
exp_trips=json.loads((ROOT/"data/trips/009.json").read_text(encoding="utf-8"))
exp_line=json.loads((ROOT/"data/rozklady/linie/9.json").read_text(encoding="utf-8"))
stops=mod.metadata()
rows=[]
row_number=1
for direction in exp_line["directions"]:
    selected=[t for t in exp_trips["trips"] if str(t["direction"])==direction["slug"][-1]]
    header={0:"ID KURSU"}
    header.update({i+1:t["trip_id"] for i,t in enumerate(selected)})
    rows.append((row_number,header))
    row_number += 1
    for index,stop in enumerate(direction["route_stops"]):
        cells={0:stop["stop_id"]+stop["stop_name"]+" ("+stop["platform"]+")"}
        for col,trip in enumerate(selected,1):
            found=next((t for t in trip["stop_times"] if t["stop_sequence"]==index+1),None)
            if found: cells[col]=found["time"]
        rows.append((row_number,cells))
        row_number+=1
with patch.object(mod,"read_arkusz1",return_value=rows):
    line_number,line,trips=mod.import_file(Path("9.xlsx"),stops,cfg)
assert line_number=="9"
assert trips["trips"] == exp_trips["trips"]
assert {t["route_pattern_id"]:t for t in trips["route_patterns"]} == {t["route_pattern_id"]:t for t in exp_trips["route_patterns"]}
assert line == exp_line
print("OK: import produces original 50 trips, two loop directions, split 0001 and W from 0711.")
