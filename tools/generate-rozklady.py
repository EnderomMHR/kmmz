# tools/generate-rozklady.py

import json
import re
from pathlib import Path
from html import escape


BASE_DIR = Path(__file__).resolve().parents[1]

SOURCE_DIR = BASE_DIR / "data" / "rozklady" / "linie"
STOPS_DIR = BASE_DIR / "data" / "stops"

OUTPUT_ROZKLADY_DIR = BASE_DIR / "rozklady"
OUTPUT_ODJAZDY_DIR = BASE_DIR / "data" / "odjazdy"
OUTPUT_PRZYSTANKI_DIR = BASE_DIR / "przystanki"


CSS_ROZKLAD = r"""
*{box-sizing:border-box}

body{
    margin:0;
    font-family:Arial, Helvetica, sans-serif;
    background:linear-gradient(135deg,#005bbb,#009966);
    padding:20px;
}

.page{
    max-width:1400px;
    margin:auto;
    display:grid;
    grid-template-columns:330px 1fr;
    gap:20px;
}

.panel, .timetable{
    background:white;
    border-radius:16px;
    box-shadow:0 8px 25px rgba(0,0,0,.22);
}

.panel{
    padding:15px;
}

.back{
    display:block;
    margin-bottom:15px;
    color:#005bbb;
    font-weight:bold;
    text-decoration:none;
}

.route-title{
    text-align:center;
    padding:12px;
    background:#f5c400;
    font-weight:bold;
    border-radius:10px 10px 0 0;
}

.route-subtitle{
    text-align:center;
    background:#009966;
    color:white;
    padding:8px;
    font-weight:bold;
}

.stop{
    display:block;
    padding:5px 8px;
    border-bottom:1px dashed #ccc;
    color:#222;
    text-decoration:none;
    font-size:12px;
}

.stop:hover{
    background:#eef5ff;
    color:#005bbb;
}

.current-stop{
    background:#fff3c4;
    font-weight:bold;
    font-size:12px;
}

.variant{
    margin-left:25px;
    font-style:italic;
}

.timetable{
    padding:20px;
}

.header{
    display:grid;
    grid-template-columns:110px 1fr 90px;
    gap:20px;
    align-items:center;
    margin-bottom:25px;
}

.line-button{
    background:#f5c400;
    color:#222;
    font-size:36px;
    font-weight:bold;
    text-align:center;
    padding:14px;
    border-radius:12px;
    text-decoration:none;
}

.stop-name{
    font-size:21px;
    font-weight:bold;
    color:#005bbb;
    text-decoration:none;
}

.stop-code{
    background:#dcecff;
    color:#005bbb;
    padding:6px 10px;
    border-radius:6px;
    font-weight:bold;
    margin-right:8px;
    font-size:14px;
}

.direction{
    margin-top:10px;
    font-size:15px;
}

.map-button{
    text-decoration:none;
    background:#eaf4ff;
    border:2px solid #005bbb;
    color:#005bbb;
    border-radius:12px;
    font-size:13px;
    padding:9px;
    text-align:center;
    font-weight:bold;
}

.map-icon{
    font-size:26px;
    display:block;
}

.section-title{
    margin-top:14px;
    padding:7px 10px;
    font-weight:bold;
    border-radius:6px;
    font-size:14px;
}

.workday{background:#eaf4ff;}
.saturday{background:#eef7df;}
.sunday{background:#ffe5e5;}
.holiday{background:#fff3c4;}

.times{
    display:grid;
    grid-template-columns:repeat(8,1fr);
    gap:0;
    padding:6px 0 12px 0;
    border-bottom:1px dashed #ccc;
}

.time{
    text-align:center;
    padding:5px;
    font-size:14px;
}

.no-service{
    padding:9px;
    color:#777;
    font-style:italic;
    font-size:14px;
}

.legend{
    margin-top:30px;
    border:2px solid #ccc;
    border-radius:14px;
    overflow:hidden;
}

.legend-title{
    text-align:center;
    color:white;
    font-weight:bold;
    padding:12px;
    background:linear-gradient(90deg,#f5c400,#005bbb,#009966);
    font-size:17px;
}

.legend-row{
    padding:8px 15px;
    border-bottom:1px dashed #ccc;
}

.legend-row:last-child{
    border-bottom:none;
}

.symbol{
    color:#005bbb;
    font-weight:bold;
    display:inline-block;
    width:35px;
}

@media(max-width:900px){
    .page{
        grid-template-columns:1fr;
    }

    .header{
        grid-template-columns:1fr;
        text-align:center;
    }

    .times{
        grid-template-columns:repeat(3,1fr);
    }
}
"""


