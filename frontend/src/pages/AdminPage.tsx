import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shield, Loader2, CheckCircle, XCircle, LogOut } from "lucide-react";
import api from "../api/client";
import type { Report } from "../types";
import SeverityBadge from "../components/shared/SeverityBadge";

export default function AdminPage() {
  const [token, setToken] = useState(localStorage.getItem("gvp_admin_token") || "");
  const [keyInput, setKeyInput] = useState("");
  const [loginError, setLoginError] = useState("");
  const queryClient = useQueryClient();

  const isLoggedIn = !!token;

  const login = async () => {
    try {
      const { data } = await api.post("/api/admin/login", { key: keyInput });
      if (data.success) {
        setToken(data.token);
        localStorage.setItem("gvp_admin_token", data.token);
        setLoginError("");
      }
    } catch {
      setLoginError("Invalid admin key");
    }
  };

  const logout = () => {
    setToken("");
    localStorage.removeItem("gvp_admin_token");
  };

  const { data: pending = [], isLoading } = useQuery({
    queryKey: ["admin", "pending"],
    queryFn: async () => {
      const { data } = await api.get<Report[]>("/api/admin/pending");
      return data;
    },
    enabled: isLoggedIn,
  });

  const moderate = async (ticketId: string, action: "approve" | "reject") => {
    const endpoint = `/api/admin/reports/${ticketId}/${action}`;
    const body = action === "reject" ? { reason: "Does not meet guidelines" } : {};
    await api.post(endpoint, body);
    queryClient.invalidateQueries({ queryKey: ["admin", "pending"] });
  };

  if (!isLoggedIn) {
    return (
      <div className="max-w-sm mx-auto w-full p-4 pt-20">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Shield size={32} className="text-gray-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">Admin Panel</h1>
          <p className="text-sm text-gray-500 mt-1">
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
            className="w-full p-3 border border-gray-300 rounded-xl text-sm"
          />
          {loginError && (
            <p className="text-sm text-red-500">{loginError}</p>
          )}
          <button
            onClick={login}
            className="w-full bg-gray-900 text-white py-3 rounded-xl text-sm font-medium hover:bg-gray-800"
          >
            Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto w-full p-4 space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Moderation Queue</h1>
          <p className="text-sm text-gray-500">{pending.length} reports pending</p>
        </div>
        <button
          onClick={logout}
          className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          <LogOut size={16} /> Logout
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-gray-400" />
        </div>
      ) : pending.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <CheckCircle size={48} className="mx-auto mb-3 text-green-400" />
          <p>All caught up! No reports pending moderation.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {pending.map((report) => (
            <div
              key={report.ticket_id}
              className="bg-white border border-gray-200 rounded-xl overflow-hidden"
            >
              <div className="flex">
                {report.photo_url && (
                  <img
                    src={report.photo_url}
                    alt=""
                    className="w-32 h-32 object-cover"
                  />
                )}
                <div className="flex-1 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <SeverityBadge severity={report.severity_score} />
                    <span className="text-xs text-gray-400 font-mono">
                      {report.ticket_id}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mb-1">
                    {report.description || report.category || "No description"}
                  </p>
                  {report.address && (
                    <p className="text-xs text-gray-500">{report.address}</p>
                  )}
                  <div className="flex items-center gap-2 mt-3">
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
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
