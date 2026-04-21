import { X, MapPin, ExternalLink, CheckCircle } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchReport } from "../../api/reports";
import { CATEGORY_LABELS, SEVERITY_COLORS } from "../../types";
import api from "../../api/client";

interface Props {
  ticketId: string;
  onClose: () => void;
}

function getDaysSince(dateStr: string): number {
  const diff = Date.now() - new Date(dateStr).getTime();
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}

export default function ReportPopupCard({ ticketId, onClose }: Props) {
  const queryClient = useQueryClient();

  const { data: report, isLoading } = useQuery({
    queryKey: ["report", ticketId],
    queryFn: () => fetchReport(ticketId),
  });

  const markResolved = async () => {
    try {
      await api.post(`/api/reports/${ticketId}/mark-resolved`);
      queryClient.invalidateQueries({ queryKey: ["report", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["reports", "map"] });
    } catch {
      alert("Could not update status. Please try again.");
    }
  };

  const severityColor = report?.severity_score
    ? SEVERITY_COLORS[report.severity_score] ?? "#9ca3af"
    : "#9ca3af";

  return (
    /* Backdrop — clicking outside closes the card */
    <div
      className="fixed inset-0 z-40 flex items-end justify-center"
      onClick={onClose}
    >
      {/* Card — stop propagation so clicks inside don't close */}
      <div
        className="w-full max-w-lg z-50 pointer-events-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-white rounded-t-2xl shadow-2xl border-t border-gray-200 max-h-[80vh] overflow-y-auto">
          {/* Drag handle */}
          <div className="flex justify-center pt-3 pb-1">
            <div className="w-10 h-1 bg-gray-300 rounded-full" />
          </div>

          {/* Header row: severity + status + close */}
          <div className="flex items-center justify-between px-4 pb-2 pt-1">
            <div className="flex items-center gap-2">
              <span
                className="px-2 py-0.5 rounded text-xs font-bold text-white uppercase tracking-wide"
                style={{ backgroundColor: severityColor }}
              >
                {report?.severity_score ?? "—"}
              </span>
              <span
                className={`text-xs font-semibold ${
                  report?.status === "RESOLVED"
                    ? "text-green-600"
                    : "text-red-500"
                }`}
              >
                {report?.status === "RESOLVED" ? "Resolved" : "Unresolved"}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-gray-100 rounded-full"
            >
              <X size={18} className="text-gray-500" />
            </button>
          </div>

          {isLoading ? (
            <div className="p-10 text-center text-gray-400 text-sm">
              Loading…
            </div>
          ) : report ? (
            <div className="px-4 pb-6 space-y-4">
              {/* Title + ward */}
              <div>
                <h2 className="text-lg font-bold text-gray-900 leading-snug">
                  {report.address ?? report.ward_name ?? "Serilingampally"}
                </h2>
                {report.ward_name && (
                  <p className="text-sm text-gray-500 flex items-center gap-1 mt-0.5">
                    <MapPin size={13} />
                    {report.ward_name}
                  </p>
                )}
              </div>

              {/* Photo */}
              {report.photo_url && (
                <img
                  src={report.photo_url}
                  alt="Garbage report"
                  className="w-full h-48 object-cover rounded-xl"
                />
              )}

              {/* Stats row */}
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-gray-50 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-orange-500">1</p>
                  <p className="text-xs text-gray-500 mt-0.5">Reports</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-orange-500">
                    {getDaysSince(report.created_at)}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Days</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3 text-center">
                  <p className="text-xs font-semibold text-blue-600 leading-tight mt-1">
                    {CATEGORY_LABELS[report.category ?? ""] ??
                      report.category ??
                      "Waste"}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Type</p>
                </div>
              </div>

              {/* Description */}
              {report.description && (
                <p className="text-sm text-gray-600 bg-gray-50 rounded-xl p-3 leading-relaxed">
                  {report.description}
                </p>
              )}

              {/* "It is Cleaned Up" button */}
              {report.status !== "RESOLVED" ? (
                <button
                  onClick={markResolved}
                  className="w-full flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white py-3 rounded-xl font-medium text-sm transition-colors"
                >
                  <CheckCircle size={18} />
                  It is Cleaned Up — Verify
                </button>
              ) : (
                <div className="flex items-center justify-center gap-2 bg-green-50 text-green-700 py-3 rounded-xl font-medium text-sm">
                  <CheckCircle size={18} />
                  This issue has been resolved
                </div>
              )}

              {/* View full details */}
              <Link
                to={`/report/${ticketId}`}
                className="w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-700 py-3 rounded-xl font-medium text-sm hover:bg-gray-50 transition-colors"
              >
                <ExternalLink size={15} />
                View Full Details
              </Link>

              <p className="text-center text-xs text-gray-400">
                All reports are anonymous
              </p>
            </div>
          ) : (
            <div className="p-10 text-center text-gray-400 text-sm">
              Report not found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