CSS_PRZYSTANEK = r"""
*{
    box-sizing:border-box;
    margin:0;
    padding:0;
}

body{
    font-family:Arial, Helvetica, sans-serif;
    background:linear-gradient(135deg,#005bbb,#009966);
    min-height:100vh;
    padding:20px;
}

.container{
    max-width:1300px;
    margin:auto;
    background:white;
    border-radius:20px;
    padding:30px;
    box-shadow:0 10px 30px rgba(0,0,0,0.25);
}

.back{
    display:inline-block;
    margin-bottom:25px;
    text-decoration:none;
    color:white;
    background:#005bbb;
    padding:12px 20px;
    border-radius:10px;
    font-weight:bold;
}

.stop-header{
    display:grid;
    grid-template-columns:1fr auto;
    gap:20px;
    align-items:center;
    margin-bottom:30px;
    border-bottom:4px solid #f5c400;
    padding-bottom:20px;
}

.stop-id{
    display:inline-block;
    background:#7b2cbf;
    color:white;
    font-weight:bold;
    padding:8px 14px;
    border-radius:10px;
    margin-right:12px;
    font-size:22px;
}

.stop-name{
    font-size:30px;
    color:#005bbb;
    font-weight:bold;
}

.stop-meta{
    text-align:right;
}

.zone-badge{
    display:inline-block;
    background:#f9cb9a;
    color:#222;
    padding:10px 16px;
    border-radius:12px;
    font-weight:bold;
    margin-bottom:10px;
}

.map-button{
    display:inline-block;
    text-decoration:none;
    background:#f5c400;
    color:#222;
    padding:10px 16px;
    border-radius:12px;
    font-weight:bold;
}

.main-grid{
    display:grid;
    grid-template-columns:360px 1fr;
    gap:25px;
    align-items:start;
}

.panel{
    background:#f8fbff;
    border:1px solid #d9e6f2;
    border-radius:16px;
    padding:18px;
}

.panel-title{
    text-align:center;
    color:white;
    background:linear-gradient(90deg,#005bbb,#009966);
    border-bottom:5px solid #f5c400;
    padding:12px;
    border-radius:12px;
    font-size:18px;
    font-weight:bold;
    margin-bottom:18px;
}

.line-card{
    display:block;
    text-decoration:none;
    color:#222;
    background:white;
    border:1px solid #e1e1e1;
    border-radius:10px;
    padding:7px 10px;
    margin:6px 0;
    transition:0.2s;
}

.line-card:hover{
    background:#eaf4ff;
    transform:translateX(4px);
}

.line-row{
    display:flex;
    align-items:center;
    gap:8px;
}

.line-number{
    min-width:38px;
    height:32px;
    background:#f5c400;
    color:#222;
    border-radius:8px;
    font-size:19px;
    font-weight:bold;
    display:flex;
    justify-content:center;
    align-items:center;
}

.line-direction{
    font-size:14px;
    line-height:1.4;
}

.departure-tabs{
    display:flex;
    flex-wrap:wrap;
    gap:10px;
    margin-bottom:18px;
}

.day-tab{
    border:none;
    padding:10px 14px;
    border-radius:10px;
    font-weight:bold;
    cursor:pointer;
    background:#eaf4ff;
    color:#005bbb;
}

.day-tab.active{
    background:#005bbb;
    color:white;
    outline:3px solid #f5c400;
}

.departures-section{
    display:none;
}

.departures-section.active{
    display:block;
}

.departure-card{
    display:grid;
    grid-template-columns:55px 70px 1fr;
    gap:8px;
    align-items:center;
    position:relative;
    background:white;
    border:1px solid #e1e1e1;
    border-radius:10px;
    padding:6px 10px 6px 34px;
    margin:5px 0;
    transition:0.2s;
}

.departure-card::before{
    content:"";
    position:absolute;
    left:13px;
    top:50%;
    transform:translateY(-50%);
    width:8px;
    height:8px;
    background:#005bbb;
    border:3px solid #f5c400;
    border-radius:50%;
}

.departure-card:hover{
    background:#eaf4ff;
    transform:translateX(4px);
}

.dep-line{
    background:#f5c400;
    color:#222;
    font-weight:bold;
    border-radius:8px;
    text-align:center;
    padding:5px;
    text-decoration:none;
}

.dep-time{
    color:#005bbb;
    font-weight:bold;
    font-size:16px;
}

.dep-direction{
    font-size:13px;
    line-height:1.3;
}

.no-service{
    background:white;
    border:1px dashed #ccc;
    color:#777;
    font-style:italic;
    padding:18px;
    border-radius:12px;
    text-align:center;
}

@media(max-width:900px){
    .stop-header{
        grid-template-columns:1fr;
        text-align:center;
    }

    .stop-meta{
        text-align:center;
    }

    .main-grid{
        grid-template-columns:1fr;
    }

    .departure-card{
        grid-template-columns:55px 70px 1fr;
        font-size:13px;
    }

    .stop-name{
        font-size:24px;
    }
}
"""


