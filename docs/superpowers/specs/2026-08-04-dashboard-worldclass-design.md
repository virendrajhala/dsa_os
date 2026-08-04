# Dashboard World-Class Upgrade — Design Spec

Date: 2026-08-04
Status: approved in brainstorming session; awaiting written-spec review
Delivery: feature branch per phase; commits/PRs only with explicit user go-ahead

## Goal

Upgrade `web_dashboard/` into a best-in-class DSA-prep dashboard: smooth, keyboard-first,
information-dense but calm. Three phases, executed in this order:

1. **Phase 1 — Capabilities** (command palette, keyboard nav, drill-down/tooltips, motion, feature packs)
2. **Phase 2 — UX + Information Architecture** (nav, workspace layouts, routing)
3. **Phase 3 — Visual overhaul** (token-driven CSS rebuild, legacy CSS deleted)

## Constraints

- **Zero build step, zero dependencies.** Native ES modules + split CSS files; served by the
  existing `scripts/serve_dashboard.py` (`make web-dashboard`, 127.0.0.1:8765).
- **`file://` support dropped** (accepted): ES modules require http. Server-only from now on.
- **Dashboard stays read-only.** `update_progress.py` remains the only writer. Every new
  feature derives from existing JSON; no new stored state (localStorage allowed for UI
  prefs only: theme, sidebar state, palette frecency, what-if slider).
- **Python side untouched**: `/api/feed` contract unchanged; dashboard never recomputes what
  `_shared.build_dashboard_feed` provides.
- **Desktop-first, keyboard-first.** Mobile must not break; no dedicated mobile layouts.
- Target browsers: latest Chrome/Firefox only.

## Architecture

```
web_dashboard/
  index.html
  css/
    tokens.css          # single source: light-dark() + oklch, spacing/type scale, motion tokens
    legacy.css          # current styles.css, unchanged until Phase 3 replaces it
    components/*.css    # new + rebuilt components, one file each
  js/
    main.js             # boot: load data → render active workspace only
    state.js            # shared state + derived selectors
    data.js             # fetch/feed/degradation; explicit banner replaces silent port cliff
    svg.js              # the ONE svg/el helper (replaces 5 duplicated copies)
    engine/
      keyboard.js       # global key router, G-chords, ? help overlay
      palette.js        # Ctrl+K command palette
      tooltip.js        # shared tooltip + crosshair engine (Popover API + anchor positioning)
      drilldown.js      # clickable-anything → underlying-problems modal
      motion.js         # durations/easings, view transitions, prefers-reduced-motion gate
    features/           # streaks.js retention.js maturity.js forecast30.js pace.js
                        # bests.js badges.js nudges.js focus.js
    legacy/app.js       # current monolith as a module; shrinks as views migrate in P2–P3
```

Mechanics:

- `legacy/app.js`: minimal edit — un-IIFE, export `state` + a render registry. New modules
  import from it. No behavior change.
- **Lazy rendering is infra** (Phase 1): only the active workspace renders on load and on
  visibilitychange; workspace switch renders on demand. Replaces the current
  29-renders-every-time model.
- New CSS is scoped per component file appended after `legacy.css` — never a new override
  layer on old selectors (per the 2026-08-04 CSS-layers decision: replacement, not dedup).

## Phase 1 — Capabilities

### Command palette (Ctrl+K)
- Index: all views, all problems (id/title), skills, patterns, actions (theme toggle, focus
  mode, go-to filters).
- Fuzzy + typo-tolerant matching; frecency boost from localStorage; empty query shows
  recents + suggested actions (never blank).
- Grouped results: Recent / Actions / Go to / Problems; shortcut hint on each row.
- Keyboard model: arrows move, Enter executes, Esc clears query then closes. Opens
  instantly (no entrance animation).

### Keyboard model
- `G` chords: `g t` Today, `g p` Plan, `g b` Problem browser, `g c` Curriculum,
  `g e` Evidence, `g w` Practice.
- `j/k` + Enter on due queue, tables, problem browser; `/` focuses the relevant search;
  `t` toggles theme; `f` focus mode; `?` shortcut-help overlay.
- Revision calendar keeps its existing roving-tabindex arrow nav.
- Rule: nothing in the keyboard critical path animates.

### Universal drill-down + tooltips
- One tooltip engine: Popover API + CSS anchor positioning (no positioning JS).
- Crosshair + shared tooltip on all time-series: hint independence, mock trend,
  time invested, burnup, forecast.
- Per-cell tooltips on activity heatmap + revision calendar.
- Every tile, bar, cell, and constellation node is clickable → existing `#skill-modal`
  listing underlying problems/revisions with jump-links. Rule: **no dead pixels**.

