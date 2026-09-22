/**
 * BriefViewer — Printed Document Preview & PDF Export
 *
 * Fetches GET /cases/{case_id}/brief.json and GET /cases/{case_id}/integrity
 * in parallel. Renders the brief as a styled "printed document" (cream background,
 * Fraunces serif headings, A4-proportioned paper). A wax-seal integrity indicator
 * shows chain status. Export PDF triggers a real browser download.
 */

import React, { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { FolderCard, StampBadge, StitchedDivider } from '../../design-system';
import {
  defaultSpringTransition,
  reducedMotionTransition,
} from '../../design-system/motion';
import { apiClient, BriefExport, ChainVerificationResult } from '../../lib/api-client';
import { useBrief } from '../../hooks/useBrief';
import { useIntegrity } from '../../hooks/useIntegrity';

// ── Types ──────────────────────────────────────────────────────────────────────

interface BriefViewerProps {
  caseId: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function maskValue(value: string): string {
  if (value.length <= 4) return value;
  const suffix = value.slice(-4);
  const prefix = value.slice(0, Math.min(3, value.length - 4));
  const middle = '•'.repeat(Math.max(0, value.length - prefix.length - 4));
  return `${prefix}${middle}${suffix}`;
}

// ── Wax Seal Component ─────────────────────────────────────────────────────────

/**
 * SVG wax seal — intact (sage) when chain is valid, broken (terracotta) when not.
 * Stamp-presses in with a brief scale animation.
 */
const WaxSeal: React.FC<{ isValid: boolean }> = ({ isValid }) => {
  const shouldReduceMotion = useReducedMotion();
  const color = isValid ? '#6B7F5B' : '#C96F4F';
  const bgColor = isValid ? '#6B7F5B1A' : '#C96F4F1A';
  const label = isValid ? 'CHAIN INTACT' : 'CHAIN BROKEN';

  return (
    <motion.div
      initial={{ scale: shouldReduceMotion ? 1 : 0.6, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={
        shouldReduceMotion
          ? reducedMotionTransition
          : { type: 'spring', stiffness: 520, damping: 22, mass: 0.8 }
      }
      className="flex flex-col items-center gap-2"
    >
      {/* Wax seal SVG */}
      <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden="true">
        {/* Scalloped wax blob — 16-petal flower shape */}
        <path
          d={generateWaxSealPath(36, 36, 28, 22, 16)}
          fill={color}
          fillOpacity={0.15}
          stroke={color}
          strokeWidth={1.5}
          strokeOpacity={0.7}
        />
        {/* Inner circle */}
        <circle
          cx={36}
          cy={36}
          r={16}
          fill={bgColor}
          stroke={color}
          strokeWidth={1}
          strokeOpacity={0.5}
          strokeDasharray="3 2"
        />
        {/* Icon */}
        <text x={36} y={40} textAnchor="middle" fontSize={16}>
          {isValid ? '⚖' : '⚠'}
        </text>
        {/* Break crack — only when broken */}
        {!isValid && (
          <path
            d="M 36 20 L 38 30 L 34 36 L 37 46 L 36 52"
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeOpacity={0.8}
          />
        )}
      </svg>
      <div className="text-center">
        <p
          className="font-mono text-[10px] font-bold uppercase tracking-widest"
          style={{ color }}
        >
          {label}
        </p>
        <p className="font-mono text-[9px] text-pine/50">
          {isValid ? 'Section 63 BSA compliant' : 'Custody chain compromised'}
        </p>
      </div>
    </motion.div>
  );
};

/** Generate a scalloped wax-seal path (flower/star shape) */
function generateWaxSealPath(
  cx: number,
  cy: number,
  outerR: number,
  innerR: number,
  petals: number,
): string {
  const points: string[] = [];
  const step = (2 * Math.PI) / (petals * 2);
  for (let i = 0; i < petals * 2; i++) {
    const angle = i * step - Math.PI / 2;
    const r = i % 2 === 0 ? outerR : innerR;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    points.push(`${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  return points.join(' ') + ' Z';
}

// ── Loading Skeleton ───────────────────────────────────────────────────────────

const BriefSkeleton: React.FC = () => (
  <FolderCard
    tabTitle="CASE // BRIEF"
    tabPosition="left"
    tabBadge="TAB 04"
    classification="STATUTORY INVESTIGATIVE BRIEF // SECTION 63 BSA COMPLIANT"
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
      {/* Document skeleton */}
      <div className="mx-auto w-full max-w-2xl overflow-hidden rounded-xl border border-pine/15 bg-cream-light shadow-paper-raised">
        <div className="border-b border-pine/10 bg-cream p-6">
          <div className="mx-auto h-6 w-1/3 animate-pulse rounded bg-pine/10" />
          <div className="mx-auto mt-3 h-4 w-1/2 animate-pulse rounded bg-pine/5" />
        </div>
        <div className="space-y-3 p-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-3 animate-pulse rounded bg-pine/5"
              style={{ width: `${75 + (i % 3) * 10}%` }}
            />
          ))}
          <div className="h-3 w-1/2 animate-pulse rounded bg-pine/5" />
        </div>
      </div>
    </div>
  </FolderCard>
);

// ── Empty State ────────────────────────────────────────────────────────────────

const BriefEmptyState: React.FC = () => (
  <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-pine/25 bg-khaki-light/30 py-14 text-center">
    <div className="flex h-14 w-14 items-center justify-center rounded-full border border-pine/20 bg-cream font-mono text-2xl shadow-paper-sm">
      📄
    </div>
    <div>
      <p className="font-mono text-xs font-bold uppercase tracking-widest text-pine/50">
        Brief not yet generated
      </p>
      <p className="mt-1 font-mono text-[10px] text-pine/40">
        Run correlation and risk analysis first — upload evidence to begin
      </p>
    </div>
  </div>
);

// ── Printed Document ───────────────────────────────────────────────────────────

const PrintedBrief: React.FC<{
  brief: BriefExport;
  integrity: ChainVerificationResult;
}> = ({ brief, integrity }) => {
  const { case_summary: cs, top_entities, clusters, custody_chain, generated_at } = brief;

  return (
    <div
      className="mx-auto w-full max-w-2xl overflow-hidden rounded-xl border border-pine/20 shadow-paper-raised"
      style={{ background: '#FCFBF6' }}
    >
      {/* Document header — letterhead */}
      <div
        className="border-b border-pine/15 px-8 py-6 text-center"
        style={{ background: '#F8F6EE' }}
      >
        <p className="font-mono text-[10px] font-bold uppercase tracking-[0.25em] text-pine/50">
          EVIDENTIARY INVESTIGATIVE BRIEF
        </p>
        <h1
          className="type-display-md mt-2 text-pine"
          style={{ fontFamily: 'Fraunces, Georgia, serif' }}
        >
          {cs.name}
        </h1>
        <p className="mt-1 font-mono text-[10px] text-pine/50">
          Case ID #{cs.case_id} · Generated {formatDate(generated_at)} · Status:{' '}
          <span className="font-bold uppercase">{cs.status}</span>
        </p>
        {/* Classification stamp */}
        <div className="mt-3 flex justify-center">
          <span className="bg-terracotta/8 rounded border border-terracotta/40 px-3 py-0.5 font-mono text-[9px] font-bold uppercase tracking-[0.2em] text-terracotta-dark">
            {brief.classification}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="px-8 py-6">
        {/* Case Statistics */}
        <section className="mb-6">
          <h2
            className="mb-3 text-sm font-semibold uppercase tracking-wider text-pine/70"
            style={{
              fontFamily: 'Fraunces, Georgia, serif',
              borderBottom: '1px solid #2E3A2F20',
              paddingBottom: 6,
            }}
          >
            I. Case Overview
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: 'Evidence Files', value: cs.total_evidence_files },
              { label: 'Entities', value: cs.total_entities },
              { label: 'Entity Links', value: cs.total_links },
              { label: 'Clusters', value: cs.total_clusters },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-lg border border-pine/10 bg-cream/80 p-3 text-center"
              >
                <p className="font-mono text-xl font-bold text-pine">{stat.value}</p>
                <p className="mt-0.5 font-mono text-[9px] uppercase tracking-wider text-pine/50">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Custody chain integrity */}
        <section className="mb-6">
          <h2
            className="mb-3 text-sm font-semibold uppercase tracking-wider text-pine/70"
            style={{
              fontFamily: 'Fraunces, Georgia, serif',
              borderBottom: '1px solid #2E3A2F20',
              paddingBottom: 6,
            }}
          >
            II. Custody Chain Integrity
          </h2>
          <div className="flex flex-col items-center gap-3 rounded-xl border border-pine/15 bg-cream/60 p-4 sm:flex-row sm:items-start">
            <WaxSeal isValid={integrity.is_valid} />
            <div className="min-w-0 flex-1">
              <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-pine/55">
                Statutory Statement
              </p>
              <p className="mt-1 font-mono text-[11px] leading-relaxed text-pine/80">
                {custody_chain.statutory_statement}
              </p>
              {!integrity.is_valid && integrity.reason && (
                <p className="mt-1.5 font-mono text-[10px] text-terracotta-dark">
                  ⚠ {integrity.reason}
                </p>
              )}
              <p className="mt-2 font-mono text-[9px] text-pine/40">
                {custody_chain.total_entries} custody log entries ·{' '}
                {custody_chain.head_hash
                  ? `Head: ${custody_chain.head_hash.slice(0, 12)}…`
                  : 'No entries'}
              </p>
            </div>
          </div>
        </section>

        {/* Top priority entities */}
        {top_entities.length > 0 && (
          <section className="mb-6">
            <h2
              className="mb-3 text-sm font-semibold uppercase tracking-wider text-pine/70"
              style={{
                fontFamily: 'Fraunces, Georgia, serif',
                borderBottom: '1px solid #2E3A2F20',
                paddingBottom: 6,
              }}
            >
              III. Priority Entities
            </h2>
            <div className="overflow-hidden rounded-lg border border-pine/15">
              <table className="w-full text-left" role="table">
                <thead>
                  <tr className="border-b border-pine/10 bg-khaki-light/60">
                    <th className="px-3 py-2 font-mono text-[9px] font-bold uppercase tracking-widest text-pine/55">
                      #
                    </th>
                    <th className="px-3 py-2 font-mono text-[9px] font-bold uppercase tracking-widest text-pine/55">
                      Entity
                    </th>
                    <th className="px-3 py-2 font-mono text-[9px] font-bold uppercase tracking-widest text-pine/55">
                      Identifier
                    </th>
                    <th className="px-3 py-2 font-mono text-[9px] font-bold uppercase tracking-widest text-pine/55">
                      Score
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {top_entities.map((e, i) => (
                    <tr
                      key={e.entity_id}
                      className="border-b border-pine/5 last:border-0"
                      style={{
                        background: i % 2 === 0 ? 'transparent' : 'rgba(217,201,178,0.2)',
                      }}
                    >
                      <td className="px-3 py-2 font-mono text-[10px] text-pine/50">
                        {i + 1}
                      </td>
                      <td className="px-3 py-2 font-mono text-[10px] font-semibold text-pine">
                        {e.entity_type.replace(/_/g, ' ')}
                      </td>
                      <td className="px-3 py-2 font-mono text-[10px] text-pine">
                        {maskValue(e.identifier)}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className="rounded px-1.5 py-0.5 font-mono text-[10px] font-bold"
                          style={{
                            background:
                              e.score >= 60
                                ? '#C96F4F22'
                                : e.score >= 40
                                  ? '#2E3A2F11'
                                  : '#6B7F5B11',
                            color:
                              e.score >= 60
                                ? '#B15A3B'
                                : e.score >= 40
                                  ? '#2E3A2F'
                                  : '#546447',
                          }}
                        >
                          {e.score}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Cluster summary */}
        {clusters.length > 0 && (
          <section className="mb-6">
            <h2
              className="mb-3 text-sm font-semibold uppercase tracking-wider text-pine/70"
              style={{
                fontFamily: 'Fraunces, Georgia, serif',
                borderBottom: '1px solid #2E3A2F20',
                paddingBottom: 6,
              }}
            >
              IV. Network Clusters
            </h2>
            <div className="grid gap-2 sm:grid-cols-2">
              {clusters.map((cl) => (
                <div
                  key={cl.cluster_id}
                  className="rounded-lg border border-pine/10 bg-cream/60 px-3 py-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-pine/60">
                      Cluster {cl.cluster_id}
                    </span>
                    {cl.high_risk_entity_count > 0 && (
                      <span className="rounded bg-terracotta/15 px-1.5 py-0.5 font-mono text-[9px] font-bold text-terracotta-dark">
                        {cl.high_risk_entity_count} high-risk
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 font-mono text-[10px] text-pine/60">
                    {cl.node_count} entities · {cl.entity_types.join(', ')}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Footer disclaimer */}
        <div className="border-t border-pine/10 pt-4">
          <p className="font-mono text-[9px] leading-relaxed text-pine/40">
            This brief is generated automatically for investigator reference and is not a
            substitute for judicial determination. All recommendations are non-directive
            and require human review. PII has been partially masked per operational
            security protocol. Produced under Section 63, Bharatiya Sakshya Adhiniyam 2023
            (successor to Section 65B, Indian Evidence Act 1872).
          </p>
        </div>
      </div>
    </div>
  );
};

// ── Main Component ─────────────────────────────────────────────────────────────

export const BriefViewer: React.FC<BriefViewerProps> = ({ caseId }) => {
  const shouldReduceMotion = useReducedMotion();
  const [pdfDownloading, setPdfDownloading] = useState(false);

  // Brief JSON and custody-chain integrity fetching now live in `useBrief`
  // and `useIntegrity` (TanStack Query) — both are invalidated automatically
  // by `useEvidence`'s upload mutation, so this view reflects new evidence
  // (updated totals, a re-verified custody chain) without a manual refresh.
  const briefQuery = useBrief(caseId);
  const integrityQuery = useIntegrity(caseId);

  const brief: BriefExport | null = briefQuery.data ?? null;
  const integrity: ChainVerificationResult | null = integrityQuery.data ?? null;
  const loading = briefQuery.isPending || integrityQuery.isPending;
  const error = briefQuery.error
    ? briefQuery.error.message
    : integrityQuery.error
      ? integrityQuery.error.message
      : null;

  const handleExportPdf = () => {
    setPdfDownloading(true);
    const url = apiClient.cases.getBriefPdfUrl(caseId);
    const a = document.createElement('a');
    a.href = url;
    a.download = `case-${caseId}-brief.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => setPdfDownloading(false), 1500);
  };

  if (loading) return <BriefSkeleton />;

  if (error) {
    return (
      <FolderCard
        tabTitle={`CASE ${caseId} // BRIEF`}
        tabPosition="left"
        tabBadge="TAB 04"
        classification="STATUTORY INVESTIGATIVE BRIEF // SECTION 63 BSA COMPLIANT"
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
      tabTitle={`CASE ${caseId} // BRIEF`}
      tabPosition="left"
      tabBadge="TAB 04"
      classification="STATUTORY INVESTIGATIVE BRIEF // SECTION 63 BSA COMPLIANT"
      elevation="raised"
    >
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="type-display-lg text-pine">Court-Ready Investigative Brief</h2>
            <p className="type-body mt-1 text-pine/80">
              Automated one-page evidentiary brief with Section 63, BSA 2023
              cryptographic chain verification.
            </p>
          </div>
          <StampBadge
            label="CLASSIFIED BRIEF"
            variant="pine"
            rotation={-2}
            subtext={
              integrity ? (integrity.is_valid ? 'CHAIN VERIFIED' : 'CHAIN BROKEN') : '…'
            }
          />
        </div>

        <StitchedDivider
          orientation="horizontal"
          label="LEGAL INTEGRITY & STATUTORY COMPLIANCE"
        />

        {/* Action bar */}
        <div className="flex items-center justify-between rounded-xl border border-pine/15 bg-khaki-light/40 px-4 py-3">
          <div className="flex items-center gap-3">
            {integrity && (
              <div className="flex items-center gap-2">
                <span
                  className="font-mono text-[10px] font-bold uppercase tracking-wider"
                  style={{ color: integrity.is_valid ? '#546447' : '#B15A3B' }}
                >
                  {integrity.is_valid ? '⚖ Chain Intact' : '⚠ Chain Broken'}
                </span>
                <span className="font-mono text-[10px] text-pine/40">
                  · {integrity.total_entries} custody entries
                </span>
              </div>
            )}
          </div>
          <motion.button
            onClick={handleExportPdf}
            disabled={pdfDownloading}
            whileHover={{ scale: shouldReduceMotion ? 1 : 1.02 }}
            whileTap={{ scale: shouldReduceMotion ? 1 : 0.97 }}
            transition={defaultSpringTransition}
            className="flex items-center gap-2 rounded-lg border border-pine/20 bg-cream px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-pine shadow-paper-sm transition-opacity hover:shadow-paper disabled:opacity-60"
          >
            {pdfDownloading ? (
              <>
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="inline-block"
                >
                  ⟳
                </motion.span>
                Preparing…
              </>
            ) : (
              <>
                <span>↓</span>
                Export PDF Brief
              </>
            )}
          </motion.button>
        </div>

        {/* Document or empty state */}
        {brief && integrity ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={
              shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition
            }
          >
            <PrintedBrief brief={brief} integrity={integrity} />
          </motion.div>
        ) : (
          <BriefEmptyState />
        )}
      </div>
    </FolderCard>
  );
};
