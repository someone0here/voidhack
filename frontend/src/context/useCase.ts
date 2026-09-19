import { createContext, useContext } from 'react';
import { CaseRead, CaseStatus } from '../lib/api-client';

export interface CaseContextValue {
  cases: CaseRead[];
  activeCase: CaseRead | null;
  activeCaseId: number | null;
  isLoading: boolean;
  error: string | null;
  refreshCases: () => Promise<CaseRead[]>;
  selectCase: (caseId: number) => void;
  createCase: (name: string, status?: CaseStatus) => Promise<CaseRead>;
  setActiveCaseById: (caseId: number | null) => void;
}

export const CaseContext = createContext<CaseContextValue | undefined>(undefined);

export function useCase(): CaseContextValue {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error('useCase must be used within a CaseProvider');
  }
  return context;
}
