import { Link } from "react-router-dom";
import { Clock, MapPin, ThumbsUp } from "lucide-react";
import type { Report } from "../../types";
import { CATEGORY_LABELS } from "../../types";
import SeverityBadge from "../shared/SeverityBadge";
import StatusBadge from "../shared/StatusBadge";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function ReportCard({ report }: { report: Report }) {
  return (
    <Link
      to={`/report/${report.ticket_id}`}
      className="block bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all overflow-hidden"
    >
      <div className="flex">
        {report.photo_url && (
          <div className="w-24 h-24 flex-shrink-0">
            <img
              src={report.photo_url}
              alt=""
              className="w-full h-full object-cover"
            />
          </div>
        )}
        <div className="flex-1 p-3 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <SeverityBadge severity={report.severity_score} />
            <StatusBadge status={report.status} />
            <span className="text-xs text-gray-400 ml-auto flex items-center gap-1">
              <Clock size={12} />
              {timeAgo(report.created_at)}
            </span>
          </div>
          <p className="text-sm text-gray-700 truncate">
            {report.category
              ? CATEGORY_LABELS[report.category] || report.category
              : "Report"}
            {report.address && (
              <span className="text-gray-400"> — {report.address}</span>
            )}
          </p>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
            {report.ward_name && (
              <span className="flex items-center gap-1">
                <MapPin size={12} />
                {report.ward_name}
              </span>
            )}
            <span className="flex items-center gap-1">
              <ThumbsUp size={12} />
              {report.upvote_count}
            </span>
            <span className="text-gray-400 uppercase">{report.source}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
