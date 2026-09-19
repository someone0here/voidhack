# Craft Audit — Phases 7–10 Frontend

**Rubric:** `apple-design` (emilkowalski/skills, installed via `npx skills@latest add
emilkowalski/skills`), covering interruptibility, direct manipulation, materials,
typography, and the eight design foundations from Apple's WWDC design talks,
translated for the web.

**Scope:** every interactive component built in Phases 7–10 — the design-system
primitives (`Button`, `FolderCard`, `StampBadge`, `GlassToolbar`, `Input`,
`StitchedDivider`) and the four screens (`IntakeScreen`, `CorrelationBoard`,
`RiskDesk`, `BriefViewer`) plus shell chrome (`AppShell`, `CaseSwitcher`,
`CaseRoomSidebar`, `EmptyCaseFolder`, `AppErrorBoundary`).

**Verification:** `tsc --noEmit`, `eslint --max-warnings 0`, and `vite build` all
pass clean after every fix below.

---

## 1. Interruptibility

**Checked:** tab switches (`CaseRoomSidebar`), node drags (`CorrelationBoard`),
panel/popover opens, route transitions (`AppShell`).

**Result: compliant, no fix needed.** All of these already animate via Framer
Motion springs (`layoutId` for the tab plate and sort-tab indicator, `dragConstraints`
+ spring transitions for draggable cards, spring-based `AnimatePresence` for
popovers), which read the live presentation value and re-target on interrupt by
construction — grabbing a moving element mid-flight doesn't cause a visible jump.
Rapid double-click/drag testing during an in-progress tab switch or node drag
confirms this: a second click re-targets the same spring instead of restarting
from a frozen "final" position.

One related gap did exist and is now fixed under §7: the correlation board's
*zoom* had no spring/interrupt story at its bounds at all — it hard-clamped.
See §7.

---

## 2. Response — feedback on pointer-down

**Found and fixed:**

- **`FolderCard`** (clickable, non-draggable cards — used for error states, the
  empty-case card, etc.) had `whileHover` but no `whileTap`. Feedback only
  appeared *after* the pointer moved, never on press. Added a `whileTap` that
  scales the card down instantly (or dims it under reduced motion), and made
  the card itself keyboard-focusable (see §8) so the same feedback fires for
  keyboard activation.
- **`RiskDesk`**'s `SortTabs` and `TypeFilterPills` buttons had no press state
  at all (no `whileTap`, no `:active` CSS). Added `active:scale-95`.

**Already compliant:** `Button` (`whileTap` on the press gesture, not release),
`BriefViewer`'s PDF export button, `IntakeScreen`'s drop tray (keyboard
`Enter`/`Space` and click both cover the interaction, and the tray responds to
`dragover` instantly, not on drop).

---

## 3. Reduced motion

**Found and fixed:**

- **`IntakeScreen`**'s per-file source-type dropdown menu used
  `transition={defaultSpringTransition}` unconditionally — the one animated
  element in the whole codebase that ignored `useReducedMotion()`. Every other
  spring in the app already branches on it. Fixed to branch to
  `reducedMotionTransition` like its siblings.

**Verified compliant everywhere else** by grepping every `transition={...}` and
`whileTap`/`whileHover`/`animate` call site against `useReducedMotion()`
branching: `Button`, `FolderCard`, `StampBadge`, `CaseSwitcher`, `CaseRoomSidebar`,
`AppShell`'s route transition, `CorrelationBoard`'s node popover, `RiskDesk`'s
expand/collapse, `EmptyCaseFolder`'s envelope-opening animation, and
`BriefViewer`'s wax seal all correctly degrade to a plain opacity cross-fade
with zero overshoot (`reducedMotionTransition` = `{ type: 'tween', duration:
0.15, ease: 'linear' }`, defined once in `design-system/motion.ts`).

Tested by forcing `prefers-reduced-motion: reduce` via DevTools' rendering
emulation: springs disappear, overshoot disappears, only fades remain.

---

## 4. Typography — size-specific tracking/leading

**Result: compliant, no fix needed.** `index.css`'s `.type-*` scale is
genuinely optical-size-aware, not a single fallback value dressed up as a
system:

| Class | Size | Tracking | Leading |
|---|---|---|---|
| `.type-display-hero` | 2.5–4rem (Fraunces) | `-0.025em` | `1.05` |
| `.type-display-lg` | 1.875–2.5rem (Fraunces) | `-0.02em` | `1.08` |
| `.type-display-md` | 1.5rem (Fraunces) | `-0.015em` | `1.15` |
| `.type-display-sm` | 1.125rem (Fraunces) | `-0.01em` | `1.25` |
| `.type-body` | 1rem (Inter) | `0` | `1.5` |
| `.type-body-sm` | 0.875rem (Inter) | `+0.005em` | `1.5` |
| `.type-data` | 0.875rem (mono) | `-0.01em` | `1.4` |
| `.type-data-xs` | 0.75rem (mono) | `-0.005em` | `1.35` |

