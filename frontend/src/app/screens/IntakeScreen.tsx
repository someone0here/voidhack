/**
 * IntakeScreen — Evidence Intake & Forensic Parsing
 *
 * Physical inbox-tray drop-zone: khaki tray shape, inset shadow, spring-opens
 * on dragover (damping 0.8 momentum spring). Each uploaded file appears as a
 * FolderCard document chip with paperclip icon, detected source_type, and an
 * ingestion status StampBadge. Failed ingestions show the backend IngestionError
 * detail verbatim — never a generic "upload failed."
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { FolderCard, StampBadge, StitchedDivider } from '../../design-system';
import {
  momentumSpringTransition,
  defaultSpringTransition,
  reducedMotionTransition,
} from '../../design-system/motion';
import { SourceType, ApiError } from '../../lib/api-client';
import { useEvidence } from '../../hooks/useEvidence';
import { notifySuccess } from '../../lib/toast';

// ── Types ─────────────────────────────────────────────────────────────────────

type IngestionStatus = 'pending' | 'uploading' | 'processed' | 'failed';

interface UploadedFile {
  id: string;
  file: File;
  sourceType: SourceType;
  status: IngestionStatus;
  errorDetail?: string;
  rowsProcessed?: number;
  entitiesCreated?: number;
}

interface IntakeScreenProps {
  caseId: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const SOURCE_TYPE_OPTIONS: { value: SourceType; label: string; icon: string }[] = [
  { value: 'cdr', label: 'CDR / IPDR', icon: '📡' },
  { value: 'ipdr', label: 'IPDR', icon: '📶' },
  { value: 'bank_upi', label: 'Bank / UPI', icon: '🏦' },
  { value: 'email', label: 'Email EML', icon: '✉️' },
  { value: 'android_log', label: 'Android Log', icon: '📱' },
];

function detectSourceType(file: File): SourceType {
  const name = file.name.toLowerCase();
  if (name.endsWith('.eml') || name.includes('email') || name.includes('mail'))
    return 'email';
  if (
    name.includes('bank') ||
    name.includes('upi') ||
    name.includes('transaction') ||
    name.includes('ledger')
  )
    return 'bank_upi';
  if (name.includes('ipdr')) return 'ipdr';
  if (
    name.includes('android') ||
    name.includes('log') ||
    name.endsWith('.txt') ||
    name.endsWith('.log')
  )
    return 'android_log';
  // Default: cdr for csv/xlsx
  return 'cdr';
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Sub-components ─────────────────────────────────────────────────────────────

/** Paperclip SVG icon */
const PaperclipIcon: React.FC<{ className?: string }> = ({ className = '' }) => (
  <svg
    className={className}
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M13.5 7.5 7 14a4.243 4.243 0 0 1-6-6l7-7a2.829 2.829 0 0 1 4 4l-7 7a1.414 1.414 0 0 1-2-2l6.5-6.5" />
  </svg>
);

