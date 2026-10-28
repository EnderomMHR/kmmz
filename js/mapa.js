// Startowe ustawienie mapy.
// Celowo ustawione mniej więcej na obszar Małopolski Zachodniej.
const map = L.map('map', {
  zoomControl: false
}).setView([50.15, 19.55], 10);

L.control.zoom({
  position: "bottomleft"
}).addTo(map);

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
  'data/stops/bukowno.geojson',
  'data/stops/chrzanow.geojson',
  'data/stops/dabrowa-gornicza.geojson',
  'data/stops/iwanowice.geojson',
  'data/stops/jaworzno.geojson',
  'data/stops/jerzmanowice-przeginia.geojson',
  'data/stops/klucze.geojson',
  'data/stops/krzeszowice.geojson',
  'data/stops/libiaz.geojson',
  'data/stops/olkusz.geojson',
  'data/stops/osiek.geojson',
  'data/stops/oswiecim.geojson',
  'data/stops/polanka-wielka.geojson',
  'data/stops/przeciszow.geojson',
  'data/stops/slawkow.geojson',
  'data/stops/sosnowiec.geojson',
  'data/stops/spytkowice.geojson',
  'data/stops/suloszowa-skala.geojson',
  'data/stops/trzebinia.geojson',
  'data/stops/wolbrom.geojson'
];

const panel = document.getElementById("stop-panel");
const panelClose = document.getElementById("panel-close");
const panelStopId = document.getElementById("panel-stop-id");
const panelStopName = document.getElementById("panel-stop-name");
const panelZone = document.getElementById("panel-zone");
const panelStopPage = document.getElementById("panel-stop-page");
const stopSearch = document.getElementById("stop-search");
const stopSearchInput = document.getElementById("stop-search-input");
const stopSearchClear = document.getElementById("stop-search-clear");
const stopSearchResults = document.getElementById("stop-search-results");

const allStops = [];
const stopIndex = new Map();
let currentSearchResults = [];

