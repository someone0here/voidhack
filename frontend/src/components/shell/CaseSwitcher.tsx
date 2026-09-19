import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useCase } from '../../context/useCase';
import {
  Button,
  Input,
  appleToFramerSpring,
  reducedMotionTransition,
} from '../../design-system';

interface CaseSwitcherProps {
  onCaseSelected?: (caseId: number) => void;
}

export const CaseSwitcher: React.FC<CaseSwitcherProps> = ({ onCaseSelected }) => {
  const { cases, activeCase, createCase, selectCase, isLoading } = useCase();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newCaseName, setNewCaseName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();
  const spring = appleToFramerSpring({ damping: 1.0, response: 0.3 });

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsCreating(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  const handleSelect = (caseId: number) => {
    selectCase(caseId);
    setIsOpen(false);
    if (onCaseSelected) {
      onCaseSelected(caseId);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newCaseName.trim();
    if (!trimmed) {
      setError('Please provide a case identifier');
      return;
    }
    setError(null);
    try {
      const created = await createCase(trimmed);
      setNewCaseName('');
      setIsCreating(false);
      setIsOpen(false);
      if (onCaseSelected) {
        onCaseSelected(created.id);
      }
    } catch {
      setError('Failed to create case');
    }
  };

  return (
    <div ref={containerRef} className="relative inline-block text-left">
      {/* Trigger Button inside GlassToolbar */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="group flex items-center gap-2.5 rounded-lg border border-pine/20 bg-khaki-light/80 px-3 py-1.5 shadow-paper-sm transition-all hover:border-pine/40 hover:bg-khaki hover:shadow-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pine"
        aria-expanded={isOpen}
      >
        <span className="flex h-5 w-5 items-center justify-center rounded bg-pine/10 font-mono text-xs font-bold text-pine">
          📂
        </span>
        <div className="flex flex-col text-left">
          <span className="font-mono text-[9px] uppercase tracking-wider text-pine/60">
            Active Case Dossier
          </span>
          <span className="font-mono text-xs font-bold text-pine">
            {activeCase ? activeCase.name : 'No Case Selected'}
          </span>
        </div>
        <svg
          className={`h-4 w-4 text-pine/60 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={shouldReduceMotion ? reducedMotionTransition : spring}
            className="absolute left-0 z-50 mt-2 w-72 origin-top-left rounded-xl border border-pine/20 bg-cream p-2 shadow-paper-raised backdrop-blur-md"
            style={{
              backgroundColor: 'rgba(248, 246, 238, 0.97)',
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-pine/10 px-2.5 py-1.5">
              <span className="font-mono text-[10px] uppercase tracking-widest text-pine/60">
                Investigation Cases
              </span>
              <span className="font-mono text-[10px] text-pine/50">
                {cases.length} {cases.length === 1 ? 'file' : 'files'}
              </span>
            </div>

            {/* Case List */}
            <div className="max-h-56 overflow-y-auto py-1">
              {cases.length === 0 ? (
                <div className="px-3 py-4 text-center font-mono text-xs text-pine/60">
                  No existing cases found.
                </div>
              ) : (
                cases.map((c) => {
                  const isSelected = activeCase?.id === c.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => handleSelect(c.id)}
                      className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs transition-colors ${
                        isSelected
                          ? 'bg-khaki font-semibold text-pine shadow-paper-sm'
                          : 'text-pine/80 hover:bg-khaki/50'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="font-mono text-xs text-pine/60">#{c.id}</span>
                        <span className="truncate font-mono font-medium">{c.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide ${
                            c.status === 'active'
                              ? 'bg-sage/20 text-sage-dark'
                              : 'bg-pine/10 text-pine/60'
                          }`}
                        >
                          {c.status}
                        </span>
                        {isSelected && <span className="text-xs text-pine">✓</span>}
                      </div>
                    </button>
                  );
                })
              )}
            </div>

            {/* Create New Case Section */}
            <div className="mt-1 border-t border-pine/10 pt-2">
              {!isCreating ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsCreating(true)}
                  className="w-full justify-start text-left text-xs text-pine hover:bg-khaki/50"
                  leftIcon={<span>＋</span>}
                >
                  Open New Case File...
                </Button>
              ) : (
                <form
                  onSubmit={(e) => {
                    void handleCreateSubmit(e);
                  }}
                  className="flex flex-col gap-2 p-1.5"
                >
                  <Input
                    placeholder="New case name..."
                    value={newCaseName}
                    onChange={(e) => setNewCaseName(e.target.value)}
                    error={error || undefined}
                    mono
                    autoFocus
                    disabled={isLoading}
                  />
                  <div className="flex justify-end gap-1.5">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setIsCreating(false);
                        setError(null);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="primary"
                      size="sm"
                      isLoading={isLoading}
                    >
                      Create
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
