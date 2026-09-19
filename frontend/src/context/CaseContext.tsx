/**
 * CaseContext — the app's one piece of "global app state": which case is
 * currently selected.
 *
 * Why React Context and not Zustand: this is a single scalar
 * (`activeCaseId`) that changes rarely (on navigation, not on every
 * keystroke or drag frame), is read by a handful of components (toolbar,
 * sidebar, the four screen views), and is already kept in sync with the
 * URL (`/cases/:caseId/...`) by `AppShell`. Context's lack of a selector
 * mechanism — the thing that usually pushes people toward Zustand — isn't a
 * real cost here: there's nothing in this context that updates fast enough
 * for unnecessary re-renders to matter (contrast with, say, live d3-force
 * node positions in CorrelationBoard, which correctly stay as local
 * component state rather than living here). Reaching for a separate store
 * library for one selected-id value would be the over-engineered choice,
 * not the pragmatic one.
 *
 * The *server data* half of what used to live here (the actual `GET /cases`
 * list, and case creation) has moved to `hooks/useCases.ts` and is backed by
 * TanStack Query — this component now just composes that query with the
 * plain `activeCaseId` selection state and exposes the combined shape
 * everything else in the app already depends on via `useCase()`.
 */

import React, { useState, useCallback } from 'react';
import { CaseStatus } from '../lib/api-client';
import { useCasesQuery, useCreateCase } from '../hooks/useCases';
import { CaseContext } from './useCase';

export const CaseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeCaseId, setActiveCaseId] = useState<number | null>(null);

  const casesQuery = useCasesQuery();
  const createCaseMutation = useCreateCase();

  const cases = casesQuery.data ?? [];

  // Default to the first case once the list loads, if nothing is selected yet.
  const firstCase = cases[0];
  const resolvedActiveCaseId = activeCaseId ?? (firstCase ? firstCase.id : null);

  const selectCase = useCallback((caseId: number) => {
    setActiveCaseId(caseId);
  }, []);

  const setActiveCaseById = useCallback((caseId: number | null) => {
    setActiveCaseId(caseId);
  }, []);

  const createCase = useCallback(
    async (name: string, status: CaseStatus = 'active') => {
      const newCase = await createCaseMutation.mutateAsync({ name, status });
      setActiveCaseId(newCase.id);
      return newCase;
    },
    [createCaseMutation],
  );

  const refreshCases = useCallback(async () => {
    const result = await casesQuery.refetch();
    return result.data ?? [];
  }, [casesQuery]);

  const activeCase = cases.find((c) => c.id === resolvedActiveCaseId) || null;

  return (
    <CaseContext.Provider
      value={{
        cases,
        activeCase,
        activeCaseId: resolvedActiveCaseId,
        isLoading: casesQuery.isLoading,
        error: casesQuery.error ? casesQuery.error.message : null,
        refreshCases,
        selectCase,
        createCase,
        setActiveCaseById,
      }}
    >
      {children}
    </CaseContext.Provider>
  );
};