Tracking tightens and goes negative as size increases (headings), body sits at
~0, and data blocks get their own comfortable-but-denser leading — exactly the
inverse relationship the skill specifies. `font-variation-settings: 'opsz'`
is also set per display size, which most implementations skip. No component
was found falling back to a single hardcoded `letter-spacing`/`line-height`
outside this scale.

---

## 5. Materials — translucency and layering

**Checked:** `GlassToolbar`, `CaseSwitcher`'s dropdown, `CorrelationBoard`'s
stats overlay, `DesignSystemRoute`'s floating return button.

**Result: compliant, no fix needed.**

- `GlassToolbar` is a genuine translucent layer (`rgba(248,246,238,0.78)` +
  `backdrop-filter: blur(20px) saturate(160%)`) sitting over `sticky top-0`
  content that scrolls underneath it — confirmed by scrolling a screen with
  the toolbar pinned.
- The one place a translucent surface stacks on top of another translucent
  surface — `CaseSwitcher`'s dropdown (`backdrop-blur-md` + `bg-cream`)
  rendering *inside* the translucent `GlassToolbar` — turns out not to trigger
  the legibility bug the skill warns about, because the dropdown's actual
  fill is `rgba(248,246,238,0.97)`, i.e. 97% opaque. It reads as a solid
  surface, not a second sheet of glass. No stacking violation.
- Every other "translucent-looking" surface in the app (`bg-cream/80
  backdrop-blur-sm` graph stats chip, `bg-cream/90` file chips) sits on a
  fully opaque parent (the khaki cork-board background, a solid `FolderCard`
  panel), so there's no compounding.

---

## 6. Spatial consistency — anchored origins, symmetric paths

**Found and fixed:**

- **`CorrelationBoard`'s node popover** computed its screen position once, at
  the moment of the click, from `node.x/y` and the viewport at that instant,
  then froze it in state. Because the graph keeps simulating (nodes drift as
  the d3-force layout settles) and the board can be panned/zoomed while the
  popover is open, the popover would silently detach from the node it was
  supposed to be anchored to — a direct violation of "anchor interactions to
  their source." Fixed by deriving the popover's screen position on every
  render from the node's *live* position (looked up by id from the ticking
  `nodes` array) and the *live* viewport transform, instead of storing a
  stale snapshot. It now tracks the node continuously.

**Already compliant:**

- `AppShell`'s route-transition `transformOrigin` is set to the Y coordinate
  of the sidebar tab that was actually clicked (`activeTabOriginY`), so a tab
  switch visually grows from the tab, not from the viewport center.
- `CaseRoomSidebar`'s active-tab indicator is a single `layoutId` plate that
  slides between tabs rather than two independent fade-in/fade-out elements,
  so enter and exit share one continuous path.
- `NodePopover` itself opens anchored at `screenX + 12, screenY - 20`
  (offset from the node, `transformOrigin: 'left top'`) and scales in/out from
  that same point — consistent in and out.

---

## 7. Rubber-banding — soft boundaries

**Found and fixed:** `CorrelationBoard`'s wheel-zoom hard-clamped scale with
`Math.max(0.3, Math.min(4, ...))`. Past the limit, further scroll input did
*nothing* — a dead stop, not resistance. The rubber-band formula
(`rubberBandClamp`) already existed in `design-system/motion.ts` but was
never called anywhere in the codebase.

Fixed by:
1. Letting scroll input push scale past `[0.3, 4]` but compressing the
   overshoot through `rubberBandClamp`, so it decelerates continuously instead
   of stopping dead — the further past the bound, the less it follows.
2. Adding a 160ms-debounced settle: once the wheel gesture goes idle with the
   scale still out of bounds, it eases back to the nearest bound over ~220ms
   (ease-out cubic), so the board visibly "lets go" and springs back rather
   than staying stuck at an overshot scale. A new wheel event before the
   settle finishes cancels it and resumes from the live value, so it's still
   interruptible.

Board *panning* has no fixed bounds today (it's an infinite canvas), so no
rubber-band was needed there — there's no edge to resist against.

---

## 8. Focus & keyboard

This was the checklist item with the most real findings — several surfaces
were effectively mouse/pointer-only.

**Found and fixed:**

- **Focus ring color.** `Button`, `CaseSwitcher`'s trigger, and
  `CaseRoomSidebar`'s tabs all used `focus-visible:ring-pine` instead of the
  terracotta accent the design language specifies everywhere else (stamps,
  dividers, the terracotta/khaki/sage palette). Changed all three to
  `ring-terracotta`. Also brought `Input`'s focus-within ring in line (was a
  pine-tinted box-shadow, now terracotta-tinted) and added a terracotta
  `focus-visible` ring to `FolderCard` and the `IntakeScreen` type-picker's
  trigger and options.
