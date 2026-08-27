// Startowe ustawienie mapy.
// Celowo ustawione mniej więcej na obszar Małopolski Zachodniej.
const map = L.map('map').setView([50.15, 19.55], 10);

// Podkład mapowy OpenStreetMap.
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Warstwa na przystanki.
const stopsLayer = L.geoJSON(null, {
  pointToLayer: function (feature, latlng) {
    return L.circleMarker(latlng, {
      radius: 5,
      weight: 1,
      fillOpacity: 0.85
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

// Wczytanie przystanków z pliku GeoJSON.
fetch('data/stops.geojson')
  .then(response => response.json())
  .then(data => {
    stopsLayer.addData(data);
    map.fitBounds(stopsLayer.getBounds());
  })
  .catch(error => {
    console.error('Błąd wczytywania przystanków:', error);
  });
