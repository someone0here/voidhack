/**
 * RiskDesk — Ranked Entity Risk Scoring
 *
 * Fetches GET /cases/{case_id}/risk and renders entities as ranked "case folders"
 * with large stamped risk scores, masked identifiers, and always-visible
 * recommendation text (never hidden behind a click). Sort/filter controls are
 * styled as physical toggle tabs and index switches — no HTML <select>.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { FolderCard, StampBadge, StitchedDivider } from '../../design-system';
import {
  defaultSpringTransition,
  reducedMotionTransition,
} from '../../design-system/motion';
import { apiClient, RankedEntityRiskRead } from '../../lib/api-client';

// ── Types ──────────────────────────────────────────────────────────────────────

type SortKey = 'score' | 'type';
type EntityTypeFilter = string;

interface RiskDeskProps {
  caseId: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const ENTITY_ICONS: Record<string, string> = {
  phone: '📞',
  account: '🏦',
  device_imei: '📱',
  ip_address: '🌐',
  mac_address: '💻',
  email_address: '✉️',
};

const REASON_PLAIN: Record<string, string> = {
  HIGH_VELOCITY_ROUTING:
    'Rapid fund layering connecting to 3+ distinct entities within a 10-minute window',
  SIM_SWITCHING_PATTERN:
    'Physical handset cycling through 3+ distinct phone numbers within 24 hours',
  SHARED_DEVICE_FLAGGED_PEER:
    'Shared hardware (IMEI/MAC) with an already flagged suspect entity (score ≥ 40)',
  MULE_ACCOUNT_STRUCTURE:
    'Transaction pattern consistent with mule layering — small inbound bursts, rapid outbound transfers',
  FLAGGED_IP_NEXUS: 'IP address overlaps with a cluster of high-risk entities',
  CROSS_CASE_ENTITY:
    'Entity appears across multiple cases — indicates organised network activity',
  SUSPICIOUS_UPI_CHURN:
    'UPI handle linked to abnormal churn: high volume of small-value transactions over short span',
};

function plainLanguage(code: string): string {
  return REASON_PLAIN[code] ?? code.replace(/_/g, ' ').toLowerCase();
}

function maskValue(value: string): string {
  if (value.length <= 4) return value;
  const suffix = value.slice(-4);
  const prefix = value.slice(0, Math.min(3, value.length - 4));
  const middle = '•'.repeat(Math.max(0, value.length - prefix.length - 4));
  return `${prefix}${middle}${suffix}`;
}

function scoreVariant(score: number): 'terracotta' | 'pine' | 'sage' {
  if (score >= 60) return 'terracotta';
  if (score >= 40) return 'pine';
  return 'sage';
}

function scoreTierLabel(score: number): string {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
}

// ── Loading Skeleton ───────────────────────────────────────────────────────────

const RiskSkeleton: React.FC = () => (
  <FolderCard
    tabTitle="CASE // RISK"
    tabPosition="left"
    tabBadge="TAB 03"
    classification="EXPLAINABLE HEURISTIC FRAUD SCORING & TARGET PRIORITIZATION"
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
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="flex items-start gap-4 rounded-xl border border-pine/15 bg-cream/60 p-4"
          >
            <div className="h-20 w-20 shrink-0 animate-pulse rounded-full bg-pine/10" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-1/3 animate-pulse rounded bg-pine/10" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-pine/5" />
              <div className="h-3 w-3/4 animate-pulse rounded bg-pine/5" />
              <div className="h-3 w-2/3 animate-pulse rounded bg-pine/5" />
            </div>
          </div>
        ))}
      </div>
    </div>
  </FolderCard>
);

// ── Empty State ────────────────────────────────────────────────────────────────

const RiskEmptyState: React.FC = () => (
  <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-pine/25 bg-khaki-light/30 py-14 text-center">
    <div className="flex h-14 w-14 items-center justify-center rounded-full border border-pine/20 bg-cream font-mono text-2xl shadow-paper-sm">
      📋
    </div>
    <div>
      <p className="font-mono text-xs font-bold uppercase tracking-widest text-pine/50">
        No risk scores computed yet
      </p>
      <p className="mt-1 font-mono text-[10px] text-pine/40">
        Upload evidence files in the Intake tab to begin analysis
      </p>
    </div>
  </div>
);

// ── Sort/Filter Controls ────────────────────────────────────────────────────────

const SortTabs: React.FC<{
  value: SortKey;
  onChange: (v: SortKey) => void;
}> = ({ value, onChange }) => {
  const options: { key: SortKey; label: string }[] = [
    { key: 'score', label: 'By Risk Score' },
    { key: 'type', label: 'By Entity Type' },
  ];
  return (
    <div className="relative flex rounded-lg border border-pine/20 bg-khaki-light/50 p-0.5">
      {options.map((opt) => (
        <button
          key={opt.key}
          onClick={() => onChange(opt.key)}
          className="relative z-10 flex-1 rounded-md px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider transition-colors"
          style={{
            color: value === opt.key ? '#2E3A2F' : '#2E3A2F80',
          }}
        >
          {value === opt.key && (
            <motion.div
              layoutId="sort-indicator"
              className="absolute inset-0 rounded-md border border-pine/20 bg-cream shadow-paper-sm"
              style={{ zIndex: -1 }}
              transition={defaultSpringTransition}
            />
          )}
          {opt.label}
        </button>
      ))}
    </div>
  );
};

const TypeFilterPills: React.FC<{
  types: string[];
  active: EntityTypeFilter;
  onChange: (t: EntityTypeFilter) => void;
}> = ({ types, active, onChange }) => {
  const allOptions = ['all', ...types];
  return (
    <div className="flex flex-wrap gap-1.5">
      {allOptions.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className="relative rounded-full border px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-wider transition-colors"
          style={{
            borderColor: active === t ? '#2E3A2F' : '#2E3A2F33',
            color: active === t ? '#2E3A2F' : '#2E3A2F80',
            backgroundColor: active === t ? '#D9C9B2' : 'transparent',
          }}
        >
          {t === 'all' ? 'All Types' : `${ENTITY_ICONS[t] ?? ''} ${t.replace(/_/g, ' ')}`}
        </button>
      ))}
    </div>
  );
};

// ── Entity Risk Row ────────────────────────────────────────────────────────────

const EntityRiskCard: React.FC<{
  entity: RankedEntityRiskRead;
  rank: number;
}> = ({ entity, rank }) => {
  const shouldReduceMotion = useReducedMotion();
  const [expanded, setExpanded] = useState(false);
  const variant = scoreVariant(entity.score);
  const tierLabel = scoreTierLabel(entity.score);
  const icon = ENTITY_ICONS[entity.entity_type] ?? '🔍';
  const masked = maskValue(entity.value);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition}
      className="overflow-hidden rounded-xl border border-pine/20 bg-cream/90 shadow-paper-sm"
    >
      {/* Main row */}
      <div className="flex items-start gap-4 p-4">
        {/* Rank + Score stamp */}
        <div className="flex shrink-0 flex-col items-center gap-1">
          <span className="font-mono text-[10px] font-bold text-pine/40">#{rank}</span>
          <StampBadge
            label={String(entity.score)}
            variant={variant}
            shape="circular"
            rotation={rank % 2 === 0 ? -2 : 2}
            subtext={tierLabel}
          />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          {/* Entity header */}
          <div className="flex items-center gap-2">
            <span className="text-base" aria-hidden="true">
              {icon}
            </span>
            <div>
              <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-pine/55">
                {entity.entity_type.replace(/_/g, ' ')}
              </p>
              <p className="font-mono text-sm font-semibold text-pine">{masked}</p>
            </div>
          </div>

          {/* ── RECOMMENDATION — always visible, never hidden ── */}
          <div className="mt-2 rounded-lg border border-pine/15 bg-khaki-light/60 px-3 py-2">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-widest text-pine/55">
              ⚖ Investigator Guidance
            </p>
            <p className="mt-0.5 font-mono text-[11px] leading-snug text-pine/80">
              {entity.recommendation}
            </p>
          </div>

          {/* Reason codes — expandable detail */}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-sage-dark hover:underline"
            aria-expanded={expanded}
          >
            <motion.span
              animate={{ rotate: expanded ? 90 : 0 }}
              transition={
                shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition
              }
              className="inline-block"
            >
              ▶
            </motion.span>
            {entity.reason_codes.length} reason
            {entity.reason_codes.length !== 1 ? 's' : ''} triggered
          </button>

          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={
                  shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition
                }
                className="overflow-hidden"
              >
                <div className="mt-2 space-y-1.5 border-t border-pine/10 pt-2">
                  {entity.reason_codes.map((code, i) => (
                    <div
                      key={code}
                      className="flex items-start gap-2 rounded-lg border border-pine/10 bg-khaki-light/30 px-3 py-2"
                    >
                      <span className="mt-0.5 font-mono text-[10px] font-bold text-terracotta-dark">
                        [{i + 1}]
                      </span>
                      <div>
                        <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-pine/70">
                          {code}
                        </p>
                        <p className="mt-0.5 font-mono text-[10px] leading-snug text-pine/60">
                          {entity.reason_descriptions[i] ?? plainLanguage(code)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};

// ── Main Component ─────────────────────────────────────────────────────────────

export const RiskDesk: React.FC<RiskDeskProps> = ({ caseId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entities, setEntities] = useState<RankedEntityRiskRead[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [typeFilter, setTypeFilter] = useState<EntityTypeFilter>('all');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.cases
      .getRiskScores(caseId)
      .then((data) => {
        if (!cancelled) setEntities(data);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : 'Failed to load risk data');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const entityTypes = useMemo(
    () => [...new Set(entities.map((e) => e.entity_type))],
    [entities],
  );

  const filtered = useMemo(() => {
    let list = [...entities];
    if (typeFilter !== 'all') list = list.filter((e) => e.entity_type === typeFilter);
    if (sortKey === 'score') list.sort((a, b) => b.score - a.score);
    else list.sort((a, b) => a.entity_type.localeCompare(b.entity_type));
    return list;
  }, [entities, typeFilter, sortKey]);

  if (loading) return <RiskSkeleton />;

  if (error) {
    return (
      <FolderCard
        tabTitle={`CASE ${caseId} // RISK`}
        tabPosition="left"
        tabBadge="TAB 03"
        classification="EXPLAINABLE HEURISTIC FRAUD SCORING & TARGET PRIORITIZATION"
        elevation="raised"
      >
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <StampBadge label="LOAD ERROR" variant="terracotta" rotation={2} />
          <p className="mt-4 font-mono text-xs text-pine/60">{error}</p>
        </div>
      </FolderCard>
    );
  }

  return (
    <FolderCard
      tabTitle={`CASE ${caseId} // RISK`}
      tabPosition="left"
      tabBadge="TAB 03"
      classification="EXPLAINABLE HEURISTIC FRAUD SCORING & TARGET PRIORITIZATION"
      elevation="raised"
    >
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="type-display-lg text-pine">Operational Risk Desk</h2>
            <p className="type-body mt-1 text-pine/80">
              Deterministic, human-auditable risk scoring (0–100) powered by explainable
              forensic heuristics — not black-box machine learning.
            </p>
          </div>
          <StampBadge
            label="EVALUATION DESK"
            variant="terracotta"
            rotation={-1}
            subtext={entities.length > 0 ? `${entities.length} ENTITIES` : 'EMPTY'}
          />
        </div>

        <StitchedDivider orientation="horizontal" label="PRIORITY TARGET RANKING" />

        {/* Sort + Filter Controls */}
        {entities.length > 0 && (
          <div className="flex flex-col gap-3 rounded-xl border border-pine/15 bg-khaki-light/40 p-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-pine/55">
                Sort:
              </span>
              <SortTabs value={sortKey} onChange={setSortKey} />
            </div>
            {entityTypes.length > 1 && (
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-pine/55">
                  Filter:
                </span>
                <TypeFilterPills
                  types={entityTypes}
                  active={typeFilter}
                  onChange={setTypeFilter}
                />
              </div>
            )}
          </div>
        )}

        {/* Ranked entity list */}
        {filtered.length === 0 ? (
          <RiskEmptyState />
        ) : (
          <motion.div layout className="space-y-3">
            <AnimatePresence mode="popLayout">
              {filtered.map((entity, i) => (
                <EntityRiskCard key={entity.entity_id} entity={entity} rank={i + 1} />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </FolderCard>
  );
};