### Motion system
- Tokens: 120ms feedback / 200ms overlays / 280ms workspace switch; ease-out entrances
  (`cubic-bezier(0.16, 1, 0.3, 1)`), exits ~2/3 duration; opacity + transform only.
- Workspace switches via same-document `document.startViewTransition`.
- `@starting-style` for modal/palette entrances; count-up animation on headline numbers
  (once per load); chart draw-in ≤400ms.
- Everything gated by `prefers-reduced-motion` (collapse to instant/fade).

### Feature packs (all read-only derivations)
- **Motivation**: streak + max-streak headlines beside heatmap. Active day = at least one
  solve OR revision. No grace rule — a missed day breaks the streak. Monthly badge strip
  (months where plan contract fully met); personal-bests card (fastest solve per
  difficulty, best mock score, longest streak); near-complete nudge cards ("2 to finish")
  sorted by closeness.
- **Memory analytics**: true-retention gauge — pass rate of recalls attempted on *mature*
  problems vs 90% target, where mature = revision_stage ≥ 2 (past the 21-day R2 recall)
  or MASTERED, aligned to the existing R1–R4 policy in `scoring.json`; maturity donut
  (new / learning [stage 0–1] / young [stage 2–3] / mature [MASTERED]) with hover-swap
  center stat; due forecast extended to 30 days with backlog-if-idle shading (Anki
  Future Due pattern).
- **Pace**: burnup chart gains velocity-projected finish date ("at current pace: <date>")
  + client-side what-if hrs-per-week slider (localStorage, display-only).
- **Focus mode**: `f` or palette → zero-chrome screen: current next-action problem, elapsed
  count-up timer with a passive "typical: Nm" marker (median `time_taken_minutes` for the
  same difficulty from history), edge-case checklist peek; Esc exits. No recording — CLI
  stays the writer.

## Phase 2 — UX + Information Architecture

- **Sidebar rebuilt**: 6 collapsible groups, open/closed state persisted; collapses to
  icon rail with tooltip labels; active = tint + accent bar. Fixes in same pass:
  nav/DOM order mismatch (`#deferred`), orphan `#thinking-dimensions` gets a home,
  duplicate topbar/section titles removed (topbar is the single title source).
- **Evidence workspace** → 4 sub-tabs: *Performance* (mock trend, hint independence,
  thinking profile + dimensions), *Memory* (retention, revision calendar, forecast),
  *Consistency* (heatmap, streaks, time invested), *Log* (problem history, deferred).
- **Today = mission control**: next action + today contract + 4 KPI tiles + trajectory
  hero. Everything else behind navigation, not on first paint (Stripe rule: ≤ ~7 elements
  per screen).
- **One filter system**: topbar `#list-toolbar` and browser toolbar merge into a single
  contextual filter bar; one status vocabulary.
- **URL per view**: reliable hash routing — deep-linkable, back/forward works, restores
  active workspace, Evidence sub-tab, and browser filters on reload.

## Phase 3 — Visual overhaul

- **CSS rebuilt from tokens; legacy deleted.** `tokens.css` in oklch with `light-dark()` —
  one theme definition replaces six override layers; hover/tint scales via `color-mix`;
  4px spacing grid + type scale tokens; CSS nesting; per-component files. `legacy.css`
  deleted at completion.
- **Design language**: Linear/Vercel-grade restraint — dense but calm; mono-numeral
  styling kept as signature; GitHub-style 5-step sequential scale for heatmaps; unified
  chart palette (dataviz color methodology applied at build time); constellation keeps its
  ink plate as the one deliberate dark island in light theme.
- View-by-view migration out of `legacy/app.js` + `legacy.css` completes here.

## Error handling

- `data.js` distinguishes and surfaces: server not running / wrong port / feed 500 /
  stale data — each gets an explicit banner message (no more silent degradation).
- Palette and drill-down fail soft: missing index data → group hidden, never a throw.
- Focus mode with no next action → shows due-queue top item; empty queue → empty state.

## Testing / verification

- Per phase: Playwright walk of all workspaces × both themes × reduced-motion;
  keyboard-only pass (every feature reachable without mouse).
- Per migrated view (P2–P3): before/after screenshot sign-off. No computed-style-equality
  harness in Phase 3 — change is intentional.
- Perf check: on Today, only Today renders (verify via render-registry instrumentation).

## Explicitly out of scope

- Anything requiring new persisted domain state (repair tokens as stored objects, custom
  tags, linked notes, weekly wagers).
- Mobile-dedicated layouts.
- Python/`_shared.py` changes.
- Hour-of-day analytics (completion timestamps lack time-of-day).