DAY_LABELS = {
    "workday": "Dni robocze",
    "saturday": "Soboty",
    "sunday": "Niedziele",
    "holiday": "Święta"
}

def normalize_departures_in_line_data(line_data):
    for direction in line_data.get("directions", []):
        for timetable in direction.get("timetables", []):
            departures = timetable.setdefault("departures", {})

            if "weekend" in departures:
                weekend = departures["weekend"]

                departures.setdefault("saturday", weekend)
                departures.setdefault("sunday", weekend)

                departures.pop("weekend", None)
    
ZONE_COLORS = {
    "Nieznana": "#dddddd",
    "Babice-Alwernia": "#dd7e6b",
    "Bieruń": "#d5a6bd",
    "Bolesław": "#cccccc",
    "Brzeszcze": "#a2c4c9",
    "Bukowno": "#93c47d",
    "Chełmek": "#b4a7d6",
    "Chrzanów": "#a4c2f4",
    "Dąbrowa Górnicza": "#ffd966",
    "Iwanowice": "#e6b8af",
    "Jaworzno": "#ead1dc",
    "Jerzmanowice-Przeginia": "#ea9998",
    "Klucze": "#00fe00",
    "Krzeszowice": "#f9cb9a",
    "Libiąż": "#b6d7a8",
    "Olkusz": "#ffe599",
    "Osiek": "#d9ead3",
    "Oświęcim": "#9fc4e8",
    "Polanka Wielka": "#e16656",
    "Przeciszów": "#8e7cd3",
    "Sosnowiec": "#d9d9e9",
    "Spytkowice": "#76a5af",
    "Sułoszowa-Skała": "#b7b8b7",
    "Sławków": "#af00ff",
    "Trzebinia": "#d9d2e9",
    "Trzyciąż": "#c17ba1",
    "Wolbrom": "#2a8be8",
    "Zator": "#10ffff",
    "Żarnowiec": "#fffe01",
}

def parse_time(value):
    match = re.fullmatch(r"(\d{2}:\d{2})([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]*)", value.strip())

    if not match:
        raise ValueError(f"Niepoprawny zapis godziny: {value}")

    time = match.group(1)
    symbols_text = match.group(2)
    symbols = list(symbols_text) if symbols_text else []

    return time, symbols


def get_display_direction(direction_name, direction, symbols):
    variant_destinations = direction.get("variant_destinations", {})

    for symbol in symbols:
        if symbol in variant_destinations:
            return variant_destinations[symbol]

    return direction_name


def render_time_for_line_page(value):
    time, symbols = parse_time(value)

    if symbols:
        return f'<div class="time">{escape(time)}<sup>{escape("".join(symbols))}</sup></div>'

    return f'<div class="time">{escape(time)}</div>'


