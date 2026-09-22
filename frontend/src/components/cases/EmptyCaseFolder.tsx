import React, { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  FolderCard,
  StampBadge,
  Button,
  Input,
  StitchedDivider,
  appleToFramerSpring,
  reducedMotionTransition,
} from '../../design-system';

interface EmptyCaseFolderProps {
  onCreateCase: (caseName: string) => Promise<void>;
  isLoading?: boolean;
}

export const EmptyCaseFolder: React.FC<EmptyCaseFolderProps> = ({
  onCreateCase,
  isLoading = false,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const [isOpen, setIsOpen] = useState(false);
  const [caseName, setCaseName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Default suggested identifier
  const defaultSuggestedName = `CASE-${new Date().getFullYear()}-001`;

  const springTransition = appleToFramerSpring({ damping: 1.0, response: 0.35 });

  const handleOpenFolder = () => {
    if (!isOpen) {
      setIsOpen(true);
      if (!caseName) {
        setCaseName(defaultSuggestedName);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const finalName = (caseName || defaultSuggestedName).trim();
    if (!finalName) {
      setValidationError('Case identifier cannot be empty');
      return;
    }
    setValidationError(null);
    setIsSubmitting(true);
    try {
      await onCreateCase(finalName);
    } catch {
      setValidationError('Failed to initialize case. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[70vh] items-center justify-center p-4">
      <motion.div
        layout
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={shouldReduceMotion ? reducedMotionTransition : springTransition}
        className="relative w-full max-w-lg"
      >
        {/* Closed / Opening Folder Envelope Container */}
        <motion.div
          animate={isOpen ? { scale: 1.02, rotate: 0 } : { scale: 1, rotate: 0 }}
          whileHover={!isOpen ? { scale: 1.015, y: -2 } : undefined}
          whileTap={
            !isOpen
              ? shouldReduceMotion
                ? { opacity: 0.9 }
                : { scale: 0.995 }
              : undefined
          }
          transition={shouldReduceMotion ? reducedMotionTransition : springTransition}
          onClick={!isOpen ? handleOpenFolder : undefined}
          role={!isOpen ? 'button' : undefined}
          tabIndex={!isOpen ? 0 : undefined}
          onKeyDown={
            !isOpen
              ? (e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleOpenFolder();
                  }
                }
              : undefined
          }
          className={`relative cursor-pointer transition-shadow ${!isOpen ? 'cursor-pointer rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terracotta focus-visible:ring-offset-2 focus-visible:ring-offset-cream' : 'cursor-default'}`}
        >
          <FolderCard
            tabTitle="EVIDENTIARY ARCHIVE"
            tabPosition="center"
            tabBadge="UNASSIGNED"
            classification="DIRECTORATE OF FORENSIC INTELLIGENCE // CASE INTAKE"
            elevation={isOpen ? 'floating' : 'raised'}
          >
            {/* Top Closed Flap Skeuomorphic Simulation */}
            <div className="relative mb-4 flex flex-col items-center justify-center">
              {/* Flap flap shadow & crease */}
              <motion.div
                animate={
                  isOpen
                    ? {
                        rotateX: -25,
                        y: -10,
                        opacity: 0.15,
                        height: 0,
                      }
                    : {
                        rotateX: 0,
                        y: 0,
                        opacity: 1,
                        height: 'auto',
                      }
                }
                transition={
                  shouldReduceMotion ? reducedMotionTransition : springTransition
                }
                style={{ transformOrigin: 'top center' }}
                className="w-full overflow-hidden"
              >
                <div className="relative mx-auto flex w-4/5 items-center justify-between rounded-b-xl border-x border-b border-pine/25 bg-khaki-dark/40 px-6 py-4 shadow-paper-sm">
                  {/* Brass eyelet & string washer tie */}
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-pine/40 bg-khaki font-mono text-[9px] font-bold text-pine shadow-inner">
                      ◎
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-widest text-pine/60">
                      SEALED DOSSIER ENVELOPE
                    </span>
                  </div>
                  <div className="h-0.5 w-16 border-t border-dashed border-terracotta/60" />
                </div>
              </motion.div>

              <div className="mt-4 flex w-full items-start justify-between">
                <div>
                  <h2 className="type-display-md text-pine">
                    {isOpen ? 'Initialize Investigation Case' : 'No Active Case File'}
                  </h2>
                  <p className="type-body-sm mt-1 text-pine/70">
                    {isOpen
                      ? 'Assign a formal case identifier to begin multi-source evidentiary correlation.'
                      : 'The evidentiary desk is clear. Open a new case file to start ingestion and linkage.'}
                  </p>
                </div>
                <StampBadge
                  label={isOpen ? 'OPEN' : 'ARCHIVED'}
                  variant={isOpen ? 'sage' : 'terracotta'}
                  rotation={isOpen ? 2 : -4}
                />
              </div>
            </div>

            <StitchedDivider orientation="horizontal" />

            {/* Folder Content: Either Closed Prompt or Open Creation Form */}
            {!isOpen ? (
              <div className="mt-6 flex flex-col items-center justify-center gap-4 py-6 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-pine/20 bg-cream-dark/50 shadow-paper-inset">
                  <span className="text-3xl" aria-hidden="true">
                    📁
                  </span>
                </div>
                <div className="max-w-xs">
                  <p className="font-mono text-xs font-semibold uppercase tracking-wider text-pine/80">
                    Evidentiary Desk Awaiting Case File
                  </p>
                  <p className="type-data-xs mt-1 text-pine/60">
                    Click anywhere on this folder to break seal and initialize.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleOpenFolder}
                  isLoading={isLoading}
                  className="mt-2"
                >
                  ⚡ Open a New Case File
                </Button>
              </div>
            ) : (
              <motion.form
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={
                  shouldReduceMotion ? reducedMotionTransition : springTransition
                }
                onSubmit={(e) => {
                  void handleSubmit(e);
                }}
                className="mt-4 flex flex-col gap-4"
              >
                <Input
                  label="Case Reference / Identifier"
                  placeholder="e.g. CASE-2026-MULE-81"
                  helperText="Format: CASE-YYYY-REF"
                  mono
                  value={caseName}
                  onChange={(e) => setCaseName(e.target.value)}
                  error={validationError || undefined}
                  autoFocus
                  disabled={isSubmitting || isLoading}
                />

                <div className="rounded-lg border border-pine/15 bg-cream/70 p-3">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-pine/60">
                    Evidentiary Pipeline Ready
                  </span>
                  <p className="font-mono text-xs text-pine/80">
                    ✓ Section 63 BSA cryptographic custody chain enabled
                  </p>
                  <p className="font-mono text-xs text-pine/80">
                    ✓ Cross-source correlation & heuristic risk engine armed
                  </p>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsOpen(false)}
                    disabled={isSubmitting || isLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="md"
                    isLoading={isSubmitting || isLoading}
                  >
                    Create Case Dossier →
                  </Button>
                </div>
              </motion.form>
            )}
          </FolderCard>
        </motion.div>
      </motion.div>
    </div>
  );
};
