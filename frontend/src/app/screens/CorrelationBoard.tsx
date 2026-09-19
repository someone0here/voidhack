/**
 * CorrelationBoard — Interactive Cork-Board Force-Directed Graph
 *
 * Fetches GET /cases/{case_id}/graph and renders a d3-force physics layout
 * as pin-cards on a cork board SVG. Direct manipulation drag uses Pointer Events
 * + setPointerCapture for 1:1 tracking from exact grab offset. Pinch/scroll zoom
 * and pan via wheel + pointer events. Node click opens an anchored popover at the
 * node's screen position (not screen centre).
 */

import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from 'react';
import * as d3Force from 'd3-force';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { FolderCard, StampBadge, StitchedDivider } from '../../design-system';
import {
  defaultSpringTransition,
  reducedMotionTransition,
} from '../../design-system/motion';
import { apiClient, SerializedGraph, SerializedNode, SerializedEdge } from '../../lib/api-client';

// ── Types ──────────────────────────────────────────────────────────────────────

interface NodeState extends SerializedNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx: number | null;
  fy: number | null;
}

interface CorrelationBoardProps {
  caseId: number;
}

// ── Constants & Helpers ────────────────────────────────────────────────────────

const NODE_W = 112;
const NODE_H = 52;

const ENTITY_ICONS: Record<string, string> = {
  phone: '📞',
  account: '🏦',
  device_imei: '📱',
  ip_address: '🌐',
  mac_address: '💻',
  email_address: '✉️',
};

const LINK_TYPE_COLORS: Record<string, string> = {
  shared_imei: '#06B6D4',      // cyan — device
  shared_upi_handle: '#C96F4F', // terracotta — financial
  shared_mac: '#F59E0B',        // amber — hardware
  shared_ip_subnet: '#6B7F5B',  // sage — network
  co_occurrence: '#94A3B8',     // muted — co-occurrence
  direct_communication: '#C96F4F', // terracotta — comms
  transaction: '#C96F4F',       // terracotta — money
};

const CONFIDENCE_STROKE: Record<string, number> = {
  Strong: 3.5,
  Medium: 2,
  Weak: 1,
};

/** Mask PII: keep last 4 chars visible */
function maskValue(value: string): string {
  if (value.length <= 4) return value;
  const suffix = value.slice(-4);
  const prefix = value.slice(0, Math.min(3, value.length - 4));
  const middle = '•'.repeat(Math.max(0, value.length - prefix.length - 4));
  return `${prefix}${middle}${suffix}`;
}

/** Convert SVG-space point to screen coords */
function svgToScreen(
  svg: SVGSVGElement,
  x: number,
  y: number,
  transform: DOMMatrix,
): { screenX: number; screenY: number } {
  const pt = svg.createSVGPoint();
  pt.x = x;
  pt.y = y;
  const screenPt = pt.matrixTransform(transform);
  const rect = svg.getBoundingClientRect();
  return { screenX: screenPt.x + rect.left, screenY: screenPt.y + rect.top };
}

// ── Loading Skeleton ───────────────────────────────────────────────────────────

const CorrelationSkeleton: React.FC = () => (
  <FolderCard
    tabTitle="CASE // BOARD"
    tabPosition="left"
    tabBadge="TAB 02"
    classification="CROSS-CASE LINKAGE GRAPH & ENTITY RESOLUTION"
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
      {/* Cork board skeleton */}
      <div className="relative h-[420px] w-full animate-pulse overflow-hidden rounded-xl bg-[#D9C9B2]/60">
        {/* Shimmer nodes */}
        {[
          { left: '20%', top: '30%' },
          { left: '50%', top: '20%' },
          { left: '70%', top: '55%' },
          { left: '30%', top: '65%' },
          { left: '55%', top: '70%' },
        ].map((pos, i) => (
          <div
            key={i}
            style={{ left: pos.left, top: pos.top }}
            className="absolute h-12 w-28 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-cream/60 shadow-paper-sm"
          />
        ))}
      </div>
    </div>
  </FolderCard>
);

