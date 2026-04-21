import { MapPin, Calendar, Tag, User } from "lucide-react";
import type { Report } from "../../types";
import { CATEGORY_LABELS } from "../../types";
import SeverityBadge from "../shared/SeverityBadge";
import StatusBadge from "../shared/StatusBadge";
import UpvoteButton from "../shared/UpvoteButton";
import ShareButtons from "../shared/ShareButtons";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ReportDetail({ report }: { report: Report }) {
  const shareUrl = `${window.location.origin}/report/${report.ticket_id}`;
  const shareTitle = `Garbage report at ${report.address || "Serilingampally"} — GVP Watch`;

  return (
    <div className="space-y-6">
      {/* Photo */}
      {report.photo_url && (
        <img
          src={report.photo_url}
          alt="Report photo"
          className="w-full h-64 object-cover rounded-xl"
        />
      )}

      {/* Badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <SeverityBadge severity={report.severity_score} />
        <StatusBadge status={report.status} />
        {report.category && (
          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium flex items-center gap-1">
            <Tag size={12} />
            {CATEGORY_LABELS[report.category] || report.category}
          </span>
        )}
        <span className="text-xs text-gray-400 uppercase">{report.source}</span>
      </div>

      {/* Info rows */}
      <div className="space-y-3">
        {report.address && (
          <div className="flex items-start gap-2 text-sm">
            <MapPin size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
            <span className="text-gray-700">{report.address}</span>
          </div>
        )}
        {report.ward_name && (
          <div className="flex items-center gap-2 text-sm">
            <MapPin size={16} className="text-gray-400" />
            <span className="text-gray-700">Ward: {report.ward_name}</span>
          </div>
        )}
        <div className="flex items-center gap-2 text-sm">
          <Calendar size={16} className="text-gray-400" />
          <span className="text-gray-700">Reported: {formatDate(report.created_at)}</span>
        </div>
        {report.resolved_at && (
          <div className="flex items-center gap-2 text-sm">
            <Calendar size={16} className="text-gray-400" />
            <span className="text-green-700">Resolved: {formatDate(report.resolved_at)}</span>
          </div>
        )}
        {report.reporter_name && (
          <div className="flex items-center gap-2 text-sm">
            <User size={16} className="text-gray-400" />
            <span className="text-gray-700">{report.reporter_name}</span>
          </div>
        )}
      </div>

      {/* Description */}
      {report.description && (
        <div className="p-4 bg-gray-50 rounded-xl text-sm text-gray-700">
          {report.description}
        </div>
      )}

      {/* Ticket ID */}
      <div className="text-xs text-gray-400 font-mono">
        ID: {report.ticket_id}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4 pt-2">
        <UpvoteButton ticketId={report.ticket_id} count={report.upvote_count} />
        <ShareButtons title={shareTitle} url={shareUrl} />
      </div>

      {/* Helpline info */}
      <div className="p-4 bg-blue-50 rounded-xl text-sm">
        <p className="font-medium text-blue-800 mb-1">GHMC Helpline</p>
        <p className="text-blue-700">
          Call: <a href="tel:04021111111" className="underline">040-21111111</a>
          {" "} | WhatsApp: <a href="https://wa.me/918125966586" className="underline">8125966586</a>
        </p>
      </div>
    </div>
  );
}
