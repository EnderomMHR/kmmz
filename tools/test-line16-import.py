#!/usr/bin/env python3
"""Re-import all 47 line 16 courses through the current production importer."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kmmz_excel16", ROOT / "tools/import-excel.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

config=read("data/import-config/16.json")
expected_trips=read("data/trips/016.json")
expected_line=read("data/rozklady/linie/16.json")
courses=expected_trips["trips"]
route=expected_line["directions"][0]["route_stops"]
rows=[
    (2,{0:"ID KURSU",**{col:t["trip_id"] for col,t in enumerate(courses,1)}})
]
for seq,stop in enumerate(route,1):
    cells={0:f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
    for col,course in enumerate(courses,1):
        record=course["stop_times"][seq-1]
        assert record["stop_sequence"]==seq
        assert record["stop_id"]==stop["stop_id"]
        cells[col]=record["time"]
    rows.append((seq+2,cells))

with patch.object(mod,"read_arkusz1",return_value=rows):
    line_no,line,trips=mod.import_file(
        Path("P.A.M. - Linia 16.xlsx"),mod.metadata(),config
    )

assert line_no=="16"
assert trips==expected_trips, "Importer produced a different list of courses"
assert line==expected_line, "Importer changed stop occurrence/segment/timetable data"
print("OK: line 16: 47 courses / 752 times roundtrip with duplicated 0200 and segment switch")