// ── Empty State ────────────────────────────────────────────────────────────────

const BoardEmptyState: React.FC = () => (
  <div className="flex h-[420px] flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-pine/25 bg-khaki-light/30">
    <div className="flex h-14 w-14 items-center justify-center rounded-full border border-pine/20 bg-cream font-mono text-2xl shadow-paper-sm">
      🕸
    </div>
    <div className="text-center">
      <p className="font-mono text-xs font-bold uppercase tracking-widest text-pine/50">
        No entities correlated yet
      </p>
      <p className="mt-1 font-mono text-[10px] text-pine/40">
        Upload evidence files in the Intake tab to begin analysis
      </p>
    </div>
  </div>
);

// ── Node Pin Card ──────────────────────────────────────────────────────────────

interface NodeCardProps {
  node: NodeState;
  isSelected: boolean;
  onPointerDown: (e: React.PointerEvent, nodeId: number) => void;
  onClick: (e: React.MouseEvent, node: NodeState) => void;
}

const NodeCard: React.FC<NodeCardProps> = ({ node, isSelected, onPointerDown, onClick }) => {
  const icon = ENTITY_ICONS[node.entity_type] ?? '🔍';
  const masked = maskValue(node.value);

  return (
    <g
      transform={`translate(${node.x - NODE_W / 2},${node.y - NODE_H / 2})`}
      style={{ cursor: 'grab' }}
      onPointerDown={(e) => onPointerDown(e, node.id)}
      onClick={(e) => onClick(e, node)}
    >
      {/* Push-pin dot */}
      <circle
        cx={NODE_W / 2}
        cy={-5}
        r={5}
        fill={isSelected ? '#C96F4F' : '#6B7F5B'}
        stroke="white"
        strokeWidth={1.5}
      />
      {/* Card body */}
      <rect
        x={0}
        y={0}
        width={NODE_W}
        height={NODE_H}
        rx={8}
        ry={8}
        fill={isSelected ? '#F8F6EE' : '#FCFBF6'}
        stroke={isSelected ? '#C96F4F' : '#2E3A2F'}
        strokeWidth={isSelected ? 1.5 : 0.75}
        strokeOpacity={isSelected ? 0.8 : 0.2}
        filter="url(#card-shadow)"
      />
      {/* Entity type icon */}
      <text x={10} y={22} fontSize={14} dominantBaseline="middle">
        {icon}
      </text>
      {/* Entity type label */}
      <text
        x={30}
        y={17}
        fontSize={7}
        fontFamily="'JetBrains Mono', monospace"
        fontWeight="700"
        fill="#2E3A2F"
        fillOpacity={0.55}
        textAnchor="start"
        letterSpacing="0.08em"
        style={{ textTransform: 'uppercase' }}
      >
        {node.entity_type.replace(/_/g, ' ')}
      </text>
      {/* Masked value */}
      <text
        x={30}
        y={33}
        fontSize={9}
        fontFamily="'JetBrains Mono', monospace"
        fontWeight="600"
        fill="#2E3A2F"
        textAnchor="start"
        clipPath={`url(#clip-${node.id})`}
      >
        {masked}
      </text>
      <clipPath id={`clip-${node.id}`}>
        <rect x={28} y={24} width={NODE_W - 34} height={18} />
      </clipPath>
      {/* Cluster ID dot */}
      <circle cx={NODE_W - 8} cy={NODE_H - 8} r={4} fill="#D9C9B2" stroke="#2E3A2F" strokeOpacity={0.2} strokeWidth={0.5} />
      <text x={NODE_W - 8} y={NODE_H - 8} fontSize={5} fontFamily="monospace" fill="#2E3A2F" fillOpacity={0.6} textAnchor="middle" dominantBaseline="middle">
        {node.cluster_id}
      </text>
    </g>
  );
};

// ── Node Popover ───────────────────────────────────────────────────────────────

