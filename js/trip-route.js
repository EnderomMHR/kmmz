/* Helpers for matching a map departure to ONE scheduled trip.
 * No street routing: consecutive planned stop positions are connected directly.
 * Kept independent of Leaflet so the real JSON can be tested in Node.
 */
(function (root) {
  "use strict";

  const SERVICE_DAYS = {
    R: ["workday"],
    S: ["saturday"],
    N: ["sunday"],
    SW: ["holiday"],
    SN: ["saturday", "sunday"]
  };

  function serviceMatches(serviceCode, dayType) {
    return (SERVICE_DAYS[String(serviceCode)] || []).includes(dayType);
  }

  function findTripForDeparture(departure, stopId, lineData, tripsData) {
    const directions = Array.isArray(lineData?.directions) ? lineData.directions : [];
    const directionIndex = directions.findIndex(d => d.slug === departure?.direction_slug);

    if (directionIndex < 0) {
      return { trip: null, error: "Nie znaleziono kierunku kursu." };
    }

    const candidates = (tripsData?.trips || []).filter(trip => {
      if (Number(trip.direction) !== directionIndex + 1 ||
          !serviceMatches(trip.service_code, departure.day_type) ||
          !Array.isArray(trip.stop_times)) {
        return false;
      }

      // The last time of a course is an arrival, never a selectable departure.
      return trip.stop_times.slice(0, -1).some(stop =>
        String(stop.stop_id) === String(stopId) && stop.time === departure.time
      );
    });

    if (candidates.length === 1) {
      return { trip: candidates[0], error: null };
    }

    if (!candidates.length) {
      return { trip: null, error: "Nie znaleziono kursu odpowiadającego temu odjazdowi." };
    }

    // A shared departure can describe two services at the same stop/time.
    // A different terminus normally tells them apart (e.g. extended service).
    const routeStops = directions[directionIndex].route_stops || [];
    const byTerminus = candidates.filter(trip => {
      const last = trip.stop_times[trip.stop_times.length - 1];
      const terminus = routeStops[last.stop_sequence - 1];
      return terminus?.stop_name === departure.display_direction;
    });

    if (byTerminus.length === 1) {
      return { trip: byTerminus[0], error: null };
    }

    // Never silently draw an arbitrary course when two variants are possible.
    return {
      trip: null,
      error: "Kilka kursów ma tę samą godzinę. Nie można jednoznacznie wskazać trasy."
    };
  }

  // Look up the selected VISIT, not merely the stop ID: a circular route
  // can call at one physical stop several times with different departure hours.
  // Final arrival is intentionally not considered a boarding position.
  function findBoardingIndex(trip, stopId, departureTime) {
    const stops = Array.isArray(trip?.stop_times) ? trip.stop_times : [];
    const matches = [];
    for (let index = 0; index < stops.length - 1; index++) {
      if (String(stops[index].stop_id) === String(stopId) &&
          stops[index].time === departureTime) {
        matches.push(index);
      }
    }
    // Do not highlight the wrong visit when a circular bus calls twice
    // at exactly the same stop and time.
    return matches.length === 1 ? matches[0] : -1;
  }

  function getTripStopRows(trip, lineData, stopIndex) {
    const direction = (lineData.directions || [])[Number(trip.direction) - 1];
    if (!direction || !Array.isArray(trip.stop_times)) return [];

    return trip.stop_times.map((stop, i) => {
      const routeStop = direction.route_stops?.[Number(stop.stop_sequence) - 1];
      const geoStop = stopIndex.get(String(stop.stop_id));
      return {
        stop_id: String(stop.stop_id),
        stop_name: routeStop?.stop_name || geoStop?.name || String(stop.stop_id),
        platform: routeStop?.platform ?? geoStop?.platform ?? "",
        time: stop.time,
        latlng: geoStop?.latlng ?? null,
        layer: geoStop?.layer ?? null,
        first: i === 0,
        last: i === trip.stop_times.length - 1
      };
    });
  }

  const api = { serviceMatches, findTripForDeparture, findBoardingIndex, getTripStopRows };
  root.KMMZTripRoute = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
