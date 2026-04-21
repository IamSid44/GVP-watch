import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { ReportMapItem } from "../../types";
import { MAP_CENTER, MAP_ZOOM, SEVERITY_COLORS } from "../../types";

interface Props {
  reports: ReportMapItem[];
  onMarkerClick?: (id: string) => void;
  wardBoundaries?: GeoJSON.FeatureCollection | null;
}

export default function MapView({ reports, onMarkerClick, wardBoundaries }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      },
      center: MAP_CENTER,
      zoom: MAP_ZOOM,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      // Reports source with clustering
      map.addSource("reports", {
        type: "geojson",
        data: reportsToGeoJSON(reports),
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      });

      // Cluster circles
      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "reports",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": [
            "step",
            ["get", "point_count"],
            "#f59e0b",
            5,
            "#f97316",
            15,
            "#ef4444",
          ],
          "circle-radius": ["step", ["get", "point_count"], 18, 5, 24, 15, 32],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#fff",
        },
      });

      // Cluster count
      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "reports",
        filter: ["has", "point_count"],
        layout: {
          "text-field": "{point_count_abbreviated}",
          "text-size": 13,
        },
        paint: {
          "text-color": "#fff",
        },
      });

      // Individual markers
      map.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "reports",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": [
            "match",
            ["get", "severity"],
            "LOW",
            SEVERITY_COLORS.LOW,
            "MEDIUM",
            SEVERITY_COLORS.MEDIUM,
            "HIGH",
            SEVERITY_COLORS.HIGH,
            "#9ca3af",
          ],
          "circle-radius": [
            "match",
            ["get", "severity"],
            "LOW",
            7,
            "MEDIUM",
            9,
            "HIGH",
            12,
            8,
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#fff",
          "circle-opacity": [
            "match",
            ["get", "status"],
            "RESOLVED",
            0.5,
            "UNRESPONSIVE",
            0.4,
            1,
          ],
        },
      });

      // Ward boundaries if available
      if (wardBoundaries && wardBoundaries.features.length > 0) {
        map.addSource("wards", {
          type: "geojson",
          data: wardBoundaries,
        });
        map.addLayer(
          {
            id: "ward-fill",
            type: "fill",
            source: "wards",
            paint: {
              "fill-color": "#3b82f6",
              "fill-opacity": 0.05,
            },
          },
          "clusters"
        );
        map.addLayer(
          {
            id: "ward-outline",
            type: "line",
            source: "wards",
            paint: {
              "line-color": "#3b82f6",
              "line-width": 1.5,
              "line-opacity": 0.5,
            },
          },
          "clusters"
        );
      }

      // Click handlers
      map.on("click", "unclustered-point", (e) => {
        const id = e.features?.[0]?.properties?.id;
        if (id && onMarkerClick) onMarkerClick(id);
      });

      map.on("click", "clusters", (e) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["clusters"],
        });
        const clusterId = features[0]?.properties?.cluster_id;
        const source = map.getSource("reports") as maplibregl.GeoJSONSource;
        source.getClusterExpansionZoom(clusterId).then((zoom) => {
          map.easeTo({
            center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
            zoom,
          });
        });
      });

      map.on("mouseenter", "unclustered-point", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "unclustered-point", () => {
        map.getCanvas().style.cursor = "";
      });
      map.on("mouseenter", "clusters", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "clusters", () => {
        map.getCanvas().style.cursor = "";
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update reports data when it changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource("reports") as maplibregl.GeoJSONSource | undefined;
    if (source) {
      source.setData(reportsToGeoJSON(reports));
    }
  }, [reports]);

  return <div ref={containerRef} className="w-full h-full" />;
}

function reportsToGeoJSON(reports: ReportMapItem[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: reports.map((r) => ({
      type: "Feature" as const,
      properties: {
        id: r.ticket_id,
        severity: r.severity_score || "MEDIUM",
        status: r.status,
        category: r.category,
      },
      geometry: {
        type: "Point" as const,
        coordinates: [r.longitude, r.latitude],
      },
    })),
  };
}
