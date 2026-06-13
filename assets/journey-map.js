(function () {
  let map;
  const empty = { type: "FeatureCollection", features: [] };

  function escapeHtml(value) {
    const node = document.createElement("div");
    node.textContent = String(value || "");
    return node.innerHTML;
  }

  function initialize() {
    const container = document.getElementById("journey-map");
    if (!container || !window.maplibregl || map) return;
    map = new maplibregl.Map({
      container,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "paper", type: "background", paint: { "background-color": "#ded8c8" } }],
      },
      center: [-97.7431, 30.2672],
      zoom: 11,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", () => {
      for (let order = 1; order <= 15; order += 1) {
        const canvas = document.createElement("canvas");
        canvas.width = 32;
        canvas.height = 32;
        const context = canvas.getContext("2d");
        context.fillStyle = "#173f3a";
        context.beginPath();
        context.arc(16, 16, 13, 0, Math.PI * 2);
        context.fill();
        context.strokeStyle = "#fff8eb";
        context.lineWidth = 3;
        context.stroke();
        context.fillStyle = "#fff8eb";
        context.font = "bold 12px sans-serif";
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.fillText(String(order), 16, 16);
        map.addImage(`marker-${order}`, context.getImageData(0, 0, 32, 32));
      }
      map.addSource("journey", { type: "geojson", data: empty });
      map.addLayer({ id: "journey-route", type: "line", source: "journey", filter: ["==", ["geometry-type"], "LineString"], paint: { "line-color": "#e15d44", "line-width": 4, "line-opacity": 0.75 } });
      map.addLayer({ id: "journey-points", type: "symbol", source: "journey", filter: ["==", ["geometry-type"], "Point"], layout: { "icon-image": ["concat", "marker-", ["to-string", ["get", "order"]]], "icon-size": 1, "icon-allow-overlap": true } });
      map.on("click", "journey-points", (event) => {
        const feature = event.features[0];
        const p = feature.properties;
        new maplibregl.Popup({ maxWidth: "320px" }).setLngLat(feature.geometry.coordinates).setHTML(`<strong>${escapeHtml(p.order)}. ${escapeHtml(p.name)}</strong><br>${escapeHtml(p.time)} · ${escapeHtml(p.category)} · ${escapeHtml(p.duration_minutes)} min<br>${escapeHtml(p.capabilities)}<br><br>${escapeHtml(p.description)}<br><br>Simulated rating: ${escapeHtml(p.rating)}/5 (${escapeHtml(p.review_count)} demo reviews)<br>Simulated cost: $${escapeHtml(p.estimated_cost)}<br><br><em>${escapeHtml(p.reason)}</em>`).addTo(map);
      });
      map.on("mouseenter", "journey-points", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "journey-points", () => { map.getCanvas().style.cursor = ""; });
    });
  }

  window.JourneyMap = {
    update(data) {
      initialize();
      if (!map) return;
      const apply = () => {
        const source = map.getSource("journey");
        if (!source) return;
        source.setData(data || empty);
        const points = (data?.features || []).filter((f) => f.geometry.type === "Point");
        if (points.length) {
          const bounds = new maplibregl.LngLatBounds();
          points.forEach((f) => bounds.extend(f.geometry.coordinates));
          map.fitBounds(bounds, { padding: 55, maxZoom: 14 });
        }
      };
      map.loaded() ? apply() : map.once("load", apply);
    },
  };
  document.addEventListener("DOMContentLoaded", initialize);
  setTimeout(initialize, 500);
})();
