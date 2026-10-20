#!/usr/bin/env python3
"""Regression: repeated physical stop IDs must not create phantom departures."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "kmmz_import_excel", Path(__file__).resolve().parent / "import-excel.py"
)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def build_rows(stops, hours, trip_id="008-1-0-R-01"):
    rows = [(1, {0: "ID KURSU", 1: trip_id, 3: "Czas narastająco"})]
    for index, (sid, hour) in enumerate(zip(stops, hours), start=2):
        rows.append((index, {0: f"{sid} Stop {sid}", 1: hour, 3: str(index - 2)}))
    return rows


def import_mock(rows, stops):
    known = {sid: {"stop_id": sid, "stop_name": f"Stop {sid}",
                   "platform": "0", "zone": "Test"} for sid in set(stops)}
    cfg = {"directions": {"1": {"slug": "okrezna", "name": "Pętla"}}}
    with patch.object(importer, "read_arkusz1", return_value=rows):
        return importer.import_file(Path("8.xlsx"), known, cfg)


class RepeatedStopsTests(unittest.TestCase):
    def test_round_trip_same_origin_and_terminus(self):
        stops = ["0200", "0228", "0238", "0200"]
        rows = build_rows(stops, ["08:00", "08:05", "08:11", "08:26"])
        _, line, detail = import_mock(rows, stops)
        self.assertEqual(detail["route_patterns"][0]["stop_ids"], stops)
        self.assertEqual([s["stop_id"] for s in detail["trips"][0]["stop_times"]], stops)
        self.assertEqual([s["stop_sequence"] for s in detail["trips"][0]["stop_times"]],
                         [1, 2, 3, 4])
        direction = line["directions"][0]
        self.assertEqual([s["stop_id"] for s in direction["route_stops"]], stops)
        self.assertEqual([s["stop_id"] for s in direction["timetables"]],
                         ["0200", "0228", "0238", "0200"])
        self.assertEqual(direction["route_stops"][-1]["file"],
                         "0200-okrezna-koniec.html")
        self.assertEqual(direction["timetables"][-1], {
            "stop_id": "0200", "stop_name": "Stop 0200",
            "platform": "0", "file": "0200-okrezna-koniec.html",
            "arrival_only": True, "departures": {},
        })
        times = {t["stop_id"]: t["departures"]
                 for t in direction["timetables"] if not t.get("arrival_only")}
        self.assertEqual(times["0200"]["workday"], ["08:00"])
        self.assertEqual(times["0228"]["workday"], ["08:05"])
        self.assertEqual(times["0238"]["workday"], ["08:11"])
        self.assertEqual(detail["trips"][0]["stop_times"][-1]["time"], "08:26")

    def test_intermediate_revisit_is_real_departure(self):
        stops = ["0200", "0228", "0200", "0238", "0200"]
        rows = build_rows(stops, ["08:00", "08:05", "08:10", "08:15", "08:20"])
        _, line, detail = import_mock(rows, stops)
        direction = line["directions"][0]
        self.assertEqual([s["stop_id"] for s in direction["route_stops"]], stops)
        pages = {t["file"]: t for t in direction["timetables"]}
        self.assertEqual(direction["timetables"][-1]["file"], "0200-okrezna-koniec.html")
        self.assertEqual(direction["timetables"][-1]["departures"], {})
        self.assertEqual(pages["0200-okrezna.html"]["departures"]["workday"], ["08:00"])
        self.assertEqual(pages["0200-okrezna-ponownie.html"]["departures"]["workday"], ["08:10"])
        self.assertEqual(pages["0238-okrezna.html"]["departures"]["workday"], ["08:15"])
        self.assertNotIn("08:20", str(direction["timetables"]))
        self.assertEqual(len(detail["route_patterns"][0]["stop_ids"]), 5)

    def test_different_starts_with_same_loop_variant(self):
        trips = [
            {"trip_id": "008-1-0-R-01", "direction": 1, "variant": "0",
             "route_pattern_id": "008-1-0",
             "stop_times": [{"stop_id": s} for s in ["0200", "0228", "0238", "0200"]]},
            {"trip_id": "008-1-0-R-02", "direction": 1, "variant": "0",
             "route_pattern_id": "008-1-0",
             "stop_times": [{"stop_id": s} for s in ["0228", "0238", "0200"]]},
        ]
        patterns = importer.infer_variant_patterns(trips)
        self.assertEqual(patterns["008-1-0"]["stop_ids"],
                         ["0200", "0228", "0238", "0200"])

    def test_merge_loops_when_shorter_block_comes_first(self):
        routes = [
            ["0228", "0238", "0200"],
            ["0200", "0228", "0238", "0200"],
            ["0200", "0228", "0238", "0200"],
        ]
        self.assertEqual(importer.merge_direction_stops(routes),
                         ["0200", "0228", "0238", "0200"])

    def test_merge_variant_branch_and_reject_reversed_traversal(self):
        self.assertEqual(
            importer.merge_direction_stops([
                ["0001", "0002", "0003", "0004"],
                ["0001", "0099", "0003", "0004"],
            ]),
            ["0001", "0002", "0099", "0003", "0004"],
        )
        with self.assertRaisesRegex(ValueError, "Niespójna kolejność"):
            importer.merge_direction_stops([["0001", "0002"], ["0002", "0001"]])


if __name__ == "__main__":
    unittest.main()
