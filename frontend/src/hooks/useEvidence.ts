import { useMutation, useQueryClient, UseMutationResult } from '@tanstack/react-query';
import { apiClient, IngestionSummary, SourceType } from '../lib/api-client';
import { queryKeys } from '../lib/queryKeys';

interface UploadEvidenceVariables {
  caseId: number;
  file: File;
  sourceType: SourceType;
}

/**
 * POST /cases/{caseId}/evidence — the mutation behind IntakeScreen's
 * dropzone.
 *
 * IntakeScreen owns the optimistic per-file chip state itself (pending →
 * uploading → processed/failed appears the instant a file is dropped, well
 * before the network resolves — see `IntakeScreen.tsx`), so this hook's job
 * is narrower: perform the upload and, on success, invalidate every query
 * that a new piece of evidence can change:
 *
 *  - `graph` and `risk` (required by this ticket — new evidence can add
 *    entities/links and shift risk scores)
 *  - `integrity` (a new evidence file extends the custody chain hash, so a
 *    stale wax-seal indicator would be actively misleading)
 *  - `brief` (its `case_summary.total_evidence_files` etc. would otherwise
 *    go stale until the tab is revisited)
 *
 * Invalidating (rather than manually refetching or writing the response
 * into those caches) is deliberate: it lets each screen's own `useQuery`
 * decide whether it's actually mounted and needs the data right now,
 * instead of this hook reaching into caches it doesn't own.
 */
export function useEvidence(
  caseId: number,
): UseMutationResult<IngestionSummary, Error, Omit<UploadEvidenceVariables, 'caseId'>> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, sourceType }: Omit<UploadEvidenceVariables, 'caseId'>) =>
      apiClient.cases.uploadEvidence(caseId, file, sourceType),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.graph(caseId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.risk(caseId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.integrity(caseId) });
      void queryClient.invalidateQueries({
        queryKey: ['cases', caseId, 'brief'],
      });
    },
  });
}
