#!/usr/bin/env python3
"""KMMZ: import Arkusz1 z Excela do danych kursów i rozkładów przystankowych.

Użycie: python tools/import-excel.py data/excel/5.xlsx
       python tools/import-excel.py --check data/excel/5.xlsx
       python tools/import-excel.py  (wszystkie pliki XLSX w data/excel/)

Wymaga jedynie biblioteki standardowej Pythona. Nie modyfikuje pliku XLSX.
Formuły muszą mieć zapisany wynik obliczeń (cache) z Excela/Arkuszy Google.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}
COURSE = re.compile(r"^(\d{3})-([12])-([A-Za-z0-9]+)-(SN|SW|R|S|N)-(\d{2,})$")
STOP = re.compile(r"^(\d{4})\s*(\S.*)$")
CLOCK = re.compile(r"^(\d{1,2}):(\d{2})$")
DAYS = {"R": ["workday"], "S": ["saturday"], "N": ["sunday"],
        "SN": ["saturday", "sunday"], "SW": ["holiday"]}
LABELS = {"R": "Dni robocze", "S": "Soboty", "N": "Niedziele",
          "SN": "Soboty i niedziele", "SW": "Święta"}


def read_arkusz1(path: Path):
    """Czyta wyłącznie wskazany arkusz oraz wartości przeliczone formuł (data_only)."""
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.find("m:sheets", NS)
        match = next((s for s in sheets if s.attrib.get("name") == "Arkusz1"), None)
        if match is None:
            raise ValueError(f"{path.name}: brak arkusza 'Arkusz1'")
        relationship = match.attrib[f"{{{NS['r']}}}id"]
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next((r.attrib["Target"] for r in rels
                       if r.attrib["Id"] == relationship), None)
        if not target:
            raise ValueError("Nie znaleziono powiązania arkusza")
        # Target bywa np. /xl/worksheets/sheet1.xml lub worksheets/sheet1.xml.
        sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        sheet_path = sheet_path.replace("xl/xl/", "xl/")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in strings.findall("m:si", NS):
                shared.append("".join(node.text or "" for node in item.iter(f"{{{NS['m']}}}t")))
        sheet = ET.fromstring(archive.read(sheet_path))
        rows = []
        for row in sheet.findall(".//m:sheetData/m:row", NS):
            cells = {}
            for cell in row.findall("m:c", NS):
                address = cell.attrib.get("r", "")
                letters = re.match(r"[A-Z]+", address)
                if not letters:
                    continue
                col = 0
                for ch in letters.group():
                    col = col * 26 + ord(ch) - 64
                col -= 1
                type_ = cell.attrib.get("t")
                value = cell.find("m:v", NS)
                inline = cell.find("m:is", NS)
                if type_ == "inlineStr" and inline is not None:
                    raw = "".join(n.text or "" for n in inline.iter(f"{{{NS['m']}}}t"))
                elif value is not None and value.text is not None:
                    raw = shared[int(value.text)] if type_ == "s" else value.text
                else:
                    raw = None
                if cell.find("m:f", NS) is not None and raw is None:
                    raise ValueError(f"{path.name}: formuła w komórce {address} nie ma obliczonego wyniku; otwórz i zapisz skoroszyt ponownie")
                if raw is not None:
                    cells[col] = raw
            rows.append((int(row.attrib.get("r", len(rows) + 1)), cells))
        return rows


def minutes(raw, location):
    """Normalizacja HH:MM i liczby seryjnej czasu Excela (ułamek doby)."""
    if raw is None or str(raw).strip() == "":
        return None
    s = str(raw).strip()
    if CLOCK.fullmatch(s):
        h, m = map(int, s.split(":"))
        if h < 24 and m < 60:
            return h * 60 + m
    try:
        serial = float(s.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"{location}: niepoprawna godzina {s!r}") from exc
    if not (0 <= serial < 1):
        raise ValueError(f"{location}: czas poza dobą {s!r}; sprawdź formułę")
    return round(serial * 1440)


def format_time(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def metadata():
    stops = {}
    for file in sorted((ROOT / "data/stops").glob("*.geojson")):
        for feature in json.loads(file.read_text(encoding="utf-8")).get("features", []):
            p = feature.get("properties", {})
            sid = str(p.get("stop_id") or "").zfill(4)
            if not sid or sid == "0000":
                continue
            item = {
                "stop_id": sid,
                "stop_name": p.get("name", ""),
                "platform": str(p.get("platform", "0")),
                "zone": p.get("zone", ""),
            }
            if sid in stops and stops[sid] != item:
                raise ValueError(f"Sprzeczne informacje o przystanku {sid} w GeoJSON")
            stops[sid] = item
    if not stops:
        raise ValueError("Brak bazy przystanków w data/stops/*.geojson")
    return stops


def import_file(file: Path, known_stops: dict, config: dict):
    rows = read_arkusz1(file)
    header_indices = [i for i, (_, cells) in enumerate(rows)
                      if str(cells.get(0, "")).strip().upper() == "ID KURSU"]
    if not header_indices:
        raise ValueError(f"{file.name}: nie odnaleziono wiersza ID KURSU")

    trips = []
    patterns = {}
    directions = {}
    warnings = []
    line_number = None
    for block, index in enumerate(header_indices):
        row_no, heading = rows[index]
        columns = {}
        for col, raw in heading.items():
            if col == 0 or not COURSE.fullmatch(str(raw).strip()):
                continue
            trip_id = str(raw).strip()
            if any(t["trip_id"] == trip_id for t in trips):
                raise ValueError(f"Powtórzone ID kursu: {trip_id}")
            line3, direction_code, variant, service, ordinal = COURSE.fullmatch(trip_id).groups()
            if line_number is None:
                line_number = str(int(line3))
            elif line_number != str(int(line3)):
                raise ValueError(f"{trip_id}: inna linia w tym samym pliku")
            columns[col] = {
                "trip_id": trip_id, "line": line_number,
                "direction": int(direction_code), "variant": variant,
                "service_code": service,
                "route_pattern_id": f"{line3}-{direction_code}-{variant}",
                "stop_times": [],
            }
        if not columns:
            raise ValueError(f"Wiersz {row_no}: nie znaleziono poprawnych ID kursów")
        if len({x["direction"] for x in columns.values()}) != 1:
            raise ValueError(f"Wiersz {row_no}: wymieszane kierunki")
        direction_no = next(iter(columns.values()))["direction"]
        direction = directions.setdefault(direction_no, [])
        end = header_indices[block + 1] if block + 1 < len(header_indices) else len(rows)
        block_stops = []
        for stop_row, cells in rows[index + 1:end]:
            label = str(cells.get(0, "")).strip()
            m = STOP.fullmatch(label)
            if not m:
                continue
            sid, sheet_name = m.groups()
            if sid not in known_stops:
                raise ValueError(f"Wiersz {stop_row}: brak ID przystanku {sid} w GeoJSON")
            if sid in block_stops:
                raise ValueError(f"Wiersz {stop_row}: powtórzony ID przystanku {sid} w jednym kierunku")
            block_stops.append(sid)
            direction.append(sid)
            canonical = known_stops[sid]["stop_name"]
            platform = known_stops[sid]["platform"]
            sheet_clean = re.sub(r"\\s*\\((\\d+)\\)\\s*$", "", sheet_name).strip()
            if canonical.casefold() != sheet_clean.casefold():
                warnings.append(f"{sid}: Excel={sheet_clean!r}, GeoJSON={canonical!r}")
            sheet_platform = re.search(r"\\((\\d+)\\)\\s*$", sheet_name)
            if sheet_platform and sheet_platform.group(1) != platform:
                raise ValueError(f"Wiersz {stop_row}: przystanek {sid} ma peron "
                                 f"{sheet_platform.group(1)} w Excelu, a {platform} w GeoJSON")
            for col, trip in columns.items():
                raw = cells.get(col)
                if raw is None or str(raw).strip() == "":
                    continue
                when = minutes(raw, f"{file.name}, wiersz {stop_row}, {trip['trip_id']}")
                trip["stop_times"].append({
                    "stop_sequence": len(block_stops),
                    "stop_id": sid,
                    "time": format_time(when),
                })
        if not block_stops:
            raise ValueError(f"Wiersz {row_no}: brak przystanków")
        for trip in columns.values():
            times = trip["stop_times"]
            if not times:
                raise ValueError(f"{trip['trip_id']}: nie znaleziono godzin")
            if any(int(b["time"][:2]) * 60 + int(b["time"][3:]) <
                   int(a["time"][:2]) * 60 + int(a["time"][3:])
                   for a, b in zip(times, times[1:])):
                raise ValueError(f"{trip['trip_id']}: czas cofa się; wymaga sprawdzenia lub obsługi północy")
            key = trip["route_pattern_id"]
            sequence = [t["stop_id"] for t in times]
            if key in patterns and patterns[key]["stop_ids"] != sequence:
                raise ValueError(f"{trip['trip_id']}: ten sam kod wariantu ma inną trasę")
            patterns[key] = {
                "route_pattern_id": key,
                "direction": trip["direction"],
                "variant": trip["variant"],
                "stop_ids": sequence,
            }
            trips.append(trip)

    if not line_number:
        raise ValueError(f"{file.name}: brak kursów")
    cfg = config.get("directions", {})
    timetable_directions = []
    for direction_no, ids in sorted(directions.items()):
        spec = cfg.get(str(direction_no))
        if not spec or not spec.get("slug") or not spec.get("name"):
            raise ValueError(f"Brak konfiguracji kierunku {direction_no} w data/import-config/{line_number}.json")
        slug = spec["slug"]
        unique_ids = list(dict.fromkeys(ids))
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            raise ValueError(f"Niepoprawny slug: {slug}")
        route_stops = []
        timetables = []
        for sid in unique_ids:
            stop = known_stops[sid]
            page = f"{sid}-{slug}.html"
            associated = [t for t in trips if t["direction"] == direction_no]
            route = {
                "stop_id": sid, "stop_name": stop["stop_name"],
                "platform": stop["platform"], "file": page,
            }
            if sid in spec.get("variant_stops", []):
                route["variant"] = True
            route_stops.append(route)
            departures = defaultdict(list)
            for trip in associated:
                symbol = spec.get("variant_symbols", {}).get(trip["variant"], "")
                if symbol and not re.fullmatch(r"[A-Za-zĄĆĘŁŃÓŚŹŻ]", symbol):
                    raise ValueError(f"Niepoprawny symbol dla wariantu {trip['variant']}: {symbol!r}")
                # Ostatni przystanek każdego kursu oznacza PRZYJAZD, nie odjazd.
                # Zachowujemy go w trips.json do planowania podróży, ale nie
                # publikujemy jako odjazdu (również w skróconych wariantach).
                for stop_time in trip["stop_times"][:-1]:
                    if stop_time["stop_id"] == sid:
                        for day in DAYS[trip["service_code"]]:
                            departures[day].append(stop_time["time"] + symbol)
            for times in departures.values():
                times.sort()
            timetables.append({
                "stop_id": sid, "stop_name": stop["stop_name"],
                "platform": stop["platform"], "file": page,
                "departures": dict(departures),
            })
        timetable_directions.append({
            "slug": slug, "name": spec["name"],
            "variant_destinations": spec.get("variant_destinations", {}),
            "legend": spec.get("legend", {}),
            "route_stops": route_stops,
            "timetables": timetables,
        })
    result = {
        "line": line_number,
        "map_url": "https://enderommhr.github.io/kmmz/mapa.html",
        "directions": timetable_directions,
    }
    trips_result = {
        "schema_version": "kmmz-trips-v1",
        "line": line_number,
        "services": {k: LABELS[k] for k in sorted({t["service_code"] for t in trips})},
        "route_patterns": list(patterns.values()),
        "trips": trips,
    }
    print(f"Linia {line_number}: {len(trips)} kursów, {sum(len(t['stop_times']) for t in trips)} czasów, "
          f"{len(set(s for ids in directions.values() for s in ids))} ID przystanków")
    for warning in sorted(set(warnings)):
        print("UWAGA - nazwa przystanku:", warning, file=sys.stderr)
    return line_number, result, trips_result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--check", action="store_true", help="Walidacja bez zapisywania")
    args = ap.parse_args()
    files = args.files or sorted((ROOT / "data/excel").glob("*.xlsx"))
    if not files:
        ap.error("Brak plików XLSX w data/excel/")
    stops = metadata()
    for path in files:
        if path.name.startswith("~$"):
            continue
        # Konfiguracja po prefiksie z pierwszego ID, nie po nazwie pliku.
        rows = read_arkusz1(path)
        all_values = (str(v) for _, cells in rows for v in cells.values())
        course = next((COURSE.fullmatch(v.strip()) for v in all_values
                       if COURSE.fullmatch(v.strip())), None)
        if course is None:
            raise ValueError(f"{path.name}: nie znaleziono ID kursów")
        line = str(int(course.group(1)))
        cfg_path = ROOT / "data/import-config" / f"{line}.json"
        if not cfg_path.is_file():
            raise ValueError(f"Brak pliku konfiguracyjnego: {cfg_path.relative_to(ROOT)}")
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
        number, line_json, trips_json = import_file(path, stops, config)
        if args.check:
            continue
        for destination, obj in [
            (ROOT / "data/rozklady/linie" / f"{number}.json", line_json),
            (ROOT / "data/trips" / f"{int(number):03d}.json", trips_json),
        ]:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Zapisano: {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, ET.ParseError) as exc:
        print(f"BŁĄD IMPORTU: {exc}", file=sys.stderr)
        sys.exit(1)
