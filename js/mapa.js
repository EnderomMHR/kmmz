// Startowe ustawienie mapy.
// Celowo ustawione mniej więcej na obszar Małopolski Zachodniej.
const map = L.map('map').setView([50.15, 19.55], 10);

// Podkład mapowy OpenStreetMap.
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Kolory stref.
const zoneColors = {
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
  "Sławków": "#af00ff",
  "Sosnowiec": "#d9d9e9",
  "Spytkowice": "#76a5af",
  "Sułoszowa-Skała": "#b7b8b7",
  "Trzebinia": "#d9d2e9",
  "Trzyciąż": "#c17ba1",
  "Wolbrom": "#2a8be8",
  "Zator": "#10ffff",
  "Żarnowiec": "#fffe01"
};

function getZoneColor(zone) {
  return zoneColors[zone] || "#005bbb";
}

function shadeColor(hex, percent) {
  let color = hex.replace("#", "");

  if (color.length === 3) {
    color = color.split("").map(char => char + char).join("");
  }

  const num = parseInt(color, 16);
  let r = (num >> 16) + percent;
  let g = ((num >> 8) & 0x00ff) + percent;
  let b = (num & 0x0000ff) + percent;

  r = Math.max(Math.min(255, r), 0);
  g = Math.max(Math.min(255, g), 0);
  b = Math.max(Math.min(255, b), 0);

  return "#" + (b | (g << 8) | (r << 16)).toString(16).padStart(6, "0");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const stopFiles = [
  'data/stops/zarnowiec.geojson',
  'data/stops/zator.geojson',
  'data/stops/trzyciaz.geojson',
  'data/stops/chelmek.geojson',
  'data/stops/babice-alwernia.geojson',
  'data/stops/bierun.geojson',
  'data/stops/boleslaw.geojson',
  'data/stops/brzeszcze.geojson',
  'data/stops/bukowno.geojson'
];

const panel = document.getElementById("stop-panel");
const panelClose = document.getElementById("panel-close");
const panelStopId = document.getElementById("panel-stop-id");
const panelStopName = document.getElementById("panel-stop-name");
const panelZone = document.getElementById("panel-zone");
const panelStopPage = document.getElementById("panel-stop-page");

const tabNearest = document.getElementById("tab-nearest");
const tabLines = document.getElementById("tab-lines");
const sectionNearest = document.getElementById("section-nearest");
const sectionLines = document.getElementById("section-lines");

const nearestDeparturesBox = document.getElementById("nearest-departures");
const servedLinesBox = document.getElementById("served-lines");
const lineTimetableBox = document.getElementById("line-timetable");

let currentStopProperties = null;
let currentStopDeparturesData = null;
let refreshTimer = null;

panelClose.addEventListener("click", closeStopPanel);
tabNearest.addEventListener("click", () => showPanelTab("nearest"));
tabLines.addEventListener("click", () => showPanelTab("lines"));

function showPanelTab(tabName) {
  tabNearest.classList.toggle("active", tabName === "nearest");
  tabLines.classList.toggle("active", tabName === "lines");

  sectionNearest.classList.toggle("active", tabName === "nearest");
  sectionLines.classList.toggle("active", tabName === "lines");
}

function closeStopPanel() {
  panel.classList.remove("open");
  currentStopProperties = null;
  currentStopDeparturesData = null;
  lineTimetableBox.innerHTML = "";

  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

function applyZoneTheme(zone) {
  const main = getZoneColor(zone);
  const dark = shadeColor(main, -55);
  const light = shadeColor(main, 75);
  const border = shadeColor(main, 35);

  panel.style.setProperty("--zone-main", main);
  panel.style.setProperty("--zone-dark", dark);
  panel.style.setProperty("--zone-light", light);
  panel.style.setProperty("--zone-border", border);
}

function getDateKey(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${month}-${day}`;
}

function addDays(date, days) {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function getEasterDate(year) {
  // Algorytm Meeusa/Jonesa/Butchera dla kalendarza gregoriańskiego.
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;

  return new Date(year, month - 1, day);
}

function isPolishHoliday(date) {
  const fixedHolidays = new Set([
    "01-01",
    "01-06",
    "05-01",
    "05-03",
    "08-15",
    "11-01",
    "11-11",
    "12-24",
    "12-25",
    "12-26"
  ]);

  if (fixedHolidays.has(getDateKey(date))) {
    return true;
  }

  const easter = getEasterDate(date.getFullYear());
  const movableHolidays = [
    addDays(easter, 1),   // Poniedziałek Wielkanocny
    addDays(easter, 49),  // Zielone Świątki
    addDays(easter, 60)   // Boże Ciało
  ];

  return movableHolidays.some(holiday =>
    holiday.getFullYear() === date.getFullYear() &&
    holiday.getMonth() === date.getMonth() &&
    holiday.getDate() === date.getDate()
  );
}

function getCurrentDayType() {
  const now = new Date();

  if (isPolishHoliday(now)) {
    return "holiday";
  }

  const day = now.getDay();

  if (day === 6) {
    return "saturday";
  }

  if (day === 0) {
    return "sunday";
  }

  return "workday";
}

function getDayTypeLabel(dayType) {
  const labels = {
    workday: "Dni robocze",
    saturday: "Soboty",
    sunday: "Niedziele",
    holiday: "Święta"
  };

  return labels[dayType] || dayType;
}

function timeToMinutes(timeText) {
  const [hours, minutes] = timeText.split(":").map(Number);
  return hours * 60 + minutes;
}

function getCurrentMinutes() {
  const now = new Date();
  return now.getHours() * 60 + now.getMinutes();
}

function formatDepartureCountdown(minutesLeft, timeText) {
  if (minutesLeft === 0) {
    return "🚌 teraz";
  }

  if (minutesLeft > 0 && minutesLeft < 60) {
    return `za ${minutesLeft} min`;
  }

  return timeText;
}

function getUpcomingDepartures(data) {
  const currentDayType = getCurrentDayType();
  const nowMinutes = getCurrentMinutes();
  const rangeEnd = nowMinutes + 240;

  return (data.departures || [])
    .filter(item => item.day_type === currentDayType)
    .map(item => {
      const departureMinutes = timeToMinutes(item.time);
      return {
        ...item,
        minutesLeft: departureMinutes - nowMinutes
      };
    })
    .filter(item => item.minutesLeft >= 0 && item.minutesLeft <= 240)
    .sort((a, b) => a.minutesLeft - b.minutesLeft || a.line.localeCompare(b.line));
}

function renderNearestDepartures() {
  if (!currentStopDeparturesData) {
    nearestDeparturesBox.innerHTML = '<div class="panel-empty">Brak danych odjazdów dla tego przystanku.</div>';
    return;
  }

  const upcoming = getUpcomingDepartures(currentStopDeparturesData);

  if (!upcoming.length) {
    nearestDeparturesBox.innerHTML = '<div class="panel-empty">Brak odjazdów w najbliższych 4 godzinach.</div>';
    return;
  }

  nearestDeparturesBox.innerHTML = upcoming.map(item => {
    const countdown = formatDepartureCountdown(item.minutesLeft, item.time);
    const nowClass = item.minutesLeft === 0 ? " now" : "";

    return `
      <div class="departure-card">
        <div class="departure-line">${escapeHtml(item.line)}</div>
        <div>
          <div class="departure-direction">${escapeHtml(item.display_direction)}</div>
          <div class="departure-time">Rozkładowo: ${escapeHtml(item.time)}</div>
        </div>
        <div class="departure-countdown${nowClass}">${escapeHtml(countdown)}</div>
      </div>
    `;
  }).join("");
}

function getUniqueServedLines(data) {
  const mapByPage = new Map();

  (data.served_lines || []).forEach(item => {
    if (!mapByPage.has(item.page)) {
      mapByPage.set(item.page, item);
    }
  });

  return Array.from(mapByPage.values()).sort((a, b) => {
    const lineA = Number.isNaN(Number(a.line)) ? a.line : Number(a.line);
    const lineB = Number.isNaN(Number(b.line)) ? b.line : Number(b.line);

    if (lineA !== lineB) {
      return lineA > lineB ? 1 : -1;
    }

    return String(a.main_direction).localeCompare(String(b.main_direction), "pl");
  });
}

function renderServedLines(data) {
  const lines = getUniqueServedLines(data);

  if (!lines.length) {
    servedLinesBox.innerHTML = '<div class="panel-empty">Brak przypisanych linii.</div>';
    return;
  }

  servedLinesBox.innerHTML = lines.map(item => `
    <button class="line-card" type="button" data-page="${escapeHtml(item.page)}">
      <div class="line-card-row">
        <div class="line-number">${escapeHtml(item.line)}</div>
        <div class="line-direction">${escapeHtml(item.main_direction)}</div>
      </div>
    </button>
  `).join("");

  servedLinesBox.querySelectorAll(".line-card").forEach(button => {
    button.addEventListener("click", () => {
      renderLineTimetable(button.dataset.page);
    });
  });
}

function renderLineTimetable(page) {
  if (!currentStopDeparturesData) {
    return;
  }

  const currentDayType = getCurrentDayType();
  const items = (currentStopDeparturesData.departures || [])
    .filter(item => item.page === page && item.day_type === currentDayType)
    .sort((a, b) => timeToMinutes(a.time) - timeToMinutes(b.time));

  const lineInfo = getUniqueServedLines(currentStopDeparturesData)
    .find(item => item.page === page);

  if (!lineInfo) {
    lineTimetableBox.innerHTML = "";
    return;
  }

  if (!items.length) {
    lineTimetableBox.innerHTML = `
      <div class="inline-timetable">
        <div class="inline-timetable-title">Linia ${escapeHtml(lineInfo.line)} → ${escapeHtml(lineInfo.main_direction)}</div>
        <div class="inline-timetable-day">${escapeHtml(getDayTypeLabel(currentDayType))}</div>
        <div class="panel-empty">Brak kursów dla aktualnego typu dnia.</div>
      </div>
    `;
    return;
  }

  lineTimetableBox.innerHTML = `
    <div class="inline-timetable">
      <div class="inline-timetable-title">Linia ${escapeHtml(lineInfo.line)} → ${escapeHtml(lineInfo.main_direction)}</div>
      <div class="inline-timetable-day">${escapeHtml(getDayTypeLabel(currentDayType))}</div>
      <div class="inline-time-list">
        ${items.map(item => {
          const extraDirection = item.display_direction !== lineInfo.main_direction
            ? item.display_direction
            : "";

          return `
            <div class="inline-time-row">
              <div class="inline-time">${escapeHtml(item.time)}</div>
              <div class="inline-time-direction">${escapeHtml(extraDirection)}</div>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

function openStopPanel(properties) {
  currentStopProperties = properties;
  currentStopDeparturesData = null;

  const stopId = properties.stop_id;
  const stopName = properties.name;
  const platform = properties.platform;
  const zone = properties.zone;

  applyZoneTheme(zone);

  panelStopId.textContent = `ID: ${stopId}`;
  panelStopName.textContent = `${stopName} (${platform})`;
  panelZone.textContent = `STREFA ${String(zone).toUpperCase()}`;
  panelStopPage.href = `przystanki/${stopId}.html`;

  nearestDeparturesBox.innerHTML = '<div class="panel-empty">Wczytywanie odjazdów...</div>';
  servedLinesBox.innerHTML = '<div class="panel-empty">Wczytywanie linii...</div>';
  lineTimetableBox.innerHTML = "";

  showPanelTab("nearest");
  panel.classList.add("open");

  fetch(`data/odjazdy/${stopId}.json`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`Brak pliku data/odjazdy/${stopId}.json`);
      }

      return response.json();
    })
    .then(data => {
      currentStopDeparturesData = data;
      renderNearestDepartures();
      renderServedLines(data);

      if (refreshTimer) {
        clearInterval(refreshTimer);
      }

      refreshTimer = setInterval(() => {
        if (currentStopDeparturesData) {
          renderNearestDepartures();
        }
      }, 60000);
    })
    .catch(error => {
      console.warn(error);
      currentStopDeparturesData = null;

      nearestDeparturesBox.innerHTML = '<div class="panel-empty">Brak danych rozkładowych dla tego przystanku.</div>';
      servedLinesBox.innerHTML = '<div class="panel-empty">Brak danych o liniach dla tego przystanku.</div>';
    });
}

// Warstwa punktów.
const stopsLayer = L.geoJSON(null, {
  pointToLayer: function (feature, latlng) {
    const zone = feature.properties.zone;
    const color = getZoneColor(zone);

    return L.circleMarker(latlng, {
      radius: 6,
      color: "#ffffff",
      weight: 2,
      fillColor: color,
      fillOpacity: 0.9
    });
  },

  onEachFeature: function (feature, layer) {
    const p = feature.properties;

    const popupContent = `
      <div style="font-weight:bold;font-size:15px;margin-bottom:4px;">
        ${escapeHtml(p.name)} <span style="color:#555;font-size:13px;">(${escapeHtml(p.platform)})</span>
      </div>
      <div style="color:#555;font-size:13px;">ID: ${escapeHtml(p.stop_id)}</div>
      <div style="margin-top:4px;font-size:13px;">Strefa: ${escapeHtml(p.zone)}</div>
      <div style="margin-top:6px;font-size:13px;">Kliknij punkt, aby otworzyć panel odjazdów.</div>
    `;

    layer.bindPopup(popupContent);

    layer.on("click", function () {
      openStopPanel(p);
    });
  }
}).addTo(map);

// Wczytywanie plików GeoJSON z przystankami.
Promise.all(
  stopFiles.map(file =>
    fetch(file)
      .then(response => {
        console.log('Wczytywanie pliku:', file);
        console.log('Status:', response.status);

        if (!response.ok) {
          throw new Error('Nie udało się wczytać pliku: ' + file);
        }

        return response.json();
      })
  )
)
.then(filesData => {
  filesData.forEach(data => {
    console.log('Dodaję dane:', data);
    console.log('Liczba przystanków w pliku:', data.features.length);
    stopsLayer.addData(data);
  });

  console.log('Liczba punktów na mapie:', stopsLayer.getLayers().length);

  if (stopsLayer.getLayers().length > 0) {
    map.fitBounds(stopsLayer.getBounds());
  }
})
.catch(error => {
  console.error('Błąd wczytywania przystanków:', error);
});
