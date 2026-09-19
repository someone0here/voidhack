import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useCase } from '../../context/useCase';
import {
  GlassToolbar,
  Button,
  appleToFramerSpring,
  reducedMotionTransition,
} from '../../design-system';
import { CaseSwitcher } from './CaseSwitcher';
import { CaseRoomSidebar } from './CaseRoomSidebar';
import { NAV_TABS, NavTabItem } from './nav-items';
import { RouteSkeleton } from './RouteSkeleton';
import { EmptyCaseFolder } from '../cases/EmptyCaseFolder';

export const AppShell: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { caseId } = useParams<{ caseId?: string }>();
  const { cases, activeCase, isLoading, createCase, setActiveCaseById } = useCase();
  const shouldReduceMotion = useReducedMotion();

  // The router defines tabs as static child paths (intake/correlation/risk/brief),
  // not as a `:tab` param, so useParams() can never return one. Derive the active
  // tab from the last URL segment instead; fall back to 'intake' for unknown paths.
  const lastPathSegment = location.pathname.split('/').filter(Boolean).pop();
  const currentTab =
    NAV_TABS.find((t) => t.pathSegment === lastPathSegment)?.id ?? 'intake';

  // Vertical anchor coordinate of the currently active tab (for spatial consistency)
  const [activeTabOriginY, setActiveTabOriginY] = useState<number>(60);
  const [isTransitioning, setIsTransitioning] = useState<boolean>(false);

  // Sync route param with CaseContext
  useEffect(() => {
    if (caseId) {
      const parsed = parseInt(caseId, 10);
      if (!isNaN(parsed) && parsed !== activeCase?.id) {
        setActiveCaseById(parsed);
      }
    }
  }, [caseId, activeCase?.id, setActiveCaseById]);

  // Navigate to appropriate tab when clicked
  const handleTabSelect = (selectedTab: NavTabItem, tabCenterY: number) => {
    setActiveTabOriginY(tabCenterY);
    setIsTransitioning(true);

    const targetCaseId = caseId || (activeCase ? activeCase.id : null);
    if (targetCaseId) {
      void navigate(`/cases/${targetCaseId}/${selectedTab.pathSegment}`);
    } else {
      void navigate(`/${selectedTab.pathSegment}`);
    }

    // Reset transitioning flag after brief animation frame
    setTimeout(() => {
      setIsTransitioning(false);
    }, 150);
  };

  const handleCaseCreated = async (name: string) => {
    const newCase = await createCase(name);
    void navigate(`/cases/${newCase.id}/intake`);
  };

  const handleCaseSelected = (newCaseId: number) => {
    void navigate(`/cases/${newCaseId}/${currentTab}`);
  };

  const springTransition = appleToFramerSpring({ damping: 1.0, response: 0.35 });

  // Initial loading state
  if (isLoading && cases.length === 0) {
    return (
      <div className="min-h-screen bg-cream text-pine">
        <GlassToolbar
          title={
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-pine/20 bg-khaki font-mono text-sm font-bold shadow-paper-sm">
                ⚖
              </span>
              <div>
                <h1 className="type-display-sm font-bold tracking-tight text-pine">
                  Cyber Fraud Correlator
                </h1>
                <p className="font-mono text-[10px] uppercase tracking-wider text-pine/60">
                  Law Enforcement Field Dossier Platform
                </p>
              </div>
            </div>
          }
        />
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          <RouteSkeleton title="INITIALIZING EVIDENTIARY DESK..." />
        </main>
      </div>
    );
  }

  // If no cases exist at all, render the Empty State closed folder
  if (!isLoading && cases.length === 0) {
    return (
      <div className="min-h-screen bg-cream text-pine selection:bg-khaki selection:text-pine">
        <GlassToolbar
          title={
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-pine/20 bg-khaki font-mono text-sm font-bold shadow-paper-sm">
                ⚖
              </span>
              <div>
                <h1 className="type-display-sm font-bold tracking-tight text-pine">
                  Cyber Fraud Correlator
                </h1>
                <p className="font-mono text-[10px] uppercase tracking-wider text-pine/60">
                  Law Enforcement Field Dossier Platform
                </p>
              </div>
            </div>
          }
          actions={
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void navigate('/design-system');
              }}
            >
              📐 Design System
            </Button>
          }
        />
        <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
          <EmptyCaseFolder
            onCreateCase={(name) => handleCaseCreated(name)}
            isLoading={isLoading}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-cream text-pine selection:bg-khaki selection:text-pine">
      {/* Top GlassToolbar */}
      <GlassToolbar
        title={
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-pine/20 bg-khaki font-mono text-sm font-bold shadow-paper-sm">
              ⚖
            </span>
            <div className="hidden sm:block">
              <h1 className="type-display-sm font-bold tracking-tight text-pine">
                Cyber Fraud Correlator
              </h1>
              <p className="font-mono text-[10px] uppercase tracking-wider text-pine/60">
                Law Enforcement Field Dossier Platform
              </p>
            </div>
          </div>
        }
        actions={
          <div className="flex items-center gap-3">
            <CaseSwitcher onCaseSelected={handleCaseSelected} />

            <div className="hidden h-5 w-px bg-pine/15 sm:block" />

            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void navigate('/design-system');
              }}
              className="border-pine/30 text-xs shadow-paper-sm"
            >
              📐 Design System
            </Button>
          </div>
        }
      />

      {/* Main Physical Case Room "Desk" Workspace */}
      <div className="mx-auto flex max-w-7xl px-4 py-6 sm:px-6">
        {/* Left Sidebar: Stack of Vertical Folder Tabs */}
        <CaseRoomSidebar
          activeTab={currentTab}
          onTabSelect={handleTabSelect}
          caseId={activeCase ? activeCase.id : null}
        />

        {/* Main Content Area on Desk Surface */}
        <main
          role="main"
          aria-label="Dossier Workspace"
          className="relative z-10 -ml-px min-w-0 flex-1"
        >
          {/* Spatially-anchored animated route transition */}
          <AnimatePresence mode="wait">
            {isTransitioning ? (
              <motion.div
                key="loading-skeleton"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={reducedMotionTransition}
                className="w-full"
              >
                <RouteSkeleton
                  title={
                    NAV_TABS.find((t) => t.id === currentTab)?.label.toUpperCase() ||
                    'LOADING SECTION...'
                  }
                />
              </motion.div>
            ) : (
              <motion.div
                key={`${caseId || activeCase?.id || 'none'}-${location.pathname}`}
                initial={
                  shouldReduceMotion
                    ? { opacity: 0 }
                    : {
                        opacity: 0,
                        scale: 0.985,
                      }
                }
                animate={{
                  opacity: 1,
                  scale: 1,
                }}
                exit={
                  shouldReduceMotion
                    ? { opacity: 0 }
                    : {
                        opacity: 0,
                        scale: 0.99,
                      }
                }
                transition={
                  shouldReduceMotion ? reducedMotionTransition : springTransition
                }
                style={{
                  // Spatial consistency: anchor transition origin to the clicked vertical tab
                  transformOrigin: `0px ${activeTabOriginY}px`,
                }}
                className="w-full"
              >
                <Outlet />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
};
