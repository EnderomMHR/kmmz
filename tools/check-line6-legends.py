#!/usr/bin/env python3
"""Line 6: show a variant legend only on pages using that letter.

Regression against the *generated* HTML in both directions. It also
protects the existing variant symbols and original scheduled hours.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

line = load("data/rozklady/linie/6.json")
config = load("data/import-config/6.json")
assert line["line"] == "6"
assert len(line["directions"]) == 2

total_with_legend = 0
total_without_legend = 0
for direction_no, direction in enumerate(line["directions"], 1):
    symbol = "Z" if direction_no == 1 else "O"
    assert direction["legend_only_used_symbols"] is True
    assert config["directions"][str(direction_no)]["legend_only_used_symbols"] is True
    assert set(direction["legend"]) == {symbol}
    assert direction["legend"][symbol] == (
        "do: Oświęcim Park Zasole" if symbol == "Z"
        else "do: Oświęcim Dąbrowskiego Kościół"
    )

    for timetable in direction["timetables"]:
        departures = [str(value) for values in timetable["departures"].values()
                      for value in values]
        symbols_used = set()
        for raw in departures:
            match = re.fullmatch(r"\d{2}:\d{2}([A-Z]*)", raw)
            assert match is not None, (timetable["file"], raw)
            symbols_used.update(match.group(1))
        assert symbols_used <= {symbol}, (timetable["file"], symbols_used)

        page_path = ROOT / "rozklady" / "6" / timetable["file"]
        assert page_path.is_file(), page_path
        html = page_path.read_text(encoding="utf-8")
        actual_legends = re.findall(
            r'<div class="legend-row"><span class="symbol">([^<]+)</span>'
            r' - ([^<]+)</div>',
            html
        )
        expected = (
            [(symbol, direction["legend"][symbol])] if symbol in symbols_used
            else []
        )
        assert actual_legends == expected, (timetable["file"], actual_legends, expected)
        assert ('<div class="legend">' in html) == bool(expected), timetable["file"]

        if expected:
            total_with_legend += 1
        else:
            total_without_legend += 1

# The reported example: no Z departures on Rajsko Ogrody.
html_0641 = (ROOT / "rozklady/6/0641-wilczkowice.html").read_text(encoding="utf-8")
assert '<div class="legend">' not in html_0641
assert "<div class=\"time\">04:46</div>" in html_0641

# Keep a positive case, too: a legitimate variant still needs its legend.
html_0616 = (ROOT / "rozklady/6/0616-wilczkowice.html").read_text(encoding="utf-8")
assert '<span class="symbol">Z</span>' in html_0616
html_0649 = (ROOT / "rozklady/6/0649-oswiecim.html").read_text(encoding="utf-8")
assert '<span class="symbol">O</span>' in html_0649

assert total_with_legend == 38, total_with_legend
assert total_without_legend == 30, total_without_legend
print(f"OK: line 6 — {total_without_legend} pages without needless legends; "
      f"{total_with_legend} pages retain valid Z/O legends.")
