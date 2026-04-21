import { FileText, AlertCircle, CheckCircle, Clock, TrendingUp } from "lucide-react";
import type { AnalyticsSummary } from "../../types";

export default function SummaryCards({ data }: { data: AnalyticsSummary }) {
  const cards = [
    { label: "Total Reports", value: data.total_reports, icon: FileText, color: "text-gray-700", bg: "bg-gray-50" },
    { label: "Open", value: data.open_reports, icon: AlertCircle, color: "text-red-700", bg: "bg-red-50" },
    { label: "Resolved", value: data.resolved_reports, icon: CheckCircle, color: "text-green-700", bg: "bg-green-50" },
    { label: "Pending", value: data.pending_reports, icon: Clock, color: "text-amber-700", bg: "bg-amber-50" },
    { label: "Resolution Rate", value: `${data.resolution_rate}%`, icon: TrendingUp, color: "text-blue-700", bg: "bg-blue-50" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`${card.bg} rounded-xl p-4`}
        >
          <div className={`flex items-center gap-2 ${card.color} mb-1`}>
            <card.icon size={16} />
            <span className="text-xs font-medium">{card.label}</span>
          </div>
          <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}
