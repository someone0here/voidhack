import React, { useState, useEffect, useCallback } from 'react';
import { apiClient, CaseRead, CaseCreate, CaseStatus } from '../lib/api-client';
import { CaseContext } from './useCase';

export const CaseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [cases, setCases] = useState<CaseRead[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshCases = useCallback(async (): Promise<CaseRead[]> => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedCases = await apiClient.cases.list();
      setCases(fetchedCases);
      const first = fetchedCases[0];
      if (first && activeCaseId === null) {
        setActiveCaseId(first.id);
      }
      return fetchedCases;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch cases';
      setError(msg);
      return [];
    } finally {
      setIsLoading(false);
    }
  }, [activeCaseId]);

  useEffect(() => {
    void refreshCases();
  }, [refreshCases]);

  const selectCase = useCallback((caseId: number) => {
    setActiveCaseId(caseId);
  }, []);

  const setActiveCaseById = useCallback((caseId: number | null) => {
    setActiveCaseId(caseId);
  }, []);

  const createCase = useCallback(
    async (name: string, status: CaseStatus = 'active'): Promise<CaseRead> => {
      setIsLoading(true);
      setError(null);
      try {
        const payload: CaseCreate = { name, status };
        const newCase = await apiClient.cases.create(payload);
        setCases((prev) => [newCase, ...prev]);
        setActiveCaseId(newCase.id);
        return newCase;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to create case';
        setError(msg);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  const activeCase = cases.find((c) => c.id === activeCaseId) || null;

  return (
    <CaseContext.Provider
      value={{
        cases,
        activeCase,
        activeCaseId,
        isLoading,
        error,
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
