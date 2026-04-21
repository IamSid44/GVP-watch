import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Map, List, Loader2 } from "lucide-react";
import MapView from "../components/map/MapView";
import ReportPopupCard from "../components/map/ReportPopupCard";
import ReportCard from "../components/reports/ReportCard";
import { fetchMapReports, fetchReports } from "../api/reports";
import { fetchWardBoundaries } from "../api/wards";

export default function HomePage() {
  const [view, setView] = useState<"map" | "list">("map");
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  const { data: mapReports = [], isLoading: mapLoading } = useQuery({
    queryKey: ["reports", "map"],
    queryFn: fetchMapReports,
  });

  const { data: reports = [], isLoading: listLoading } = useQuery({
    queryKey: ["reports", "list"],
    queryFn: () => fetchReports({ limit: 50 }),
    enabled: view === "list",
  });

  const { data: boundaries } = useQuery({
    queryKey: ["ward-boundaries"],
    queryFn: fetchWardBoundaries,
  });

  return (
    <div className="flex-1 flex flex-col relative">
      {/* View toggle */}
      <div className="absolute top-3 left-3 z-10 bg-white rounded-lg shadow-md border border-gray-200 flex">
        <button
          onClick={() => setView("map")}
          className={`px-3 py-1.5 text-sm font-medium flex items-center gap-1.5 rounded-l-lg transition-colors ${
            view === "map"
              ? "bg-gray-900 text-white"
              : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          <Map size={14} /> Map
        </button>
        <button
          onClick={() => setView("list")}
          className={`px-3 py-1.5 text-sm font-medium flex items-center gap-1.5 rounded-r-lg transition-colors ${
            view === "list"
              ? "bg-gray-900 text-white"
              : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          <List size={14} /> List
        </button>
      </div>

      {/* Report count badge */}
      <div className="absolute top-3 right-14 z-10 bg-white rounded-lg shadow-md border border-gray-200 px-3 py-1.5 text-sm">
        <span className="font-bold text-gray-900">{mapReports.length}</span>
        <span className="text-gray-500 ml-1">reports</span>
      </div>

      {view === "map" ? (
        <div className="relative" style={{ height: "calc(100vh - 56px)" }}>
          {mapLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 size={32} className="animate-spin text-gray-400" />
            </div>
          ) : (
            <MapView
              reports={mapReports}
              wardBoundaries={boundaries}
              onMarkerClick={(id) => setSelectedReportId(id)}
            />
          )}
          {/* Popup card overlay */}
          {selectedReportId && (
            <ReportPopupCard
              ticketId={selectedReportId}
              onClose={() => setSelectedReportId(null)}
            />
          )}
        </div>
      ) : (
        <div className="max-w-2xl mx-auto w-full p-4 space-y-3 pb-20">
          {listLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={32} className="animate-spin text-gray-400" />
            </div>
          ) : reports.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No reports yet. Be the first to report!
            </div>
          ) : (
            reports.map((r) => <ReportCard key={r.ticket_id} report={r} />)
          )}
        </div>
      )}
    </div>
  );
}
