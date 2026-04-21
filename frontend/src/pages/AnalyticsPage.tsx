import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import SummaryCards from "../components/analytics/SummaryCards";
import DailyTrendChart from "../components/analytics/DailyTrendChart";
import WorstWardsChart from "../components/analytics/WorstWardsChart";
import StatusBreakdown from "../components/analytics/StatusBreakdown";
import { fetchSummary, fetchDailyTrend, fetchByWard, fetchByStatus } from "../api/analytics";

export default function AnalyticsPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: fetchSummary,
  });

  const { data: daily = [] } = useQuery({
    queryKey: ["analytics", "daily"],
    queryFn: () => fetchDailyTrend(30),
  });

  const { data: byWard = [] } = useQuery({
    queryKey: ["analytics", "by-ward"],
    queryFn: fetchByWard,
  });

  const { data: byStatus = [] } = useQuery({
    queryKey: ["analytics", "by-status"],
    queryFn: fetchByStatus,
  });

  if (summaryLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto w-full p-4 space-y-6 pb-20">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Analytics</h1>
        <p className="text-sm text-gray-500">
          Serilingampally Zone — Waste Management Overview
        </p>
      </div>

      {summary && <SummaryCards data={summary} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DailyTrendChart data={daily} />
        <StatusBreakdown data={byStatus} />
      </div>

      <WorstWardsChart data={byWard} />
    </div>
  );
}
