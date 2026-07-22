import { useEffect } from 'react';

export const clearCsrfToken = () => {
  csrfToken = null;
  initPromise = null;
};

export const initCSRF = (): Promise<string | null> => {
  if (csrfToken) return Promise.resolve(csrfToken);
  if (initPromise) return initPromise;

  initPromise = (async () => {
    try {
      const response = await fetch('/api/csrf-token', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        csrfToken = data.csrf_token;
        return csrfToken;
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to initialize CSRF token:', error);
      }
    } finally {
      initPromise = null;
    }
    return null;
  })();

  return initPromise;
};

export const getCsrfToken = async (): Promise<string | null> => {
  if (csrfToken) return csrfToken;
  return initCSRF();
};

// Custom hook to initialize CSRF on app load
export const useCSRF = () => {
  useEffect(() => {
    initCSRF();
  }, []);
};

// Helper for API calls
export const apiCall = async (
  method: 'POST' | 'PUT' | 'DELETE',
  endpoint: string,
  data: any
) => {
  const response = await fetch(endpoint, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken || '',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return response.json();
};
