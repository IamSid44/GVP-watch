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
  const { data } = await api.get("/api/wards/boundaries");
  return data;
}

export async function fetchWardRepresentatives(
  wardId: string
): Promise<Representative[]> {
  const { data } = await api.get(`/api/wards/${wardId}/representatives`);
  return data;
}