- **`CorrelationBoard` graph nodes** were an SVG `<g>` with only an `onClick` —
  no `tabIndex`, `role`, or `onKeyDown`. The correlation board, arguably the
  most information-dense screen in the app, was entirely unreachable by
  keyboard. Fixed: nodes are now `role="button" tabIndex={0}` with an
  `aria-label` describing the entity/cluster, respond to `Enter`/`Space`, and
  get a visible terracotta focus outline.
- **Escape didn't close any popover/dropdown in the app.** Fixed for all
  three: `CaseSwitcher`'s case-picker dropdown, `CorrelationBoard`'s node
  popover, and `IntakeScreen`'s per-file source-type menu.
- **`IntakeScreen`'s source-type dropdown** also had no outside-click
  dismissal (every other dropdown in the app does). Added, matching the
  pattern already used in `CaseSwitcher`.
- **`EmptyCaseFolder`**'s "click anywhere on this folder to open it" envelope
  was a `motion.div` with `onClick` and no keyboard path. (A real `<Button>`
  inside it already covered keyboard users, so this wasn't a hard blocker,
  but it broke parity with the "click anywhere" affordance.) Added
  `role="button"`, `tabIndex`, `onKeyDown`, and a matching focus ring/press
  state for consistency.

**Already compliant:** `IntakeScreen`'s drop tray (`role="button" tabIndex={0}`
with `Enter`/`Space` handling was already correct — a good reference
implementation), tab order throughout (no `tabIndex` traps or skips found),
`RiskDesk`'s reason-code disclosure button (native `<button>`, works by
default).

---

## Accessibility pass

### Color contrast (WCAG AA)

Computed relative-luminance contrast ratios for every text/background
combination actually used in the app (not just the raw palette):

| Pairing | Before | After | AA target |
|---|---|---|---|
| `terracotta-dark` text on `khaki` | 2.95:1 | **4.59:1** | 4.5:1 (normal text) |
| `terracotta-dark` text on `cream` | 4.42:1 | **6.88:1** | 4.5:1 |
| `cream` text on `Button` primary bg | 3.31:1 | **6.88:1** | 4.5:1 |
| `white` text on `Button` danger bg | 3.76:1 | **6.11:1** | 4.5:1 |
| `pine` on `khaki`/`cream`/`sage-dark` combos | 5.6–11.0:1 | unchanged | — |

The first two rows matter because `terracotta-dark` is the color used for
every "FAILED", critical-score, and error-detail label in the app — all of
them render as small (9–11px) bold mono text sitting on `FolderCard`'s solid
khaki surface or `bg-cream/90` chip backgrounds, both of which are below the
4.5:1 floor for text that size at the original shade. Darkened
`terracotta.dark` from `#B15A3B` to `#84432C` in `tailwind.config.ts` and the
matching CSS custom property in `index.css` — one change, propagates
everywhere the token is used.

Separately, `Button`'s primary variant (cream text on the *lighter*
`terracotta` DEFAULT) and danger variant (white on `dossier-crimson`) both
independently failed contrast regardless of the token fix above, since
they're bold/semibold at 12–16px — not large enough to qualify for the
3.0:1 large-text exception. Switched both to darker backgrounds
(`terracotta-dark`, `red-700`) and moved hover/active state from a color swap
to opacity, so the ratio holds during interaction instead of drifting back
toward the failing lighter shade on hover.

No other text/background combination in the palette (pine-on-khaki,
pine-on-cream, sage-dark-on-cream, cream-on-pine) fell below 4.5:1; several
clear 7–11:1.

### Color is never the only risk signal

Checked every place risk/status is communicated: `StampBadge` always renders
its variant color *alongside* a text label (`subtext` carries "CRITICAL" /
"HIGH" / "MEDIUM" / "LOW" tier names, not just a colored pill), and
`BriefViewer`'s chain-integrity indicator pairs its color with both an icon
(⚖ / ⚠) and text ("Chain Intact" / "Chain Broken"). This was already correct
in the original implementation — no fix needed, called out here because it
was explicitly in scope to verify.

---

## Files touched

- `tailwind.config.ts`, `src/index.css` — `terracotta.dark` contrast fix
- `src/design-system/primitives/Button.tsx` — contrast-safe variants, terracotta focus ring
- `src/design-system/primitives/FolderCard.tsx` — press feedback, keyboard access
- `src/design-system/primitives/Input.tsx` — terracotta focus ring
- `src/components/shell/CaseSwitcher.tsx` — terracotta focus ring, Escape-to-close
- `src/components/shell/CaseRoomSidebar.tsx` — terracotta focus ring
- `src/components/cases/EmptyCaseFolder.tsx` — keyboard access on the envelope
- `src/app/screens/CorrelationBoard.tsx` — rubber-band zoom + settle-back, node
  keyboard access, popover Escape-to-close + live position tracking
- `src/app/screens/RiskDesk.tsx` — press feedback + focus rings on sort/filter controls
- `src/app/screens/IntakeScreen.tsx` — reduced-motion fix, outside-click +
  Escape on the source-type dropdown, focus rings

`tsc --noEmit`, `eslint --max-warnings 0`, and `vite build` all pass clean on
the final state.
