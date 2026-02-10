import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { tokenStorage } from './tokenStorage';
import { authService } from '../services/authService';

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _skipAuthRefresh?: boolean;
}

// Flags to prevent infinite refresh attempts
let isRefreshing = false;
let hasRefreshFailed = false; // Track permanent refresh failure

interface QueuedPromise {
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}
let failedQueue: QueuedPromise[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom: QueuedPromise) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

export const setupAxiosInterceptors = () => {
  // Request interceptor to add auth token
  const requestInterceptor = axios.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = tokenStorage.getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor to handle 401 errors
  const responseInterceptor = axios.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as CustomAxiosRequestConfig;

      if (!originalRequest) {
        return Promise.reject(error);
      }

      // Skip auth refresh for the refresh endpoint itself to prevent infinite loops
      if (originalRequest._skipAuthRefresh) {
        return Promise.reject(error);
      }

      // If we get a 401 and haven't already tried to refresh
      if (error.response?.status === 401 && !originalRequest._retry) {
        // If refresh already failed permanently, immediately redirect to login
        if (hasRefreshFailed) {
          tokenStorage.clearTokens();
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          return Promise.reject(error);
        }

        originalRequest._retry = true;

        const refreshToken = tokenStorage.getRefreshToken();

        if (refreshToken && !isRefreshing) {
          isRefreshing = true;

          try {
            // Try to refresh the token
            await authService.refreshToken();

            // Get the new access token
            const newToken = tokenStorage.getAccessToken();

            // Reset the refreshing flag
            isRefreshing = false;

            // Process the queue with the new token
            processQueue(null, newToken);

            // Update the Authorization header
            if (newToken) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
            }

            // Retry the original request
            return axios.request(originalRequest);
          } catch (refreshError) {
            // Refresh failed permanently - prevent any further refresh attempts
            hasRefreshFailed = true;
            isRefreshing = false;
            tokenStorage.clearTokens();
            processQueue(refreshError, null);

            // Redirect to login page if in browser
            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }

            return Promise.reject(error);
          }
        } else if (isRefreshing) {
          // If already refreshing, add this request to the queue
          // But if refresh already failed, immediately reject
          if (hasRefreshFailed) {
            return Promise.reject(new Error('Authentication refresh failed'));
          }

          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then(token => {
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return axios.request(originalRequest);
          }).catch(err => {
            return Promise.reject(err);
          });
        } else {
          // No refresh token available or already failed
          tokenStorage.clearTokens();

          // Redirect to login if in browser
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
      }

      return Promise.reject(error);
    }
  );

  // Return cleanup function
  return () => {
    axios.interceptors.request.eject(requestInterceptor);
    axios.interceptors.response.eject(responseInterceptor);
  };
};

// Export function to reset refresh failure flag (call on successful login)
export const resetRefreshFailure = () => {
  hasRefreshFailed = false;
};