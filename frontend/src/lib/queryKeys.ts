/**
 * queryKeys.ts — Single source of truth for TanStack Query cache keys.
 *
 * Centralizing these avoids the classic react-query foot-gun where one hook
 * invalidates `['risk', caseId]` and another reads `[caseId, 'risk']` and
 * they silently never talk to each other. Every hook in `src/hooks/` and
 * every invalidation call in `useEvidence.ts` imports from here.
 */

export const queryKeys = {
  cases: {
    all: ['cases'] as const,
    detail: (caseId: number) => ['cases', caseId] as const,
  },
  graph: (caseId: number) => ['cases', caseId, 'graph'] as const,
  risk: (caseId: number) => ['cases', caseId, 'risk'] as const,
  brief: (caseId: number, maskPii: boolean) =>
    ['cases', caseId, 'brief', maskPii] as const,
  integrity: (caseId: number) => ['cases', caseId, 'integrity'] as const,
};
