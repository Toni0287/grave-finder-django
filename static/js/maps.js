/* Grave Finder map helpers (Leaflet + OpenStreetMap, no API key needed). */
(function () {
  "use strict";

  const CAPE_TOWN = [-33.9249, 18.4241];

  function readJSON(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }

  function baseMap(elementId, center, zoom) {
    const map = L.map(elementId).setView(center || CAPE_TOWN, zoom || 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    return map;
  }

  function popupFor(marker) {
    const wrap = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = marker.name;
    wrap.appendChild(title);
    if (marker.cemetery) {
      wrap.appendChild(document.createElement("br"));
      wrap.appendChild(document.createTextNode(marker.cemetery));
    }
    if (marker.location) {
      wrap.appendChild(document.createElement("br"));
      wrap.appendChild(document.createTextNode(marker.location));
    }
    if (marker.url) {
      wrap.appendChild(document.createElement("br"));
      const link = document.createElement("a");
      link.href = marker.url;
      link.textContent = "View details";
      wrap.appendChild(link);
    }
    return wrap;
  }

  /** A map with one pin per marker, zoomed to fit them all. */
  function markerMap(elementId, dataId) {
    const markers = readJSON(dataId) || [];
    const map = baseMap(elementId);
    if (!markers.length) return map;
    const layer = L.featureGroup(
      markers.map((m) => L.marker([m.lat, m.lng]).bindPopup(popupFor(m)))
    ).addTo(map);
    const fit = () => map.fitBounds(layer.getBounds().pad(0.2), { maxZoom: 16 });
    fit();
    // If the map was drawn while hidden or zero-sized, refit once it gets a real size.
    if (window.ResizeObserver) {
      let fitted = map.getSize().x > 0;
      new ResizeObserver(function () {
        map.invalidateSize();
        if (!fitted && map.getSize().x > 0) { fitted = true; fit(); }
      }).observe(document.getElementById(elementId));
    }
    return map;
  }

  /** A single grave, with a "Get directions" button that routes from the visitor. */
  function graveMap(elementId, dataId) {
    const grave = readJSON(dataId);
    const map = baseMap(elementId, [grave.lat, grave.lng], 17);
    L.marker([grave.lat, grave.lng]).addTo(map).bindPopup(popupFor(grave)).openPopup();

    const button = document.getElementById("directions-btn");
    const status = document.getElementById("directions-status");
    let routing = null;

    function say(text) { if (status) status.textContent = text; }

    if (button) {
      button.addEventListener("click", function () {
        if (!navigator.geolocation) {
          say("Your browser cannot share your location. Use the Google Maps link instead.");
          return;
        }
        say("Finding your location…");
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            const from = L.latLng(pos.coords.latitude, pos.coords.longitude);
            if (routing) map.removeControl(routing);
            routing = L.Routing.control({
              waypoints: [from, L.latLng(grave.lat, grave.lng)],
              routeWhileDragging: false,
              addWaypoints: false,
              show: true,
            })
              .on("routesfound", function (e) {
                const s = e.routes[0].summary;
                say(`About ${(s.totalDistance / 1000).toFixed(1)} km, ${Math.round(s.totalTime / 60)} minutes by car.`);
              })
              .on("routingerror", function () {
                say("Could not plan a route right now. Try the Google Maps link.");
              })
              .addTo(map);
          },
          function () {
            say("Location permission was refused. Use the Google Maps link instead.");
          },
          { enableHighAccuracy: true, timeout: 10000 }
        );
      });
    }
    return map;
  }

  /** Share a page with the device's share sheet, or copy the link. */
  function shareButton(buttonId) {
    const button = document.getElementById(buttonId);
    if (!button) return;
    button.addEventListener("click", async function () {
      const data = { title: document.title, text: button.dataset.text || "", url: window.location.href };
      try {
        if (navigator.share) {
          await navigator.share(data);
        } else {
          await navigator.clipboard.writeText(data.url);
          button.textContent = "Link copied";
        }
      } catch (err) {
        /* user closed the share sheet */
      }
    });
  }

  window.GraveFinder = { markerMap, graveMap, shareButton };
})();
