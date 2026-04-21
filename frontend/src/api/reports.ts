import api from "./client";
import type { Report, ReportMapItem } from "../types";

export async function fetchReports(params?: {
  skip?: number;
  limit?: number;
  status?: string;
  ward_id?: string;
  severity?: string;
  category?: string;
}): Promise<Report[]> {
  const { data } = await api.get("/api/reports", { params });
  return data;
}

export async function fetchMapReports(): Promise<ReportMapItem[]> {
  const { data } = await api.get("/api/reports/map");
  return data;
}

export async function fetchReport(id: string): Promise<Report> {
  const { data } = await api.get(`/api/reports/${id}`);
  return data;
}

export async function submitReport(formData: FormData): Promise<Report> {
  const { data } = await api.post("/api/reports", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function upvoteReport(
  id: string,
  fingerprint: string
): Promise<{ success: boolean; upvote_count: number }> {
  const { data } = await api.post(`/api/reports/${id}/upvote`, { fingerprint });
  return data;
}

export async function markReportResolved(id: string): Promise<Report> {
  const { data } = await api.post(`/api/reports/${id}/mark-resolved`);
  return data;
}