interface PopoverProps {
  node: NodeState;
  edges: SerializedEdge[];
  allNodes: NodeState[];
  screenX: number;
  screenY: number;
  onClose: () => void;
}

const NodePopover: React.FC<PopoverProps> = ({
  node,
  edges,
  allNodes,
  screenX,
  screenY,
  onClose,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const connected = edges
    .filter((e) => e.source === node.id || e.target === node.id)
    .map((e) => {
      const peerId = e.source === node.id ? e.target : e.source;
      const peer = allNodes.find((n) => n.id === peerId);
      return { edge: e, peer };
    })
    .filter((c): c is { edge: SerializedEdge; peer: NodeState } => c.peer !== undefined);

  return (
    <>
      {/* Backdrop close */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
        aria-hidden="true"
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={shouldReduceMotion ? reducedMotionTransition : defaultSpringTransition}
        style={{
          position: 'fixed',
          left: screenX + 12,
          top: screenY - 20,
          transformOrigin: 'left top',
          zIndex: 50,
        }}
        className="w-72 overflow-hidden rounded-xl border border-pine/20 bg-cream shadow-paper-raised"
        role="dialog"
        aria-label={`Entity details for ${node.entity_type} ${node.value}`}
      >
        <div className="border-b border-pine/15 bg-khaki-light/60 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg">{ENTITY_ICONS[node.entity_type] ?? '🔍'}</span>
              <div>
                <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-pine/60">
                  {node.entity_type.replace(/_/g, ' ')}
                </p>
                <p className="font-mono text-xs font-semibold text-pine">{maskValue(node.value)}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded p-1 font-mono text-[10px] text-pine/50 hover:text-pine"
              aria-label="Close popover"
            >
              ✕
            </button>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className="rounded bg-pine/10 px-2 py-0.5 font-mono text-[10px] font-bold text-pine">
              CLUSTER {node.cluster_id}
            </span>
          </div>
        </div>

        <div className="p-4">
          {connected.length > 0 ? (
            <>
              <p className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest text-pine/55">
                Connected via ({connected.length})
              </p>
              <div className="space-y-2">
                {connected.map(({ edge, peer }) => (
                  <div
                    key={`${edge.source}-${edge.target}`}
                    className="flex items-center gap-2 rounded-lg border border-pine/15 bg-khaki-light/40 p-2"
                  >
                    <span>{ENTITY_ICONS[peer.entity_type] ?? '🔍'}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-[10px] font-semibold text-pine">
                        {maskValue(peer.value)}
                      </p>
                      <p className="font-mono text-[9px] text-pine/50">
                        {edge.link_type.replace(/_/g, ' ')} ·{' '}
                        <span
                          style={{ color: LINK_TYPE_COLORS[edge.link_type] ?? '#94A3B8' }}
                        >
                          {edge.confidence_label}
                        </span>{' '}
                        ({(edge.confidence * 100).toFixed(0)}%)
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="font-mono text-[10px] text-pine/40">No connections found</p>
          )}
        </div>
      </motion.div>
    </>
  );
};

// ── Main Component ─────────────────────────────────────────────────────────────

export const CorrelationBoard: React.FC<CorrelationBoardProps> = ({ caseId }) => {
  const shouldReduceMotion = useReducedMotion();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graph, setGraph] = useState<SerializedGraph | null>(null);

  // Live node positions (mutable ref for d3, synced to state for render)
  const [nodes, setNodes] = useState<NodeState[]>([]);
  const simulationRef = useRef<d3Force.Simulation<NodeState, SerializedEdge> | null>(null);
  const tickCount = useRef(0);
  const animFrameRef = useRef<number>(0);

  // Viewport transform: pan (tx, ty) + scale
  const [viewport, setViewport] = useState({ tx: 0, ty: 0, scale: 1 });
  const vpRef = useRef(viewport);
  vpRef.current = viewport;

  // Drag state (pointer events)
  const dragRef = useRef<{
    nodeId: number;
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startNodeX: number;
    startNodeY: number;
  } | null>(null);

  // Pan state
  const panRef = useRef<{
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startTx: number;
    startTy: number;
  } | null>(null);

  // Selected node popover
  const [selectedNode, setSelectedNode] = useState<NodeState | null>(null);
  const [popoverScreen, setPopoverScreen] = useState<{ x: number; y: number } | null>(null);

  // ── Fetch graph ──────────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.cases
      .getGraph(caseId)
      .then((g) => {
        if (!cancelled) setGraph(g);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load graph');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  // ── Build d3 simulation ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!graph || !containerRef.current) return;

    const W = containerRef.current.clientWidth || 800;
    const H = 420;

    // Initialise node positions at random around centre
    const initNodes: NodeState[] = graph.nodes.map((n) => ({
      ...n,
      x: W / 2 + (Math.random() - 0.5) * 200,
      y: H / 2 + (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0,
      fx: null,
      fy: null,
    }));

    const sim = d3Force
      .forceSimulation<NodeState>(initNodes)
      .force('charge', d3Force.forceManyBody<NodeState>().strength(-320))
      .force('center', d3Force.forceCenter(W / 2, H / 2).strength(0.05))
      .force('collide', d3Force.forceCollide<NodeState>(70))
      .force(
        'link',
        d3Force
          .forceLink<NodeState, SerializedEdge>(graph.edges)
          .id((d) => d.id)
          // Stronger confidence → shorter rest length → nodes pulled closer
          .distance((edge) => 120 + (1 - edge.confidence) * 160)
          .strength((edge) => edge.confidence * 0.6),
      )
      .alphaDecay(0.028)
      .velocityDecay(0.4);

    simulationRef.current = sim;
    tickCount.current = 0;

    // Sync d3 positions to React state on each tick
    const tick = () => {
      tickCount.current++;
      setNodes([...sim.nodes()]);
      if (sim.alpha() > sim.alphaMin()) {
        animFrameRef.current = requestAnimationFrame(tick);
      }
    };
    sim.on('tick', () => {
      // Throttle to rAF
    });
    animFrameRef.current = requestAnimationFrame(tick);

    // Centre viewport
    setViewport({ tx: 0, ty: 0, scale: 1 });

    return () => {
      sim.stop();
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [graph]);

  // ── Pointer Events — Node Drag ────────────────────────────────────────────────

  const handleNodePointerDown = useCallback(
    (e: React.PointerEvent, nodeId: number) => {
      e.stopPropagation();
      (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);

      const node = simulationRef.current?.nodes().find((n) => n.id === nodeId);
      if (!node) return;

      // Compute exact grab offset in SVG-space
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const svgX = (e.clientX - rect.left - vpRef.current.tx) / vpRef.current.scale;
      const svgY = (e.clientY - rect.top - vpRef.current.ty) / vpRef.current.scale;

      dragRef.current = {
        nodeId,
        pointerId: e.pointerId,
        startClientX: e.clientX,
        startClientY: e.clientY,
        startNodeX: node.x,
        startNodeY: node.y,
      };

      // Fix node position so d3 doesn't fight us
      node.fx = svgX;
      node.fy = svgY;
      simulationRef.current?.alphaTarget(0.15).restart();
    },
    [],
  );

  const handleSvgPointerMove = useCallback((e: React.PointerEvent) => {
    const svg = svgRef.current;
    if (!svg) return;

    if (dragRef.current && dragRef.current.pointerId === e.pointerId) {
      // Node drag: track 1:1 from grab point
      const rect = svg.getBoundingClientRect();
      const svgX = (e.clientX - rect.left - vpRef.current.tx) / vpRef.current.scale;
      const svgY = (e.clientY - rect.top - vpRef.current.ty) / vpRef.current.scale;

      const node = simulationRef.current?.nodes().find((n) => n.id === dragRef.current!.nodeId);
      if (node) {
        node.fx = svgX;
        node.fy = svgY;
      }
      return;
    }

    if (panRef.current && panRef.current.pointerId === e.pointerId) {
      const dx = e.clientX - panRef.current.startClientX;
      const dy = e.clientY - panRef.current.startClientY;
      setViewport({
        ...vpRef.current,
        tx: panRef.current.startTx + dx,
        ty: panRef.current.startTy + dy,
      });
    }
  }, []);

  const handleSvgPointerUp = useCallback((e: React.PointerEvent) => {
    if (dragRef.current && dragRef.current.pointerId === e.pointerId) {
      const node = simulationRef.current?.nodes().find((n) => n.id === dragRef.current!.nodeId);
      if (node) {
        // Release fix — spring-settle
        node.fx = null;
        node.fy = null;
      }
      simulationRef.current?.alphaTarget(0).restart();
      dragRef.current = null;
    }
    if (panRef.current && panRef.current.pointerId === e.pointerId) {
      panRef.current = null;
    }
  }, []);

  // ── Board-level pointer (pan) ─────────────────────────────────────────────────

  const handleBoardPointerDown = useCallback((e: React.PointerEvent) => {
    if (dragRef.current) return; // node drag takes priority
    (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
    panRef.current = {
      pointerId: e.pointerId,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startTx: vpRef.current.tx,
      startTy: vpRef.current.ty,
    };
  }, []);

  // ── Scroll zoom ───────────────────────────────────────────────────────────────

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    setViewport((prev) => {
      const newScale = Math.max(0.3, Math.min(4, prev.scale * factor));
      const scaleRatio = newScale / prev.scale;
      const newTx = mouseX - (mouseX - prev.tx) * scaleRatio;
      const newTy = mouseY - (mouseY - prev.ty) * scaleRatio;
      return { tx: newTx, ty: newTy, scale: newScale };
    });
  }, []);

  // ── Node click popover ────────────────────────────────────────────────────────

  const handleNodeClick = useCallback(
    (e: React.MouseEvent, node: NodeState) => {
      e.stopPropagation();
      if (selectedNode?.id === node.id) {
        setSelectedNode(null);
        setPopoverScreen(null);
        return;
      }
      setSelectedNode(node);
      // Anchor popover to screen coords of node centre
      const svg = svgRef.current;
      if (svg) {
        const rect = svg.getBoundingClientRect();
        const screenX = node.x * viewport.scale + viewport.tx + rect.left;
        const screenY = node.y * viewport.scale + viewport.ty + rect.top;
        setPopoverScreen({ x: screenX, y: screenY });
      }
    },
    [selectedNode, viewport],
  );

  const edges = graph?.edges ?? [];

  // ── Render ────────────────────────────────────────────────────────────────────

  if (loading) return <CorrelationSkeleton />;

  if (error) {
    return (
      <FolderCard
        tabTitle={`CASE ${caseId} // BOARD`}
        tabPosition="left"
        tabBadge="TAB 02"
        classification="CROSS-CASE LINKAGE GRAPH & ENTITY RESOLUTION"
        elevation="raised"
      >
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <StampBadge label="LOAD ERROR" variant="terracotta" rotation={2} />
          <p className="mt-4 font-mono text-xs text-pine/60">{error}</p>
        </div>
      </FolderCard>
    );
  }

  const isEmpty = !graph || graph.nodes.length === 0;

  return (
    <FolderCard
      tabTitle={`CASE ${caseId} // BOARD`}
      tabPosition="left"
      tabBadge="TAB 02"
      classification="CROSS-CASE LINKAGE GRAPH & ENTITY RESOLUTION"
      elevation="raised"
    >
      <div className="flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="type-display-lg text-pine">Correlation Board</h2>
            <p className="type-body mt-1 text-pine/80">
              Confidence-weighted entity network resolving shared IMEIs, mule accounts,
              and direct communication channels across disparate evidentiary streams.
            </p>
          </div>
          <StampBadge label="LINKAGE MATRIX" variant="sage" rotation={2} subtext="LIVE GRAPH" />
        </div>

        <StitchedDivider orientation="horizontal" label="CONFIDENCE SIGNAL SPECIFICATION" />

        {/* Legend */}
        <div className="flex flex-wrap gap-3">
          {[
            { label: 'Strong ≥ 0.8', width: 3.5, color: '#C96F4F' },
            { label: 'Medium 0.5–0.8', width: 2, color: '#F59E0B' },
            { label: 'Weak < 0.5', width: 1, color: '#94A3B8' },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <svg width="28" height="8" aria-hidden="true">
                <line
                  x1="0"
                  y1="4"
                  x2="28"
                  y2="4"
                  stroke={item.color}
                  strokeWidth={item.width}
                  strokeLinecap="round"
                />
              </svg>
              <span className="font-mono text-[10px] font-semibold text-pine/60">{item.label}</span>
            </div>
          ))}
          <div className="ml-auto flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-pine/40">
              Scroll to zoom · Drag board to pan · Drag nodes to reposition
            </span>
          </div>
        </div>

        {/* Cork Board */}
        {isEmpty ? (
          <BoardEmptyState />
        ) : (
          <div
            ref={containerRef}
            className="relative overflow-hidden rounded-xl"
            style={{ height: 420 }}
          >
            <svg
              ref={svgRef}
              className="h-full w-full touch-none select-none"
              style={{
                background:
                  'radial-gradient(circle at 1px 1px, #C7B49B 1px, transparent 0) 0 0 / 20px 20px',
                backgroundColor: '#D9C9B2',
              }}
              onPointerDown={handleBoardPointerDown}
              onPointerMove={handleSvgPointerMove}
              onPointerUp={handleSvgPointerUp}
              onPointerCancel={handleSvgPointerUp}
              onWheel={handleWheel}
            >
              {/* Defs */}
              <defs>
                <filter id="card-shadow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.12" />
                </filter>
              </defs>

              <g transform={`translate(${viewport.tx},${viewport.ty}) scale(${viewport.scale})`}>
                {/* Edges (strings) */}
                <g>
                  {edges.map((edge) => {
                    const src = nodes.find((n) => n.id === edge.source);
                    const tgt = nodes.find((n) => n.id === edge.target);
                    if (!src || !tgt) return null;
                    const color = LINK_TYPE_COLORS[edge.link_type] ?? '#94A3B8';
                    const strokeWidth = CONFIDENCE_STROKE[edge.confidence_label] ?? 1;
                    // Slight curve for visual string effect
                    const mx = (src.x + tgt.x) / 2;
                    const my = (src.y + tgt.y) / 2 - 20;
                    return (
                      <path
                        key={`${edge.source}-${edge.target}`}
                        d={`M ${src.x} ${src.y} Q ${mx} ${my} ${tgt.x} ${tgt.y}`}
                        fill="none"
                        stroke={color}
                        strokeWidth={strokeWidth}
                        strokeOpacity={0.65}
                        strokeLinecap="round"
                      />
                    );
                  })}
                </g>

                {/* Nodes */}
                <g>
                  {nodes.map((node) => (
                    <NodeCard
                      key={node.id}
                      node={node}
                      isSelected={selectedNode?.id === node.id}
                      onPointerDown={handleNodePointerDown}
                      onClick={handleNodeClick}
                    />
                  ))}
                </g>
              </g>
            </svg>

            {/* Graph stats overlay */}
            <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg border border-pine/20 bg-cream/80 px-3 py-1.5 backdrop-blur-sm">
              <p className="font-mono text-[10px] font-semibold text-pine/70">
                {graph.nodes.length} entities · {graph.edges.length} links ·{' '}
                {(viewport.scale * 100).toFixed(0)}% zoom
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Anchored node popover */}
      <AnimatePresence>
        {selectedNode && popoverScreen && (
          <NodePopover
            key={selectedNode.id}
            node={selectedNode}
            edges={edges}
            allNodes={nodes}
            screenX={popoverScreen.x}
            screenY={popoverScreen.y}
            onClose={() => {
              setSelectedNode(null);
              setPopoverScreen(null);
            }}
          />
        )}
      </AnimatePresence>
    </FolderCard>
  );
};