/** Individual document chip for an uploaded file */
const FileChip: React.FC<{
  item: UploadedFile;
  onSourceTypeChange: (id: string, st: SourceType) => void;
}> = ({ item, onSourceTypeChange }) => {
  const shouldReduceMotion = useReducedMotion();
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  const menuContainerRef = useRef<HTMLDivElement>(null);

  // The dropdown previously had no outside-click and no Escape handler — the
  // only way to dismiss it was picking an option, and it also ignored
  // reduced-motion on its own transition (fixed below).
  useEffect(() => {
    if (!showTypeMenu) return;
    const handleOutside = (e: MouseEvent) => {
      if (
        menuContainerRef.current &&
        !menuContainerRef.current.contains(e.target as Node)
      ) {
        setShowTypeMenu(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowTypeMenu(false);
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [showTypeMenu]);

  const statusConfig: Record<
    IngestionStatus,
    { label: string; variant: 'pine' | 'sage' | 'terracotta'; rotation: number }
  > = {
    pending: { label: 'QUEUED', variant: 'pine', rotation: -2 },
    uploading: { label: 'PARSING', variant: 'pine', rotation: 1 },
    processed: { label: 'INGESTED', variant: 'sage', rotation: -3 },
    failed: { label: 'FAILED', variant: 'terracotta', rotation: 2 },
  };

  const cfg = statusConfig[item.status];
  const sourceInfo = SOURCE_TYPE_OPTIONS.find((o) => o.value === item.sourceType);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition}
      className="relative flex flex-col gap-2 rounded-lg border border-pine/20 bg-cream/90 p-3 shadow-paper-sm"
    >
      {/* Header row */}
      <div className="flex items-start gap-2">
        <PaperclipIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-pine/60" />
        <div className="min-w-0 flex-1">
          <p
            className="truncate font-mono text-xs font-semibold text-pine"
            title={item.file.name}
          >
            {item.file.name}
          </p>
          <p className="font-mono text-[10px] text-pine/50">
            {formatBytes(item.file.size)}
          </p>
        </div>
        <StampBadge
          label={cfg.label}
          variant={cfg.variant}
          shape="pill"
          rotation={cfg.rotation}
          className="shrink-0 text-[9px]"
        />
      </div>

      {/* Source type selector */}
      <div className="relative" ref={menuContainerRef}>
        <button
          onClick={() => setShowTypeMenu((v) => !v)}
          disabled={item.status === 'uploading' || item.status === 'processed'}
          aria-expanded={showTypeMenu}
          className="flex items-center gap-1.5 rounded border border-pine/20 bg-khaki-light/60 px-2 py-1 font-mono text-[10px] font-bold uppercase tracking-wider text-pine transition-colors hover:bg-khaki focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terracotta disabled:cursor-not-allowed disabled:opacity-60"
        >
          <span>{sourceInfo?.icon}</span>
          <span>{sourceInfo?.label ?? item.sourceType}</span>
          {item.status !== 'processed' && (
            <svg
              className="ml-0.5 h-2.5 w-2.5 text-pine/50"
              viewBox="0 0 10 10"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M5 7 1 3h8z" />
            </svg>
          )}
        </button>
        <AnimatePresence>
          {showTypeMenu && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={
                shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition
              }
              className="absolute left-0 top-full z-30 mt-1 min-w-[140px] rounded-lg border border-pine/20 bg-cream shadow-paper"
            >
              {SOURCE_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => {
                    onSourceTypeChange(item.id, opt.value);
                    setShowTypeMenu(false);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-pine transition-colors first:rounded-t-lg last:rounded-b-lg hover:bg-khaki-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-terracotta"
                >
                  <span>{opt.icon}</span>
                  <span>{opt.label}</span>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Uploading shimmer bar */}
      {item.status === 'uploading' && (
        <div className="h-1 w-full overflow-hidden rounded-full bg-pine/10">
          <motion.div
            className="h-full w-1/3 rounded-full bg-sage"
            animate={{ x: ['0%', '300%'] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
          />
        </div>
      )}

      {/* Success stats */}
      {item.status === 'processed' && item.rowsProcessed !== undefined && (
        <p className="font-mono text-[10px] text-sage-dark">
          ✓ {item.rowsProcessed} rows · {item.entitiesCreated ?? 0} entities extracted
        </p>
      )}

      {/* Error detail — verbatim from backend IngestionError */}
      {item.status === 'failed' && item.errorDetail && (
        <div className="bg-terracotta/8 rounded border border-terracotta/30 p-2">
          <p className="font-mono text-[10px] leading-snug text-terracotta-dark">
            ⚠ {item.errorDetail}
          </p>
        </div>
      )}
    </motion.div>
  );
};

// ── Loading Skeleton ───────────────────────────────────────────────────────────

const IntakeSkeleton: React.FC = () => (
  <FolderCard
    tabTitle="CASE // INTAKE"
    tabPosition="left"
    tabBadge="TAB 01"
    classification="EVIDENTIARY ARTIFACT INTAKE & FORENSIC PARSING"
    elevation="raised"
  >
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div className="w-2/3 space-y-2.5">
          <div className="h-7 w-3/5 animate-pulse rounded-md bg-pine/10" />
          <div className="h-4 w-4/5 animate-pulse rounded bg-pine/5" />
        </div>
        <div className="h-8 w-28 animate-pulse rounded-full border border-pine/15 bg-pine/5" />
      </div>
      <div className="h-px w-full border-b border-dashed border-pine/15" />
      {/* Tray skeleton */}
      <div className="h-48 w-full animate-pulse rounded-xl bg-pine/5" />
      {/* Chips row */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {[1, 2].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg bg-pine/5" />
        ))}
      </div>
    </div>
  </FolderCard>
);

// ── Empty State ────────────────────────────────────────────────────────────────

const TrayEmptyState: React.FC = () => (
  <div className="flex flex-col items-center py-6 text-center">
    <div className="flex h-12 w-12 items-center justify-center rounded-full border border-pine/20 bg-cream font-mono text-2xl shadow-paper-sm">
      📎
    </div>
    <p className="mt-3 font-mono text-xs font-semibold uppercase tracking-wider text-pine/50">
      No artifacts ingested yet
    </p>
    <p className="mt-1 max-w-[220px] font-mono text-[10px] text-pine/40">
      Drag files into the tray above or click to browse
    </p>
  </div>
);

// ── Main Component ─────────────────────────────────────────────────────────────

export const IntakeScreen: React.FC<IntakeScreenProps> = ({ caseId }) => {
  const shouldReduceMotion = useReducedMotion();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragOver, setIsDragOver] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const dragCounter = useRef(0);

  // Upload mutation: on success, invalidates the graph/risk/integrity/brief
  // queries for this case (see `hooks/useEvidence.ts`) so the other three
  // screens pick up new evidence automatically. The chip's own
  // pending → uploading → processed/failed lifecycle below is local,
  // optimistic UI — the chip appears the instant a file is dropped, well
  // before this mutation resolves, which matters for the "golden hour" demo.
  const evidenceMutation = useEvidence(caseId);

  // Build a stable upload function
  const uploadFile = useCallback(
    async (uploadItem: UploadedFile) => {
      setFiles((prev) =>
        prev.map((f) => (f.id === uploadItem.id ? { ...f, status: 'uploading' } : f)),
      );

      try {
        const result = await evidenceMutation.mutateAsync({
          file: uploadItem.file,
          sourceType: uploadItem.sourceType,
        });
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadItem.id
              ? {
                  ...f,
                  status: 'processed',
                  rowsProcessed: result.rows_processed,
                  entitiesCreated: result.entities_created,
                }
              : f,
          ),
        );
        notifySuccess(
          `${uploadItem.file.name} ingested`,
          `${result.rows_processed} rows · ${result.entities_created} entities extracted`,
        );
      } catch (err: unknown) {
        const detail =
          err instanceof ApiError
            ? (err.detail ?? err.message)
            : err instanceof Error
              ? err.message
              : 'Unknown error during ingestion';
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadItem.id ? { ...f, status: 'failed', errorDetail: detail } : f,
          ),
        );
      }
    },
    [evidenceMutation],
  );

  const enqueueFiles = useCallback(
    (rawFiles: FileList | File[]) => {
      const arr = Array.from(rawFiles);
      const newItems: UploadedFile[] = arr.map((file) => ({
        id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
        file,
        sourceType: detectSourceType(file),
        status: 'pending',
      }));
      setFiles((prev) => [...prev, ...newItems]);
      // Start uploads after state update
      newItems.forEach((item) => {
        void uploadFile(item);
      });
    },
    [uploadFile],
  );

  // Drag event handlers
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current++;
    if (dragCounter.current === 1) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current--;
    if (dragCounter.current === 0) setIsDragOver(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current = 0;
    setIsDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      enqueueFiles(e.dataTransfer.files);
    }
  };

  const handleSourceTypeChange = (id: string, sourceType: SourceType) => {
    setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, sourceType } : f)));
  };

  // Tray spring animation params: slightly taller + wider opening on drag-over
  const trayMotion = {
    initial: { scaleY: 1, scaleX: 1 },
    animate: isDragOver
      ? { scaleY: shouldReduceMotion ? 1 : 1.06, scaleX: shouldReduceMotion ? 1 : 1.01 }
      : { scaleY: 1, scaleX: 1 },
    transition: shouldReduceMotion ? reducedMotionTransition : momentumSpringTransition,
  };

  return (
    <FolderCard
      tabTitle={`CASE ${caseId} // INTAKE`}
      tabPosition="left"
      tabBadge="TAB 01"
      classification="EVIDENTIARY ARTIFACT INTAKE & FORENSIC PARSING"
      elevation="raised"
    >
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="type-display-lg text-pine">Evidence Intake</h2>
            <p className="type-body mt-1 text-pine/80">
              Direct ingest of heterogeneous evidentiary artifacts with real-time SHA-256
              tamper-evident custody chain hashing.
            </p>
          </div>
          <StampBadge
            label="EVIDENCE RECEPTACLE"
            variant="terracotta"
            rotation={-2}
            subtext="INTAKE DOCK"
          />
        </div>

        <StitchedDivider
          orientation="horizontal"
          label="ARTIFACT DROPZONE // DRAG TO INGEST"
        />

        {/* Physical Inbox Tray */}
        <motion.div
          {...trayMotion}
          style={{ transformOrigin: 'bottom center' }}
          className="relative"
        >
          {/* Tray outer rim — the raised physical edge */}
          <div
            className="pointer-events-none absolute inset-x-0 -bottom-2 h-3 rounded-b-xl bg-khaki-dark"
            aria-hidden="true"
          />
          <div
            className="pointer-events-none absolute inset-x-1 -bottom-1 h-2 rounded-b-xl bg-khaki-dark/70"
            aria-hidden="true"
          />

          {/* Tray surface */}
          <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Evidence intake tray — drag files here or click to browse"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
            }}
            className={[
              'relative min-h-[160px] w-full cursor-pointer overflow-hidden rounded-xl',
              'border-2 border-dashed transition-colors duration-150',
              'flex flex-col items-center justify-center gap-3 p-6',
              isDragOver
                ? 'border-sage bg-sage/10 shadow-paper-inset-focus'
                : 'border-pine/25 bg-khaki-light/40 shadow-paper-inset hover:border-pine/40',
            ].join(' ')}
          >
            {/* Paper grain on tray surface */}
            <div
              aria-hidden="true"
              className="paper-grain pointer-events-none absolute inset-0 opacity-30 mix-blend-multiply"
            />

            {/* Tray label */}
            <AnimatePresence mode="wait">
              {isDragOver ? (
                <motion.div
                  key="dragover"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={defaultSpringTransition}
                  className="flex flex-col items-center gap-2 text-center"
                >
                  <span className="text-3xl" aria-hidden="true">
                    📂
                  </span>
                  <p className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                    Release to ingest
                  </p>
                </motion.div>
              ) : (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={defaultSpringTransition}
                  className="flex flex-col items-center gap-2 text-center"
                >
                  <span className="text-3xl" aria-hidden="true">
                    📁
                  </span>
                  <div>
                    <p className="font-mono text-xs font-bold uppercase tracking-widest text-pine/70">
                      Drop evidence files here
                    </p>
                    <p className="mt-0.5 font-mono text-[10px] text-pine/45">
                      CDR · IPDR · Bank/UPI · Email EML · Android Logs
                    </p>
                  </div>
                  <div className="mt-1 rounded border border-pine/20 bg-cream/70 px-3 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-pine/60 shadow-paper-sm">
                    Click to browse files
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="sr-only"
          onChange={(e) => {
            if (e.target.files?.length) {
              enqueueFiles(e.target.files);
              e.target.value = '';
            }
          }}
          aria-hidden="true"
        />

        {/* File chips grid */}
        {files.length > 0 ? (
          <>
            <StitchedDivider
              orientation="horizontal"
              label={`INGESTED ARTIFACTS (${files.length})`}
            />
            <motion.div layout className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <AnimatePresence>
                {files.map((item) => (
                  <FileChip
                    key={item.id}
                    item={item}
                    onSourceTypeChange={handleSourceTypeChange}
                  />
                ))}
              </AnimatePresence>
            </motion.div>
          </>
        ) : (
          <TrayEmptyState />
        )}
      </div>
    </FolderCard>
  );
};

// Named export used by IntakeView
export { IntakeSkeleton };
