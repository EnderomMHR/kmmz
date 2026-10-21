#!/usr/bin/env python3
"""Re-run the line 11 importer with Arkusz1-shaped rows, including empty cells."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("line11_import", ROOT / "tools/import-excel.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def data(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

config = data("data/import-config/11.json")
detail = data("data/trips/011.json")
line = data("data/rozklady/linie/11.json")
rows = []
row_no = 1
for d in line["directions"]:
    direction = 1 if d["slug"] == "tarnawa" else 2
    selected = [t for t in detail["trips"] if t["direction"] == direction]
    header = {0: "ID KURSU"}
    header.update({c + 1: t["trip_id"] for c, t in enumerate(selected)})
    rows.append((row_no, header))
    row_no += 1
    for sequence, stop in enumerate(d["route_stops"], start=1):
        cells = {0: f'{stop["stop_id"]}{stop["stop_name"]} ({stop["platform"]})'}
        for c, trip in enumerate(selected, start=1):
            match = next((s for s in trip["stop_times"] if s["stop_sequence"] == sequence), None)
            if match:
                cells[c] = match["time"]
        rows.append((row_no, cells))
        row_no += 1

with patch.object(mod, "read_arkusz1", return_value=rows):
    number, imported_line, imported_trips = mod.import_file(
        Path("line11-arkusz1.xlsx"), mod.metadata(), config
    )
assert number == "11"
assert imported_trips == detail, "Trip time or route mismatch with importer"
assert imported_line == line, "Variant suffixes, departures or destination mismatch"
print("OK: line 11 importer roundtrip, PZ, per-letter Z/P cutoffs and directions")
