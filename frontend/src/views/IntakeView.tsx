import React from 'react';
import { useParams } from 'react-router-dom';
import { useCase } from '../context/useCase';
import { RouteSkeleton } from '../components/shell/RouteSkeleton';
import { IntakeScreen } from '../app/screens/IntakeScreen';

export const IntakeView: React.FC = () => {
  const { activeCase, isLoading } = useCase();
  const { caseId: routeCaseId } = useParams<{ caseId?: string }>();

  if (isLoading) return <RouteSkeleton title="EVIDENCE INTAKE // LOADING..." />;

  const resolvedId = activeCase?.id ?? (routeCaseId ? parseInt(routeCaseId, 10) : null);

  if (!resolvedId || isNaN(resolvedId)) {
    return <RouteSkeleton title="EVIDENCE INTAKE // NO CASE SELECTED" />;
  }

  return <IntakeScreen caseId={resolvedId} />;
};
