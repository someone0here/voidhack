import React from 'react';
import { useParams } from 'react-router-dom';
import { useCase } from '../context/useCase';
import { RouteSkeleton } from '../components/shell/RouteSkeleton';
import { RiskDesk } from '../app/screens/RiskDesk';

export const RiskDeskView: React.FC = () => {
  const { activeCase, isLoading } = useCase();
  const { caseId: routeCaseId } = useParams<{ caseId?: string }>();

  if (isLoading) return <RouteSkeleton title="RISK DESK // LOADING..." />;

  const resolvedId =
    activeCase?.id ?? (routeCaseId ? parseInt(routeCaseId, 10) : null);

  if (!resolvedId || isNaN(resolvedId)) {
    return <RouteSkeleton title="RISK DESK // NO CASE SELECTED" />;
  }

  return <RiskDesk caseId={resolvedId} />;
};
