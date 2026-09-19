import React from 'react';

export interface GlassToolbarProps {
  /**
   * Optional title or dossier header
   */
  title?: React.ReactNode;
  /**
   * Action items on the right
   */
  actions?: React.ReactNode;
  /**
   * Secondary row or filter tabs
   */
  bottomRow?: React.ReactNode;
  /**
   * Whether to position as sticky top bar
   * @default true
   */
  sticky?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export const GlassToolbar: React.FC<GlassToolbarProps> = ({
  title,
  actions,
  bottomRow,
  sticky = true,
  className = '',
  children,
}) => {
  return (
    <header
      className={`relative z-30 w-full transition-all ${sticky ? 'sticky top-0' : ''} ${className}`}
      style={{
        // Apple warm cream translucent glass material
        backgroundColor: 'rgba(248, 246, 238, 0.78)',
        backdropFilter: 'blur(20px) saturate(160%)',
        WebkitBackdropFilter: 'blur(20px) saturate(160%)',
      }}
    >
      {/* Top subtle rim highlight */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/60"
      />

      {/* Main bar content */}
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        {title && (
          <div className="flex items-center gap-3">
            {typeof title === 'string' ? (
              <h2 className="type-display-sm font-semibold tracking-tight text-pine">
                {title}
              </h2>
            ) : (
              title
            )}
          </div>
        )}

        {children}

        {actions && <div className="flex items-center gap-2.5">{actions}</div>}
      </div>

      {bottomRow && (
        <div className="border-t border-pine/10 px-4 py-2 sm:px-6">{bottomRow}</div>
      )}

      {/* Bottom hairline divider */}
      <div
        aria-hidden="true"
        className="bg-pine/12 pointer-events-none absolute inset-x-0 bottom-0 h-px"
      />
    </header>
  );
};
