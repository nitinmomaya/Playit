// Vite injects this public URL at build time; never put secrets in VITE_ variables.
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

// File summary
// - Shares the backend URL across provider and Gemini clients.
// - Uses localhost when no deployment URL is configured.