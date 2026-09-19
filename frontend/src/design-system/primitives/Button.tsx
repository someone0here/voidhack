import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  APPLE_MOTION_SPECS,
  instantPressTransition,
  defaultSpringTransition,
  reducedMotionTransition,
} from '../motion';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-terracotta hover:bg-terracotta-light active:bg-terracotta-dark text-cream font-semibold shadow-[0_1px_2px_rgba(46,58,47,0.15),0_2px_4px_rgba(201,111,79,0.25)] border border-terracotta-dark/20',
  secondary:
    'bg-transparent hover:bg-sage/10 active:bg-sage/20 text-pine font-semibold border-2 border-sage shadow-sm',
  ghost:
    'bg-transparent hover:bg-pine/5 active:bg-pine/10 text-pine font-medium border border-transparent',
  danger:
    'bg-dossier-crimson hover:bg-red-600 text-white font-semibold shadow-sm border border-red-700',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-md gap-1.5',
  md: 'px-4 py-2 text-sm rounded-lg gap-2',
  lg: 'px-6 py-2.5 text-base rounded-xl gap-2.5',
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled = false,
  children,
  className = '',
  ...props
}) => {
  const shouldReduceMotion = useReducedMotion();

  // Instant pointer-down depression token per Apple motion spec:
  // scale: 0.97, ~100ms. In reduced motion, replace with opacity cross-fade.
  const tapMotion = shouldReduceMotion
    ? { opacity: 0.75 }
    : { scale: APPLE_MOTION_SPECS.pressFeedback.scale };

  const hoverMotion = shouldReduceMotion
    ? { opacity: 0.92 }
    : { y: -0.5, transition: defaultSpringTransition };

  return (
    <motion.button
      whileHover={!disabled && !isLoading ? hoverMotion : undefined}
      whileTap={!disabled && !isLoading ? tapMotion : undefined}
      transition={shouldReduceMotion ? reducedMotionTransition : instantPressTransition}
      disabled={disabled || isLoading}
      className={`relative inline-flex select-none items-center justify-center font-sans transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pine focus-visible:ring-offset-2 focus-visible:ring-offset-cream disabled:pointer-events-none disabled:opacity-50 disabled:grayscale ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...(props as React.ComponentPropsWithoutRef<typeof motion.button>)}
    >
      {/* Top subtle highlight rim evoking physical beveled edge on primary */}
      {variant === 'primary' && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-[inherit] bg-white/25"
        />
      )}

      {/* Loading Spinner */}
      {isLoading ? (
        <svg
          className="h-4 w-4 animate-spin text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        <>
          {leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>}
          <span>{children}</span>
          {rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
        </>
      )}
    </motion.button>
  );
};
