// Startowe ustawienie mapy.
// Celowo ustawione mniej więcej na obszar Małopolski Zachodniej.
const map = L.map('map').setView([50.15, 19.55], 10);

// Podkład mapowy OpenStreetMap.
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Warstwa na przystanki.
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
  return zoneColors[zone] || "#555555";
}
const stopFiles = [
  'data/stops/zarnowiec.geojson',
  'data/stops/zator.geojson'
];


// TUTAJ zostaje Twoja warstwa punktów
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
      <div class="popup-title">${p.name} <span class="popup-id">(${p.platform})</span></div>
      <div class="popup-id">ID: ${p.stop_id}</div>
      <div class="popup-zone">Strefa: ${p.zone}</div>
      <div style="margin-top:6px;">
        <a href="przystanki/${p.stop_id}.html">Otwórz stronę przystanku</a>
      </div>
    `;

    layer.bindPopup(popupContent);
  }
}).addTo(map);


// TUTAJ zamiast starego fetch('data/stops.geojson') wklejasz to:
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
