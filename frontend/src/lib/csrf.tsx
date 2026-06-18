import { useEffect } from 'react';

let csrfToken: string | null = null;

export const getCsrfToken = (): string | null => csrfToken;

export const initCSRF = async () => {
  try {
    const response = await fetch('/api/csrf-token');
    if (response.ok) {
      const data = await response.json();
      csrfToken = data.csrf_token;
    }
  } catch (error) {
    if (import.meta.env.DEV) {
      console.error('Failed to initialize CSRF token:', error);
    }
  }
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
    body: JSON.stringify(data),
  });
  return response.json();
};
