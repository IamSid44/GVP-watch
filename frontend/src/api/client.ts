import axios from "axios";

const api = axios.create({
  baseURL: "",
  headers: { "Content-Type": "application/json" },
});

// Add admin token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("gvp_admin_token");
  if (token && config.url?.startsWith("/api/admin")) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