def render_times_for_line_page(values):
    if not values:
        return '<div class="no-service">Brak kursów</div>'

    return '<div class="times">\n' + "\n".join(render_time_for_line_page(v) for v in values) + "\n</div>"

def render_day_sections_for_line_page(departures):
    html = []

    for day_type, label in DAY_LABELS.items():
        if day_type not in departures:
            continue

        html.append(f"""
<div class="section-title {escape(day_type)}">{escape(label)}</div>
{render_times_for_line_page(departures.get(day_type, []))}
""")

    return "\n".join(html)
    

def render_route_stops(route_stops, current_file):
    start_index = 0

    for index, stop in enumerate(route_stops):
        if stop["file"] == current_file:
            start_index = index
            break

    visible_stops = route_stops[start_index:]

    html = []

    for stop in visible_stops:
        classes = ["stop"]

        if stop.get("variant"):
            classes.append("variant")

        if stop["file"] == current_file:
            classes.append("current-stop")

        class_text = " ".join(classes)
        label = f'{stop["stop_id"]} {stop["stop_name"]} ({stop["platform"]})'

        html.append(
            f'<a class="{class_text}" href="../{escape(stop["line"])}/{escape(stop["file"])}">'
            f'{escape(label)}</a>'
        )

    return "\n".join(html)


def render_legend(legend):
    if not legend:
        return ""

    rows = []

    for symbol, description in legend.items():
        rows.append(
            f'<div class="legend-row"><span class="symbol">{escape(symbol)}</span> - {escape(description)}</div>'
        )

    return f"""
<div class="legend">
<div class="legend-title">Legenda</div>
{chr(10).join(rows)}
</div>
"""


def render_line_timetable_html(line_data, direction, timetable):
    line = line_data["line"]
    current_file = timetable["file"]
    stop_id = timetable["stop_id"]
    stop_name = timetable["stop_name"]
    platform = timetable["platform"]
    direction_name = direction["name"]
    map_url = line_data.get("map_url", "https://enderommhr.github.io/kmmz/mapa.html")

    route_html = render_route_stops(direction["route_stops"], current_file)

    departures = timetable["departures"]

    day_sections_html = render_day_sections_for_line_page(departures)

    legend_html = render_legend(direction.get("legend", {}))

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KMMZ | Linia {escape(line)} | {escape(stop_id)} {escape(stop_name)}</title>

<style>
{CSS_ROZKLAD}
</style>
</head>

<body>

<div class="page">

<div class="panel">
<a class="back" href="../../linie/{escape(line)}.html">← Powrót do trasy linii {escape(line)}</a>

<div class="route-title">Kierunek: {escape(direction_name)}</div>
<div class="route-subtitle">Trasa przejazdu od tego przystanku</div>

{route_html}
</div>

<div class="timetable">

<div class="header">
<a class="line-button" href="../../linie/{escape(line)}.html">{escape(line)}</a>

<div>
<a class="stop-name" href="../../przystanki/{escape(stop_id)}.html">
<span class="stop-code">{escape(stop_id)}</span>{escape(stop_name)} ({escape(platform)})
</a>
<div class="direction">Kierunek: <strong>{escape(direction_name)}</strong></div>
</div>

<a class="map-button" href="{escape(map_url)}" target="_blank">
<span class="map-icon">🗺️</span>
Mapa
</a>
</div>

{day_sections_html}

{legend_html}
  
</div>

</div>

