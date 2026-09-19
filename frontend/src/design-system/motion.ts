/**
 * Apple Fluid Motion Tokens & Spring Physics
 *
 * Implements Apple fluid-interaction specifications:
 * - Default UI spring: critically damped, no overshoot (damping 1.0, response 0.35)
 * - Momentum/flick interactions: slight bounce (damping 0.8, response 0.35)
 * - Tactile pointer-down depression: instant scale 0.97 (~100ms)
 * - Draggable rubber-band resistance formula:
 *     offset = (overshoot * dimension * 0.55) / (dimension + 0.55 * abs(overshoot))
 * - Reduced motion fallbacks: simple opacity cross-fade, zero overshoot
 */

import type { Transition, TargetAndTransition } from 'framer-motion';

/**
 * Raw Apple motion parameter representation
 */
export interface AppleSpringConfig {
  damping: number;
  response: number;
}

export const APPLE_MOTION_SPECS = {
  defaultSpring: { damping: 1.0, response: 0.35 } as AppleSpringConfig,
  momentumSpring: { damping: 0.8, response: 0.35 } as AppleSpringConfig,
  pressFeedback: { scale: 0.97, duration: 0.1 },
} as const;

/**
 * Converts Apple fluid motion (damping ratio zeta, response tau) into
 * Framer Motion spring parameters (stiffness, damping, mass=1).
 *
 * omega0 = 2 * PI / tau
 * stiffness = omega0^2
 * damping = 2 * zeta * omega0
 */
export function appleToFramerSpring(config: AppleSpringConfig): Transition {
  const omega0 = (2 * Math.PI) / config.response;
  const stiffness = Math.round(omega0 * omega0);
  const damping = Number((2 * config.damping * omega0).toFixed(1));

  return {
    type: 'spring',
    stiffness,
    damping,
    mass: 1,
  };
}

/**
 * Default UI spring (critically damped, no overshoot).
 * Ideal for panels, drawers, modals, menu reveals, and folder card expansion.
 */
export const defaultSpringTransition: Transition = appleToFramerSpring(
  APPLE_MOTION_SPECS.defaultSpring,
);

/**
 * Momentum / flick interaction spring (slight bounce: damping 0.8, response 0.35).
 * Ideal for drag-released cards, movable dossier notes, and graph nodes.
 */
export const momentumSpringTransition: Transition = appleToFramerSpring(
  APPLE_MOTION_SPECS.momentumSpring,
);

/**
 * Instant pointer-down feedback transition (~100ms, scale 0.97).
 */
export const instantPressTransition: Transition = {
  duration: 0.1,
  ease: [0.25, 1, 0.5, 1],
};

/**
 * Reduced-motion transition:
 * Replaces springs, positional slides, and bounces with pure opacity cross-fade.
 */
export const reducedMotionTransition: Transition = {
  type: 'tween',
  duration: 0.15,
  ease: 'linear',
};

/**
 * Apple rubber-band resistance formula for draggable-with-bounds elements:
 * f(x) = (x * d * 0.55) / (d + 0.55 * |x|)
 *
 * @param overshoot Distance past the boundary in pixels
 * @param dimension Total dimension of the draggable area / container in pixels
 * @returns Dampened resistance offset in pixels
 */
export function rubberBandClamp(overshoot: number, dimension: number): number {
  if (overshoot === 0 || dimension <= 0) return 0;
  const absOvershoot = Math.abs(overshoot);
  const dampened = (overshoot * dimension * 0.55) / (dimension + 0.55 * absOvershoot);
  return dampened;
}

/**
 * Calculate bounded position with Apple rubber-band resistance
 */
export function calculateRubberBandPosition(
  currentPos: number,
  minBound: number,
  maxBound: number,
  dimension: number,
): number {
  if (currentPos < minBound) {
    const overshoot = currentPos - minBound;
    return minBound + rubberBandClamp(overshoot, dimension);
  }
  if (currentPos > maxBound) {
    const overshoot = currentPos - maxBound;
    return maxBound + rubberBandClamp(overshoot, dimension);
  }
  return currentPos;
}

/**
 * Helper to select motion transition respecting reduced-motion preference
 */
export function resolveTransition(
  prefersReducedMotion: boolean,
  activeTransition: Transition = defaultSpringTransition,
): Transition {
  return prefersReducedMotion ? reducedMotionTransition : activeTransition;
}

/**
 * Compositor-friendly interactive button variants
 */
export function getButtonMotionVariants(prefersReducedMotion: boolean): {
  initial: TargetAndTransition;
  hover: TargetAndTransition;
  tap: TargetAndTransition;
} {
  if (prefersReducedMotion) {
    return {
      initial: { opacity: 1 },
      hover: { opacity: 0.92 },
      tap: { opacity: 0.8 },
    };
  }

  return {
    initial: { scale: 1, opacity: 1 },
    hover: { scale: 1.015, transition: defaultSpringTransition },
    tap: {
      scale: APPLE_MOTION_SPECS.pressFeedback.scale,
      transition: instantPressTransition,
    },
  };
}
