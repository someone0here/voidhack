import React from 'react';

export interface StitchedDividerProps {
  /**
   * Orientation of the divider
   * @default 'horizontal'
   */
  orientation?: 'horizontal' | 'vertical';
  /**
   * Optional centered label / section mark
   */
  label?: string;
  /**
   * Stitch color tone
   * @default 'sage'
   */
  stitchColor?: 'sage' | 'pine' | 'khaki';
  className?: string;
}

export const StitchedDivider: React.FC<StitchedDividerProps> = ({
  orientation = 'horizontal',
  label,
  stitchColor = 'sage',
  className = '',
}) => {
  const colorMap = {
    sage: 'border-sage/70 text-sage-dark',
    pine: 'border-pine/60 text-pine',
    khaki: 'border-khaki-dark text-pine/70',
  };

  if (orientation === 'vertical') {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={`relative inline-flex h-full flex-col items-center justify-center px-2 py-1 ${className}`}
      >
        {/* Double dashed stitch lines */}
        <div className="relative flex h-full items-center gap-1">
          <div
            className={`h-full w-0 border-r-2 border-dashed ${colorMap[stitchColor]} shadow-[1px_0_0_rgba(255,255,255,0.4)]`}
            style={{ strokeDasharray: '4 4' }}
          />
          <div
            className={`h-full w-0 border-r-2 border-dashed ${colorMap[stitchColor]} opacity-70`}
            style={{ strokeDasharray: '4 4' }}
          />
        </div>
        {label && (
          <span className="my-2 rotate-90 whitespace-nowrap font-mono text-[10px] font-bold uppercase tracking-widest text-pine/75">
            {label}
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      className={`relative my-4 flex w-full items-center ${className}`}
    >
      {/* Left Stitch Line (Double thread) */}
      <div className="relative flex flex-1 flex-col gap-0.5">
        <div
          className={`w-full border-b-2 border-dashed ${colorMap[stitchColor]} shadow-[0_1px_0_rgba(255,255,255,0.5)]`}
          style={{ strokeDasharray: '5 4' }}
        />
        <div
          className={`w-full border-b-2 border-dashed ${colorMap[stitchColor]} opacity-60`}
          style={{ strokeDasharray: '5 4' }}
        />
      </div>

      {/* Center Label (if provided) */}
      {label && (
        <div className="relative mx-3 shrink-0 rounded-full border border-pine/20 bg-cream-light px-3 py-1 shadow-sm">
          <span className="font-mono text-[11px] font-bold uppercase tracking-widest text-pine">
            {label}
          </span>
        </div>
      )}

      {/* Right Stitch Line (Double thread) */}
      <div className="relative flex flex-1 flex-col gap-0.5">
        <div
          className={`w-full border-b-2 border-dashed ${colorMap[stitchColor]} shadow-[0_1px_0_rgba(255,255,255,0.5)]`}
          style={{ strokeDasharray: '5 4' }}
        />
        <div
          className={`w-full border-b-2 border-dashed ${colorMap[stitchColor]} opacity-60`}
          style={{ strokeDasharray: '5 4' }}
        />
      </div>
    </div>
  );
};
