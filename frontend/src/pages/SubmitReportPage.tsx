import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import ReportForm from "../components/reports/ReportForm";

export default function SubmitReportPage() {
  return (
    <div className="max-w-lg mx-auto w-full p-4 pb-20">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={16} /> Back to map
      </Link>
      <h1 className="text-xl font-bold text-gray-900 mb-1">
        Report a GVP Issue
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        Help keep Serilingampally clean by reporting garbage, overflowing bins,
        or other waste management issues.
      </p>
      <ReportForm />
    </div>
  );
}
