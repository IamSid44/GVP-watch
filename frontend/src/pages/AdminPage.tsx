import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shield, Loader2, CheckCircle, XCircle, LogOut, CheckSquare, Upload, X, Camera, Sun, Moon } from "lucide-react";
import api from "../api/client";
import type { Report } from "../types";
import SeverityBadge from "../components/shared/SeverityBadge";
import StatusBadge from "../components/shared/StatusBadge";
import { useDarkMode } from "../context/DarkModeContext";

export default function AdminPage() {
  const [token, setToken] = useState(localStorage.getItem("gvp_admin_token") || "");
  const [keyInput, setKeyInput] = useState("");
  const [loginError, setLoginError] = useState("");
  const [activeTab, setActiveTab] = useState<"open" | "needs_verification" | "pending">("open");
  const [resolveModalTicketId, setResolveModalTicketId] = useState<string | null>(null);
  const [resolvePhoto, setResolvePhoto] = useState<File | null>(null);
  const [resolvePhotoPreview, setResolvePhotoPreview] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const { dark, toggle } = useDarkMode();

  const isLoggedIn = !!token;

  const login = async () => {
    try {
      const { data } = await api.post("/api/admin/login", { key: keyInput });
      if (data.success) {
        setToken(data.token);
        localStorage.setItem("gvp_admin_token", data.token);
        window.dispatchEvent(new Event("gvp-admin-auth-changed"));
        setLoginError("");
      }
    } catch {
      setLoginError("Invalid admin key");
    }
  };

  const logout = () => {
    setToken("");
    localStorage.removeItem("gvp_admin_token");
    window.dispatchEvent(new Event("gvp-admin-auth-changed"));
  };

  const { data: openReports = [], isLoading: openLoading } = useQuery({
    queryKey: ["admin", "open"],
    queryFn: async () => {
      const { data } = await api.get<Report[]>("/api/admin/reports?status=OPEN");
      return data;
    },
    enabled: isLoggedIn && activeTab === "open",
  });

  const { data: needsVerification = [], isLoading: verificationLoading } = useQuery({
    queryKey: ["admin", "needs_verification"],
    queryFn: async () => {
      const { data } = await api.get<Report[]>("/api/admin/reports?status=PENDING_VERIFICATION");
      return data;
    },
    enabled: isLoggedIn && activeTab === "needs_verification",
  });

  const { data: pending = [], isLoading: pendingLoading } = useQuery({
    queryKey: ["admin", "pending"],
    queryFn: async () => {
      const { data } = await api.get<Report[]>("/api/admin/pending");
      return data;
    },
    enabled: isLoggedIn && activeTab === "pending",
  });

  const moderate = async (ticketId: string, action: "approve" | "reject") => {
    const endpoint = `/api/admin/reports/${ticketId}/${action}`;
    const body = action === "reject" ? { reason: "Does not meet guidelines" } : {};
    await api.post(endpoint, body);
    queryClient.invalidateQueries({ queryKey: ["admin", "pending"] });
  };

  const openResolveModal = (ticketId: string) => {
    setResolveModalTicketId(ticketId);
    setResolvePhoto(null);
    setResolvePhotoPreview(null);
  };

  const closeResolveModal = () => {
    setResolveModalTicketId(null);
    setResolvePhoto(null);
    setResolvePhotoPreview(null);
  };

  const onPhotoSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setResolvePhoto(file);
    setResolvePhotoPreview(URL.createObjectURL(file));
  };

  const submitResolve = async () => {
    if (!resolveModalTicketId || !resolvePhoto) return;
    setResolving(true);
    try {
      const form = new FormData();
      form.append("photo", resolvePhoto);
      await api.post(`/api/admin/reports/${resolveModalTicketId}/resolve`, form, {
        headers: { "Content-Type": undefined },
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "open"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "needs_verification"] });
      queryClient.invalidateQueries({ queryKey: ["reports", "map"] });
      closeResolveModal();
    } finally {
      setResolving(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="max-w-sm mx-auto w-full p-4 pt-20">
        <div className="text-center mb-8">
          <div className="flex justify-end mb-2">
            <button
              onClick={toggle}
              className="p-2 rounded-lg text-gray-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title={dark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Shield size={32} className="text-gray-400 dark:text-amber-300" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-amber-300">Admin Panel</h1>
          <p className="text-sm text-gray-500 dark:text-gray-300 mt-1">
            Enter admin key to access moderation
          </p>
        </div>
        <div className="space-y-3">
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && login()}
            placeholder="Admin key"
            className="w-full p-3 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-xl text-sm"
          />
          {loginError && (
            <p className="text-sm text-red-500">{loginError}</p>
          )}
          <button
            onClick={login}
            className="w-full bg-gray-900 dark:bg-amber-500 text-white dark:text-gray-950 py-3 rounded-xl text-sm font-medium hover:bg-gray-800 dark:hover:bg-amber-400"
          >
            Login
          </button>
        </div>
      </div>
    );
  }

  const isLoading = activeTab === "open" ? openLoading : activeTab === "needs_verification" ? verificationLoading : pendingLoading;
  const reports = activeTab === "open" ? openReports : activeTab === "needs_verification" ? needsVerification : pending;

  return (
    <div className="max-w-3xl mx-auto w-full p-4 space-y-4 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900 dark:text-amber-300">Admin Panel</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={toggle}
            className="p-2 rounded-lg text-gray-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            onClick={logout}
            className="text-sm text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white flex items-center gap-1"
          >
            <LogOut size={16} /> Logout
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
        <button
          onClick={() => setActiveTab("open")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "open"
              ? "bg-gray-900 text-white"
              : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          Open
        </button>
        <button
          onClick={() => setActiveTab("needs_verification")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "needs_verification"
              ? "bg-amber-500 text-white"
              : "text-amber-600 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/30"
          }`}
        >
          Needs Verify
        </button>
        <button
          onClick={() => setActiveTab("pending")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "pending"
              ? "bg-gray-900 text-white"
              : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          Moderation
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-gray-400" />
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-300">
          <CheckCircle size={48} className="mx-auto mb-3 text-green-400" />
          <p>
            {activeTab === "open"
              ? "No open reports."
              : "All caught up! No reports pending moderation."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-gray-500 dark:text-gray-300">{reports.length} reports</p>
          {reports.map((report) => (
            <div
              key={report.ticket_id}
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden"
            >
              <div className="flex flex-col">
                <div className="flex">
                  {report.photo_url && (
                    <img
                      src={report.photo_url}
                      alt=""
                      className="w-32 h-32 object-cover flex-shrink-0"
                    />
                  )}
                  <div className="flex-1 p-4 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <SeverityBadge severity={report.severity_score} />
                      <StatusBadge status={report.status} />
                      <span className="text-xs text-gray-400 font-mono truncate">
                        {report.ticket_id}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-200 mb-1 line-clamp-2">
                      {report.description || report.category || "No description"}
                    </p>
                    {report.address && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{report.address}</p>
                    )}
                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      {activeTab === "open" ? (
                        <button
                          onClick={() => openResolveModal(report.ticket_id)}
                          className="bg-green-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700 inline-flex items-center gap-1"
                        >
                          <CheckSquare size={14} /> Mark Resolved
                        </button>
                      ) : activeTab === "needs_verification" ? (
                        <button
                          onClick={() => openResolveModal(report.ticket_id)}
                          className="bg-amber-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-amber-600 inline-flex items-center gap-1"
                        >
                          <CheckSquare size={14} /> Confirm &amp; Resolve
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => moderate(report.ticket_id, "approve")}
                            className="bg-green-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700 inline-flex items-center gap-1"
                          >
                            <CheckCircle size={14} /> Approve
                          </button>
                          <button
                            onClick={() => moderate(report.ticket_id, "reject")}
                            className="bg-red-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-red-700 inline-flex items-center gap-1"
                          >
                            <XCircle size={14} /> Reject
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                {/* Show citizen's cleanup photo for needs_verification tab */}
                {activeTab === "needs_verification" && (report as Report & { citizen_resolution_photo_url?: string }).citizen_resolution_photo_url && (
                  <div className="px-4 pb-4">
                    <p className="text-xs text-amber-700 dark:text-amber-300 font-medium mb-1">Citizen's cleanup photo:</p>
                    <img
                      src={(report as Report & { citizen_resolution_photo_url?: string }).citizen_resolution_photo_url}
                      alt="Citizen cleanup"
                      className="w-full h-40 object-cover rounded-xl ring-2 ring-amber-300"
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Resolve with photo modal */}
      {resolveModalTicketId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-sm shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800">
              <h2 className="font-semibold text-gray-900 dark:text-gray-100">Upload Verification Photo</h2>
              <button onClick={closeResolveModal} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                <X size={20} />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Upload a photo showing the area has been cleaned up. This will be used to verify the resolution.
              </p>

              {resolvePhotoPreview ? (
                <div className="relative">
                  <img
                    src={resolvePhotoPreview}
                    alt="Resolution preview"
                    className="w-full h-48 object-cover rounded-xl"
                  />
                  <button
                    onClick={() => { setResolvePhoto(null); setResolvePhotoPreview(null); }}
                    className="absolute top-2 right-2 bg-black/50 text-white rounded-full p-1 hover:bg-black/70"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full h-40 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl flex flex-col items-center justify-center gap-2 text-gray-500 dark:text-gray-300 hover:border-green-400 hover:text-green-600 transition-colors"
                >
                  <Camera size={32} />
                  <span className="text-sm font-medium">Tap to upload photo</span>
                  <span className="text-xs text-gray-400 dark:text-gray-500">JPG, PNG, HEIC accepted</span>
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
            </div>
            <div className="flex gap-3 p-4 border-t border-gray-100 dark:border-gray-800">
              <button
                onClick={closeResolveModal}
                className="flex-1 py-2.5 border border-gray-300 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={submitResolve}
                disabled={!resolvePhoto || resolving}
                className="flex-1 py-2.5 bg-green-600 text-white rounded-xl text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
              >
                {resolving ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Upload size={16} />
                )}
                {resolving ? "Uploading…" : "Confirm Resolved"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
