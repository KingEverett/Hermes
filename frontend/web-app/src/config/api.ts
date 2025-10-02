/**
 * API Configuration
 *
 * Handles API base URL configuration for different environments:
 * - Development: Uses proxy to localhost:8000
 * - Production: Uses REACT_APP_API_URL environment variable
 * - CI: Uses explicit http://localhost:8000
 */

// Get the API base URL from environment variable or use default
const getApiBaseUrl = (): string => {
  // In production build, use REACT_APP_API_URL if set
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  // In development, use relative URLs (proxy handles routing)
  return '';
};

export const API_BASE_URL = getApiBaseUrl();

/**
 * Creates a full API URL from a relative path
 */
export const createApiUrl = (path: string): string => {
  // Remove leading slash if present to avoid double slashes
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;

  if (API_BASE_URL) {
    return `${API_BASE_URL}/${cleanPath}`;
  }

  // Return relative URL for development proxy
  return `/${cleanPath}`;
};