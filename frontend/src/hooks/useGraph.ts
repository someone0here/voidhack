import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient, SerializedGraph } from '../lib/api-client';
import { queryKeys } from '../lib/queryKeys';

/**
 * GET /cases/{caseId}/graph — the correlation graph behind CorrelationBoard.
 *
 * Invalidated (not directly refetched) by `useEvidence`'s upload mutation,
 * so a fresh ingestion on the Intake screen makes the graph refetch itself
 * the next time this hook is mounted or its window refocuses — no manual
 * refresh required to see newly-correlated entities.
 */
export function useGraph(caseId: number | null): UseQueryResult<SerializedGraph> {
  return useQuery({
    queryKey: queryKeys.graph(caseId ?? -1),
    queryFn: () => apiClient.cases.getGraph(caseId as number),
    enabled: caseId !== null,
  });
}
