import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2 } from "lucide-react";
import { fetchReport } from "../api/reports";
import ReportDetail from "../components/reports/ReportDetail";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();

  const { data: report, isLoading, error } = useQuery({
    queryKey: ["report", id],
    queryFn: () => fetchReport(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-lg mx-auto p-4 text-center py-20">
        <p className="text-gray-500 mb-4">Report not found</p>
        <Link to="/" className="text-red-500 underline">
          Back to map
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto w-full p-4 pb-20">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={16} /> Back to map
      </Link>
      <ReportDetail report={report} />
    </div>
  );
}
