import api from "./client";
import type {
  AnalyticsSummary,
  DailyTrend,
  WardStats,
  SeverityStats,
  StatusStats,
} from "../types";

export async function fetchSummary(): Promise<AnalyticsSummary> {
  const { data } = await api.get("/api/analytics/summary");
  return data;
}

export async function fetchDailyTrend(days = 30): Promise<DailyTrend[]> {
  const { data } = await api.get("/api/analytics/daily", { params: { days } });
  return data;
}

export async function fetchByWard(): Promise<WardStats[]> {
  const { data } = await api.get("/api/analytics/by-ward");
  return data;
}

export async function fetchBySeverity(): Promise<SeverityStats[]> {
  const { data } = await api.get("/api/analytics/by-severity");
  return data;
}

export async function fetchByStatus(): Promise<StatusStats[]> {
  const { data } = await api.get("/api/analytics/by-status");
  return data;
}
