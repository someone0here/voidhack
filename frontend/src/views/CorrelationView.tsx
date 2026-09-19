import React from 'react';
import { useParams } from 'react-router-dom';
import { useCase } from '../context/useCase';
import { RouteSkeleton } from '../components/shell/RouteSkeleton';
import { CorrelationBoard } from '../app/screens/CorrelationBoard';

export const CorrelationView: React.FC = () => {
  const { activeCase, isLoading } = useCase();
  const { caseId: routeCaseId } = useParams<{ caseId?: string }>();

  if (isLoading) return <RouteSkeleton title="CORRELATION BOARD // LOADING..." />;

  const resolvedId = activeCase?.id ?? (routeCaseId ? parseInt(routeCaseId, 10) : null);

  if (!resolvedId || isNaN(resolvedId)) {
    return <RouteSkeleton title="CORRELATION BOARD // NO CASE SELECTED" />;
  }

  return <CorrelationBoard caseId={resolvedId} />;
};
