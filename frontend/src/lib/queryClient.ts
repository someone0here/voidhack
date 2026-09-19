/**
 * queryClient.ts — TanStack Query configuration.
 *
 * One QueryClient for the whole app. Two things live here beyond the usual
 * defaults:
 *
 *  1. Sensible cache/retry defaults for an investigative console: data is
 *     fetched over a LAN/local backend, not a flaky public API, so we retry
 *     failed queries once (never mutations — an upload retrying itself
 *     silently is a correctness bug in a chain-of-custody tool) and treat
 *     data as fresh for a short window to avoid duplicate fetches when a
 *     screen remounts (e.g. tab switch).
 *  2. A global `onError` on both the QueryCache and MutationCache. This is
 *     what makes "every failed API call surfaces a toast, never a raw stack
 *     trace" a property of the fetching layer itself rather than something
 *     each of the four screens has to remember to implement. Screens can
 *     still read `query.error` for inline messaging (RiskDesk, BriefViewer,
 *     CorrelationBoard already render a FolderCard error state that way) —
 *     the toast is a supplementary, ambient signal, not a replacement for
 *     that inline state.
 */

import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { ApiError } from './api-client';
import { notifyApiError } from './toast';

/** Extract a human-readable message from any thrown value. */
function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.detail ?? error.message;
  if (error instanceof Error) return error.message;
  return 'Something went wrong talking to the correlator service.';
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000, // 15s — short-lived console data, but avoids refetch storms
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => {
        // Don't retry 4xx — a 404 case or a 422 payload won't fix itself.
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 1;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Silent queries (e.g. background prefetches) can opt out via meta.
      if (query.meta?.silent) return;
      notifyApiError(describeError(error));
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _vars, _ctx, mutation) => {
      if (mutation.meta?.silent) return;
      notifyApiError(describeError(error));
    },
  }),
});
