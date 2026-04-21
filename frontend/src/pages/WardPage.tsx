import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2, MapPin, Users } from "lucide-react";
import { fetchWard, fetchWardRepresentatives } from "../api/wards";
import { fetchReports } from "../api/reports";
import ReportCard from "../components/reports/ReportCard";

export default function WardPage() {
  const { id } = useParams<{ id: string }>();

  const { data: ward, isLoading } = useQuery({
    queryKey: ["ward", id],
    queryFn: () => fetchWard(id!),
    enabled: !!id,
  });

  const { data: reps = [] } = useQuery({
    queryKey: ["ward-reps", id],
    queryFn: () => fetchWardRepresentatives(id!),
    enabled: !!id,
  });

  const { data: reports = [] } = useQuery({
    queryKey: ["ward-reports", id],
    queryFn: () => fetchReports({ ward_id: id, limit: 50 }),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin text-gray-400" />
      </div>
    );
  }

  if (!ward) {
    return (
      <div className="max-w-lg mx-auto p-4 text-center py-20">
        <p className="text-gray-500">Ward not found</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto w-full p-4 space-y-6 pb-20">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft size={16} /> Back
      </Link>

      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <MapPin size={20} />
          {ward.ward_name}
          {ward.ward_number && (
            <span className="text-sm font-normal text-gray-400">
              #{ward.ward_number}
            </span>
          )}
        </h1>
        {ward.circle && (
          <p className="text-sm text-gray-500">
            Circle: {ward.circle} — Zone: {ward.zone || "Serilingampally"}
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{ward.total_reports}</p>
          <p className="text-xs text-gray-500">Total</p>
        </div>
        <div className="bg-red-50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-red-700">{ward.open_reports}</p>
          <p className="text-xs text-red-600">Open</p>
        </div>
        <div className="bg-green-50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-700">{ward.resolved_reports}</p>
          <p className="text-xs text-green-600">Resolved</p>
        </div>
      </div>

      {/* Representatives */}
      {reps.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-1.5">
            <Users size={16} /> Representatives
          </h2>
          <div className="space-y-2">
            {reps.map((rep) => (
              <div
                key={rep.rep_id}
                className="p-3 bg-gray-50 rounded-lg flex items-center justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{rep.name}</p>
                  <p className="text-xs text-gray-500">
                    {rep.title}
                    {rep.party && ` — ${rep.party}`}
                  </p>
                </div>
                <span className="text-xs px-2 py-0.5 bg-gray-200 rounded-full text-gray-600">
                  {rep.level}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reports in this ward */}
      <div>
        <h2 className="text-sm font-medium text-gray-700 mb-3">
          Reports ({reports.length})
        </h2>
        <div className="space-y-3">
          {reports.map((r) => (
            <ReportCard key={r.ticket_id} report={r} />
          ))}
        </div>
      </div>
    </div>
  );
}
