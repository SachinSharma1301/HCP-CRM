import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export const createInteraction = (payload) =>
  api.post("/api/interactions", payload).then((r) => r.data);

export const updateInteraction = (id, payload) =>
  api.patch(`/api/interactions/${id}`, payload).then((r) => r.data);

export const fetchHcpHistory = (hcpName) =>
  api.get(`/api/interactions/hcp/${encodeURIComponent(hcpName)}`).then((r) => r.data);

export const searchMaterials = (q = "") =>
  api.get("/api/materials", { params: { q } }).then((r) => r.data);

export const sendChatMessage = (sessionId, message) =>
  api.post("/api/chat", { session_id: sessionId, message }).then((r) => r.data);
