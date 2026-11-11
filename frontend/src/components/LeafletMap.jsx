import { useEffect, useRef, useState } from "react";
import L from "leaflet";

function ndviColor(ndvi) {
  if (ndvi >= 0.68) return "#065f46";
  if (ndvi >= 0.55) return "#10b981";
  if (ndvi >= 0.42) return "#84cc16";
  if (ndvi >= 0.30) return "#eab308";
  return "#dc2626";
}

function sarColor(vv) {
  // Higher backscatter (less negative dB) -> denser woody structure
  if (vv >= -9.2) return "#1d4ed8";
  if (vv >= -10.5) return "#2563eb";
  if (vv >= -11.8) return "#0ea5e9";
  return "#64748b";
}

export default function LeafletMap({
  farms = [],
  selectedFarmId = null,
  onSelectFarm = null,
  ndviGrid = [],
  layerMode = "ndvi", // "ndvi" | "sar" | "boundary"
  showInnerBuffer = true,
  corePolygonGeojson = null,
  drawingMode = false,
  drawnPoints = [],
  onAddDrawPoint = null,
  heightClass = "h-[440px]",
  viewMode = "farmer",
  lang = "en",
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layersRef = useRef(null);
  const [basemap, setBasemap] = useState("satellite");

  // Initialize Leaflet map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: [18.0985, 78.8942],
      zoom: 15,
      zoomControl: true,
    });
    const layerGroup = L.layerGroup().addTo(map);
    mapRef.current = map;
    layersRef.current = layerGroup;

    return () => {
      map.remove();
      mapRef.current = null;
      layersRef.current = null;
    };
  }, []);

  // Swap basemap tiles
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    map.eachLayer((lyr) => {
      if (lyr instanceof L.TileLayer) {
        map.removeLayer(lyr);
      }
    });

    const tileUrl =
      basemap === "satellite"
        ? "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

    const attr =
      basemap === "satellite"
        ? "Tiles © Esri World Imagery"
        : "© OpenStreetMap contributors";

    L.tileLayer(tileUrl, { attribution: attr, maxZoom: 19 }).addTo(map);
  }, [basemap]);

  // Handle drawing click listener
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const handleClick = (e) => {
      if (drawingMode && onAddDrawPoint) {
        onAddDrawPoint([Number(e.latlng.lng.toFixed(6)), Number(e.latlng.lat.toFixed(6))]);
      }
    };
    map.on("click", handleClick);
    map.getContainer().style.cursor = drawingMode ? "crosshair" : "";
    return () => {
      map.off("click", handleClick);
      if (map.getContainer()) map.getContainer().style.cursor = "";
    };
  }, [drawingMode, onAddDrawPoint]);

  // Render polygons, inner buffer, NDVI/SAR spatial cells, and drawn vertices
  useEffect(() => {
    const map = mapRef.current;
    const group = layersRef.current;
    if (!map || !group) return;

    group.clearLayers();

    let focusBounds = null;

    farms.forEach((f) => {
      const isSelected = f.id === selectedFarmId;
      const isFlagged = f.verification_status === "FLAGGED_REVIEW";
      const strokeColor = isFlagged ? "#ef4444" : isSelected ? "#f59e0b" : "#10b981";
      const polyGeo = L.geoJSON(f.polygon_geojson, {
        style: {
          color: strokeColor,
          weight: isSelected ? 3 : 2,
          fillColor: strokeColor,
          fillOpacity: isSelected && ndviGrid?.length ? 0.05 : 0.22,
        },
      });

      polyGeo.bindTooltip(
        `<div style="font-size:12px;">
          <strong>${f.name}</strong><br/>
          ${f.gross_area_ha} ha (${f.core_pixels_10m} core 10m px)<br/>
          Status: ${f.verification_status}
        </div>`,
        { sticky: true }
      );

      if (onSelectFarm && !drawingMode) {
        polyGeo.on("click", () => onSelectFarm(f.id));
      }
      polyGeo.addTo(group);

      if (isSelected) {
        focusBounds = polyGeo.getBounds();
      }
    });

    // Draw 10m inner negative buffer polygon for selected farm
    if (showInnerBuffer && corePolygonGeojson) {
      L.geoJSON(corePolygonGeojson, {
        style: {
          color: "#fef08a",
          weight: 2,
          dashArray: "6 5",
          fillOpacity: 0,
        },
      })
        .bindTooltip("10m Inner Negative Buffer (Mixed Edge Pixels Excluded)")
        .addTo(group);
    }

    // Draw spatial 10m NDVI or Sentinel-1 SAR grid cells
    if (layerMode !== "boundary" && ndviGrid && ndviGrid.length > 0) {
      ndviGrid.forEach((cell) => {
        const fill = layerMode === "sar" ? sarColor(cell.vv_db) : ndviColor(cell.ndvi);
        L.geoJSON(cell.geojson, {
          style: {
            color: "#ffffff",
            weight: 0.4,
            fillColor: fill,
            fillOpacity: 0.62,
          },
        })
          .bindTooltip(
            `<span class="font-mono">NDVI: ${cell.ndvi} · SAR VV: ${cell.vv_db} dB</span>`,
            { sticky: true }
          )
          .addTo(group);
      });
    }

    // Draw active polygon-drawing vertices
    if (drawnPoints && drawnPoints.length > 0) {
      const latLngs = drawnPoints.map((p) => [p[1], p[0]]);
      drawnPoints.forEach((p, idx) => {
        L.circleMarker([p[1], p[0]], {
          radius: 6,
          color: "#0D2818",
          weight: 2,
          fillColor: "#f59e0b",
          fillOpacity: 1,
        })
          .bindTooltip(`Vertex #${idx + 1}`)
          .addTo(group);
      });
      if (latLngs.length >= 2) {
        const shapeLayer =
          latLngs.length >= 3
            ? L.polygon(latLngs, { color: "#f59e0b", weight: 2.5, fillColor: "#f59e0b", fillOpacity: 0.25 })
            : L.polyline(latLngs, { color: "#f59e0b", weight: 2.5, dashArray: "4 4" });
        shapeLayer.addTo(group);
      }
    }

    if (focusBounds && focusBounds.isValid() && !drawingMode) {
      map.fitBounds(focusBounds, { padding: [45, 45], maxZoom: 17 });
    } else if (!selectedFarmId && farms.length > 1 && !drawingMode) {
      const allGroup = L.featureGroup(farms.map((f) => L.geoJSON(f.polygon_geojson)));
      if (allGroup.getBounds().isValid()) {
        map.fitBounds(allGroup.getBounds(), { padding: [40, 40], maxZoom: 6 });
      }
    }
  }, [farms, selectedFarmId, ndviGrid, layerMode, showInnerBuffer, corePolygonGeojson, drawingMode, drawnPoints, onSelectFarm]);

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-[#E5DFD1]">
      <div ref={containerRef} className={`w-full ${heightClass}`} />
      <div className="absolute top-3 right-3 z-[400] flex gap-1.5 bg-white/95 backdrop-blur px-2 py-1.5 rounded-lg shadow border border-[#E5DFD1] text-xs font-semibold">
        <button
          type="button"
          onClick={() => setBasemap("satellite")}
          className={`px-2.5 py-1 rounded-md transition ${
            basemap === "satellite" ? "bg-[#0D2818] text-white" : "text-[#163A24] hover:bg-[#F3EFE6]"
          }`}
        >
          Satellite
        </button>
        <button
          type="button"
          onClick={() => setBasemap("street")}
          className={`px-2.5 py-1 rounded-md transition ${
            basemap === "street" ? "bg-[#0D2818] text-white" : "text-[#163A24] hover:bg-[#F3EFE6]"
          }`}
        >
          Street Map
        </button>
      </div>
      {layerMode !== "boundary" && ndviGrid?.length > 0 && (
        <div className="absolute bottom-3 left-3 z-[400] bg-white/95 backdrop-blur px-3 py-2 rounded-lg shadow border border-[#E5DFD1] text-[11px]">
          <div className="font-bold text-[#0D2818] mb-1">
            {viewMode === "farmer"
              ? layerMode === "sar"
                ? lang === "te"
                  ? "వర్షాకాల రాడార్ చెట్ల స్కాన్"
                  : "Cloud-Proof Radar Tree Scan"
                : lang === "te"
                ? "చెట్ల పచ్చదనం & ఆరోగ్యం"
                : "Tree Greenery & Health"
              : layerMode === "sar"
              ? "Sentinel-1 VV Backscatter (dB)"
              : "Sentinel-2 NDVI Grid (10m Proxy)"}
          </div>
          <div className="flex items-center gap-2 text-slate-600">
            {layerMode === "sar" ? (
              <>
                <span className="inline-block w-3 h-3 rounded bg-[#64748b]" /> {viewMode === "farmer" && lang === "te" ? "తక్కువ" : "Low"}
                <span className="inline-block w-3 h-3 rounded bg-[#0ea5e9]" /> {viewMode === "farmer" && lang === "te" ? "మధ్యస్థం" : "Med"}
                <span className="inline-block w-3 h-3 rounded bg-[#1d4ed8]" /> {viewMode === "farmer" && lang === "te" ? "దట్టమైన చెట్లు" : "Dense Trees"}
              </>
            ) : (
              <>
                <span className="inline-block w-3 h-3 rounded bg-[#dc2626]" /> {viewMode === "farmer" ? (lang === "te" ? "ఖాళీ భూమి" : "Bare") : "<0.30"}
                <span className="inline-block w-3 h-3 rounded bg-[#eab308]" /> {viewMode === "farmer" ? (lang === "te" ? "లేత" : "Young") : "0.42"}
                <span className="inline-block w-3 h-3 rounded bg-[#84cc16]" /> {viewMode === "farmer" ? (lang === "te" ? "పెరుగుతోంది" : "Growing") : "0.55"}
                <span className="inline-block w-3 h-3 rounded bg-[#065f46]" /> {viewMode === "farmer" ? (lang === "te" ? "ఆరోగ్యంగా ఉంది" : "Healthy") : ">0.68"}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

