import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  defaultSpringTransition,
  momentumSpringTransition,
  reducedMotionTransition,
} from '../motion';

export interface FolderCardProps {
  /**
   * Title displayed inside the die-cut folder tab
   */
  tabTitle?: string;
  /**
   * Die-cut tab horizontal alignment
   * @default 'left'
   */
  tabPosition?: 'left' | 'center' | 'right';
  /**
   * Small tag or classification number inside the tab
   */
  tabBadge?: string;
  /**
   * Classification stamp / header line on card face (e.g. "EVIDENTIARY DOSSIER // DEPT 04")
   */
  classification?: string;
  /**
   * Depth elevation tier following Apple materials rules:
   * - 'flat': subtle contact shadow
   * - 'raised': distinct layered ambient + direct shadow
   * - 'floating': high elevation with expansive blur
   * @default 'raised'
   */
  elevation?: 'flat' | 'raised' | 'floating';
  /**
   * Enables interactive Apple fluid momentum dragging
   * @default false
   */
  isDraggable?: boolean;
  /**
   * Whether to include the subtle SVG paper-grain texture
   * @default true
   */
  showPaperGrain?: boolean;
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

const elevationShadows = {
  flat: 'shadow-paper-sm',
  raised: 'shadow-paper',
  floating: 'shadow-paper-raised',
};

const tabAlignments = {
  left: 'justify-start pl-6',
  center: 'justify-center',
  right: 'justify-end pr-6',
};

export const FolderCard: React.FC<FolderCardProps> = ({
  tabTitle,
  tabPosition = 'left',
  tabBadge,
  classification,
  elevation = 'raised',
  isDraggable = false,
  showPaperGrain = true,
  children,
  className = '',
  onClick,
}) => {
  const shouldReduceMotion = useReducedMotion();

  const motionProps = isDraggable
    ? {
        drag: true,
        dragConstraints: { left: -30, right: 30, top: -20, bottom: 20 },
        dragElastic: 0.2,
        dragTransition: { bounceStiffness: 323, bounceDamping: 29 },
        whileDrag: {
          scale: 1.02,
          boxShadow:
            '0 20px 35px -5px rgba(46, 58, 47, 0.22), 0 10px 10px -5px rgba(46, 58, 47, 0.12)',
        },
        transition: shouldReduceMotion
          ? reducedMotionTransition
          : momentumSpringTransition,
      }
    : {
        whileHover: onClick
          ? {
              y: -2,
              transition: shouldReduceMotion
                ? reducedMotionTransition
                : defaultSpringTransition,
            }
          : undefined,
      };

  return (
    <motion.div
      {...motionProps}
      onClick={onClick}
      className={`group relative flex flex-col ${isDraggable ? 'cursor-grab active:cursor-grabbing' : ''} ${className}`}
    >
      {/* Die-cut Manila Folder Tab */}
      {tabTitle && (
        <div className={`flex w-full items-end ${tabAlignments[tabPosition]}`}>
          <div className="relative inline-flex items-center gap-2 rounded-t-lg border-x border-t border-pine/20 bg-khaki-light px-4 py-1.5 shadow-[0_-1px_3px_rgba(46,58,47,0.06)]">
            {/* Subtle paper grain on tab */}
            {showPaperGrain && (
              <div
                aria-hidden="true"
                className="paper-grain pointer-events-none absolute inset-0 rounded-t-lg opacity-40"
              />
            )}
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-pine-light">
              {tabTitle}
            </span>
            {tabBadge && (
              <span className="rounded bg-pine/10 px-1.5 py-0.5 font-mono text-[10px] font-bold text-pine">
                {tabBadge}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Main Manila Paper Stock Surface */}
      <div
        className={`relative overflow-hidden rounded-xl border border-pine/20 bg-khaki p-6 text-pine transition-shadow ${elevationShadows[elevation]}`}
      >
        {/* Subtle Paper Grain Filter Overlay */}
        {showPaperGrain && (
          <div
            aria-hidden="true"
            className="paper-grain pointer-events-none absolute inset-0 opacity-45 mix-blend-multiply"
          />
        )}

        {/* Top Rim Highlight (evoking physical paper stock thickness) */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/40"
        />

        {/* Classification Header / Case Ref */}
        {classification && (
          <div className="relative mb-4 flex items-center justify-between border-b border-pine/15 pb-2">
            <span className="font-mono text-xs font-semibold uppercase tracking-widest text-pine/70">
              {classification}
            </span>
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span className="h-1.5 w-1.5 rounded-full bg-sage" />
              <span className="h-1.5 w-1.5 rounded-full bg-terracotta/80" />
            </div>
          </div>
        )}

        {/* Content Container */}
        <div className="relative z-10">{children}</div>
      </div>
    </motion.div>
  );
};
