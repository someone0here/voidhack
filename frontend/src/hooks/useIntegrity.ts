import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient, ChainVerificationResult } from '../lib/api-client';
import { queryKeys } from '../lib/queryKeys';

/**
 * GET /cases/{caseId}/integrity — custody chain verification behind
 * BriefViewer's wax-seal indicator. Invalidated alongside graph/risk on
 * evidence upload, since new evidence extends the custody chain.
 */
export function useIntegrity(
  caseId: number | null,
): UseQueryResult<ChainVerificationResult> {
  return useQuery({
    queryKey: queryKeys.integrity(caseId ?? -1),
    queryFn: () => apiClient.cases.getIntegrity(caseId as number),
    enabled: caseId !== null,
  });
}
