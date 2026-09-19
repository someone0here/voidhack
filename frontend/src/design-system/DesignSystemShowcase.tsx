import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  FolderCard,
  StampBadge,
  Button,
  GlassToolbar,
  StitchedDivider,
  Input,
  rubberBandClamp,
  defaultSpringTransition,
  momentumSpringTransition,
  reducedMotionTransition,
} from './index';

export const DesignSystemShowcase: React.FC = () => {
  const [simulateReducedMotion, setSimulateReducedMotion] = useState(false);
  const [testInputValue, setTestInputValue] = useState('');
  const [testHashValue, setTestHashValue] = useState(
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  );
  const [dragOvershoot, setDragOvershoot] = useState(0);
  const [dragOffset, setDragOffset] = useState(0);
  const dragContainerRef = useRef<HTMLDivElement>(null);

  // Palette swatches definition
  const palette = [
    {
      name: 'Pine',
      variable: '--color-pine',
      hex: '#2E3A2F',
      role: 'Primary / Dark',
      description: 'Headers, primary text, leather-bound dossier surfaces',
      textColor: 'text-cream',
    },
    {
      name: 'Sage',
      variable: '--color-sage',
      hex: '#6B7F5B',
      role: 'Secondary / Accent',
      description: 'Folder tabs, secondary actions, muted evidentiary tags',
      textColor: 'text-cream',
    },
    {
      name: 'Khaki',
      variable: '--color-khaki',
      hex: '#D9C9B2',
      role: 'Surface Stock',
      description: 'Manila folder card backgrounds, archival paper stock',
      textColor: 'text-pine',
    },
    {
      name: 'Terracotta',
      variable: '--color-terracotta',
      hex: '#C96F4F',
      role: 'Alert / CTA',
      description: 'Primary action buttons, risk stamps, critical badges',
      textColor: 'text-cream',
    },
    {
      name: 'Cream',
      variable: '--color-cream',
      hex: '#F8F6EE',
      role: 'Background Desk',
      description: 'The tactile desk surface the field dossier binder sits upon',
      textColor: 'text-pine',
    },
  ];

  return (
    <div className="relative min-h-screen bg-cream text-pine selection:bg-khaki selection:text-pine">
      {/* 1. Translucent Warm Cream Glass Toolbar */}
      <GlassToolbar
        title={
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-pine/20 bg-khaki font-mono text-sm font-bold shadow-paper-sm">
              📁
            </span>
            <div>
              <h1 className="type-display-sm font-bold tracking-tight text-pine">
                Field Dossier Design System
              </h1>
              <p className="font-mono text-[10px] uppercase tracking-wider text-pine/60">
                Skeuomorphic Primitives & Apple Fluid Motion Engine
              </p>
            </div>
          </div>
        }
        actions={
          <div className="flex items-center gap-3">
            {/* Reduced Motion Simulation Toggle */}
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-pine/20 bg-cream-light px-3 py-1.5 shadow-sm">
              <input
                type="checkbox"
                checked={simulateReducedMotion}
                onChange={(e) => setSimulateReducedMotion(e.target.checked)}
                className="h-4 w-4 rounded border-pine/30 text-sage focus:ring-sage"
              />
              <span className="font-mono text-xs font-semibold text-pine-light">
                Reduced Motion Mode
              </span>
            </label>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            >
              Top ↑
            </Button>
          </div>
        }
      />

      {/* Main Content Area */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Banner / Overview Card */}
        <div className="relative mb-10 overflow-hidden rounded-2xl border border-pine/20 bg-khaki-light/80 p-8 shadow-paper">
          <div className="paper-grain pointer-events-none absolute inset-0 opacity-40" />
          <div className="relative z-10 max-w-3xl">
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-sage/40 bg-sage/10 px-3 py-0.5">
              <span className="h-2 w-2 rounded-full bg-sage" />
              <span className="font-mono text-xs font-semibold tracking-wide text-sage-dark">
                SYSTEM SPECIFICATION // PHASE 7 FOUNDATION
              </span>
            </div>
            <h2 className="type-display-lg mt-2 font-bold text-pine">
              Tactile Case File Dossier Architecture
            </h2>
            <p className="type-body mt-3 text-pine/80">
              Combines Apple fluid-interaction physics—critically damped springs, instant
              pointer-down tactile depress feedback, and rubber-band boundary
              resistance—with a physical field case file skin reminiscent of tactical
              evidentiary folders, warm paper stock, stamped classification ink, and
              saddle-stitched binding.
            </p>
          </div>
        </div>

        {/* ===================================================================
            SECTION 1: PALETTE & MATERIAL TOKENS
            =================================================================== */}
        <section id="palette" className="mb-14">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                Token Architecture 01
              </span>
              <h2 className="type-display-md mt-1 font-bold text-pine">
                Dossier Core Palette & Material Depths
              </h2>
            </div>
            <StampBadge label="CANONICAL" variant="sage" rotation={2} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {palette.map((c) => (
              <div
                key={c.name}
                className="group relative flex flex-col overflow-hidden rounded-xl border border-pine/20 bg-cream-light p-4 shadow-paper-sm transition-transform hover:-translate-y-1"
              >
                <div
                  className={`flex h-24 w-full items-end rounded-lg p-2.5 shadow-inner ${c.textColor}`}
                  style={{ backgroundColor: c.hex }}
                >
                  <span className="font-mono text-xs font-bold tracking-tight opacity-90">
                    {c.hex}
                  </span>
                </div>
                <div className="mt-3 flex flex-col">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-pine/60">
                    {c.variable}
                  </span>
                  <span className="font-display text-lg font-bold text-pine">
                    {c.name}
                  </span>
                  <span className="font-mono text-xs font-semibold text-sage-dark">
                    {c.role}
                  </span>
                  <p className="mt-1 font-sans text-xs text-pine/70">{c.description}</p>
                </div>
              </div>
            ))}
          </div>

          <StitchedDivider
            orientation="horizontal"
            label="TYPOGRAPHY & OPTICAL SIZING"
            className="my-10"
          />
        </section>

        {/* ===================================================================
            SECTION 2: TYPOGRAPHY & APPLE OPTICAL SIZING
            =================================================================== */}
        <section id="typography" className="mb-14">
          <div className="mb-6">
            <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
              Token Architecture 02
            </span>
            <h2 className="type-display-md mt-1 font-bold text-pine">
              Apple Optical Sizing Rules & Font Hierarchy
            </h2>
            <p className="type-body-sm mt-1 text-pine/70">
              Large display titles get tightened tracking (-0.02em) and tight leading
              (~1.05); body text uses neutral tracking with comfortable leading (~1.5);
              data uses monospace for a typewritten evidentiary record.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Display Headings (Fraunces) */}
            <div className="rounded-xl border border-pine/20 bg-khaki/40 p-6 shadow-paper-sm">
              <div className="mb-4 flex items-center justify-between border-b border-pine/15 pb-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-pine">
                  Display Serif // Fraunces
                </span>
                <span className="font-mono text-[10px] text-sage-dark">
                  Tightened Tracking (-0.02em)
                </span>
              </div>
              <div className="space-y-4">
                <div>
                  <span className="font-mono text-[10px] uppercase text-pine/50">
                    type-display-hero (-0.025em / leading 1.05)
                  </span>
                  <h1 className="type-display-hero text-pine">Case Dossier #4092</h1>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase text-pine/50">
                    type-display-lg (-0.02em / leading 1.08)
                  </span>
                  <h2 className="type-display-lg text-pine">
                    Syndicate Financial Telemetry
                  </h2>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase text-pine/50">
                    type-display-md (-0.015em / leading 1.15)
                  </span>
                  <h3 className="type-display-md text-pine">
                    Automated Linkage Analysis Report
                  </h3>
                </div>
              </div>
            </div>

            {/* Humanist Body (Inter) & Telemetry (JetBrains Mono) */}
            <div className="space-y-6">
              <div className="rounded-xl border border-pine/20 bg-cream-light p-6 shadow-paper-sm">
                <div className="mb-4 flex items-center justify-between border-b border-pine/15 pb-2">
                  <span className="font-mono text-xs font-bold uppercase tracking-wider text-pine">
                    Humanist Body // Inter
                  </span>
                  <span className="font-mono text-[10px] text-sage-dark">
                    Neutral Tracking (0) / Leading (1.5)
                  </span>
                </div>
                <p className="type-body text-pine/90">
                  During forensic normalization of CDR and UPI statements, three mule bank
                  accounts were linked to a singular IMEI device cluster operating across
                  Delhi and Bengaluru telecom circles.
                </p>
                <p className="type-body-sm mt-3 text-pine/70">
                  Secondary evidentiary logs indicate rapid fund layer dispersion within
                  14 minutes of the primary phishing incident payload.
                </p>
              </div>

              <div className="rounded-xl border border-pine/20 bg-pine/5 p-6 shadow-paper-sm">
                <div className="mb-4 flex items-center justify-between border-b border-pine/15 pb-2">
                  <span className="font-mono text-xs font-bold uppercase tracking-wider text-pine">
                    Evidentiary Telemetry // JetBrains Mono
                  </span>
                  <span className="font-mono text-[10px] font-bold text-terracotta-dark">
                    Typewritten Record
                  </span>
                </div>
                <div className="space-y-1.5 font-mono text-xs">
                  <div className="flex justify-between">
                    <span className="text-pine/60">RECORD_ID:</span>
                    <span className="font-bold text-pine">EV-2026-9810-AF</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-pine/60">TIMESTAMP:</span>
                    <span className="text-pine">2026-09-19T06:40:12Z</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-pine/60">SHA-256:</span>
                    <span className="break-all text-[11px] text-sage-dark">
                      e3b0c44298fc1c149afbf4c8996fb92427ae41e4
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <StitchedDivider
            orientation="horizontal"
            label="MOTION ENGINE & SPRING PHYSICS"
            className="my-10"
          />
        </section>

        {/* ===================================================================
            SECTION 3: APPLE FLUID MOTION ENGINE & RUBBER-BAND
            =================================================================== */}
        <section id="motion" className="mb-14">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                Token Architecture 03
              </span>
              <h2 className="type-display-md mt-1 font-bold text-pine">
                Apple Fluid Motion & Rubber-band Physics
              </h2>
            </div>
            <span className="font-mono text-xs font-semibold text-pine/70">
              {simulateReducedMotion
                ? '⚙ Mode: Reduced Motion (Cross-fade)'
                : '⚡ Mode: Fluid Springs Active'}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Spring Comparison Cards */}
            <div className="flex flex-col gap-4 rounded-xl border border-pine/20 bg-khaki/30 p-6 shadow-paper-sm">
              <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-pine">
                Spring Dynamic Profiles
              </h3>

              {/* Critically Damped Card */}
              <div className="rounded-lg border border-pine/15 bg-cream p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-pine">
                    Default UI Spring (Panels, Drawers, Menus)
                  </span>
                  <span className="rounded bg-pine/10 px-2 py-0.5 font-mono text-[10px] text-pine">
                    damping: 1.0, response: 0.35
                  </span>
                </div>
                <p className="mt-1 text-xs text-pine/70">
                  Critically damped with zero overshoot. Settles precisely into resting
                  position.
                </p>
                <motion.div
                  whileHover={{ x: 20 }}
                  transition={
                    simulateReducedMotion
                      ? reducedMotionTransition
                      : defaultSpringTransition
                  }
                  className="mt-3 inline-flex cursor-pointer items-center gap-2 rounded-md border border-pine/20 bg-khaki px-3 py-1.5 font-mono text-xs font-semibold text-pine shadow-sm"
                >
                  <span>Hover to test critical spring</span>
                  <span>→</span>
                </motion.div>
              </div>

              {/* Momentum Flick Card */}
              <div className="rounded-lg border border-pine/15 bg-cream p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-pine">
                    Momentum / Flick Spring (Released Cards, Graphs)
                  </span>
                  <span className="rounded bg-sage/20 px-2 py-0.5 font-mono text-[10px] font-bold text-sage-dark">
                    damping: 0.8, response: 0.35
                  </span>
                </div>
                <p className="mt-1 text-xs text-pine/70">
                  Light tactile rebound bounce on gesture release.
                </p>
                <motion.div
                  whileHover={{ x: 20 }}
                  transition={
                    simulateReducedMotion
                      ? reducedMotionTransition
                      : momentumSpringTransition
                  }
                  className="mt-3 inline-flex cursor-pointer items-center gap-2 rounded-md border border-sage/40 bg-sage/10 px-3 py-1.5 font-mono text-xs font-semibold text-sage-dark shadow-sm"
                >
                  <span>Hover to test momentum bounce</span>
                  <span>↗</span>
                </motion.div>
              </div>
            </div>

            {/* Interactive Apple Rubber-Band Draggable Arena */}
            <div
              ref={dragContainerRef}
              className="flex flex-col rounded-xl border border-pine/20 bg-cream-light p-6 shadow-paper-sm"
            >
              <div className="flex items-center justify-between border-b border-pine/15 pb-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-pine">
                  Rubber-Band Resistance Lab
                </span>
                <span className="font-mono text-[10px] font-semibold text-terracotta-dark">
                  formula: x·d·0.55 / (d + 0.55·|x|)
                </span>
              </div>
              <p className="mt-2 text-xs text-pine/70">
                Drag the evidentiary card past the boundary. Observe the exact
                logarithmic-style rubber-band damping curve implemented per Apple fluid
                specifications.
              </p>

              {/* Draggable surface */}
              <div className="relative mt-4 flex h-40 w-full items-center justify-center overflow-hidden rounded-lg border-2 border-dashed border-pine/20 bg-khaki/20">
                <motion.div
                  drag="x"
                  dragConstraints={{ left: -100, right: 100 }}
                  dragElastic={0.25}
                  onDrag={(_, info) => {
                    const overshoot = Math.max(0, Math.abs(info.offset.x) - 100);
                    const clamped = rubberBandClamp(overshoot, 200);
                    setDragOvershoot(Math.round(overshoot));
                    setDragOffset(Math.round(clamped));
                  }}
                  whileDrag={{ scale: 1.05 }}
                  className="relative flex cursor-grab select-none items-center gap-2 rounded-lg border border-pine/30 bg-khaki px-4 py-2 shadow-paper active:cursor-grabbing"
                >
                  <span className="font-mono text-xs font-bold text-pine">
                    ⇋ Drag Me Horizontally
                  </span>
                </motion.div>
              </div>

              {/* Telemetry output */}
              <div className="mt-3 flex items-center justify-around rounded-md bg-pine/5 p-2 font-mono text-xs">
                <div>
                  <span className="text-pine/60">Raw Overshoot: </span>
                  <span className="font-bold text-terracotta-dark">
                    {dragOvershoot}px
                  </span>
                </div>
                <div>
                  <span className="text-pine/60">Dampened Offset: </span>
                  <span className="font-bold text-sage-dark">{dragOffset}px</span>
                </div>
              </div>
            </div>
          </div>

          <StitchedDivider
            orientation="horizontal"
            label="SKEUOMORPHIC PRIMITIVES"
            className="my-10"
          />
        </section>

        {/* ===================================================================
            SECTION 4: SKEUOMORPHIC PRIMITIVES MATRIX
            =================================================================== */}
        <section id="primitives" className="mb-14 space-y-12">
          {/* PRIMITIVE 1: FOLDER CARD */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                  Primitive 01
                </span>
                <h3 className="type-display-md font-bold text-pine">
                  &lt;FolderCard&gt; — Manila Card with Die-Cut Tab & Paper Grain
                </h3>
              </div>
              <StampBadge label="CORE ASSET" variant="terracotta" rotation={-2} />
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
              {/* Tab Left */}
              <FolderCard
                tabTitle="EXHIBIT A-1"
                tabPosition="left"
                tabBadge="3 FILES"
                classification="EVIDENTIARY RECORD // SEC 1"
                elevation="raised"
              >
                <h4 className="font-display text-base font-bold text-pine">
                  CDR Telecom Records
                </h4>
                <p className="mt-1 font-sans text-xs text-pine/80">
                  Call Detail Records extracted from Gateway Switch 08. Contains 1,420
                  originating session handoffs.
                </p>
                <div className="mt-4 flex items-center justify-between border-t border-pine/10 pt-2">
                  <span className="font-mono text-[11px] font-semibold text-sage-dark">
                    CONFIRMED LINKAGE
                  </span>
                  <StampBadge label="VERIFIED" variant="sage" shape="pill" rotation={0} />
                </div>
              </FolderCard>

              {/* Tab Center */}
              <FolderCard
                tabTitle="SUSPECT PROFILE"
                tabPosition="center"
                tabBadge="CONFIDENTIAL"
                classification="TARGET DOSSIER // PRIORITY 1"
                elevation="floating"
                isDraggable={true}
              >
                <h4 className="font-display text-base font-bold text-pine">
                  Primary Mule Syndicate
                </h4>
                <p className="mt-1 font-sans text-xs text-pine/80">
                  Interactive draggable card. Release to test Apple momentum flick spring
                  physics.
                </p>
                <div className="mt-4 flex items-center justify-between border-t border-pine/10 pt-2">
                  <span className="font-mono text-[11px] font-semibold text-terracotta-dark">
                    HIGH RISK CLUSTER
                  </span>
                  <StampBadge
                    label="HIGH PRIORITY"
                    variant="terracotta"
                    shape="pill"
                    rotation={-3}
                  />
                </div>
              </FolderCard>

              {/* Tab Right */}
              <FolderCard
                tabTitle="IPDR DUMP"
                tabPosition="right"
                tabBadge="ARCHIVE"
                classification="FORENSIC EXTRACTION // SEC 4"
                elevation="flat"
              >
                <h4 className="font-display text-base font-bold text-pine">
                  Tor Gateway Exit Telemetry
                </h4>
                <p className="mt-1 font-sans text-xs text-pine/80">
                  Archived IPDR packet captures matching victim transaction initiation
                  window.
                </p>
                <div className="mt-4 flex items-center justify-between border-t border-pine/10 pt-2">
                  <span className="font-mono text-[11px] font-semibold text-pine/60">
                    FILED TO VAULT
                  </span>
                  <StampBadge label="ARCHIVED" variant="pine" shape="pill" rotation={2} />
                </div>
              </FolderCard>
            </div>
          </div>

          {/* PRIMITIVE 2: STAMP BADGE */}
          <div>
            <div className="mb-4">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                Primitive 02
              </span>
              <h3 className="type-display-md font-bold text-pine">
                &lt;StampBadge&gt; — Inked Rubber Stamp Status Indicators
              </h3>
              <p className="type-body-sm text-pine/70">
                Slightly rotated with dashed stamp rings and ink distress simulation.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-6 rounded-xl border border-pine/20 bg-khaki/30 p-6 shadow-paper-sm">
              <StampBadge
                label="HIGH PRIORITY"
                variant="terracotta"
                shape="pill"
                rotation={-3}
                subtext="SEV-1 ALERT"
              />
              <StampBadge
                label="VERIFIED"
                variant="sage"
                shape="pill"
                rotation={2}
                subtext="COURT READY"
              />
              <StampBadge
                label="CLASSIFIED"
                variant="pine"
                shape="rectangular"
                rotation={-1}
                subtext="OFFICIAL USE"
              />
              <StampBadge
                label="EVIDENTIARY"
                variant="terracotta"
                shape="rectangular"
                rotation={4}
              />
              <StampBadge
                label="APPROVED"
                variant="sage"
                shape="circular"
                rotation={-4}
                subtext="DEPT 04"
              />
              <StampBadge
                label="SEALED"
                variant="pine"
                shape="circular"
                rotation={3}
                subtext="2026.09"
              />
            </div>
          </div>

          {/* PRIMITIVE 3: BUTTON */}
          <div>
            <div className="mb-4">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                Primitive 03
              </span>
              <h3 className="type-display-md font-bold text-pine">
                &lt;Button&gt; — Tactile Buttons with Instant Pointer-Down Feedback
              </h3>
              <p className="type-body-sm text-pine/70">
                Responds immediately on pointer-DOWN (scale 0.97, ~100ms), not upon mouse
                release.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 rounded-xl border border-pine/20 bg-cream-light p-6 shadow-paper-sm">
              <Button variant="primary" size="lg">
                Primary Terracotta (LG)
              </Button>
              <Button variant="primary" size="md">
                Primary (MD)
              </Button>
              <Button variant="secondary" size="md">
                Secondary Sage
              </Button>
              <Button variant="ghost" size="md">
                Ghost Dossier
              </Button>
              <Button variant="danger" size="md">
                Critical Redact
              </Button>
              <Button variant="primary" size="sm" isLoading={true}>
                Processing
              </Button>
              <Button variant="primary" size="sm" disabled={true}>
                Disabled
              </Button>
            </div>
          </div>

          {/* PRIMITIVE 4: STITCHED DIVIDER */}
          <div>
            <div className="mb-4">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                Primitive 04
              </span>
              <h3 className="type-display-md font-bold text-pine">
                &lt;StitchedDivider&gt; — Leather Thread Saddle Stitching
              </h3>
            </div>

            <div className="rounded-xl border border-pine/20 bg-khaki/30 p-6 shadow-paper-sm">
              <StitchedDivider
                orientation="horizontal"
                label="HORIZONTAL SADDLE STITCH // SAGE"
                stitchColor="sage"
              />
              <StitchedDivider
                orientation="horizontal"
                label="HORIZONTAL STITCH // PINE WAX THREAD"
                stitchColor="pine"
              />
              <div className="my-6 flex h-24 items-center justify-center gap-8">
                <span className="font-mono text-xs text-pine/70">Sub-file A</span>
                <StitchedDivider orientation="vertical" label="SEC" stitchColor="sage" />
                <span className="font-mono text-xs text-pine/70">Sub-file B</span>
                <StitchedDivider orientation="vertical" label="REL" stitchColor="pine" />
                <span className="font-mono text-xs text-pine/70">Sub-file C</span>
              </div>
            </div>
          </div>

          {/* PRIMITIVE 5: INPUT */}
          <div>
            <div className="mb-4">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-sage-dark">
                Primitive 05
              </span>
              <h3 className="type-display-md font-bold text-pine">
                &lt;Input&gt; — Debossed Pressed-Paper Inset Shadow
              </h3>
              <p className="type-body-sm text-pine/70">
                Uses an authentic inset box-shadow to simulate indented typewriter
                indentations on archival paper stock.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 rounded-xl border border-pine/20 bg-khaki/20 p-6 shadow-paper-sm md:grid-cols-2">
              <Input
                label="Investigator Note / Title"
                placeholder="e.g. Cross-Border Mule Account Flow"
                helperText="Standard humanist sans input"
                value={testInputValue}
                onChange={(e) => setTestInputValue(e.target.value)}
              />

              <Input
                label="Forensic Hash / Record ID"
                mono={true}
                placeholder="SHA-256 Hash"
                helperText="Monospace typewritten data font"
                value={testHashValue}
                onChange={(e) => setTestHashValue(e.target.value)}
              />

              <Input
                label="UPI Virtual Payment Address"
                placeholder="suspect@upi"
                error="Account flagged by NPCI intelligence unit"
                defaultValue="fraudulent_node@okhdfcbank"
              />

              <Input
                label="Locked Evidentiary Vault Key"
                disabled={true}
                defaultValue="VAULT-KEY-ENCRYPTED-AES256"
                helperText="Disabled field with tactile deboss preservation"
              />
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-pine/15 bg-khaki-light/50 py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-pine">
              Cyber Fraud Correlator
            </span>
            <span className="font-mono text-xs text-pine/50">
              // Design System Vocabulary v1.0
            </span>
          </div>
          <p className="font-mono text-xs text-pine/60">
            Apple Fluid Physics · Skeuomorphic Dossier Primitives · Strict A11y
          </p>
        </div>
      </footer>
    </div>
  );
};

export default DesignSystemShowcase;
