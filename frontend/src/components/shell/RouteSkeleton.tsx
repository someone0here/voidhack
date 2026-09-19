import React from 'react';
import { FolderCard } from '../../design-system';

interface RouteSkeletonProps {
  title?: string;
}

export const RouteSkeleton: React.FC<RouteSkeletonProps> = ({
  title = 'LOADING DOSSIER SECTION...',
}) => {
  return (
    <div className="animate-fadeIn w-full">
      <FolderCard
        tabTitle={title}
        tabPosition="left"
        tabBadge="..."
        classification="CLASSIFIED // RETRIEVING EVIDENTIARY RECORDS"
        elevation="raised"
      >
        <div className="flex flex-col gap-6">
          {/* Skeleton Header */}
          <div className="flex items-start justify-between">
            <div className="w-2/3 space-y-2.5">
              {/* Title bar */}
              <div className="h-7 w-3/5 animate-pulse rounded-md bg-pine/10" />
              {/* Subtitle bars */}
              <div className="h-4 w-4/5 animate-pulse rounded bg-pine/5" />
              <div className="h-3.5 w-1/2 animate-pulse rounded bg-pine/5" />
            </div>
            {/* Stamp Badge skeleton */}
            <div className="h-8 w-24 animate-pulse rounded-full border border-pine/15 bg-pine/5" />
          </div>

          {/* Stitched Divider simulation */}
          <div className="h-px w-full border-b border-dashed border-pine/15" />

          {/* Metric cards grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="space-y-2 rounded-lg border border-pine/15 bg-cream/70 p-4 shadow-paper-sm"
              >
                <div className="h-3 w-1/2 animate-pulse rounded bg-pine/10" />
                <div className="h-6 w-3/4 animate-pulse rounded bg-pine/15" />
                <div className="h-2.5 w-2/3 animate-pulse rounded bg-pine/5" />
              </div>
            ))}
          </div>

          {/* Content Rows / Table skeleton */}
          <div className="space-y-3 rounded-xl border border-pine/15 bg-cream/50 p-4">
            <div className="flex items-center justify-between border-b border-pine/10 pb-2">
              <div className="h-3 w-32 animate-pulse rounded bg-pine/10" />
              <div className="h-3 w-16 animate-pulse rounded bg-pine/10" />
            </div>
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-pine/5 py-2 last:border-0"
              >
                <div className="flex w-1/2 items-center gap-3">
                  <div className="h-4 w-4 animate-pulse rounded bg-pine/10" />
                  <div className="h-3.5 w-3/4 animate-pulse rounded bg-pine/10" />
                </div>
                <div className="h-3 w-20 animate-pulse rounded bg-pine/10" />
                <div className="h-5 w-16 animate-pulse rounded-full bg-pine/5" />
              </div>
            ))}
          </div>
        </div>
      </FolderCard>
    </div>
  );
};
