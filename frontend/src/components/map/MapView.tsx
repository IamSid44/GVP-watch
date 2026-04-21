import { useCallback, useRef, useState } from "react";
import { GoogleMap, useJsApiLoader, OverlayView } from "@react-google-maps/api";
import type { ReportMapItem } from "../../types";
import { SEVERITY_COLORS } from "../../types";

const GOOGLE_MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY as string;

const MAP_CENTER = { lat: 17.4931, lng: 78.302 };
const MAP_OPTIONS: google.maps.MapOptions = {
  zoom: 12,
  disableDefaultUI: false,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
  clickableIcons: false,
};

interface Props {
  reports: ReportMapItem[];
  onMarkerClick?: (id: string) => void;
  wardBoundaries?: GeoJSON.FeatureCollection | null;
}

const SEVERITY_SIZE: Record<string, number> = {
  HIGH: 16,
  MEDIUM: 12,
  LOW: 10,
};

export default function MapView({ reports, onMarkerClick, wardBoundaries }: Props) {
  const mapRef = useRef<google.maps.Map | null>(null);
  const [zoom, setZoom] = useState(12);

  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: GOOGLE_MAPS_KEY,
    id: "google-map-script",
  });

  const onLoad = useCallback(
    (map: google.maps.Map) => {
      mapRef.current = map;

      // Draw ward boundaries as polygons
      if (wardBoundaries) {
        wardBoundaries.features.forEach((feature) => {
          const geom = feature.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
          const props = feature.properties as {
            ward_name?: string;
            ward_number?: number;
          };

          const drawRing = (ring: number[][]) => {
            const path = ring.map(([lng, lat]) => ({ lat, lng }));
            const polygon = new google.maps.Polygon({
              paths: path,
              strokeColor: "#3b82f6",
              strokeOpacity: 0.7,
              strokeWeight: 1.5,
              fillColor: "#3b82f6",
              fillOpacity: 0.04,
              map,
            });
            if (props?.ward_name) {
              const infoWindow = new google.maps.InfoWindow({
                content: `<div style="font-size:13px;font-weight:600">${props.ward_name}${props.ward_number ? ` (#${props.ward_number})` : ""}</div>`,
              });
              polygon.addListener("mouseover", (e: google.maps.PolyMouseEvent) => {
                infoWindow.setPosition(e.latLng);
                infoWindow.open(map);
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
      }
    },
    [wardBoundaries]
  );

  const onUnmount = useCallback(() => {
    mapRef.current = null;
  }, []);

  if (loadError) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100">
        <div className="text-center text-gray-500">
          <p className="font-medium">Map failed to load</p>
          <p className="text-sm mt-1">Check your Google Maps API key</p>
        </div>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100">
        <div className="text-sm text-gray-400">Loading map…</div>
      </div>
    );
  }

  // Group nearby reports into clusters at low zoom levels
  const clusters = zoom < 13 ? clusterReports(reports, zoom) : null;

  return (
    <GoogleMap
      mapContainerStyle={{ width: "100%", height: "100%" }}
      center={MAP_CENTER}
      options={MAP_OPTIONS}
      onLoad={onLoad}
      onUnmount={onUnmount}
      onZoomChanged={() => {
        if (mapRef.current) setZoom(mapRef.current.getZoom() ?? 12);
      }}
    >
      {clusters
        ? /* Clustered view */
          clusters.map((cluster, i) =>
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
                  mapRef.current?.setZoom((mapRef.current.getZoom() ?? 12) + 2);
                  mapRef.current?.panTo({ lat: cluster.lat, lng: cluster.lng });
                }}
              />
            )
          )
        : /* Individual markers at high zoom */
          reports.map((r) => (
            <SingleMarker key={r.ticket_id} report={r} onClick={onMarkerClick} />
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
  const color = SEVERITY_COLORS[report.severity_score ?? "MEDIUM"] ?? "#9ca3af";
  const size = SEVERITY_SIZE[report.severity_score ?? "MEDIUM"] ?? 12;
  const opacity = report.status === "RESOLVED" || report.status === "UNRESPONSIVE" ? 0.45 : 1;

  return (
    <OverlayView
      position={{ lat: report.latitude, lng: report.longitude }}
      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
    >
      <div
        onClick={() => onClick?.(report.ticket_id)}
        style={{
          width: size * 2,
          height: size * 2,
          borderRadius: "50%",
          backgroundColor: color,
          opacity,
          border: "2px solid white",
          boxShadow: "0 1px 4px rgba(0,0,0,0.35)",
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
  const size = count >= 15 ? 40 : count >= 5 ? 32 : 26;

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
          border: "2px solid white",
          boxShadow: "0 1px 4px rgba(0,0,0,0.35)",
          cursor: "pointer",
          transform: "translate(-50%, -50%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          fontSize: 12,
          fontWeight: 700,
        }}
      >
        {count}
      </div>
    </OverlayView>
  );
}

// ─── Simple grid-based clustering ────────────────────────────────────────────

interface Cluster {
  lat: number;
  lng: number;
  reports: ReportMapItem[];
}

function clusterReports(reports: ReportMapItem[], zoom: number): Cluster[] {
  const cellSize = zoom < 10 ? 0.08 : zoom < 11 ? 0.05 : zoom < 12 ? 0.025 : 0.012;
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
