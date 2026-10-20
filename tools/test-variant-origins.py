#!/usr/bin/env python3
"""Regression: starts do not define passenger variants; destinations and routes do."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("kmmz_import_excel", Path(__file__).resolve().parent / "import-excel.py")
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def course(ident, stop_ids):
    return {
        "trip_id": ident,
        "direction": 1,
        "variant": ident.split("-")[2],
        "route_pattern_id": "-".join(ident.split("-")[:3]),
        "stop_times": [{"stop_id": s} for s in stop_ids],
    }


class VariantOriginTests(unittest.TestCase):
    def test_suffix_origins_same_variant_and_destination_symbol(self):
        # Pierwszy blok zaczyna się POŹNIEJ; pełna trasa jest w kolejnym bloku.
        # Kolumna D zawiera pomocnicze minuty i nie jest godziną żadnego kursu.
        rows = [
            (1, {0: "ID KURSU", 1: "008-1-0-R-01", 3: "Czas narastająco"}),
            (2, {0: "0002 B", 1: "08:03", 3: "03"}),
            (3, {0: "0003 C", 1: "08:07", 3: "07"}),
            (4, {0: "0004 D", 1: "08:09", 3: "09"}),
            (5, {0: "ID KURSU", 1: "008-1-0-R-02", 2: "008-1-1-R-03",
                 3: "Czas narastająco", 5: "008-1-1-R-04"}),
            (6, {0: "0001 A", 1: "07:00", 2: "09:00", 3: "00"}),
            (7, {0: "0002 B", 1: "07:03", 2: "09:03", 3: "03", 5: "10:03"}),
            (8, {0: "0003 C", 1: "07:07", 2: "09:07", 3: "07", 5: "10:07"}),
            (9, {0: "0004 D", 1: "07:09", 3: "09"}),
        ]
        known = {
            f"000{x}": {"stop_id": f"000{x}", "stop_name": name, "platform": "0", "zone": "Test"}
            for x, name in enumerate("ABCD", 1)
        }
        config = {"directions": {"1": {
            "slug": "test", "name": "D",
            "variant_symbols": {"0": "", "1": "K"},
            "variant_destinations": {"K": "C"},
            "legend": {"K": "do: C"},
        }}}
        with patch.object(importer, "read_arkusz1", return_value=rows):
            line_id, line_json, trip_json = importer.import_file(Path("test.xlsx"), known, config)
        self.assertEqual(line_id, "8")
        self.assertEqual(len(trip_json["trips"]), 4)
        self.assertEqual([p["stop_ids"] for p in trip_json["route_patterns"]],
                         [["0001", "0002", "0003", "0004"], ["0001", "0002", "0003"]])
        direction = line_json["directions"][0]
        self.assertEqual([s["stop_id"] for s in direction["route_stops"]], ["0001", "0002", "0003", "0004"])
        t = {item["stop_id"]: item["departures"] for item in direction["timetables"]}
        self.assertEqual(t["0001"]["workday"], ["07:00", "09:00K"])
        self.assertEqual(t["0002"]["workday"], ["07:03", "08:03", "09:03K", "10:03K"])
        # Kursy wariantu K kończą tu jazdę, więc nie udajemy odjazdów.
        self.assertEqual(t["0003"]["workday"], ["07:07", "08:07"])
        self.assertEqual(t["0004"], {})
        self.assertEqual(trip_json["trips"][0]["stop_times"][-1]["time"], "08:09")
        self.assertEqual(trip_json["trips"][3]["stop_times"][-1]["time"], "10:07")

    def test_same_variant_must_keep_endpoint(self):
        trips = [
            course("008-1-0-R-01", ["0001", "0002", "0003", "0004"]),
            course("008-1-0-R-02", ["0001", "0002", "0003"]),
        ]
        with self.assertRaisesRegex(ValueError, "osobnego numeru wariantu"):
            importer.infer_variant_patterns(trips)

    def test_same_variant_must_not_divert_or_skip_intermediate_stops(self):
        trips = [
            course("008-1-0-R-01", ["0001", "0002", "0003", "0004"]),
            course("008-1-0-R-02", ["0001", "0099", "0003", "0004"]),
        ]
        with self.assertRaisesRegex(ValueError, "osobnego numeru wariantu"):
            importer.infer_variant_patterns(trips)
        trips[1]["stop_times"] = [{"stop_id": s} for s in ["0001", "0003", "0004"]]
        with self.assertRaisesRegex(ValueError, "osobnego numeru wariantu"):
            importer.infer_variant_patterns(trips)

    def test_different_variant_can_divert(self):
        trips = [
            course("008-1-0-R-01", ["0001", "0002", "0003", "0004"]),
            course("008-1-1-R-02", ["0001", "0099", "0003", "0004"]),
        ]
        patterns = importer.infer_variant_patterns(trips)
        self.assertEqual(len(patterns), 2)
        merged = importer.merge_direction_stops([
            ["0001", "0002", "0003", "0004"],
            ["0001", "0099", "0003", "0004"],
        ])
        self.assertEqual(set(merged), {"0001", "0002", "0003", "0004", "0099"})
        self.assertLess(merged.index("0001"), merged.index("0099"))
        self.assertLess(merged.index("0099"), merged.index("0003"))

    def test_inconsistent_stop_order_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Niespójna kolejność"):
            importer.merge_direction_stops([["0001", "0002"], ["0002", "0001"]])


if __name__ == "__main__":
    unittest.main()