</body>
</html>
"""


def load_stop_metadata():
    stops = {}

    if not STOPS_DIR.exists():
        return stops

    for geojson_file in sorted(STOPS_DIR.glob("*.geojson")):
        with open(geojson_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            stop_id = properties.get("stop_id")

            if not stop_id:
                continue

            stops[stop_id] = {
                "stop_id": stop_id,
                "stop_name": properties.get("name", ""),
                "platform": properties.get("platform", ""),
                "zone": properties.get("zone", "Nieznana"),
                "coordinates": feature.get("geometry", {}).get("coordinates")
            }

    return stops


def build_departures_from_line_files(line_files):
    by_stop = {}

    for line_file in line_files:
        with open(line_file, "r", encoding="utf-8") as file:
            line_data = json.load(file)
            normalize_departures_in_line_data(line_data)

        line = line_data["line"]

        for direction in line_data["directions"]:
            direction_name = direction["name"]
            direction_slug = direction["slug"]
            legend = direction.get("legend", {})

            for timetable in direction["timetables"]:
                stop_id = timetable["stop_id"]

                if stop_id not in by_stop:
                    by_stop[stop_id] = {
                        "stop_id": stop_id,
                        "stop_name": timetable["stop_name"],
                        "platform": timetable["platform"],
                        "departures": [],
                        "served_lines": {},
                        "legends": {}
                    }

                line_direction_key = f"{line}|{direction_name}|{timetable['file']}"

                by_stop[stop_id]["served_lines"][line_direction_key] = {
                    "line": line,
                    "main_direction": direction_name,
                    "page": f"rozklady/{line}/{timetable['file']}"
                }

                by_stop[stop_id]["legends"][line] = legend

                for day_type, values in timetable["departures"].items():
                    for raw_value in values:
                        time, symbols = parse_time(raw_value)
                        display_direction = get_display_direction(direction_name, direction, symbols)

                        by_stop[stop_id]["departures"].append({
                            "line": line,
                            "main_direction": direction_name,
                            "display_direction": display_direction,
                            "direction_slug": direction_slug,
                            "page": f"rozklady/{line}/{timetable['file']}",
                            "day_type": day_type,
                            "time": time,
                            "symbols": symbols
                        })

    for stop_data in by_stop.values():
        stop_data["departures"].sort(key=lambda item: (item["day_type"], item["time"], item["line"], item["display_direction"]))

    return by_stop


def write_map_departures(by_stop):
    OUTPUT_ODJAZDY_DIR.mkdir(parents=True, exist_ok=True)

    for stop_id, data in by_stop.items():
        output_data = {
            "stop_id": data["stop_id"],
            "stop_name": data["stop_name"],
            "platform": data["platform"],
            "departures": data["departures"],
            "served_lines": list(data["served_lines"].values()),
            "legends": data["legends"]
        }

        output_path = OUTPUT_ODJAZDY_DIR / f"{stop_id}.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(output_data, file, ensure_ascii=False, indent=2)


def render_served_lines(served_lines):
    if not served_lines:
        return '<div class="no-service">Brak przypisanych linii.</div>'

    lines = sorted(served_lines, key=lambda item: (int(item["line"]) if item["line"].isdigit() else item["line"], item["main_direction"]))

    html = []

    for item in lines:
        href = "../" + item["page"]

        html.append(f"""
<a class="line-card" href="{escape(href)}">
<div class="line-row">
<div class="line-number">{escape(item["line"])}</div>
<div class="line-direction">
{escape(item["main_direction"])}
</div>
</div>
</a>
""")

    return "\n".join(html)


def render_departure_cards(departures, day_type):
    items = [item for item in departures if item["day_type"] == day_type]
    items.sort(key=lambda item: (item["time"], int(item["line"]) if item["line"].isdigit() else item["line"], item["display_direction"]))

    if not items:
        return '<div class="no-service">Brak odjazdów.</div>'

    html = []

    for item in items:
        href = "../" + item["page"]

        html.append(f"""
