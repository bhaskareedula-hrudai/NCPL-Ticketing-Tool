import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Generic hook for async data fetching with loading / error state.
 * Pass a stable async function (or wrap in useCallback) and dependency array.
 *
 * Returns { data, loading, error, refetch }
 */
export function useAsync(asyncFn, deps = []) {
  const [state, setState] = useState({ data: undefined, loading: true, error: null });
  const mountedRef = useRef(true);

  const run = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await asyncFn();
      if (mountedRef.current) setState({ data, loading: false, error: null });
    } catch (err) {
      if (mountedRef.current) setState({ data: undefined, loading: false, error: err });
    }
  }, deps); // deps is intentionally spread — callers control re-run triggers

  useEffect(() => {
    mountedRef.current = true;
    run();
    return () => { mountedRef.current = false; };
  }, [run]);

  return { ...state, refetch: run };
}