// The selected trip is drawn separately from the permanently visible stops.
const tripPanel = document.getElementById("trip-panel");
const tripPanelTitle = document.getElementById("trip-panel-title");
const tripPanelBody = document.getElementById("trip-panel-body");
const tripPanelClose = document.getElementById("trip-panel-close");
const tripRouteLayer = L.layerGroup().addTo(map);
const tripsJsonCache = new Map();
const linesJsonCache = new Map();
let tripSelectionToken = 0;
let activeTripRows = null;

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
tripPanelClose.addEventListener("click", closeTripRoute);
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

  // The mobile stop sheet temporarily covers the itinerary sheet.
  if (activeTripRows && window.matchMedia("(max-width: 700px)").matches) {
    tripPanel.classList.add("open");
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

// Load trip details only on demand; cache the result for further departures.
function loadCourseJson(cache, path) {
  if (!cache.has(path)) {
    const request = fetch(path)
      .then(response => {
        if (!response.ok) throw new Error("Nie można pobrać danych kursu.");
        return response.json();
      })
      .catch(error => {
        cache.delete(path);
        throw error;
      });

    cache.set(path, request);
  }

  return cache.get(path);
}

function closeTripRoute() {
  ++tripSelectionToken; // Cancel any request that has not finished loading.
  activeTripRows = null;
  tripRouteLayer.clearLayers();
  tripPanel.classList.remove("open");
}

function focusTripStop(index) {
  const stop = activeTripRows?.[index];
  if (!stop || !stop.latlng) return;
  map.setView(stop.latlng, Math.max(map.getZoom(), 15), { animate: true });
  if (stop.layer) {
    stop.layer.openPopup();
    setTimeout(() => renderPopupLines(stop.stop_id), 60);
  }
}

function drawSelectedTrip(rows) {
  tripRouteLayer.clearLayers();
  let segment = [];
  const points = [];

  function flushSegment() {
    if (segment.length > 1) {
      L.polyline(segment, {
        color: "#005bbb", weight: 5, opacity: 0.9,
        lineCap: "round", lineJoin: "round", interactive: false
      }).addTo(tripRouteLayer).bringToBack();
    }
    segment = [];
  }

  rows.forEach(stop => {
    if (stop.latlng) {
      segment.push(stop.latlng);
      points.push(stop.latlng);
    } else {
      // Do not draw a misleading shortcut across a missing coordinate.
      flushSegment();
    }
  });
  flushSegment();

  for (const stop of [rows[0], rows[rows.length - 1]]) {
    if (!stop?.latlng) continue;
    L.circleMarker(stop.latlng, {
      radius: 9, color: "#102a43", weight: 3,
      fillColor: "#f5c400", fillOpacity: 1, interactive: false
    }).addTo(tripRouteLayer);
  }

  if (points.length > 1) {
    const mobile = window.matchMedia("(max-width: 700px)").matches;
    map.fitBounds(L.latLngBounds(points), {
      paddingTopLeft: mobile ? [20, 50] : [430, 70],
      paddingBottomRight: mobile ? [20, 260] : [55, 70],
      maxZoom: 14,
      animate: true
    });
  } else if (points.length === 1) {
    map.setView(points[0], 14);
  }
}

function renderSelectedTrip(trip, departure, rows, boardingIndex) {
  const finalStop = rows[rows.length - 1];
  tripPanelTitle.textContent = `Linia ${departure.line} → ${departure.display_direction}`;

  const missingCount = rows.filter(stop => !stop.latlng).length;
  const missingMessage = missingCount
    ? `<div class="panel-empty">Brakuje współrzędnych ${missingCount} przystanków. Nie łączymy ich linią na skróty.</div>`
    : "";

  tripPanelBody.innerHTML = `
    <div class="trip-panel-meta">
      <strong>${escapeHtml(getDayTypeLabel(departure.day_type))}</strong>
      · ${escapeHtml(trip.trip_id)}<br>
      ${escapeHtml(rows.length)} przystanków ·
      ${escapeHtml(rows[0].time)}–${escapeHtml(finalStop.time)}<br>
      <strong>Twój odjazd:</strong>
      ${escapeHtml(rows[boardingIndex].stop_name)} (${escapeHtml(rows[boardingIndex].platform)})
      · ${escapeHtml(rows[boardingIndex].time)}
    </div>
    <div class="trip-panel-note">
      Przystanki przed Twoim odjazdem są przygaszone.
      Niebieska linia łączy przystanki prostymi odcinkami, a godziny są planowe.
    </div>
    ${missingMessage}
    <div class="trip-stop-list">
      ${rows.map((stop, index) => `
        <button class="trip-stop-button${stop.first ? " first" : ""}${stop.last ? " last" : ""}${index < boardingIndex ? " past" : ""}${index === boardingIndex ? " boarding" : ""}"
          type="button" data-index="${index}"
          ${stop.latlng ? "" : "disabled"}
          aria-label="${escapeHtml(stop.stop_name)}, ${escapeHtml(stop.time)}${index === boardingIndex ? ", tutaj wsiadasz" : ""}"
          ${index === boardingIndex ? 'aria-current="step"' : ""}>
          <span class="trip-stop-time">${escapeHtml(stop.time)}</span>
          <span class="trip-stop-dot" aria-hidden="true"></span>
          <span class="trip-stop-name">
            ${escapeHtml(stop.stop_name)} (${escapeHtml(stop.platform)})
            <span class="trip-stop-id">
              ${escapeHtml(stop.stop_id)}
              ${index === boardingIndex ? " · TU WSIADASZ" : stop.first ? " · początek" : stop.last ? " · przyjazd końcowy" : ""}
            </span>
          </span>
        </button>
      `).join("")}
    </div>
  `;

  tripPanelBody.querySelectorAll(".trip-stop-button").forEach(button => {
    button.addEventListener("click", () => focusTripStop(Number(button.dataset.index)));
  });
  activeTripRows = rows;
  drawSelectedTrip(rows);
}

function showTripForDeparture(departure, fromStopId) {
  const line = String(departure.line);
  if (!/^\d{1,3}$/.test(line) || !fromStopId) return;

  ++tripSelectionToken;
  const requestToken = tripSelectionToken;
  activeTripRows = null;
  tripRouteLayer.clearLayers();
  closeStopPanel();
  map.closePopup();

  tripPanelTitle.textContent = `Linia ${line} → ${departure.display_direction}`;
  tripPanelBody.innerHTML = '<div class="panel-empty">Wczytywanie przebiegu kursu...</div>';
  tripPanel.classList.add("open");

  Promise.all([
    loadCourseJson(linesJsonCache, `data/rozklady/linie/${line}.json`),
    loadCourseJson(tripsJsonCache, `data/trips/${line.padStart(3, "0")}.json`)
  ]).then(([lineInfo, tripsInfo]) => {
    if (requestToken !== tripSelectionToken) return;

    const selected = KMMZTripRoute.findTripForDeparture(
      departure, fromStopId, lineInfo, tripsInfo
    );

    if (!selected.trip) {
      tripPanelBody.innerHTML = `<div class="panel-empty">${escapeHtml(selected.error)}</div>`;
      return;
    }

    const rows = KMMZTripRoute.getTripStopRows(selected.trip, lineInfo, stopIndex);
    if (!rows.length) {
      tripPanelBody.innerHTML = '<div class="panel-empty">Ten kurs nie ma listy przystanków.</div>';
      return;
    }

    const boardingIndex = KMMZTripRoute.findBoardingIndex(
      selected.trip, fromStopId, departure.time
    );
    if (boardingIndex < 0) {
      tripPanelBody.innerHTML = '<div class="panel-empty">Nie udało się jednoznacznie ustalić przystanku wsiadania dla tego odjazdu.</div>';
      return;
    }

    renderSelectedTrip(selected.trip, departure, rows, boardingIndex);
  }).catch(error => {
    if (requestToken !== tripSelectionToken) return;
    console.warn("Błąd wyświetlania przebiegu kursu:", error);
    tripPanelBody.innerHTML =
      '<div class="panel-empty">Nie udało się pobrać przebiegu tego kursu. Spróbuj ponownie.</div>';
  });
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

  nearestDeparturesBox.innerHTML = upcoming.map((item, index) => {
    const countdown = formatDepartureCountdown(item.minutesLeft, item.time);
    const nowClass = item.minutesLeft === 0 ? " now" : "";

    return `
      <button class="departure-card" type="button" data-index="${index}"
        title="Pokaż przebieg kursu ${escapeHtml(item.line)} o ${escapeHtml(item.time)} na mapie">
        <div class="departure-line">${escapeHtml(item.line)}</div>
        <div>
          <div class="departure-direction">${escapeHtml(item.display_direction)}</div>
          <div class="departure-time">Rozkładowo: ${escapeHtml(item.time)}</div>
        </div>
        <div class="departure-countdown${nowClass}">${escapeHtml(countdown)}</div>
      </button>
    `;
  }).join("");

  nearestDeparturesBox.querySelectorAll(".departure-card").forEach(button => {
    button.addEventListener("click", () => {
      const item = upcoming[Number(button.dataset.index)];
      if (item) showTripForDeparture(item, currentStopProperties?.stop_id);
    });
  });
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
        <div class="panel-empty">Brak kursów dla aktualnego dnia.</div>
      </div>
    `;
    return;
  }

  lineTimetableBox.innerHTML = `
    <div class="inline-timetable">
      <div class="inline-timetable-title">Linia ${escapeHtml(lineInfo.line)} → ${escapeHtml(lineInfo.main_direction)}</div>
      <div class="inline-timetable-day">${escapeHtml(getDayTypeLabel(currentDayType))}</div>
      <div class="inline-time-list">
        ${items.map((item, index) => {
          const extraDirection = item.display_direction !== lineInfo.main_direction
            ? item.display_direction
            : "";

          return `
            <button class="inline-time-row" type="button" data-index="${index}"
              title="Pokaż przebieg kursu o ${escapeHtml(item.time)} na mapie">
              <div class="inline-time">${escapeHtml(item.time)}</div>
              <div class="inline-time-direction">${escapeHtml(extraDirection)}</div>
            </button>
          `;
        }).join("")}
      </div>
    </div>
  `;

  lineTimetableBox.querySelectorAll(".inline-time-row").forEach(button => {
    button.addEventListener("click", () => {
      const item = items[Number(button.dataset.index)];
      if (item) showTripForDeparture(item, currentStopProperties?.stop_id);
    });
  });
}

function openStopPanel(properties) {
  // On small screens both sheets occupy the bottom; never overlap them.
  if (window.matchMedia("(max-width: 700px)").matches) {
    tripPanel.classList.remove("open");
  }

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

  fetch(`data/odjazdy/${stopId}.json`, { cache: "no-store" })
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

function normalizeSearchText(value) {
  return String(value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function buildStopSearchText(stop) {
  return normalizeSearchText([
    stop.stop_id,
    stop.name,
    stop.platform,
    stop.zone,
    `${stop.name} ${stop.platform}`,
    `${stop.name} (${stop.platform})`
  ].join(" "));
}

function hideSearchResults() {
  stopSearchResults.classList.remove("open");
}

function showSearchResults() {
  stopSearchResults.classList.add("open");
}

function getSearchResults(query) {
  const normalizedQuery = normalizeSearchText(query).trim();

  if (!normalizedQuery) {
    return [];
  }

  return allStops
    .filter(stop => stop.searchText.includes(normalizedQuery))
    .sort((a, b) => {
      const aIdStarts = a.stop_id.startsWith(query);
      const bIdStarts = b.stop_id.startsWith(query);

      if (aIdStarts && !bIdStarts) return -1;
      if (!aIdStarts && bIdStarts) return 1;

      const aNameStarts = normalizeSearchText(a.name).startsWith(normalizedQuery);
      const bNameStarts = normalizeSearchText(b.name).startsWith(normalizedQuery);

      if (aNameStarts && !bNameStarts) return -1;
      if (!aNameStarts && bNameStarts) return 1;

      return a.name.localeCompare(b.name, "pl");
    })
    .slice(0, 15);
}

function renderSearchResults(results) {
  currentSearchResults = results;

  if (!results.length) {
    stopSearchResults.innerHTML = `
      <div class="stop-search-empty">Brak pasujących przystanków.</div>
    `;
    showSearchResults();
    return;
  }

  stopSearchResults.innerHTML = results.map((stop, index) => `
    <button class="stop-search-result" type="button" data-index="${index}">
      <div class="stop-search-result-main">
        <span class="stop-search-id">${escapeHtml(stop.stop_id)}</span>
        ${escapeHtml(stop.name)} (${escapeHtml(stop.platform)})
      </div>
      <div class="stop-search-result-meta">
        Strefa: ${escapeHtml(stop.zone)}
      </div>
    </button>
  `).join("");

  stopSearchResults.querySelectorAll(".stop-search-result").forEach(button => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.index);
      const stop = currentSearchResults[index];

      if (stop) {
        focusStopFromSearch(stop);
      }
    });
  });

  showSearchResults();
}

function handleStopSearch() {
  const query = stopSearchInput.value.trim();

  if (!query) {
    hideSearchResults();
    currentSearchResults = [];
    return;
  }

  const results = getSearchResults(query);
  renderSearchResults(results);
}

function focusStopFromSearch(stop) {
  hideSearchResults();

  stopSearchInput.value = `${stop.name} (${stop.platform})`;

  const targetZoom = Math.max(map.getZoom(), 16);

  map.setView(stop.latlng, targetZoom, {
    animate: true
  });

  stop.layer.openPopup();
  openStopPanel(stop.properties);

  setTimeout(() => {
    if (typeof renderPopupLines === "function") {
      renderPopupLines(stop.stop_id);
    }
  }, 80);
}

stopSearchInput.addEventListener("input", handleStopSearch);

stopSearchInput.addEventListener("focus", () => {
  if (stopSearchInput.value.trim()) {
    handleStopSearch();
  }
});

stopSearchInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && currentSearchResults.length) {
    event.preventDefault();
    focusStopFromSearch(currentSearchResults[0]);
  }

  if (event.key === "Escape") {
    hideSearchResults();
  }
});

stopSearchClear.addEventListener("click", () => {
  stopSearchInput.value = "";
  currentSearchResults = [];
  hideSearchResults();
  stopSearchInput.focus();
});

document.addEventListener("click", event => {
  if (!stopSearch.contains(event.target)) {
    hideSearchResults();
  }
});

// Warstwa punktów.
function renderPopupLines(stopId) {
  const target = document.getElementById(`popup-lines-${stopId}`);

  if (!target) {
    return;
  }

  fetch(`data/odjazdy/${stopId}.json`, { cache: "no-store" })
    .then(response => {
      if (!response.ok) {
        throw new Error(`Brak pliku data/odjazdy/${stopId}.json`);
      }

      return response.json();
    })
    .then(data => {
      const lines = new Set();

      (data.served_lines || []).forEach(item => {
        if (item.line) {
          lines.add(String(item.line));
        }
      });

      if (!lines.size) {
        target.textContent = "brak danych";
        return;
      }

      const sortedLines = Array.from(lines).sort((a, b) => {
        const numberA = Number(a);
        const numberB = Number(b);

        if (!Number.isNaN(numberA) && !Number.isNaN(numberB)) {
          return numberA - numberB;
        }

        return a.localeCompare(b, "pl");
      });

      target.innerHTML = sortedLines.map(line => `
        <span style="
          display:inline-block;
          background:#f5c400;
          color:#222;
          font-weight:bold;
          border-radius:7px;
          padding:2px 7px;
          margin:2px 2px 0 3px;
          font-size:12px;
        ">${escapeHtml(line)}</span>
      `).join("");
    })
    .catch(() => {
      target.textContent = "brak danych";
    });
}
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
    
    const coordinates = feature.geometry.coordinates;
    const searchLatLng = L.latLng(coordinates[1], coordinates[0]);

const searchItem = {
  stop_id: String(p.stop_id),
  name: String(p.name),
  platform: String(p.platform),
  zone: String(p.zone),
  properties: p,
  layer: layer,
  latlng: searchLatLng
};

searchItem.searchText = buildStopSearchText(searchItem);
allStops.push(searchItem);
stopIndex.set(searchItem.stop_id, searchItem);

    const popupContent = `
  <div style="font-weight:bold;font-size:15px;margin-bottom:4px;">
    ${escapeHtml(p.name)} <span style="color:#555;font-size:13px;">(${escapeHtml(p.platform)})</span>
  </div>
  <div style="color:#555;font-size:13px;">ID: ${escapeHtml(p.stop_id)}</div>
  <div style="margin-top:4px;font-size:13px;">Strefa: ${escapeHtml(p.zone)}</div>
  <div style="margin-top:7px;font-size:13px;">
    <strong>Linie:</strong>
    <span id="popup-lines-${escapeHtml(p.stop_id)}">wczytywanie...</span>
  </div>
`;

    layer.bindPopup(popupContent);

    layer.on("click", function () {
  openStopPanel(p);
  setTimeout(() => {
    renderPopupLines(p.stop_id);
  }, 50);
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
