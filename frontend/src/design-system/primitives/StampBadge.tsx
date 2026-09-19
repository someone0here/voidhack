import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { defaultSpringTransition, reducedMotionTransition } from '../motion';

export type StampVariant = 'terracotta' | 'sage' | 'pine';
export type StampShape = 'pill' | 'circular' | 'rectangular';

export interface StampBadgeProps {
  label: string;
  /**
   * Color variant:
   * - 'terracotta': Alert, Critical, High Priority, Redacted
   * - 'sage': Verified, Approved, Declassified
   * - 'pine': Archived, Official, Filed
   * @default 'terracotta'
   */
  variant?: StampVariant;
  /**
   * Geometric footprint of the stamp
   * @default 'pill'
   */
  shape?: StampShape;
  /**
   * Subtle angular rotation in degrees (e.g. -3, 2) to emulate hand-stamped ink
   * @default -3
   */
  rotation?: number;
  /**
   * Typewritten sub-text or date stamp (e.g. "19.09.2026")
   */
  subtext?: string;
  className?: string;
}

const variantStyles: Record<
  StampVariant,
  {
    text: string;
    border: string;
    innerBorder: string;
    bg: string;
    shadow: string;
  }
> = {
  terracotta: {
    text: 'text-terracotta-dark',
    border: 'border-terracotta/80',
    innerBorder: 'border-terracotta/50',
    bg: 'bg-terracotta/10',
    shadow: 'shadow-stamp',
  },
  sage: {
    text: 'text-sage-dark',
    border: 'border-sage',
    innerBorder: 'border-sage/50',
    bg: 'bg-sage/10',
    shadow: 'shadow-stamp-sage',
  },
  pine: {
    text: 'text-pine',
    border: 'border-pine/80',
    innerBorder: 'border-pine/40',
    bg: 'bg-pine/10',
    shadow: 'shadow-[0_0_0_1px_rgba(46,58,47,0.3)]',
  },
};

const shapeStyles: Record<StampShape, string> = {
  pill: 'rounded-full px-3.5 py-1',
  rectangular: 'rounded-md px-3 py-1',
  circular: 'rounded-full w-20 h-20 flex-col justify-center text-center p-2',
};

export const StampBadge: React.FC<StampBadgeProps> = ({
  label,
  variant = 'terracotta',
  shape = 'pill',
  rotation = -3,
  subtext,
  className = '',
}) => {
  const shouldReduceMotion = useReducedMotion();
  const v = variantStyles[variant];

  // In reduced motion, skip angular tilt and stamp pop
  const initialRotate = shouldReduceMotion ? 0 : rotation - 2;
  const targetRotate = shouldReduceMotion ? 0 : rotation;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92, rotate: initialRotate }}
      animate={{ opacity: 1, scale: 1, rotate: targetRotate }}
      transition={shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition}
      className={`relative inline-flex select-none items-center justify-center ${v.bg} ${v.text} ${shapeStyles[shape]} ${v.shadow} ${className}`}
      style={{
        transformOrigin: 'center center',
      }}
    >
      {/* Outer physical stamped ink rim */}
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-0.5 ${shape === 'circular' ? 'rounded-full' : shape === 'pill' ? 'rounded-full' : 'rounded'} border-2 border-dashed ${v.border} opacity-80`}
      />

      {/* Subtle stamped ink texture mask */}
      <div
        aria-hidden="true"
        className="stamp-distress pointer-events-none absolute inset-0 bg-current opacity-20 mix-blend-multiply"
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center leading-none">
        <span className="font-mono text-xs font-bold uppercase tracking-widest">
          {label}
        </span>
        {subtext && (
          <span className="mt-0.5 font-mono text-[9px] font-medium tracking-tight opacity-75">
            {subtext}
          </span>
        )}
      </div>
    </motion.div>
  );
};
