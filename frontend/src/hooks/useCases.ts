import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
  UseMutationResult,
} from '@tanstack/react-query';
import { apiClient, CaseRead, CaseCreate, CaseStatus } from '../lib/api-client';
import { queryKeys } from '../lib/queryKeys';

/**
 * GET /cases — the case list behind `CaseContext`. Not consumed directly by
 * screens; `CaseContext` wraps this together with the (non-query, per-tab)
 * "which case is currently selected" state. See `CaseContext.tsx` for why
 * that split exists.
 */
export function useCasesQuery(): UseQueryResult<CaseRead[]> {
  return useQuery({
    queryKey: queryKeys.cases.all,
    queryFn: () => apiClient.cases.list(),
  });
}

/**
 * POST /cases. On success, writes the new case straight into the `cases`
 * list cache (cheap and exact — we already have the full new object from
 * the response) rather than invalidating and waiting on a refetch, so the
 * sidebar/switcher show the new case immediately.
 */
export function useCreateCase(): UseMutationResult<
  CaseRead,
  Error,
  { name: string; status?: CaseStatus }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, status }: { name: string; status?: CaseStatus }) => {
      const payload: CaseCreate = { name, status };
      return apiClient.cases.create(payload);
    },
    onSuccess: (newCase) => {
      queryClient.setQueryData<CaseRead[]>(queryKeys.cases.all, (prev) =>
        prev ? [newCase, ...prev] : [newCase],
      );
    },
  });
}
