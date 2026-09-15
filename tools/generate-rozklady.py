import json
import re
from pathlib import Path
from html import escape


BASE_DIR = Path(__file__).resolve().parents[1]

SOURCE_DIR = BASE_DIR / "data" / "rozklady" / "linie"
OUTPUT_ROZKLADY_DIR = BASE_DIR / "rozklady"
OUTPUT_ODJAZDY_DIR = BASE_DIR / "data" / "odjazdy"


CSS = r"""
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


DAY_LABELS = {
    "workday": "Dni robocze",
    "saturday": "Soboty",
    "sunday": "Niedziele",
    "holiday": "Święta"
}


def parse_time(value):
    """
    Zamienia np. '05:18H' na:
    time = '05:18'
    symbols = ['H']

    Zamienia np. '14:20HP' na:
    time = '14:20'
    symbols = ['H', 'P']
    """
    match = re.fullmatch(r"(\d{2}:\d{2})([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]*)", value.strip())

    if not match:
        raise ValueError(f"Niepoprawny zapis godziny: {value}")

    time = match.group(1)
    symbols_text = match.group(2)
    symbols = list(symbols_text) if symbols_text else []

    return time, symbols

def get_display_direction(direction_name, direction, symbols):
    """
    Zwraca kierunek wyświetlany dla konkretnego kursu.

    Na przykład:
    05:22H   -> Laski Pętla
    06:25P   -> Bukowno Przymiarki
    14:24HP  -> Bukowno Przymiarki
    18:35B   -> Bukowno Dworzec PKP
    """
    variant_destinations = direction.get("variant_destinations", {})

    for symbol in symbols:
        if symbol in variant_destinations:
            return variant_destinations[symbol]

    return direction_name

def render_time(value):
    time, symbols = parse_time(value)

    if symbols:
        return f'<div class="time">{escape(time)}<sup>{escape("".join(symbols))}</sup></div>'

    return f'<div class="time">{escape(time)}</div>'


def render_times(values):
    if not values:
        return '<div class="no-service">Brak kursów</div>'

    return '<div class="times">\n' + "\n".join(render_time(v) for v in values) + "\n</div>"


def render_route_stops(route_stops, current_file):
    """
    Lewy panel pokazuje trasę od obecnego przystanku.
    Dlatego generator ucina listę od aktualnej strony w dół.
    """
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


def render_html(line_data, direction, timetable):
    line = line_data["line"]
    current_file = timetable["file"]
    stop_id = timetable["stop_id"]
    stop_name = timetable["stop_name"]
    platform = timetable["platform"]
    direction_name = direction["name"]
    map_url = line_data.get("map_url", "https://enderommhr.github.io/kmmz/mapa.html")

    route_html = render_route_stops(direction["route_stops"], current_file)

    departures = timetable["departures"]

    workday_html = render_times(departures.get("workday", []))
    saturday_html = render_times(departures.get("saturday", []))
    sunday_html = render_times(departures.get("sunday", []))
    holiday_html = render_times(departures.get("holiday", []))

    legend_html = render_legend(direction.get("legend", {}))

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KMMZ | Linia {escape(line)} | {escape(stop_id)} {escape(stop_name)}</title>

<style>
{CSS}
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

<div class="section-title workday">{DAY_LABELS["workday"]}</div>
{workday_html}

<div class="section-title saturday">{DAY_LABELS["saturday"]}</div>
{saturday_html}

<div class="section-title sunday">{DAY_LABELS["sunday"]}</div>
{sunday_html}
    
<div class="section-title holiday">{DAY_LABELS["holiday"]}</div>
{holiday_html}

{legend_html}
  
</div>

</div>

</body>
</html>
"""


def build_map_departures(all_line_files):
    """
    Tworzy zbiorcze dane pod przyszłą mapę:
    data/odjazdy/0177.json
    data/odjazdy/0238.json
    itd.

    Na razie mapa jeszcze tego nie czyta, ale dane będą już gotowe.
    """
    by_stop = {}

    for line_file in all_line_files:
        with open(line_file, "r", encoding="utf-8") as file:
            line_data = json.load(file)

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
                        "legends": {}
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

    OUTPUT_ODJAZDY_DIR.mkdir(parents=True, exist_ok=True)

    for stop_id, data in by_stop.items():
        output_path = OUTPUT_ODJAZDY_DIR / f"{stop_id}.json"

        data["departures"].sort(key=lambda item: (item["day_type"], item["time"], item["line"]))

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)


def generate_pages():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    line_files = sorted(SOURCE_DIR.glob("*.json"))

    if not line_files:
        print("Brak plików JSON w data/rozklady/linie/")
        return

    for line_file in line_files:
        with open(line_file, "r", encoding="utf-8") as file:
            line_data = json.load(file)

        line = line_data["line"]
        output_line_dir = OUTPUT_ROZKLADY_DIR / line
        output_line_dir.mkdir(parents=True, exist_ok=True)

        for direction in line_data["directions"]:
            # dopisujemy numer linii do każdego przystanku w panelu bocznym
            for route_stop in direction["route_stops"]:
                route_stop["line"] = line

            for timetable in direction["timetables"]:
                html = render_html(line_data, direction, timetable)
                output_path = output_line_dir / timetable["file"]

                with open(output_path, "w", encoding="utf-8") as file:
                    file.write(html)

                print(f"Wygenerowano: {output_path.relative_to(BASE_DIR)}")

    build_map_departures(line_files)

    print("Gotowe — wygenerowano strony rozkładów oraz dane pod mapę.")


if __name__ == "__main__":
    generate_pages()