<div class="departure-card">
<a class="dep-line" href="{escape(href)}">{escape(item["line"])}</a>
<div class="dep-time">{escape(item["time"])}</div>
<div class="dep-direction">{escape(item["display_direction"])}</div>
</div>
""")

    return "\n".join(html)


def render_stop_page_html(stop_id, stop_data, stop_meta):
    stop_name = stop_meta.get("stop_name") or stop_data["stop_name"]
    platform = stop_meta.get("platform") or stop_data["platform"]
    zone = stop_meta.get("zone") or "Nieznana"

    zone_label = f"STREFA {zone.upper()}" if zone != "Nieznana" else "STREFA NIEZNANA"
    zone_color = ZONE_COLORS.get(zone, "#dddddd")

    served_lines_html = render_served_lines(list(stop_data["served_lines"].values()))

    departures = stop_data["departures"]

    workday_html = render_departure_cards(departures, "workday")
    saturday_html = render_departure_cards(departures, "saturday")
    sunday_html = render_departure_cards(departures, "sunday")
    holiday_html = render_departure_cards(departures, "holiday")

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>KMMZ | {escape(stop_id)} {escape(stop_name)}</title>

<style>
{CSS_PRZYSTANEK}
</style>
</head>

<body>

<div class="container">

<a class="back" href="../przystanki.html">← Powrót do listy przystanków</a>

<div class="stop-header">

<div>
<span class="stop-id">{escape(stop_id)}</span>
<span class="stop-name">{escape(stop_name)} ({escape(platform)})</span>
</div>

<div class="stop-meta">
<div class="zone-badge" style="background:{escape(zone_color)};">{escape(zone_label)}</div><br>
<a class="map-button" href="../mapa.html" target="_blank">🗺️ Pokaż na mapie</a>
</div>

</div>

<div class="main-grid">

<div class="panel">
<div class="panel-title">Obsługiwane linie</div>

{served_lines_html}

</div>

<div class="panel">
<div class="panel-title">Odjazdy chronologiczne</div>

<div class="departure-tabs">
<button class="day-tab active" onclick="showDay('workday', this)">Dni robocze</button>
<button class="day-tab" onclick="showDay('saturday', this)">Soboty</button>
<button class="day-tab" onclick="showDay('sunday', this)">Niedziele</button>
<button class="day-tab" onclick="showDay('holiday', this)">Święta</button>
</div>

<div class="departures-section active" id="workday">
{workday_html}
</div>

<div class="departures-section" id="saturday">
{saturday_html}
</div>

<div class="departures-section" id="sunday">
{sunday_html}
</div>

<div class="departures-section" id="holiday">
{holiday_html}
</div>

</div>

</div>

</div>

<script>
function showDay(dayId, button){{
    const sections = document.querySelectorAll(".departures-section");
    const buttons = document.querySelectorAll(".day-tab");

    sections.forEach(section => {{
        section.classList.remove("active");
    }});

    buttons.forEach(btn => {{
        btn.classList.remove("active");
    }});

    document.getElementById(dayId).classList.add("active");
    button.classList.add("active");
}}
</script>

</body>
</html>
"""


def generate_line_pages(line_files):
    for line_file in line_files:
        with open(line_file, "r", encoding="utf-8") as file:
            line_data = json.load(file)
            normalize_departures_in_line_data(line_data)

        line = line_data["line"]
        output_line_dir = OUTPUT_ROZKLADY_DIR / line
        output_line_dir.mkdir(parents=True, exist_ok=True)

        for direction in line_data["directions"]:
            for route_stop in direction["route_stops"]:
                route_stop["line"] = line

            for timetable in direction["timetables"]:
                html = render_line_timetable_html(line_data, direction, timetable)
                output_path = output_line_dir / timetable["file"]

                with open(output_path, "w", encoding="utf-8") as file:
                    file.write(html)

                print(f"Wygenerowano rozkład: {output_path.relative_to(BASE_DIR)}")


def generate_stop_pages(by_stop, stop_metadata):
    OUTPUT_PRZYSTANKI_DIR.mkdir(parents=True, exist_ok=True)

    for stop_id, stop_data in sorted(by_stop.items()):
        stop_meta = stop_metadata.get(stop_id, {})

        html = render_stop_page_html(stop_id, stop_data, stop_meta)
        output_path = OUTPUT_PRZYSTANKI_DIR / f"{stop_id}.html"

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(html)

        print(f"Wygenerowano stronę przystanku: {output_path.relative_to(BASE_DIR)}")


def generate_pages():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    line_files = sorted(SOURCE_DIR.glob("*.json"))

    if not line_files:
        print("Brak plików JSON w data/rozklady/linie/")
        return

    generate_line_pages(line_files)

    by_stop = build_departures_from_line_files(line_files)
    stop_metadata = load_stop_metadata()

    write_map_departures(by_stop)
    generate_stop_pages(by_stop, stop_metadata)

    print("Gotowe — wygenerowano strony rozkładów, dane pod mapę oraz strony przystanków.")


if __name__ == "__main__":
    generate_pages()
