import React from 'react';
import { useParams } from 'react-router-dom';
import { useCase } from '../context/useCase';
import { RouteSkeleton } from '../components/shell/RouteSkeleton';
import { BriefViewer } from '../app/screens/BriefViewer';

export const BriefView: React.FC = () => {
  const { activeCase, isLoading } = useCase();
  const { caseId: routeCaseId } = useParams<{ caseId?: string }>();

  if (isLoading) return <RouteSkeleton title="BRIEF VIEWER // LOADING..." />;

  const resolvedId =
    activeCase?.id ?? (routeCaseId ? parseInt(routeCaseId, 10) : null);

  if (!resolvedId || isNaN(resolvedId)) {
    return <RouteSkeleton title="BRIEF VIEWER // NO CASE SELECTED" />;
  }

  return <BriefViewer caseId={resolvedId} />;
};
