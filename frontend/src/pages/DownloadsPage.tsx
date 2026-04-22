import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText } from "lucide-react";
import { fetchWards } from "../api/wards";

export default function DownloadsPage() {
  const [selectedWard, setSelectedWard] = useState<string>("");
  const { data: wards = [] } = useQuery({
    queryKey: ["wards"],
    queryFn: fetchWards,
  });

  const downloadCSV = (wardId?: string) => {
    const params = new URLSearchParams();
    if (wardId) params.set("ward_id", wardId);
    window.open(`/api/exports/csv?${params.toString()}`, "_blank");
  };

  return (
    <div className="max-w-2xl mx-auto w-full p-4 space-y-6 pb-20">
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Downloads</h1>
        <p className="text-sm text-gray-500 dark:text-gray-300">
          Export report data as CSV for analysis
        </p>
      </div>

      {/* City-wide */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-red-50 dark:bg-red-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText size={20} className="text-red-500 dark:text-red-300" />
          </div>
          <div className="flex-1">
            <h2 className="font-medium text-gray-900 dark:text-gray-100">All Reports (CSV)</h2>
            <p className="text-sm text-gray-500 dark:text-gray-300 mt-1">
              Download all approved reports across all wards
            </p>
            <button
              onClick={() => downloadCSV()}
              className="mt-3 bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-800 inline-flex items-center gap-1.5"
            >
              <Download size={16} /> Download CSV
            </button>
          </div>
        </div>
      </div>

      {/* Per-ward */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-blue-50 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText size={20} className="text-blue-500 dark:text-blue-300" />
          </div>
          <div className="flex-1">
            <h2 className="font-medium text-gray-900 dark:text-gray-100">Ward-Specific (CSV)</h2>
            <p className="text-sm text-gray-500 dark:text-gray-300 mt-1">
              Download reports for a specific ward
            </p>
            <div className="mt-3 flex items-center gap-2">
              <select
                value={selectedWard}
                onChange={(e) => setSelectedWard(e.target.value)}
                className="flex-1 p-2 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 rounded-lg text-sm"
              >
                <option value="">Select a ward...</option>
                {wards.map((w) => (
                  <option key={w.ward_id} value={w.ward_id}>
                    {w.ward_name}
                    {w.ward_number ? ` (#${w.ward_number})` : ""}
                    {` — ${w.total_reports} reports`}
                  </option>
                ))}
              </select>
              <button
                onClick={() => selectedWard && downloadCSV(selectedWard)}
                disabled={!selectedWard}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 inline-flex items-center gap-1.5"
              >
                <Download size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
