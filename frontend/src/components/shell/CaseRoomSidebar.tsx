import React, { useRef } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { appleToFramerSpring, reducedMotionTransition } from '../../design-system';
import { NAV_TABS, NavTabItem } from './nav-items';

export { NAV_TABS };
export type { NavTabItem };

interface CaseRoomSidebarProps {
  activeTab: string;
  onTabSelect: (tab: NavTabItem, tabCenterY: number) => void;
  caseId: number | null;
}

export const CaseRoomSidebar: React.FC<CaseRoomSidebarProps> = ({
  activeTab,
  onTabSelect,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  // Apple spring spec: damping 1.0, response 0.3 for interruptible tab switching
  const tabSpringTransition = appleToFramerSpring({ damping: 1.0, response: 0.3 });

  const handleTabClick = (tab: NavTabItem) => {
    const el = tabRefs.current.get(tab.id);
    let tabY = 100;
    if (el) {
      const rect = el.getBoundingClientRect();
      const parentRect = el.parentElement?.getBoundingClientRect();
      if (parentRect) {
        tabY = rect.top - parentRect.top + rect.height / 2;
      } else {
        tabY = rect.top + rect.height / 2;
      }
    }
    onTabSelect(tab, tabY);
  };

  return (
    <aside
      aria-label="Case Room Navigation"
      className="relative z-20 flex w-60 shrink-0 select-none flex-col pr-0 pt-4"
    >
      {/* Dossier Stack Header */}
      <div className="mb-3 px-4">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-terracotta" />
          <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-pine/60">
            Dossier Sections
          </span>
        </div>
      </div>

      {/* Vertical Stack of Die-cut Folder Tabs */}
      <nav className="relative flex flex-col gap-1.5 pr-0">
        {NAV_TABS.map((tab) => {
          const isActive = activeTab === tab.id;

          return (
            <div key={tab.id} className="relative">
              <button
                ref={(el) => {
                  if (el) tabRefs.current.set(tab.id, el);
                  else tabRefs.current.delete(tab.id);
                }}
                type="button"
                onClick={() => handleTabClick(tab)}
                aria-current={isActive ? 'page' : undefined}
                className={`group relative flex w-full items-center justify-between rounded-l-xl border-y border-l px-4 py-3.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pine ${
                  isActive
                    ? 'z-30 border-pine/25 bg-khaki text-pine shadow-[0_2px_8px_rgba(46,58,47,0.08)]'
                    : 'z-10 border-pine/15 bg-khaki-dark/40 text-pine/70 hover:bg-khaki-light/60 hover:text-pine'
                }`}
                style={{
                  // Inactive tabs visually recede behind active tab
                  transform: isActive ? 'translateX(2px)' : 'translateX(-2px)',
                  transition: 'transform 0.15s ease-out',
                }}
              >
                {/* Paper grain overlay */}
                <div
                  aria-hidden="true"
                  className="paper-grain pointer-events-none absolute inset-0 rounded-l-xl opacity-35"
                />

                {/* Top rim highlight */}
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-x-0 top-0 h-px rounded-tl-xl bg-white/40"
                />

                {/* Apple spring active indicator plate */}
                {isActive && (
                  <motion.div
                    layoutId="activeFolderTabPlate"
                    transition={
                      shouldReduceMotion ? reducedMotionTransition : tabSpringTransition
                    }
                    className="absolute inset-0 rounded-l-xl bg-khaki shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]"
                    style={{ zIndex: -1 }}
                  />
                )}

                {/* Tab Content */}
                <div className="relative z-10 flex items-center gap-2.5">
                  <span className="text-base" aria-hidden="true">
                    {tab.icon}
                  </span>
                  <div className="flex flex-col">
                    <span
                      className={`font-mono text-xs tracking-tight ${
                        isActive ? 'font-bold text-pine' : 'font-medium text-pine/80'
                      }`}
                    >
                      {tab.label}
                    </span>
                    <span className="font-mono text-[9px] uppercase tracking-wider text-pine/50">
                      {tab.classification}
                    </span>
                  </div>
                </div>

                {/* Die-Cut Tab Badge (Index Number) */}
                <div className="relative z-10 flex items-center gap-1">
                  <span
                    className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                      isActive
                        ? 'bg-pine text-cream shadow-sm'
                        : 'bg-pine/10 text-pine/60 group-hover:bg-pine/20 group-hover:text-pine'
                    }`}
                  >
                    {tab.badge}
                  </span>
                </div>

                {/* Right edge connector to eliminate shadow gap against main desk card */}
                {isActive && (
                  <div
                    aria-hidden="true"
                    className="pointer-events-none absolute -right-2 bottom-0 top-0 z-40 w-3 bg-khaki"
                  />
                )}
              </button>
            </div>
          );
        })}
      </nav>

      {/* Case Room Desk Telemetry Footer */}
      <div className="mt-auto px-4 py-6">
        <div className="rounded-lg border border-pine/15 bg-khaki-light/60 p-3 shadow-paper-sm">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[9px] uppercase tracking-widest text-pine/60">
              PHYSICAL CASE ROOM
            </span>
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sage" />
          </div>
          <p className="mt-1 font-mono text-[10px] text-pine/70">
            Evidentiary Desk Surface // High Density
          </p>
          <div className="mt-2 font-mono text-[10px] text-pine/50">
            Direct manipulation ready
          </div>
        </div>
      </div>
    </aside>
  );
};
