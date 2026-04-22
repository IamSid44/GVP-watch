import api from "./client";
import type { Ward, Representative } from "../types";

export async function fetchWards(): Promise<Ward[]> {
  const { data } = await api.get("/api/wards");
  return data;
}

export async function fetchWard(id: string): Promise<Ward> {
  const { data } = await api.get(`/api/wards/${id}`);
  return data;
}

export async function fetchWardBoundaries(): Promise<GeoJSON.FeatureCollection> {
  try {
    const { data } = await api.get("/api/wards/boundaries");
    if (data?.features?.length > 0) return data;
  } catch {
    // fall through to local file
  }
  // Fallback: load the bundled GeoJSON from the public folder
  const res = await fetch("/ghmc_wards.geojson");
  return res.json();
}

export async function fetchWardRepresentatives(
  wardId: string
): Promise<Representative[]> {
  const { data } = await api.get(`/api/wards/${wardId}/representatives`);
  return data;
}
