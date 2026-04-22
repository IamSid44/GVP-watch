import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GoogleMap, useJsApiLoader, OverlayView } from "@react-google-maps/api";
import type { ReportMapItem } from "../../types";
import { SEVERITY_COLORS } from "../../types";
import { useDarkMode } from "../../context/DarkModeContext";

const GOOGLE_MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY as string;

const MAP_CENTER = { lat: 17.456, lng: 78.336 };

const SERILINGAMPALLY_BOUNDS = {
  north: 17.5400,
  south: 17.3800,
  east:  78.4300,
  west:  78.2400,
};

// Active jurisdiction: wards 104, 105, 106, 111
const HIGHLIGHTED_WARDS = new Set([104, 105, 106, 111]);

// Hide POI icons/labels, keep roads and area names
const LIGHT_BASE_STYLES: google.maps.MapTypeStyle[] = [
  { featureType: "poi", elementType: "all", stylers: [{ visibility: "off" }] },
  { featureType: "transit.station", elementType: "all", stylers: [{ visibility: "off" }] },
];

// Google Maps "night" theme
const DARK_MAP_STYLES: google.maps.MapTypeStyle[] = [
  { elementType: "geometry", stylers: [{ color: "#1d2c3e" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#1d2c3e" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#8fa3b8" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#2c3e50" }] },
  { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#1a252f" }] },
  { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#9ca3af" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#3d5166" }] },
  { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#253647" }] },
  { featureType: "road.highway", elementType: "labels.text.fill", stylers: [{ color: "#b0bec5" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#0f1c2e" }] },
  { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#4e6d8c" }] },
  { featureType: "landscape", elementType: "geometry", stylers: [{ color: "#18293a" }] },
  { featureType: "administrative", elementType: "geometry.stroke", stylers: [{ color: "#334d66" }] },
  { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#8fa3b8" }] },
  { featureType: "poi", elementType: "all", stylers: [{ visibility: "off" }] },
  { featureType: "transit.station", elementType: "all", stylers: [{ visibility: "off" }] },
];

const BASE_MAP_OPTIONS: google.maps.MapOptions = {
  zoom: 13,
  minZoom: 10,
  maxZoom: 19,
  disableDefaultUI: false,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
  clickableIcons: false,
  restriction: {
    latLngBounds: SERILINGAMPALLY_BOUNDS,
    strictBounds: false,
  },
};

interface Props {
  reports: ReportMapItem[];
  onMarkerClick?: (id: string) => void;
  wardBoundaries?: GeoJSON.FeatureCollection | null;
}

interface WardLabel {
  lat: number;
  lng: number;
  text: string;
}

const SEVERITY_SIZE: Record<string, number> = {
  HIGH: 9,
  MEDIUM: 7,
  LOW: 6,
};

export default function MapView({ reports, onMarkerClick, wardBoundaries }: Props) {
  const mapRef = useRef<google.maps.Map | null>(null);
  const polygonsRef = useRef<google.maps.Polygon[]>([]);
  const [zoom, setZoom] = useState(13);
  // mapReady is state (not a ref) so that setting it in onLoad triggers dependent effects
  const [mapReady, setMapReady] = useState(false);
  const { dark } = useDarkMode();

  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: GOOGLE_MAPS_KEY,
    id: "google-map-script",
  });

  // Apply dark/light map styles whenever dark mode changes
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.setOptions({ styles: dark ? DARK_MAP_STYLES : LIGHT_BASE_STYLES });
  }, [dark, mapReady]);

  // Draw (or redraw) ward polygons whenever boundaries, map, or dark mode changes.
  // mapReady (state) is in the dep array so this effect re-runs the moment onLoad fires,
  // even if wardBoundaries was already available before the map instance was created.
  useEffect(() => {
    if (!mapRef.current || !wardBoundaries) return;

    polygonsRef.current.forEach((p) => p.setMap(null));
    polygonsRef.current = [];

    // Pastel blue palette — lighter in dark mode for contrast against dark basemap
    const normalStroke = dark ? "#60a5fa" : "#93c5fd";
    const normalFill   = dark ? "#3b82f6" : "#bfdbfe";
    const normalFillOp = dark ? 0.15 : 0.22;
    const hoverStroke  = dark ? "#93c5fd" : "#2563eb";
    const hoverFill    = dark ? "#60a5fa" : "#3b82f6";
    const hoverFillOp  = dark ? 0.30 : 0.28;
    const labelColor   = dark ? "#bfdbfe" : "#1e40af";

    wardBoundaries.features.forEach((feature) => {
      const geom = feature.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
      // Support both API format (ward_number/ward_name) and local GeoJSON format (ward: "104-NAME")
      const raw = feature.properties as Record<string, unknown>;
      let wardNum: number | null = null;
      let wardLabel: string | null = null;

      if (raw.ward_number != null) {
        wardNum = Number(raw.ward_number);
        wardLabel = (raw.ward_name as string) ?? null;
      } else if (typeof raw.ward === "string") {
        const parts = (raw.ward as string).split("-");
        wardNum = parseInt(parts[0], 10);
        wardLabel = parts.slice(1).join(" ").trim() || null;
      }

      if (!wardNum || !HIGHLIGHTED_WARDS.has(wardNum)) return;

      // Compute centroid of the largest exterior ring for label placement
      const rings: number[][][] =
        geom.type === "Polygon"
          ? geom.coordinates
          : geom.coordinates.map((poly) => poly[0]);
      const largestRing = rings.reduce((a, b) => (b.length > a.length ? b : a), rings[0]);

      const drawRing = (ring: number[][]) => {
        const path = ring.map(([lng, lat]) => ({ lat, lng }));
        const polygon = new google.maps.Polygon({
          paths: path,
          strokeColor: normalStroke,
          strokeOpacity: 1.0,
          strokeWeight: 2,
          fillColor: normalFill,
          fillOpacity: normalFillOp,
          map: mapRef.current!,
        });
        polygonsRef.current.push(polygon);

        polygon.addListener("mouseover", () => {
          polygon.setOptions({
            strokeColor: hoverStroke,
            strokeWeight: 3.5,
            fillColor: hoverFill,
            fillOpacity: hoverFillOp,
          });
        });
        polygon.addListener("mouseout", () => {
          polygon.setOptions({
            strokeColor: normalStroke,
            strokeWeight: 2,
            fillColor: normalFill,
            fillOpacity: normalFillOp,
          });
        });
      };

      if (geom.type === "Polygon") {
        geom.coordinates.forEach(drawRing);
      } else if (geom.type === "MultiPolygon") {
        geom.coordinates.forEach((poly) => poly.forEach(drawRing));
      }
    });
  }, [wardBoundaries, mapReady, dark]);

  const wardLabels = useMemo<WardLabel[]>(() => {
    if (!wardBoundaries) return [];

    const result: WardLabel[] = [];
    wardBoundaries.features.forEach((feature) => {
      const geom = feature.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
      const raw = feature.properties as Record<string, unknown>;
      let wardNum: number | null = null;
      let wardLabel: string | null = null;

      if (raw.ward_number != null) {
        wardNum = Number(raw.ward_number);
        wardLabel = (raw.ward_name as string) ?? null;
      } else if (typeof raw.ward === "string") {
        const parts = (raw.ward as string).split("-");
        wardNum = parseInt(parts[0], 10);
        wardLabel = parts.slice(1).join(" ").trim() || null;
      }

      if (!wardNum || !HIGHLIGHTED_WARDS.has(wardNum)) return;

      const rings: number[][][] =
        geom.type === "Polygon"
          ? geom.coordinates
          : geom.coordinates.map((poly) => poly[0]);
      const largestRing = rings.reduce((a, b) => (b.length > a.length ? b : a), rings[0]);
      const centLat = largestRing.reduce((s, c) => s + c[1], 0) / largestRing.length;
      const centLng = largestRing.reduce((s, c) => s + c[0], 0) / largestRing.length;

      result.push({
        lat: centLat,
        lng: centLng,
        text: wardLabel ? `${wardNum} · ${wardLabel}` : `Ward ${wardNum}`,
      });
    });

    return result;
  }, [wardBoundaries]);

  const onLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
    map.setOptions({ styles: dark ? DARK_MAP_STYLES : LIGHT_BASE_STYLES });
    setMapReady(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onUnmount = useCallback(() => {
    polygonsRef.current.forEach((p) => p.setMap(null));
    polygonsRef.current = [];
    mapRef.current = null;
    setMapReady(false);
  }, []);

  if (loadError) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-900">
        <div className="text-center text-gray-500">
          <p className="font-medium">Map failed to load</p>
          <p className="text-sm mt-1">Check your Google Maps API key</p>
        </div>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-900">
        <div className="text-sm text-gray-400">Loading map…</div>
      </div>
    );
  }

  const clusters = clusterReports(reports, zoom);

  return (
    <GoogleMap
      mapContainerStyle={{ width: "100%", height: "100%" }}
      center={MAP_CENTER}
      options={BASE_MAP_OPTIONS}
      onLoad={onLoad}
      onUnmount={onUnmount}
      onZoomChanged={() => {
        if (mapRef.current) setZoom(mapRef.current.getZoom() ?? 13);
      }}
    >
      {clusters.map((cluster, i) =>
        cluster.reports.length === 1 ? (
          <SingleMarker
            key={cluster.reports[0].ticket_id}
            report={cluster.reports[0]}
            onClick={onMarkerClick}
          />
        ) : (
          <ClusterMarker
            key={i}
            lat={cluster.lat}
            lng={cluster.lng}
            count={cluster.reports.length}
            onClick={() => {
              mapRef.current?.setZoom((mapRef.current.getZoom() ?? 13) + 2);
              mapRef.current?.panTo({ lat: cluster.lat, lng: cluster.lng });
            }}
          />
        )
      )}

      {wardLabels.map((label) => (
        <OverlayView
          key={label.text}
          position={{ lat: label.lat, lng: label.lng }}
          mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
        >
          <div
            style={{
              transform: "translate(-50%, -50%)",
              pointerEvents: "none",
              color: dark ? "#bfdbfe" : "#1e40af",
              fontSize: "16px",
              fontWeight: 800,
              textShadow: dark
                ? "0 1px 3px rgba(0,0,0,0.8)"
                : "0 1px 2px rgba(255,255,255,0.9)",
              zIndex: 999,
              whiteSpace: "nowrap",
            }}
          >
            {label.text}
          </div>
        </OverlayView>
      ))}
    </GoogleMap>
  );
}

// ─── Single coloured circle marker ──────────────────────────────────────────

function SingleMarker({
  report,
  onClick,
}: {
  report: ReportMapItem;
  onClick?: (id: string) => void;
}) {
  const isResolved = report.status === "RESOLVED";
  const isUnresponsive = report.status === "UNRESPONSIVE";
  const color = isResolved
    ? "#22c55e"
    : isUnresponsive
    ? "#6b7280"
    : (SEVERITY_COLORS[report.severity_score ?? "MEDIUM"] ?? "#9ca3af");
  const r = SEVERITY_SIZE[report.severity_score ?? "MEDIUM"] ?? 7;
  const opacity = isUnresponsive ? 0.6 : 1;

  return (
    <OverlayView
      position={{ lat: report.latitude, lng: report.longitude }}
      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
    >
      <div
        onClick={() => onClick?.(report.ticket_id)}
        style={{
          width: r * 2,
          height: r * 2,
          borderRadius: "50%",
          backgroundColor: color,
          opacity,
          border: "2px solid white",
          boxShadow: "0 1px 4px rgba(0,0,0,0.4)",
          cursor: "pointer",
          transform: "translate(-50%, -50%)",
        }}
        title={report.category ?? ""}
      />
    </OverlayView>
  );
}

// ─── Cluster bubble ──────────────────────────────────────────────────────────

function ClusterMarker({
  lat,
  lng,
  count,
  onClick,
}: {
  lat: number;
  lng: number;
  count: number;
  onClick: () => void;
}) {
  const color = count >= 15 ? "#ef4444" : count >= 5 ? "#f97316" : "#f59e0b";
  // Size grows logarithmically with count, capped
  const size = Math.min(52, 28 + Math.round(Math.log2(count) * 6));

  return (
    <OverlayView
      position={{ lat, lng }}
      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
    >
      <div
        onClick={onClick}
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          backgroundColor: color,
          border: "3px solid white",
          boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
          cursor: "pointer",
          transform: "translate(-50%, -50%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          fontSize: size < 36 ? 11 : 13,
          fontWeight: 800,
          letterSpacing: "-0.5px",
        }}
      >
        {count}
      </div>
    </OverlayView>
  );
}

// ─── Grid-based clustering ────────────────────────────────────────────────────

interface Cluster {
  lat: number;
  lng: number;
  reports: ReportMapItem[];
}

function clusterReports(reports: ReportMapItem[], zoom: number): Cluster[] {
  const cellSize =
    zoom <= 11 ? 0.08 :
    zoom <= 12 ? 0.035 :
    zoom <= 13 ? 0.018 :
    zoom <= 14 ? 0.009 :
    zoom <= 15 ? 0.004 :
    zoom <= 16 ? 0.002 : 0.001;

  const cells = new Map<string, ReportMapItem[]>();
  for (const r of reports) {
    const key = `${Math.floor(r.latitude / cellSize)},${Math.floor(r.longitude / cellSize)}`;
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key)!.push(r);
  }

  return Array.from(cells.values()).map((group) => ({
    lat: group.reduce((s, r) => s + r.latitude, 0) / group.length,
    lng: group.reduce((s, r) => s + r.longitude, 0) / group.length,
    reports: group,
  }));
}
