import { useRef, useState } from "react";
import { X, MapPin, ExternalLink, CheckCircle, Camera, Upload, Clock, Loader2, Phone, ChevronDown, ChevronUp, UserCheck } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchReport } from "../../api/reports";
import { fetchWardRepresentatives } from "../../api/wards";
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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [showOfficials, setShowOfficials] = useState(false);

  const { data: report, isLoading } = useQuery({
    queryKey: ["report", ticketId],
    queryFn: () => fetchReport(ticketId),
  });

  const { data: representatives = [] } = useQuery({
    queryKey: ["representatives", report?.ward_id],
    queryFn: () => fetchWardRepresentatives(report!.ward_id!),
    enabled: !!report?.ward_id && showOfficials,
  });

  const onPhotoSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const submitCleanup = async () => {
    if (!photoFile) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("photo", photoFile);
      await api.post(`/api/reports/${ticketId}/mark-resolved`, form, {
        headers: { "Content-Type": undefined },
      });
      queryClient.invalidateQueries({ queryKey: ["report", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["reports", "map"] });
      setShowUpload(false);
      setPhotoFile(null);
      setPhotoPreview(null);
    } catch {
      alert("Could not submit. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const severityColor = report?.severity_score
    ? SEVERITY_COLORS[report.severity_score] ?? "#9ca3af"
    : "#9ca3af";

  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg z-50 pointer-events-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-white dark:bg-gray-900 rounded-t-2xl shadow-2xl border-t border-gray-200 dark:border-gray-700 max-h-[82vh] overflow-y-auto">
          {/* Drag handle */}
          <div className="flex justify-center pt-3 pb-1">
            <div className="w-10 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />
          </div>

          {/* Header row */}
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
                    : report?.status === "PENDING_VERIFICATION"
                    ? "text-amber-600"
                    : "text-red-500"
                }`}
              >
                {report?.status === "RESOLVED"
                  ? "Resolved"
                  : report?.status === "PENDING_VERIFICATION"
                  ? "Awaiting Admin Verification"
                  : "Unresolved"}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full"
            >
              <X size={18} className="text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          {isLoading ? (
            <div className="p-10 text-center text-gray-400 text-sm">Loading…</div>
          ) : report ? (
            <div className="px-4 pb-6 space-y-4">
              {/* Title */}
              <div>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white leading-snug">
                  {report.address ?? report.ward_name ?? "Serilingampally"}
                </h2>
                {report.ward_name && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
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
                <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-orange-500">1</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Reports</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-orange-500">
                    {getDaysSince(report.created_at)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Days old</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-3 text-center">
                  <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 leading-tight mt-1">
                    {CATEGORY_LABELS[report.category ?? ""] ?? report.category ?? "Waste"}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Type</p>
                </div>
              </div>

              {/* Description */}
              {report.description && (
                <p className="text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-xl p-3 leading-relaxed">
                  {report.description}
                </p>
              )}

              {/* Officials accordion */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                <button
                  onClick={() => setShowOfficials((s) => !s)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <UserCheck size={16} className="text-blue-500" />
                    Responsible Officials
                  </span>
                  {showOfficials ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {showOfficials && (
                  <div className="divide-y divide-gray-100 dark:divide-gray-800">
                    {representatives.length === 0 ? (
                      <p className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500">
                        No officials on record for this ward.
                      </p>
                    ) : (
                      representatives.map((rep) => (
                        <div key={rep.rep_id} className="px-4 py-3 flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                              {rep.name}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">{rep.title}</p>
                          </div>
                          {rep.phone && (
                            <a
                              href={`tel:${rep.phone}`}
                              className="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 font-medium hover:underline"
                            >
                              <Phone size={13} />
                              {rep.phone}
                            </a>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Resolution actions */}
              {report.status === "RESOLVED" ? (
                <div className="flex items-center justify-center gap-2 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 py-3 rounded-xl font-medium text-sm">
                  <CheckCircle size={18} />
                  This issue has been resolved
                </div>
              ) : report.status === "PENDING_VERIFICATION" ? (
                <div className="flex items-center justify-center gap-2 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 py-3 rounded-xl font-medium text-sm">
                  <Clock size={18} />
                  Cleanup photo submitted — awaiting admin confirmation
                </div>
              ) : showUpload ? (
                <div className="space-y-3">
                  <p className="text-sm text-gray-600 dark:text-gray-300 font-medium">
                    Upload a photo showing it's been cleaned up
                  </p>
                  {photoPreview ? (
                    <div className="relative">
                      <img
                        src={photoPreview}
                        alt="Preview"
                        className="w-full h-40 object-cover rounded-xl"
                      />
                      <button
                        onClick={() => { setPhotoFile(null); setPhotoPreview(null); }}
                        className="absolute top-2 right-2 bg-black/50 text-white rounded-full p-1"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full h-36 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl flex flex-col items-center justify-center gap-2 text-gray-500 dark:text-gray-400 hover:border-green-400 hover:text-green-600 transition-colors"
                    >
                      <Camera size={28} />
                      <span className="text-sm font-medium">Tap to add photo</span>
                    </button>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={onPhotoSelected}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setShowUpload(false); setPhotoFile(null); setPhotoPreview(null); }}
                      className="flex-1 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={submitCleanup}
                      disabled={!photoFile || uploading}
                      className="flex-1 py-2.5 bg-green-500 hover:bg-green-600 text-white rounded-xl text-sm font-medium disabled:opacity-50 inline-flex items-center justify-center gap-2"
                    >
                      {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                      {uploading ? "Uploading…" : "Submit"}
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowUpload(true)}
                  className="w-full flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white py-3 rounded-xl font-medium text-sm transition-colors"
                >
                  <CheckCircle size={18} />
                  It is Cleaned Up — Upload Photo
                </button>
              )}

              <Link
                to={`/report/${ticketId}`}
                className="w-full flex items-center justify-center gap-2 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 py-3 rounded-xl font-medium text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <ExternalLink size={15} />
                View Full Details
              </Link>

              <p className="text-center text-xs text-gray-400 dark:text-gray-600">
                All reports are anonymous
              </p>
            </div>
          ) : (
            <div className="p-10 text-center text-gray-400 text-sm">Report not found.</div>
          )}
        </div>
      </div>
    </div>
  );
}
