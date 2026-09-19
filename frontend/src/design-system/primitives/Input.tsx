import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /**
   * Field label displayed above the pressed-paper surface
   */
  label?: string;
  /**
   * Secondary helper note or format hint
   */
  helperText?: string;
  /**
   * Error message if validation failed
   */
  error?: string;
  /**
   * Use typewritten monospace font (ideal for hashes, phone numbers, UPI IDs, CDR records)
   * @default false
   */
  mono?: boolean;
  /**
   * Left icon or badge
   */
  leftIcon?: React.ReactNode;
  /**
   * Right action or status indicator
   */
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      helperText,
      error,
      mono = false,
      leftIcon,
      rightIcon,
      id,
      className = '',
      disabled,
      ...props
    },
    ref,
  ) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="flex w-full flex-col gap-1.5">
        {label && (
          <div className="flex items-baseline justify-between">
            <label
              htmlFor={inputId}
              className="font-mono text-xs font-semibold uppercase tracking-wider text-pine-light"
            >
              {label}
            </label>
            {helperText && !error && (
              <span className="font-mono text-[11px] text-pine/60">{helperText}</span>
            )}
          </div>
        )}

        <div
          className={`relative flex items-center rounded-lg border transition-all duration-150 ${
            error
              ? 'border-terracotta/70 bg-terracotta/5 shadow-[inset_0_2px_4px_rgba(201,111,79,0.15)]'
              : 'border-pine/20 bg-cream/70 shadow-[inset_0_2px_4px_rgba(46,58,47,0.10),inset_0_1px_2px_rgba(46,58,47,0.06),0_1px_0_rgba(255,255,255,0.7)] focus-within:border-pine/60 focus-within:bg-white/90 focus-within:shadow-[inset_0_2px_5px_rgba(46,58,47,0.16),0_0_0_2px_rgba(46,58,47,0.25)] hover:border-pine/35'
          } ${disabled ? 'cursor-not-allowed bg-khaki/30 opacity-50' : ''}`}
        >
          {leftIcon && (
            <span className="pointer-events-none flex items-center pl-3 text-pine/60">
              {leftIcon}
            </span>
          )}

          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            className={`w-full bg-transparent px-3 py-2 text-sm text-pine placeholder-pine/40 outline-none disabled:cursor-not-allowed ${mono ? 'font-mono text-xs tracking-tight' : 'font-sans'} ${leftIcon ? 'pl-2' : ''} ${rightIcon ? 'pr-2' : ''} ${className}`}
            {...props}
          />

          {rightIcon && (
            <span className="flex items-center pr-3 text-pine/60">{rightIcon}</span>
          )}
        </div>

        {error && (
          <p
            role="alert"
            className="flex items-center gap-1 font-mono text-xs font-semibold text-terracotta-dark"
          >
            <span aria-hidden="true">⚠</span>
            {error}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';
