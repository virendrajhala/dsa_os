# Dashboard Phase 3 — Visual Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the dashboard's visual system from a single token sheet — one theme definition via `light-dark()`, per-component CSS files, unified validated chart palette — and delete `legacy.css` (6,616 lines) entirely.

**Architecture:** CSS cascade layers are the kill mechanism: `@layer legacy, tokens, base, components;`. `legacy.css` gets wrapped in `@layer legacy {…}` so every later layer beats it regardless of selector specificity — no override wars, no specificity escalation. Each view then gets a component file in the `components` layer that FULLY specifies it from tokens. A view is "migrated" when it renders correctly with the legacy stylesheet disabled (`document.querySelector('#legacy-css').disabled = true` — the independence check). When every view passes, deleting legacy.css is a no-op by construction, verified by screenshot diff.

**Tech Stack:** CSS layers, nesting, `light-dark()` + `color-scheme`, `color-mix()`, CSS custom properties. Palette = the validated dataviz reference instance (values inlined below — do NOT invent colors).

## Global Constraints

- **Zero build step, zero dependencies.** No npm/CDN/webfonts — system font stack only.
- **JS changes limited to**: class-name additions on generated DOM, inline `style="fill: var(--series-N)"`-style token references in chart renderers, and deleting now-dead class emissions. No behavior changes.
- **Layer discipline:** every stylesheet declares its rules inside its named layer. Unlayered CSS is FORBIDDEN (it would beat all layers). `!important` is forbidden in new CSS (13 `!important`s exist in legacy; important declarations REVERSE layer order — each must be neutralized when its component migrates: find them with `grep -n '!important' css/legacy.css` and either replicate intent in the component file or confirm the rule is dead).
- **Design identity keeps:** mono numerals (`.num` stays monospace — deliberate signature, overriding the palette reference's sans-figures advice); the constellation's ink plate in both themes; density.
- **Chart palette is the validated set inlined in Task 1** — adopted with its reference surfaces verbatim, so its CVD validation carries over. If you change ANY surface or series hex, STOP: the validation no longer holds (revalidation needs the dataviz validator; do not eyeball).
- Dataviz rules that bind every chart touch-up: series identity by fixed slot order, never cycled; text wears ink tokens, never series colors; status colors (good/warn/…) never used as series; ≥2 series ⇒ legend; sequential = one hue light→dark.
- **Commits:** conventional, no AI attribution, one per task, branch `feat/dashboard/worldclass-upgrade`.
- **Verification:** `make web-dashboard` (background); ALWAYS append `?cb=<n>` cache-busters when loading in Playwright (server can serve stale assets — proven in Phase 2). Screenshot every affected view in BOTH themes per task; `tests.html` stays `PASS (24)`.
- **Route map for walks:** `#/today`, `#/plan`, `#/problems`, `#/practice`, `#/curriculum` (+`?s=` for stages/ladder/skills/patterns), `#/evidence/performance|memory|consistency|log`. Focus mode via `f`; palette via Ctrl+K; modal via any problem click.

## Design language (the taste decisions, fixed here)

- **Neutrals:** warm-gray system (from the validated reference): light page `#f9f9f7`, light surface `#fcfcfb`; dark page `#0d0d0d`, dark surface `#1a1a19`. Hairline borders, not boxes-in-boxes.
- **Accent:** blue `#2a78d6` light / `#3987e5` dark (= series-1; also the app's historical accent).
- **Type:** `system-ui, -apple-system, "Segoe UI", sans-serif`; scale 12 / 13 (body) / 14 / 16 / 20 / 28; weights 400/500/650; `.microlabel` = 11px, 0.08em tracking, uppercase; `.num` = existing mono stack + `font-variant-numeric: tabular-nums`.
- **Spacing:** 4px grid tokens only (no raw px paddings in new CSS).
- **Radius:** 6 (controls) / 10 (cards) / 14 (modals). **Shadows:** 2 tiers only.
- **Motion:** unchanged Phase-1 tokens.
- **Restraint rules:** color only where it carries meaning (status, series, accent-on-interactive); everything else ink-on-surface. One border color. No gradients except the two shadow tiers and heatmap ramps.

---

### Task 1: Layer scaffold + full token sheet (global retheme)

**Files:**
- Modify: `web_dashboard/css/legacy.css` (wrap in layer), `web_dashboard/index.html` (id the legacy link), all 8 `css/components/*.css` (wrap each in `@layer components {…}`)
- Rewrite: `web_dashboard/css/tokens.css`

**Interfaces:**
- Produces: the token vocabulary EVERY later task uses (do not invent new token names downstream):
  `--bg --surface --surface-2 --line --line-strong --text --text-2 --muted --accent --focus-ring --good --warn --bad --serious --series-1..8 --seq-1..5 --sp-1..8 --fs-0..5 --radius-s/m/l --shadow-sm/lg --mono`.
- Legacy consumes some of these same names (`--bg --surface --line --text --muted --good --warn --bad --accent --series-*` + refresh-layer extras `--bg-2 --surface-3 --surface-soft --line-strong --control-bg --focus-ring --shadow-sm --shadow-lg --radius --shadow`): redefining them at `:root` AND `.main` in the tokens layer beats every legacy scope (layers beat specificity), which rethemes ALL legacy views in one move.

- [x] **Step 1: Wrap legacy** — first line of `css/legacy.css` becomes `@layer legacy {`, append closing `}` at EOF. In index.html give its link `id="legacy-css"`. Wrap each of the 8 component files' entire content in `@layer components {` … `}`.

- [x] **Step 2: Rewrite css/tokens.css** (declares layer order FIRST — it is the first stylesheet loaded):

```css
@layer legacy, tokens, base, components;

@layer tokens {
  :root { color-scheme: light dark; }
  :root[data-theme="light"] { color-scheme: light; }
  :root[data-theme="dark"] { color-scheme: dark; }

  :root, .main {
    /* surfaces + ink (validated reference chrome) */
    --bg: light-dark(#f9f9f7, #0d0d0d);
    --bg-2: light-dark(#f4f3f0, #131312);
    --surface: light-dark(#fcfcfb, #1a1a19);
    --surface-2: light-dark(#f4f3f0, #222221);
    --surface-3: var(--surface-2);
    --surface-soft: var(--surface-2);
    --control-bg: var(--surface);
    --line: light-dark(#e1e0d9, #2c2c2a);
    --line-strong: light-dark(#c3c2b7, #383835);
    --text: light-dark(#0b0b0b, #ffffff);
    --text-2: light-dark(#52514e, #c3c2b7);
    --muted: #898781;
    --accent: light-dark(#2a78d6, #3987e5);
    --focus-ring: color-mix(in oklab, var(--accent) 60%, transparent);

    /* status (fixed, never series) */
    --good: #0ca30c;
    --warn: light-dark(#c98500, #fab219);
    --serious: #ec835a;
    --bad: light-dark(#d03b3b, #e66767);

    /* categorical series - validated order, never re-order or cycle */
    --series-1: light-dark(#2a78d6, #3987e5);
    --series-2: light-dark(#eb6834, #d95926);
    --series-3: light-dark(#1baf7a, #199e70);
    --series-4: light-dark(#eda100, #c98500);
    --series-5: light-dark(#e87ba4, #d55181);
    --series-6: #008300;
    --series-7: light-dark(#4a3aa7, #9085e9);
    --series-8: light-dark(#e34948, #e66767);

    /* sequential blue ramp, 5 steps low->high (heatmaps): low recedes to surface */
    --seq-1: light-dark(#cde2fb, #0d366b);
    --seq-2: light-dark(#86b6ef, #1c5cab);
    --seq-3: light-dark(#3987e5, #2a78d6);
    --seq-4: light-dark(#1c5cab, #5598e7);
    --seq-5: light-dark(#0d366b, #86b6ef);

    /* scale */
    --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px;
    --sp-5: 20px; --sp-6: 24px; --sp-7: 32px; --sp-8: 48px;
    --fs-0: 11px; --fs-1: 12px; --fs-2: 13px; --fs-3: 14px;
    --fs-4: 16px; --fs-5: 20px; --fs-6: 28px;
    --radius-s: 6px; --radius-m: 10px; --radius-l: 14px;
    --radius: var(--radius-m);
    --mono: "SFMono-Regular", ui-monospace, "Cascadia Mono", Consolas, monospace;
    --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.06);
    --shadow-lg: 0 8px 28px rgb(0 0 0 / 0.16);
    --shadow: var(--shadow-sm);

    /* motion (carried from phase 1) */
    --dur-feedback: 120ms; --dur-overlay: 200ms; --dur-view: 280ms;
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  }

  @media (prefers-reduced-motion: reduce) {
    :root { --dur-feedback: 0ms; --dur-overlay: 0ms; --dur-view: 0ms; }
    ::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) { animation: none !important; }
  }
  ::view-transition-old(root) { animation-duration: calc(var(--dur-view) * 0.66); }
  ::view-transition-new(root) { animation-duration: var(--dur-view); animation-timing-function: var(--ease-out); }
}
```

(The `!important` in the reduced-motion view-transition rule is the ONE permitted exception — it's a motion-kill, and layer-reversal works in its favor.)

- [x] **Step 3: Verify the retheme** — reload both themes, walk all routes. EXPECTED: global palette shift to warm neutrals + validated series everywhere tokens reach; hardcoded-hex spots (291 in legacy) will look inconsistent — that is Tasks 3-8's job, note the worst offenders per view but don't fix here. REQUIRED-INTACT: layout unbroken everywhere, theme toggle still flips both directions, view transitions still fire, tests.html `PASS (24)`, zero console errors. If any view's layout (not color) broke, a legacy `!important` or unlayered leak is the suspect — fix before committing.

- [x] **Step 4: Commit**

```bash
git add web_dashboard/css web_dashboard/index.html
git commit -m "feat/dashboard: cascade-layer scaffold + single light-dark token sheet rethemes app"
```

---

### Task 2: Base layer — typography, controls, shared primitives

**Files:**
- Create: `web_dashboard/css/base.css` (link AFTER tokens.css, before legacy.css)

**Interfaces:**
- Produces `@layer base` rules for: `body` (font stack, `--fs-2`, `--text` on `--bg`), headings scale (h1 `--fs-5`, h2 `--fs-5`, h3 `--fs-4`, h4 `--fs-3`; weight 650; margins on the 4px grid), `.microlabel`, `.eyebrow`, `.num` (mono + `tabular-nums`), links, `input/select/button` (control height 30px, `--radius-s`, `--control-bg`, hairline `--line`, focus-visible ring `0 0 0 2px var(--focus-ring)`), `.pill`, `.mini-button`, `.icon-button`, `.metric-card`, `.panel`, `.section`, `.section-head`, `.chart-note`, `.chart-legend`, `.table-wrap table` (header `--text-2` uppercase `--fs-0`, row hairlines, hover wash `color-mix(in oklab, var(--text) 4%, transparent)`), `dialog::backdrop`, scrollbars (`scrollbar-width: thin; scrollbar-color: var(--line-strong) transparent`), `.data-warning`, `.small-muted`, `.stack`.

- [x] **Step 1: Write base.css** — fully specify each primitive above from tokens (no raw px outside the scale, no hex). These selectors deliberately re-cover legacy's most-repeated shared rules; base layer beats legacy so the old 25-selector repeated lists become inert without being touched.
- [x] **Step 2: Verify** — all routes × both themes: tables, pills, buttons, inputs, panels, section heads consistent; focus-visible ring on every control (Tab walk); no double-borders or clipped text anywhere. tests green.
- [x] **Step 3: Commit** — `git add web_dashboard/css/base.css web_dashboard/index.html && git commit -m "feat/dashboard: base layer - type scale, controls, shared primitives on tokens"`

---

### Tasks 3-8: View migrations (same procedure each — written once here, referenced per task)

**PROCEDURE (applies to every migration task):**
1. Inventory: `grep -oE '\.[a-z][a-z0-9-]+' css/legacy.css | sort -u` filtered to the view's class prefixes (listed per task) + inspect the view's DOM in DevTools for the real class list.
2. Author `css/components/<name>.css` in `@layer components`, fully specifying every class the view emits, from tokens only. Add `<link>` to index.html.
3. Replace hardcoded colors in the view's JS renderers (SVG `fill`/`stroke` attributes) with `var(--series-N)` / `var(--seq-N)` / ink tokens via inline style or class — series slot assignment stays FIXED per entity.
4. Neutralize any of the 13 legacy `!important`s that hit this view.
5. **Independence check:** in DevTools run `document.querySelector('#legacy-css').disabled = true` — the view must render correctly without legacy. Re-enable after.
6. Screenshot both themes; check against the restraint rules; commit.

### Task 3: Shell — app frame, topbar, modal, overlays polish

**Files:** Create `css/components/shell.css`; touch up `sidebar.css`, `tabs.css`, `filterbar.css`, `palette.css`, `tooltip.css`, `focus.css`, `keyboard.css` (retoken: replace any remaining hex with tokens).
**Covers:** `.app-shell .sidebar .brand .rail-footer .source-card .main .topbar .topbar-subtitle .modal .modal-shell .modal-head .modal-body` + the Phase-1/2 component files' hexes.
**Design:** sidebar on `--bg-2` with hairline right border; topbar transparent on `--bg`, NOT sticky-broken (keep current stickiness behavior); modal `--radius-l` + `--shadow-lg`; palette/tooltip/focus surfaces on `--surface` + `--line`.
Commit: `feat/dashboard: shell migrated - frame, topbar, modal, overlay components on tokens`

### Task 4: Today + Plan views

**Files:** Create `css/components/today.css`, `css/components/plan.css`.
**Covers Today:** `.briefing-next .next-action .contract-list .trajectory .trajectory-strip .trajectory-station .gridpaper .due-queue .due-row .pace-tiles .briefing-grid` (+ metric-card variants).
**Covers Plan:** `.weekbars .milestone-board .insight-chart .pace-projection` + burnup SVG ink (axis `--muted`, grid `--line`, actual line `--series-1`, projection dashed `--muted`, target `--line-strong`).
**Design:** next-action is the ONE hero card — `--surface`, accent left rail 3px, `--fs-6` mono headline; trajectory strip stations use status tokens; due-row overdue flag = `--bad` text + icon (never color alone); deload weeks in weekbars = `--muted` texture, not a new hue.
Commit: `feat/dashboard: today + plan views migrated to component css`

### Task 5: Problems + Practice views

**Files:** Create `css/components/problems.css`, `css/components/practice.css`.
**Covers:** `.browser-layout .browser-tree .browser-table` + status glyph colors (`✓`=`--good` `★`=`--accent` `✗`=`--bad` `·`=`--muted`, each beside its text label); `.weakness-grid .edge-case-grid .nudge-card .drill-row`.
**Design:** tree selection = accent inset bar + wash (`color-mix(in oklab, var(--accent) 10%, transparent)`); frequency stars `--warn` in dark/`--series-4` treatment NOT as series — use `--muted` filled stars with `--text-2` count instead (color restraint).
Commit: `feat/dashboard: problems + practice views migrated`

### Task 6: Curriculum views + constellation port

**Files:** Create `css/components/curriculum.css`, `css/components/constellation.css`.
**Covers:** `.stage-board .skill-grid` (+ pattern grid, ladder table specifics beyond base tables).
**Constellation:** move the ENTIRE self-scoped `.constellation-plate` block (legacy.css:6206-EOF) into `css/components/constellation.css` inside `@layer components`, near-verbatim — it keeps its ink plate in both themes BY DESIGN. Only retoken its accent/status references where they exist; do not restyle the plate.
Commit: `feat/dashboard: curriculum views migrated; constellation ported with its ink plate`

### Task 7: Evidence views (charts, heatmap, calendar, tiles)

**Files:** Create `css/components/evidence.css`; retoken `features.css` (streaks/badges/bests) fully.
**Covers:** `.insight-stack .sparkline-card .bar-list .retention-tiles .memory-gauges .heatmap .heatmap-legend .calendar-layout .calendar-grid .calendar-detail .streak-strip .badge .bests-card .best-row`.
**Charts JS retoken (the big one):** heatmap cells → `--seq-1..5` (5-step quartile scale, both themes; the solve/revision diagonal split keeps two SEQUENTIAL treatments, not two hues — solves = seq ramp, revisions = seq ramp at 55% opacity); hint-independence line `--series-1`, mastery bands `--line`-tinted washes; mock trend `--series-1` + target `--line-strong`; time chart bars `--series-1`, difficulty split if present = series 1/2/3 fixed by difficulty; thinking bars `--series-1` with `--muted` track; retention gauge needle `--text`, target tick `--good`, arc track `--line`; maturity donut segments = `--muted`→`--seq-2`→`--seq-3`→`--seq-4` (ordered maturity = sequential, NOT categorical); forecast bars `--series-1`, backlog-if-idle area `--warn` at 18% opacity.
Commit: `feat/dashboard: evidence views + all chart inks migrated to validated palette`

### Task 8: Sweep — remaining selectors, the 13 !importants, dead-code delete

**Files:** whatever remains.

- [x] **Step 1:** `document.querySelector('#legacy-css').disabled = true` and walk EVERY route both themes + modal + focus mode + palette + help overlay. List every visual defect → each is an unmigrated selector; fix in the owning component file.
- [x] **Step 2:** `grep -n '!important' css/legacy.css` — confirm all 13 are either replicated (intent) or dead; document each in the commit body.
- [x] **Step 3:** Delete dead JS class emissions if any renderer emits classes no stylesheet defines (grep emitted class names against new CSS).
- [x] Commit: `refactor/dashboard: close independence gaps - all views render without legacy.css`

---

### Task 9: Delete legacy.css

**Files:** Delete `web_dashboard/css/legacy.css`; modify `index.html` (remove link); `css/tokens.css` (drop `legacy,` from the layer order line).

- [x] **Step 1:** Capture screenshots of every route × both themes WITH legacy enabled (post-Task-8 state).
- [x] **Step 2:** `git rm web_dashboard/css/legacy.css`, remove the link + layer name.
- [x] **Step 3:** Re-capture identical screenshots. Diff: differences must be ZERO (Task 8 proved independence; this proves it cold). Any diff → restore file, fix the gap in the owning component, retry.
- [x] **Step 4:** Full regression: tests.html `PASS (24)`; keyboard-only pass; reduced-motion pass; focus/palette/modal/tooltips/drill-downs.
- [x] **Step 5: Commit**

```bash
git add -A web_dashboard
git commit -m "refactor/dashboard: delete legacy.css - token-driven component css is the only styling

6616-line 6-layer stylesheet retired; every view fully specified in
css/base.css + css/components/* from the single tokens.css sheet"
```

---

### Task 10: Final design walk + memory-worthy notes

- [ ] **Step 1:** Fresh-eyes walk of every route × both themes at 1440px and 1100px widths: hunt label collisions, cramped spacing off the 4px grid, color used without meaning, series-order violations, contrast complaints (text < AA on its surface — fix with ink tokens, never by inventing hexes).
- [ ] **Step 2:** Cosmetic leftovers from Phase 2: rail inner scrollbar when all groups expanded — style via base scrollbar rules or `overflow: overlay`-style thin treatment in sidebar.css.
- [ ] **Step 3:** Fix findings; commit `fix/dashboard: phase-3 design walk fixes`.
- [ ] **Step 4:** Report: per-task commits, the before/after line counts (`wc -l css/*.css css/components/*.css`), any token additions made mid-flight (each needs a one-line justification), remaining known issues.

---

## Self-review notes (already applied)

- Spec coverage: tokens in oklch — DELIBERATE DEVIATION: values are the validated palette's hex (adopting them verbatim preserves its CVD validation; converting to oklch notation adds risk, zero benefit — `light-dark()`/`color-mix()` still used as specced). One theme definition ✓ (T1), spacing/type scale ✓ (T1/T2), per-component files ✓ (T3-8), legacy deleted ✓ (T9), GitHub-style 5-step heatmap ✓ (T7 `--seq-*`), unified chart palette via dataviz method ✓ (T1 + T7), mono numerals kept ✓, ink plate kept ✓ (T6), Linear/Vercel restraint ✓ (design-language block).
- The layer mechanism makes "migrate then delete" safe without the forbidden legacy-rule surgery: legacy rules are never edited (except the two wrapper lines + the constellation block move), they're out-competed, then the whole file is deleted at once behind a zero-diff screenshot gate. This respects the 2026-08-04 decision (no mechanical dedup of legacy) while still killing the file.
- Type consistency: token names in T1 are the only vocabulary used in T2-T8; independence-check procedure identical in T3-8 step 5 and T8/T9 gates; `#legacy-css` id set in T1 step 1, used in T8/T9.
- Known risks flagged: layer-wrapping flips precedence for the 8 existing component files (they already win by load order today — wrapping preserves outcome, verified in T1 step 3); `!important` layer-reversal (inventoried T8 step 2); stale-asset serving (cache-buster rule in constraints).
