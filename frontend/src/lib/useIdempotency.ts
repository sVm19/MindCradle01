import { useRef, useState, useCallback } from 'react';

/**
 * Generates a crypto-secure UUID v4 string for idempotent requests,
 * with a resilient fallback for older browser environments.
 */
export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}-${Math.random().toString(36).substring(2, 11)}`;
}

export interface UseIdempotentActionOptions<TResult> {
  onSuccess?: (result: TResult) => void;
  onError?: (error: unknown) => void;
  /** Keep the button/action locked even after resolution (e.g. for external window redirects) */
  keepLockedOnSuccess?: boolean;
}

/**
 * A dedicated hook providing client-side idempotency protection:
 * 1. Synchronous mutex lock (via ref) preventing rapid multi-clicks or double-clicks
 *    before React re-renders `disabled` state.
 * 2. Idempotency key management: generates a unique key per action cycle,
 *    attaches it to requests, and rotates on failure so retry works cleanly.
 * 3. Loading state and accessibility indicators.
 */
export function useIdempotentAction<TArgs extends any[], TResult>(
  action: (idempotencyKey: string, ...args: TArgs) => Promise<TResult>,
  options?: UseIdempotentActionOptions<TResult>
) {
  const [isProcessing, setIsProcessing] = useState(false);
  const isLockedRef = useRef(false);
  const idempotencyKeyRef = useRef<string>(generateIdempotencyKey());

  const execute = useCallback(
    async (...args: TArgs): Promise<TResult | undefined> => {
      // Synchronous mutex lock: if already executing, drop redundant clicks immediately
      if (isLockedRef.current) {
        return undefined;
      }

      isLockedRef.current = true;
      setIsProcessing(true);

      try {
        const result = await action(idempotencyKeyRef.current, ...args);
        options?.onSuccess?.(result);

        if (!options?.keepLockedOnSuccess) {
          // Rotate key for subsequent distinct transactions
          idempotencyKeyRef.current = generateIdempotencyKey();
          isLockedRef.current = false;
          setIsProcessing(false);
        }
        return result;
      } catch (err) {
        // Rotate key on error so a user retry is treated as a clean fresh attempt
        idempotencyKeyRef.current = generateIdempotencyKey();
        isLockedRef.current = false;
        setIsProcessing(false);
        options?.onError?.(err);
        throw err;
      }
    },
    [action, options]
  );

  const reset = useCallback(() => {
    isLockedRef.current = false;
    setIsProcessing(false);
    idempotencyKeyRef.current = generateIdempotencyKey();
  }, []);

  return {
    execute,
    isProcessing,
    reset,
    idempotencyKey: idempotencyKeyRef.current,
  };
}
