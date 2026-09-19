import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient, RankedEntityRiskRead } from '../lib/api-client';
import { queryKeys } from '../lib/queryKeys';

/**
 * GET /cases/{caseId}/risk — ranked entity risk scores behind RiskDesk.
 *
 * Like `useGraph`, this is invalidated by `useEvidence`'s upload mutation:
 * new evidence can shift entity risk scores, so the desk refetches on its
 * own rather than showing stale scores after an upload.
 */
export function useRisk(caseId: number | null): UseQueryResult<RankedEntityRiskRead[]> {
  return useQuery({
    queryKey: queryKeys.risk(caseId ?? -1),
    queryFn: () => apiClient.cases.getRiskScores(caseId as number),
    enabled: caseId !== null,
  });
}
