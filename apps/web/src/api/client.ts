import axios from 'axios';
import { getStoredToken, getValidToken, clearToken } from './auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const AUTH_FREE_PATHS = ['/auth/login', '/auth/register'];

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use(
  async (config) => {
    const urlPath = (config.url || '').toLowerCase();
    if (AUTH_FREE_PATHS.some((path) => urlPath.startsWith(path))) {
      return config;
    }

    let token = getStoredToken();
    if (!token) {
      try {
        token = await getValidToken();
      } catch (error) {
        token = null;
      }
    }

    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken();
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export { api };
export const API_BASE_URL = api.defaults.baseURL || API_BASE_URL;
