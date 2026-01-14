/**
 * Centralized configuration for service URLs and ports.
 *
 * Values are read from environment variables at build time (Vite).
 * Use .env or .env.local files to override defaults.
 *
 * Environment variables must be prefixed with VITE_ to be exposed to the client.
 */

// Helper to get the API host, using 127.0.0.1 for localhost to avoid IPv6 issues
export const getApiHost = (): string => {
  const hostname = window.location.hostname;
  return hostname === 'localhost' ? '127.0.0.1' : hostname;
};

// Service ports - can be overridden via environment variables
export const PORTS = {
  /** Web GUI frontend (default: 5173) */
  WEB_GUI: parseInt(import.meta.env.VITE_WEB_GUI_PORT || '5173'),

  /** Metrics API for GPU/system monitoring (default: 5174) */
  METRICS_API: parseInt(import.meta.env.VITE_METRICS_API_PORT || '5174'),

  /** Model Manager API for starting/stopping models (default: 5175) */
  MODEL_MANAGER: parseInt(import.meta.env.VITE_MODEL_MANAGER_PORT || '5175'),

  /** Tool Sandbox API for code execution (default: 5176) */
  SANDBOX: parseInt(import.meta.env.VITE_SANDBOX_PORT || '5176'),

  /** SearXNG search engine (default: 8080) */
  SEARXNG: parseInt(import.meta.env.VITE_SEARXNG_PORT || '8080'),
};

// Full service URLs
export const SERVICES = {
  /** Metrics API base URL */
  get METRICS_API(): string {
    return import.meta.env.VITE_METRICS_API_URL || `http://${getApiHost()}:${PORTS.METRICS_API}`;
  },

  /** Model Manager API base URL */
  get MODEL_MANAGER(): string {
    return import.meta.env.VITE_MODEL_MANAGER_URL || `http://${getApiHost()}:${PORTS.MODEL_MANAGER}`;
  },

  /** Tool Sandbox API base URL */
  get SANDBOX(): string {
    return import.meta.env.VITE_SANDBOX_URL || `http://${getApiHost()}:${PORTS.SANDBOX}`;
  },

  /** SearXNG search engine URL */
  get SEARXNG(): string {
    return import.meta.env.VITE_SEARXNG_URL || `http://${getApiHost()}:${PORTS.SEARXNG}`;
  },
};

// Build model API URL from port
export const getModelApiUrl = (port: number): string => {
  return `http://${getApiHost()}:${port}`;
};

// Export for debugging
export const logConfig = (): void => {
  console.log('📋 Service Configuration:', {
    METRICS_API: SERVICES.METRICS_API,
    MODEL_MANAGER: SERVICES.MODEL_MANAGER,
    SANDBOX: SERVICES.SANDBOX,
    SEARXNG: SERVICES.SEARXNG,
  });
};
