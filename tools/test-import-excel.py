#!/usr/bin/env python3
"""Tests for stop ID/name parsing without a mandatory separator."""
import re
import unittest
from pathlib import Path

# Read the same pattern from the importer without loading the whole importer.
import ast
tree = ast.parse((Path(__file__).resolve().parent / "import-excel.py").read_text(encoding="utf-8"))
pattern = next(node.value.args[0].value for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "STOP" for t in node.targets))
STOP = re.compile(pattern)

class StopLabelTests(unittest.TestCase):
    def test_with_space(self):
        self.assertEqual(STOP.fullmatch("0649 Wilczkowice Pętla").groups(), ("0649", "Wilczkowice Pętla"))
    def test_without_space(self):
        self.assertEqual(STOP.fullmatch("0649Wilczkowice Pętla").groups(), ("0649", "Wilczkowice Pętla"))
    def test_multiple_spaces(self):
        self.assertEqual(STOP.fullmatch("0649   Wilczkowice Pętla").groups(), ("0649", "Wilczkowice Pętla"))
    def test_reject_empty_name(self):
        self.assertIsNone(STOP.fullmatch("0649"))
    def test_reject_bad_id(self):
        self.assertIsNone(STOP.fullmatch("649 Wilczkowice Pętla"))

if __name__ == "__main__":
    unittest.main()
