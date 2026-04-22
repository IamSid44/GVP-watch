import { useCallback, useEffect, useRef, useState } from "react";
import { GoogleMap, useJsApiLoader, OverlayView } from "@react-google-maps/api";
import type { ReportMapItem } from "../../types";
import { SEVERITY_COLORS } from "../../types";
import { useDarkMode } from "../../context/DarkModeContext";

const GOOGLE_MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY as string;

const MAP_CENTER = { lat: 17.4742, lng: 78.3327 };

const SERILINGAMPALLY_BOUNDS = {
  north: 17.5600,
  south: 17.3900,
  east:  78.4650,
  west:  78.2350,
};

// Wards 104–110 only
const HIGHLIGHTED_WARDS = new Set([104, 105, 106, 107, 108, 109, 110]);

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
  minZoom: 12,
  maxZoom: 19,
  disableDefaultUI: false,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
  clickableIcons: false,
  restriction: {
    latLngBounds: SERILINGAMPALLY_BOUNDS,
    strictBounds: true,
  },
};

interface Props {
  reports: ReportMapItem[];
  onMarkerClick?: (id: string) => void;
  wardBoundaries?: GeoJSON.FeatureCollection | null;
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
  const { dark } = useDarkMode();

  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: GOOGLE_MAPS_KEY,
    id: "google-map-script",
  });

  // Apply dark/light map styles whenever dark mode changes
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.setOptions({ styles: dark ? DARK_MAP_STYLES : LIGHT_BASE_STYLES });
  }, [dark]);

  // Draw (or redraw) ward polygons whenever boundaries load or map mounts
  useEffect(() => {
    if (!mapRef.current || !wardBoundaries) return;

    // Clear old polygons
    polygonsRef.current.forEach((p) => p.setMap(null));
    polygonsRef.current = [];

    wardBoundaries.features.forEach((feature) => {
      const geom = feature.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
      const props = feature.properties as { ward_name?: string; ward_number?: number };

      if (!props?.ward_number || !HIGHLIGHTED_WARDS.has(props.ward_number)) return;

      const drawRing = (ring: number[][]) => {
        const path = ring.map(([lng, lat]) => ({ lat, lng }));
        const polygon = new google.maps.Polygon({
          paths: path,
          strokeColor: "#f59e0b",
          strokeOpacity: 1.0,
          strokeWeight: 2.5,
          fillColor: "#fbbf24",
          fillOpacity: 0.18,
          map: mapRef.current!,
        });
        polygonsRef.current.push(polygon);

        if (props.ward_name) {
          const infoWindow = new google.maps.InfoWindow({
            content: `<div style="font-size:13px;font-weight:600">${props.ward_name}</div>`,
          });
          polygon.addListener("mouseover", (e: google.maps.PolyMouseEvent) => {
            infoWindow.setPosition(e.latLng);
            infoWindow.open(mapRef.current!);
          });
          polygon.addListener("mouseout", () => infoWindow.close());
        }
      };

      if (geom.type === "Polygon") {
        geom.coordinates.forEach(drawRing);
      } else if (geom.type === "MultiPolygon") {
        geom.coordinates.forEach((poly) => poly.forEach(drawRing));
      }
    });
  }, [wardBoundaries, isLoaded]);

  const onLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
    map.setOptions({ styles: dark ? DARK_MAP_STYLES : LIGHT_BASE_STYLES });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onUnmount = useCallback(() => {
    polygonsRef.current.forEach((p) => p.setMap(null));
    polygonsRef.current = [];
    mapRef.current = null;
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
