export interface Report {
  ticket_id: string;
  citizen_phone?: string | null;
  officer_phone?: string | null;
  ward_id?: string | null;
  ward_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  photo_url?: string | null;
  severity_score?: string | null;
  status: string;
  description?: string | null;
  source: string;
  upvote_count: number;
  moderation_status: string;
  address?: string | null;
  category?: string | null;
  reporter_name?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface ReportMapItem {
  ticket_id: string;
  latitude: number;
  longitude: number;
  severity_score?: string | null;
  status: string;
  category?: string | null;
  created_at: string;
}

export interface Ward {
  ward_id: string;
  ward_name: string;
  ward_number?: number | null;
  circle?: string | null;
  zone?: string | null;
  center_lat?: number | null;
  center_lng?: number | null;
  total_reports: number;
  open_reports: number;
  resolved_reports: number;
}

export interface Representative {
  rep_id: string;
  name: string;
  title: string;
  level: string;
  phone?: string | null;
  email?: string | null;
  party?: string | null;
}

export interface AnalyticsSummary {
  total_reports: number;
  open_reports: number;
  resolved_reports: number;
  pending_reports: number;
  unresponsive_reports: number;
  resolution_rate: number;
  avg_resolution_hours?: number | null;
}

export interface DailyTrend {
  date: string;
  count: number;
}

export interface WardStats {
  ward_id: string;
  ward_name: string;
  ward_number?: number | null;
  total: number;
  open: number;
  resolved: number;
}

export interface SeverityStats {
  severity: string;
  count: number;
}

export interface StatusStats {
  status: string;
  count: number;
}

export const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#f59e0b",
  MEDIUM: "#f97316",
  HIGH: "#ef4444",
};

export const SEVERITY_LABELS: Record<string, string> = {
  LOW: "Minor",
  MEDIUM: "Moderate",
  HIGH: "Severe",
};

export const STATUS_COLORS: Record<string, string> = {
  INITIATED: "#9ca3af",
  AWAITING_PHOTO: "#9ca3af",
  OPEN: "#ef4444",
  PENDING_VERIFICATION: "#f59e0b",
  RESOLVED: "#22c55e",
  UNRESPONSIVE: "#6b7280",
};

export const CATEGORY_LABELS: Record<string, string> = {
  garbage_on_roads: "Garbage on Roads",
  overflowing_bins: "Overflowing Bins",
  construction_debris: "Construction Debris",
  drain_blockage: "Drain Blockage",
  green_waste: "Green Waste",
  other: "Other",
};

export const MAP_CENTER: [number, number] = [78.302, 17.4931];
export const MAP_ZOOM = 13;
