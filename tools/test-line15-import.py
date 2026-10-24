#!/usr/bin/env python3
"""Line 15: round-trip every source Arkusz1 cell through the production importer."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("kmmz_line15_import",ROOT/"tools/import-excel.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

config=read("data/import-config/15.json")
expected_trips=read("data/trips/015.json")
expected_line=read("data/rozklady/linie/15.json")
rows=[]
row=1
for direction,d in enumerate(expected_line["directions"],1):
    selected=[t for t in expected_trips["trips"] if t["direction"]==direction]
    header={0:"ID KURSU"}
    header.update({column:t["trip_id"] for column,t in enumerate(selected,1)})
    rows.append((row,header));row+=1
    for seq,stop in enumerate(d["route_stops"],1):
        cells={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for column,trip in enumerate(selected,1):
            match=next((x for x in trip["stop_times"] if x["stop_sequence"]==seq),None)
            if match:
                cells[column]=match["time"]
        rows.append((row,cells));row+=1

with patch.object(mod,"read_arkusz1",return_value=rows):
    number,line,trips=mod.import_file(
        Path("P.A.M. - Linia 15.xlsx"),mod.metadata(),config
    )

assert number=="15"
assert trips==expected_trips,"Excel importer trip IDs, times, or stop sequences differ"
assert line==expected_line,"Excel importer generated line page/departure data differ"
print("OK: line 15 importer roundtrip: 56 trips, 2996 stop-times, all 107 stop positions")
