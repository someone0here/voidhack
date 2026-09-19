import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient, BriefExport } from '../lib/api-client';
import { queryKeys } from '../lib/queryKeys';

/**
 * GET /cases/{caseId}/brief.json — the investigative brief behind
 * BriefViewer. `maskPii` is part of the cache key: toggling it (if the UI
 * ever exposes that) is a distinct cache entry, not a stale one.
 */
export function useBrief(
  caseId: number | null,
  maskPii = true,
): UseQueryResult<BriefExport> {
  return useQuery({
    queryKey: queryKeys.brief(caseId ?? -1, maskPii),
    queryFn: () => apiClient.cases.getBriefJson(caseId as number, maskPii),
    enabled: caseId !== null,
  });
}
