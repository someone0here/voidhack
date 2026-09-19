/**
 * AppToaster — the app's single toast surface (wraps `sonner`).
 *
 * Styled to match the field-dossier palette rather than sonner's defaults:
 * cream/khaki card surface with a hairline pine border and the same
 * `shadow-paper` used by FolderCard, terracotta for errors, sage for
 * success. Mounted once in `App.tsx`; every call site uses the helpers in
 * `lib/toast.ts` rather than importing `sonner` directly.
 */

import React from 'react';
import { Toaster as SonnerToaster } from 'sonner';

export const AppToaster: React.FC = () => (
  <SonnerToaster
    position="bottom-right"
    expand={false}
    gap={10}
    toastOptions={{
      unstyled: true,
      classNames: {
        toast:
          'flex w-full items-start gap-3 rounded-lg border border-pine/20 bg-cream px-4 py-3 shadow-paper-raised font-sans',
        title: 'type-body font-semibold text-pine',
        description: 'mt-0.5 font-mono text-[11px] text-pine/60',
        actionButton:
          'rounded-md bg-pine px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider text-cream',
        cancelButton:
          'rounded-md bg-khaki-dark/40 px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider text-pine',
        closeButton: 'border-pine/20 bg-cream text-pine/50 hover:text-pine',
        error: 'border-terracotta/40 bg-terracotta/10',
        success: 'border-sage/40 bg-sage/10',
        warning: 'border-dossier-amber/40 bg-dossier-amber/10',
        info: 'border-pine/20 bg-khaki-light/60',
      },
    }}
  />
);
