import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Map, List, Loader2, ArrowUpDown } from "lucide-react";
import MapView from "../components/map/MapView";
import ReportPopupCard from "../components/map/ReportPopupCard";
import ReportCard from "../components/reports/ReportCard";
import { fetchMapReports, fetchReports } from "../api/reports";
import { fetchWardBoundaries } from "../api/wards";
import { parseUTC } from "../utils/date";

type SortKey = "newest" | "oldest" | "likes" | "severity";
type PageSize = 25 | 50 | 100 | "all";

const SEVERITY_RANK: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };

async function fetchAllReports(): Promise<Awaited<ReturnType<typeof fetchReports>>> {
  const batchSize = 100;
  let skip = 0;
  let merged: Awaited<ReturnType<typeof fetchReports>> = [];

  // Pull all approved reports in backend-safe batches.
  while (true) {
    const batch = await fetchReports({ skip, limit: batchSize });
    merged = merged.concat(batch);
    if (batch.length < batchSize) break;
    skip += batchSize;

    // Hard stop to avoid accidental unbounded loops if backend behavior changes.
    if (skip >= 10000) break;
  }

  return merged;
}

export default function HomePage() {
  const [view, setView] = useState<"map" | "list">("map");
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortKey>("newest");
  const [pageSize, setPageSize] = useState<PageSize>(50);
  const [currentPage, setCurrentPage] = useState(1);

  const { data: mapReports = [], isLoading: mapLoading } = useQuery({
    queryKey: ["reports", "map"],
    queryFn: fetchMapReports,
  });

  const { data: reports = [], isLoading: listLoading, isError: listError } = useQuery({
    queryKey: ["reports", "list", pageSize, currentPage],
    queryFn: () => {
      if (pageSize === "all") {
        return fetchAllReports();
      }
      const skip = (currentPage - 1) * pageSize;
      return fetchReports({ skip, limit: pageSize });
    },
    enabled: view === "list",
  });

  const { data: boundaries } = useQuery({
    queryKey: ["ward-boundaries"],
    queryFn: fetchWardBoundaries,
  });

  // Stats for the top-right badge (computed from the lightweight mapReports list)
  const stats = useMemo(() => {
    let total = 0, resolved = 0, severe = 0, moderate = 0, minor = 0;
    for (const r of mapReports) {
      total += 1;
      if (r.status === "RESOLVED") resolved += 1;
      if (r.severity_score === "HIGH") severe += 1;
      else if (r.severity_score === "MEDIUM") moderate += 1;
      else if (r.severity_score === "LOW") minor += 1;
    }
    return { total, resolved, severe, moderate, minor };
  }, [mapReports]);

  const sortedReports = useMemo(() => {
    const arr = [...reports];
    switch (sortBy) {
      case "newest":
        arr.sort((a, b) => parseUTC(b.created_at).getTime() - parseUTC(a.created_at).getTime());
        break;
      case "oldest":
        arr.sort((a, b) => parseUTC(a.created_at).getTime() - parseUTC(b.created_at).getTime());
        break;
      case "likes":
        arr.sort((a, b) => (b.upvote_count ?? 0) - (a.upvote_count ?? 0));
        break;
      case "severity":
        arr.sort((a, b) =>
          (SEVERITY_RANK[b.severity_score ?? ""] ?? 0) -
          (SEVERITY_RANK[a.severity_score ?? ""] ?? 0)
        );
        break;
    }
    return arr;
  }, [reports, sortBy]);

  return (
    <div className="flex-1 flex flex-col relative">
      {/* View toggle — pushed lower so the nav bar doesn't cover it */}
      <div className="absolute top-16 left-3 z-10 bg-white dark:bg-gray-900 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 flex">
        <button
          onClick={() => setView("map")}
          className={`px-3 py-1.5 text-sm font-medium flex items-center gap-1.5 rounded-l-lg transition-colors ${
            view === "map"
              ? "bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900"
              : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          <Map size={14} /> Map
        </button>
        <button
          onClick={() => setView("list")}
          className={`px-3 py-1.5 text-sm font-medium flex items-center gap-1.5 rounded-r-lg transition-colors ${
            view === "list"
              ? "bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900"
              : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          <List size={14} /> List
        </button>
      </div>

      {/* Stats badge — multi-metric */}
      <div className="absolute top-16 right-3 z-10 bg-white dark:bg-gray-900 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 px-3 py-1.5 flex items-center gap-3 text-xs">
        <StatPill label="Total" value={stats.total} color="text-gray-900 dark:text-white" />
        <div className="h-4 w-px bg-gray-200 dark:bg-gray-700" />
        <StatPill label="Resolved" value={stats.resolved} color="text-green-600 dark:text-green-400" />
        <StatPill label="Severe" value={stats.severe} color="text-red-500" />
        <StatPill label="Moderate" value={stats.moderate} color="text-orange-500" />
        <StatPill label="Minor" value={stats.minor} color="text-amber-500" />
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
          {selectedReportId && (
            <ReportPopupCard
              ticketId={selectedReportId}
              onClose={() => setSelectedReportId(null)}
            />
          )}
        </div>
      ) : (
        <div className="max-w-2xl mx-auto w-full p-4 space-y-3 pb-20 pt-16">
          {/* Sort control */}
          <div className="flex flex-wrap items-center justify-between gap-2 px-1 pb-1">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Showing {sortedReports.length} report{sortedReports.length === 1 ? "" : "s"}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                <span className="font-medium">View</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    const next = e.target.value as PageSize;
                    setPageSize(next);
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-md text-xs py-1 px-2 focus:outline-none focus:ring-1 focus:ring-gray-400"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value="all">All</option>
                </select>
                <span>at a time</span>
              </label>
              <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                <ArrowUpDown size={12} />
                <span className="font-medium">Sort by</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortKey)}
                  className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-md text-xs py-1 px-2 focus:outline-none focus:ring-1 focus:ring-gray-400"
                >
                  <option value="newest">Time reported (newest)</option>
                  <option value="oldest">Time reported (oldest)</option>
                  <option value="likes">Number of likes</option>
                  <option value="severity">Severity</option>
                </select>
              </label>
            </div>
          </div>

          {listLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={32} className="animate-spin text-gray-400" />
            </div>
          ) : listError ? (
            <div className="text-center py-12 text-red-500">
              Unable to load reports right now. Please try again.
            </div>
          ) : sortedReports.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No reports yet. Be the first to report!
            </div>
          ) : (
            sortedReports.map((r) => <ReportCard key={r.ticket_id} report={r} />)
          )}

          {pageSize !== "all" && !listLoading && !listError && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 text-xs rounded-md border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-xs text-gray-500 dark:text-gray-400">Page {currentPage}</span>
              <button
                onClick={() => setCurrentPage((p) => p + 1)}
                disabled={reports.length < pageSize}
                className="px-3 py-1.5 text-xs rounded-md border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}

          <p className="text-center text-xs text-gray-400 py-4 px-2">
          </p>
        </div>
      )}
    </div>
  );
}

function StatPill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`font-bold ${color}`}>{value}</span>
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
    </div>
  );
}
