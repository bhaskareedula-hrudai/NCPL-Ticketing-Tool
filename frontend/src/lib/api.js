import axios from "axios";

// Empty string → relative URL (/api/...) so dev proxy and Vercel rewrites both work.
// Set VITE_BACKEND_URL only when backend lives on a separate host.
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Convenience wrappers that unwrap .data automatically
export const get    = (url, cfg)    => api.get(url, cfg).then((r) => r.data);
export const post   = (url, body)   => api.post(url, body).then((r) => r.data);
export const patch  = (url, body)   => api.patch(url, body).then((r) => r.data);
export const del    = (url)         => api.delete(url).then((r) => r.data);

export { BACKEND_URL };
