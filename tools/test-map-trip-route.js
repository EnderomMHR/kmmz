#!/usr/bin/env node
"use strict";
/* Uses the actual published timetable and per-stop departure files, not mock schedules. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ROOT = path.resolve(__dirname, "..");
const route = require("../js/trip-route.js");
const get = file => JSON.parse(fs.readFileSync(path.join(ROOT, file), "utf8"));

assert.equal(route.serviceMatches("R", "workday"), true);
assert.equal(route.serviceMatches("R", "sunday"), false);
assert.equal(route.serviceMatches("SN", "saturday"), true);
assert.equal(route.serviceMatches("SN", "sunday"), true);
assert.equal(route.serviceMatches("SN", "holiday"), false);
assert.equal(route.serviceMatches("SW", "holiday"), true);
assert.equal(route.serviceMatches("S", "sunday"), false);

const locations = new Map();
for (const file of fs.readdirSync(path.join(ROOT, "data/stops")).filter(f => f.endsWith(".geojson"))) {
  for (const feature of get(path.join("data/stops", file)).features) {
    const p = feature.properties;
    const coordinates = feature.geometry.coordinates;
    assert.ok(coordinates.length >= 2);
    locations.set(String(p.stop_id), {
      name: p.name,
      platform: String(p.platform),
      latlng: [coordinates[1], coordinates[0]]
    });
  }
}

const examples = [
  ["15", "2627", "oswiecim", "Oświęcim Dworzec Fabryczny", "workday"],
  ["15", "0830", "jawiszowice", "Jawiszowice Jaźnik", "saturday"],
  ["15", "2553", "oswiecim", "Oświęcim Dworzec Fabryczny", "workday"],
  ["15", "0666", "oswiecim", "Oświęcim Dworzec Fabryczny", "workday"],
  ["15", "0631", "jawiszowice", "Jawiszowice Jaźnik", "workday"],
  ["12", "2553", "metkow", "Mętków Mały", "workday"],
  ["12", "2568", "metkow", "Mętków Mały", "sunday"],
  ["13", "2769", "zwm", "Hutki Pętla", "workday"],
  ["13", "0483", "groniec", "Sławków Groniec Świerkowa", "holiday"],
  ["14", "0334", "grojec", "Sanka Głuchówki", "workday"],
  ["14", "1399", "chrzanow", "Chrzanów Dworzec Autobusowy", "saturday"],
  ["11", "0200", "tarnawa", "Poręba Laskowska", "workday"],
  ["11", "0747", "olkusz", "Olkusz Dworzec PKS", "workday"],
  ["10", "0147", "okrezna-1", null, "workday"],
  ["9", "0001", "okrezna-1", null, "workday"]
];
let checked = 0, missingCoordinates = 0;
for (const [lineNo, stopId, slug, displayDirection, day] of examples) {
  const line = get("data/rozklady/linie/" + lineNo + ".json");
  const trips = get("data/trips/" + lineNo.padStart(3, "0") + ".json");
  const stop = get("data/odjazdy/" + stopId + ".json");
  const departures = stop.departures.filter(d =>
    d.line === lineNo && d.direction_slug === slug &&
    d.day_type === day &&
    (!displayDirection || d.display_direction === displayDirection)
  );
  if (!departures.length) {
    // For circular routes slugs can differ; everything else must be exercised.
    if (lineNo === "9" || lineNo === "10") continue;
    throw new Error("No sample departure: " + lineNo + "/" + stopId + "/" + day);
  }

  for (const departure of departures) {
    const found = route.findTripForDeparture(departure, stopId, line, trips);
    if (!found.trip) {
      // Some lines have genuinely simultaneous and indistinguishable departures.
      assert.match(found.error, /Kilka kursów|Nie znaleziono kursu/);
      continue;
    }
    const trip = found.trip;
    assert.equal(String(trip.direction), String(line.directions.findIndex(d=>d.slug===slug)+1));
    assert.ok(trip.stop_times.slice(0, -1).some(x=>x.stop_id===stopId && x.time===departure.time));
    assert.ok(route.serviceMatches(trip.service_code, day));
    const rows = route.getTripStopRows(trip, line, locations);
    const boardingIndex = route.findBoardingIndex(trip, stopId, departure.time);
    assert.ok(boardingIndex >= 0, "Boarding stop must be on the matched trip: " + trip.trip_id);
    assert.equal(rows[boardingIndex].stop_id, stopId);
    assert.equal(rows[boardingIndex].time, departure.time);
    assert.equal(boardingIndex < rows.length - 1, true, "Final arrivals aren't boarding stops");
    assert.equal(rows.slice(0, boardingIndex).length, boardingIndex);
    assert.equal(rows.slice(boardingIndex).length, rows.length - boardingIndex);
    assert.equal(rows.length, trip.stop_times.length);
    assert.equal(rows[0].first, true);
    assert.equal(rows.at(-1).last, true);
    assert.equal(rows[0].stop_id, trip.stop_times[0].stop_id);
    assert.equal(rows.at(-1).time, trip.stop_times.at(-1).time);
    missingCoordinates += rows.filter(row=>!row.latlng).length;
    checked++;
  }
}
assert.ok(checked >= 100, "Too few real course departure cases tested: "+checked);
assert.equal(missingCoordinates, 0, "Some actual route stops lack known map coordinates");

// A final arrival must never match as a departure.
const l15 = get("data/rozklady/linie/15.json");
const t15 = get("data/trips/015.json");
const bogus = route.findTripForDeparture({
  line:"15",direction_slug:"oswiecim",time:"05:41",day_type:"workday",
  display_direction:"Oświęcim Dworzec Fabryczny"
}, "0879", l15, t15);
assert.equal(bogus.trip, null);
assert.equal(route.findBoardingIndex(t15.trips[0], "0879", t15.trips[0].stop_times.at(-1).time), -1);
assert.equal(route.findBoardingIndex(t15.trips[0], "nonexistent", "04:30"), -1);

// If two otherwise indistinguishable trips share the same time, do not guess.
const duplicate = JSON.parse(JSON.stringify(t15.trips[0]));
const fake = route.findTripForDeparture({
  line:"15", direction_slug:"oswiecim", time:duplicate.stop_times[0].time,
  day_type:"workday",display_direction:"Oświęcim Dworzec Fabryczny"
}, duplicate.stop_times[0].stop_id, l15, {trips:[duplicate,duplicate]});
assert.equal(fake.trip, null);
assert.match(fake.error, /Kilka kursów/);

// Repeated stop IDs (circular routes) remain separate rows.
const loopTrip = {direction:1,stop_times:[
  {stop_id:"2627",stop_sequence:1,time:"10:00"},
  {stop_id:"2553",stop_sequence:2,time:"10:15"},
  {stop_id:"2627",stop_sequence:3,time:"10:30"}
]};
const loopRows=route.getTripStopRows(loopTrip,{
  directions:[{route_stops:[
    {stop_name:"Jawiszowice Jaźnik",platform:"1"},
    {stop_name:"Brzeszcze Dworzec PKP",platform:"0"},
    {stop_name:"Jawiszowice Jaźnik",platform:"1"}
  ]}]
},locations);
assert.equal(loopRows.length,3);
assert.equal(loopRows[0].stop_id,loopRows[2].stop_id);
assert.notEqual(loopRows[0].time,loopRows[2].time);
assert.equal(route.findBoardingIndex(loopTrip,"2627","10:00"),0);
assert.equal(route.findBoardingIndex(loopTrip,"2627","10:30"),-1,"End-of-route arrival is not a departure");
assert.equal(route.findBoardingIndex(loopTrip,"2553","10:15"),1);
const loopMulti = { stop_times: [
  {stop_id:"2627",stop_sequence:1,time:"10:00"},
  {stop_id:"2553",stop_sequence:2,time:"10:15"},
  {stop_id:"2627",stop_sequence:3,time:"10:25"},
  {stop_id:"2553",stop_sequence:4,time:"10:40"}
]};
assert.equal(route.findBoardingIndex(loopMulti,"2627","10:25"),2,
  "Two visits to the same physical stop must use the chosen hour");
assert.equal(route.findBoardingIndex(loopMulti,"2627","10:00"),0);
assert.equal(route.findBoardingIndex(loopMulti,"2553","10:40"),-1,
  "Terminal arrivals cannot be used for boarding");
const equalTimes = { stop_times: [
  {stop_id:"2627",stop_sequence:1,time:"10:00"},
  {stop_id:"2553",stop_sequence:2,time:"10:15"},
  {stop_id:"2627",stop_sequence:3,time:"10:00"},
  {stop_id:"2553",stop_sequence:4,time:"10:40"}
]};
assert.equal(route.findBoardingIndex(equalTimes,"2627","10:00"),-1,
  "An indistinguishable repeated visit must not be highlighted arbitrarily");

// The map loads helpers before the main script, and both selection UIs are real buttons.
const html=fs.readFileSync(path.join(ROOT,"mapa.html"),"utf8");
const ui=fs.readFileSync(path.join(ROOT,"js/mapa.js"),"utf8");
assert.ok(html.indexOf('src="js/trip-route.js')<html.indexOf('src="js/mapa.js'));
assert.match(html, /id="trip-panel"/);
assert.match(ui, /showTripForDeparture\(item, currentStopProperties\?\.stop_id\)/);
assert.match(ui, /L\.polyline\(segment/);
assert.match(ui, /closeTripRoute/);
assert.match(ui, /renderSelectedTrip\(selected\.trip, departure, rows, boardingIndex\)/);
assert.match(ui, /index < boardingIndex \? " past"/);
assert.match(ui, /index === boardingIndex \? " boarding"/);
assert.match(ui, /aria-current="step"/);
assert.match(ui, /" · TU WSIADASZ"/);
assert.match(ui, /escapeHtml\(extraDirection\)<\/div>/);
assert.doesNotMatch(ui, /extraDirection \|\| item\.display_direction/,
  "Only exceptional destination labels belong next to inline departure times");
assert.match(html, /\.trip-stop-button\.past\s*\{/);
assert.match(html, /\.trip-stop-button\.boarding\s*\{/);
console.log("OK: map selected-trip routing, " + checked +
  " real departures, precise boarding position, faded prior stops, normal destination labels.");
