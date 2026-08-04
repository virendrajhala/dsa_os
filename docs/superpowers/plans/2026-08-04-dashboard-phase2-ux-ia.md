# Dashboard Phase 2 — UX + Information Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the dashboard's navigation and layout: reliable URL routing, a rebuilt collapsible sidebar, Evidence consolidated into 4 sub-tabs, Today reduced to true mission control, and one unified filter system.

**Architecture:** Builds on the Phase-1 module architecture (`js/legacy/app.js` exports `state`, `RENDERERS`, `switchWorkspace`, etc.; engines in `js/engine/`). New engines: `router.js` (hash ↔ app state) and `filterbar.js` (one contextual filter bar). Sidebar and Evidence-tab markup replace old markup in `index.html` with NEW class names styled in new component CSS files — legacy selectors are never overridden.

**Tech Stack:** Vanilla ES modules, native `<details>` for collapsible groups, Popover API, existing browser test harness (`tests.html`).

## Global Constraints

- **Zero build step, zero dependencies.** No npm/node/CDN.
- **Dashboard stays read-only.** localStorage for UI prefs only — this phase adds: `sidebar-groups`, `sidebar-collapsed`.
- **Python side untouched.** `/api/feed` contract unchanged.
- **Desktop-first, keyboard-first.** Mobile must not break.
- **New CSS = new files** under `web_dashboard/css/components/`, new class names only; NEVER override legacy selectors (2026-08-04 CSS-layers decision). Deleting now-unused legacy markup is fine; deleting legacy CSS rules is NOT Phase-2 work (Phase 3 owns that).
- **Motion rules** (Phase 1): workspace/tab switches through `viewSwitch()`; nothing in the keyboard critical path animates; `prefers-reduced-motion` collapses all motion.
- **Commits:** conventional `type/scope: subject`, no AI attribution, one commit per task, on branch `feat/dashboard/worldclass-upgrade`.
- **Verification:** serve with `make web-dashboard` (background) at `http://127.0.0.1:8765/web_dashboard/`; check listed expectations in BOTH themes. `tests.html` must stay green (currently `PASS (17)`; this plan adds router tests).
- **Phase-1 interfaces you will consume** (from `js/legacy/app.js` unless noted): `state`, `RENDERERS.byWorkspace.<ws>` arrays, `switchWorkspace(workspace, targetHash)`, `WORKSPACE_META`, `markAllDirty()`; `viewSwitch(fn)` from `js/engine/motion.js`; `registerList` from `js/engine/keyboard.js`; palette action shape `{id, label, hint, run}`.

## Current → Target IA

```
RAIL (target)                        EVIDENCE TABS (target)
Today                                Performance: #mock-trend #hint-independence #thinking #thinking-dimensions
  Briefing · Due queue               Memory:      #retention #revision-calendar #forecast-panel (moved from Today)
Plan                                 Consistency: #activity-heatmap #consistency #time-invested
  Week · Month · Quarter             Log:         #history #deferred
Problems
  Browser                            TODAY (target, ≤7 elements)
Practice                             next action · today contract · trajectory hero ·
  Weakness lab · Almost done ·       due queue · pace (KPI) tiles
  Edge checklist                     (forecast → Evidence/Memory; nudges → Practice)
Curriculum
  Constellation · Stages · Ladder ·
  Skills · Patterns
Evidence
  Performance · Memory · Consistency · Log
```

---

### Task 1: Hash router (parse/format tested, then wired)

**Files:**
- Create: `web_dashboard/js/engine/router.js`
- Create: `web_dashboard/js/tests/router.test.js`
- Modify: `web_dashboard/tests.html` (import test module)
- Modify: `web_dashboard/js/legacy/app.js` (nav-click block in `main()` ~line 6015; end of `main()`)
- Modify: `web_dashboard/js/main.js`

**Interfaces:**
- Produces (consumed by Tasks 2, 3, 5):
  - `parseRoute(hash) -> {workspace, sub, params}` — `"#/evidence/memory?q=two"` → `{workspace: "evidence", sub: "memory", params: {q: "two"}}`; empty/garbage hash → `{workspace: "today", sub: "", params: {}}`.
  - `formatRoute({workspace, sub, params}) -> string` — inverse of parseRoute; omits empty sub/params.
  - `navigate(partial, {replace = false})` — merges partial into current route, writes `location.hash` (replace ⇒ `history.replaceState`), triggers apply.
  - `currentRoute() -> {workspace, sub, params}`.
  - `onRoute(fn)` — subscribe; fn(route) called on every apply (initial, hashchange, navigate). Subscribers must be idempotent.
  - `startRouter()` — parses current hash, applies once, listens to `hashchange`.

- [x] **Step 1: Write failing tests** — `js/tests/router.test.js`:

```js
import { test, assertEq } from "./run.js";
import { parseRoute, formatRoute } from "../engine/router.js";

test("parse full route", () => {
  assertEq(parseRoute("#/evidence/memory?q=two%20sum&status=mastered"),
    { workspace: "evidence", sub: "memory", params: { q: "two sum", status: "mastered" } });
});

test("parse bare workspace", () => {
  assertEq(parseRoute("#/plan"), { workspace: "plan", sub: "", params: {} });
});

test("garbage falls back to today", () => {
  assertEq(parseRoute("#overview"), { workspace: "today", sub: "", params: {} });
  assertEq(parseRoute(""), { workspace: "today", sub: "", params: {} });
  assertEq(parseRoute("#/nope"), { workspace: "today", sub: "", params: {} });
});

test("format round-trips", () => {
  const route = { workspace: "problems", sub: "", params: { q: "kadane", sort: "frequency" } };
  assertEq(parseRoute(formatRoute(route)), route);
});

test("format omits empties", () => {
  assertEq(formatRoute({ workspace: "today", sub: "", params: {} }), "#/today");
});
```

Add `import "./js/tests/router.test.js";` to tests.html. Run → FAIL (module missing).

- [x] **Step 2: Implement js/engine/router.js**

```js
import { WORKSPACE_META } from "../legacy/app.js";

const listeners = [];
let current = { workspace: "today", sub: "", params: {} };
let writing = false;

export function parseRoute(hash) {
  const fallback = { workspace: "today", sub: "", params: {} };
  if (!hash || !hash.startsWith("#/")) return fallback;
  const [path, query = ""] = hash.slice(2).split("?");
  const [workspace, sub = ""] = path.split("/");
  if (!WORKSPACE_META[workspace]) return fallback;
  const params = {};
  for (const [k, v] of new URLSearchParams(query)) if (v) params[k] = v;
  return { workspace, sub, params };
}

export function formatRoute({ workspace, sub = "", params = {} }) {
  let out = `#/${workspace}`;
  if (sub) out += `/${sub}`;
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  if (qs) out += `?${qs}`;
  return out;
}

export function currentRoute() {
  return { ...current, params: { ...current.params } };
}

export function onRoute(fn) {
  listeners.push(fn);
}

function apply(route) {
  current = route;
  for (const fn of listeners) fn(currentRoute());
}

export function navigate(partial, { replace = false } = {}) {
  const next = {
    workspace: partial.workspace ?? current.workspace,
    // A workspace change resets sub + params unless the caller provides them.
    sub: partial.sub ?? (partial.workspace && partial.workspace !== current.workspace ? "" : current.sub),
    params: partial.params ?? (partial.workspace && partial.workspace !== current.workspace ? {} : current.params),
  };
  const hash = formatRoute(next);
  writing = true;
  if (replace) history.replaceState(null, "", hash);
  else if (hash !== location.hash) location.hash = hash;
  writing = false;
  apply(next);
}

export function startRouter() {
  window.addEventListener("hashchange", () => {
    if (writing) return;
    apply(parseRoute(location.hash));
  });
  apply(parseRoute(location.hash));
}
```

NOTE: `location.hash = hash` also fires `hashchange` asynchronously; the `writing` flag only guards the synchronous window, so ALSO guard `apply` in the hashchange handler by comparing: if `formatRoute(currentRoute()) === location.hash` skip. Add that check.

- [x] **Step 3: Run tests.html → expect `PASS (22)`** (17 + 5).

- [x] **Step 4: Wire the router**

In `js/legacy/app.js` `main()` (~6015): the `[data-workspace-link]` click block stays, but its handler becomes a thin call — replace the `viewSwitch(() => switchWorkspace(...))` body with a dispatched CustomEvent so legacy doesn't import the router (avoids a cycle):

```js
link.addEventListener("click", (event) => {
  event.preventDefault();
  document.dispatchEvent(new CustomEvent("dash:navigate", {
    detail: { workspace: link.dataset.workspaceLink, section: link.getAttribute("href").slice(1) },
  }));
});
```

In `js/main.js` (after `main()` — make main.js `await main()` so data is loaded, then start routing):

```js
import { startRouter, onRoute, navigate } from "./engine/router.js";
import { switchWorkspace } from "./legacy/app.js";
import { viewSwitch } from "./engine/motion.js";

document.addEventListener("dash:navigate", (e) => {
  navigate({ workspace: e.detail.workspace, params: e.detail.section ? { s: e.detail.section } : {} });
});

let lastWorkspace = null;
onRoute((route) => {
  const target = route.params.s ? `#${route.params.s}` : "";
  if (route.workspace !== lastWorkspace) {
    lastWorkspace = route.workspace;
    viewSwitch(() => switchWorkspace(route.workspace, target));
  } else if (target) {
    switchWorkspace(route.workspace, target);
  }
});
startRouter();
```

`main()` in legacy currently calls `renderAll()` which calls `switchWorkspace(state.activeWorkspace)` — initial route apply then corrects to the URL's workspace. Also change legacy `main()` to NOT be wrapped by the g-chord path anymore: in `js/engine/keyboard.js`, replace `viewSwitch(() => switchWorkspace(ws))` with `document.dispatchEvent(new CustomEvent("dash:navigate", { detail: { workspace: ws } }))` so chords go through the router too. Same in `js/engine/palette.js` for `go:` items.

- [x] **Step 5: Verify** — Load `/web_dashboard/#/evidence` directly → opens Evidence. Click through workspaces → hash updates (`#/plan`, …). Browser Back returns to previous workspace, Forward re-advances. `g p` chord updates hash. Reload on `#/curriculum` → Curriculum restored. Rail section links still scroll (`#/curriculum?s=patterns` style) and scroll-spy still highlights.

- [x] **Step 6: Commit**

```bash
git add web_dashboard/js/engine/router.js web_dashboard/js/tests/router.test.js web_dashboard/tests.html web_dashboard/js/legacy/app.js web_dashboard/js/main.js web_dashboard/js/engine/keyboard.js web_dashboard/js/engine/palette.js
git commit -m "feat/dashboard: hash router - deep links, back/forward, restore on reload"
```

---

### Task 2: Evidence sub-tabs (+ forecast panel moves in)

**Files:**
- Modify: `web_dashboard/index.html` — evidence sections get `data-evidence-tab`; tab bar markup; `#deferred` section MOVES to after `#revision-calendar`; forecast panel MOVES out of `#overview` into a new evidence section
- Create: `web_dashboard/js/engine/tabs.js`, `web_dashboard/css/components/tabs.css` (+ link in index.html)
- Modify: `web_dashboard/js/legacy/app.js` (`switchWorkspace`, `RENDERERS`, scroll spy)

**Interfaces:**
- Consumes: `onRoute`, `navigate`, `currentRoute` (router); `RENDERERS`, `switchWorkspace` (legacy).
- Produces: `initEvidenceTabs()` from `tabs.js`; route `sub` for evidence ∈ `"" | performance | memory | consistency | log` ("" ⇒ performance). Tab mapping constant `EVIDENCE_TABS = { performance: [...], memory: [...], consistency: [...], log: [...] }` (section ids) exported for Task 4's rail.

- [ ] **Step 1: index.html surgery**

1. Cut the whole forecast `<section class="panel">…</section>` (the one containing `#forecast-chart`) out of `#overview`; paste it as a standalone section right before `#retention`:
   `<section id="forecast-panel" class="section" data-workspace-section="evidence">` (keep the inner panel-head + `#forecast-chart` div; add an `.section-head` with eyebrow "Next 30 days" / h3 "Review-load forecast" to match sibling sections; delete the old in-panel head).
2. Move the entire `#deferred` section to just after `#revision-calendar` (fixes the DOM-order mismatch).
3. Tag every evidence section: `data-evidence-tab="performance"` on `#mock-trend`, `#hint-independence`, `#thinking`, `#thinking-dimensions`; `="memory"` on `#retention`, `#revision-calendar`, `#forecast-panel`; `="consistency"` on `#activity-heatmap`, `#consistency`, `#time-invested`; `="log"` on `#history`, `#deferred`.
4. Insert the tab bar as the FIRST child of `<main>`'s evidence area — a standalone element before `#history` (first evidence section in DOM after the moves — actual first is fine, it's positioned by CSS with the sections):

```html
<nav id="evidence-tabs" class="evidence-tabs" hidden aria-label="Evidence tabs">
  <button type="button" data-tab="performance">Performance</button>
  <button type="button" data-tab="memory">Memory</button>
  <button type="button" data-tab="consistency">Consistency</button>
  <button type="button" data-tab="log">Log</button>
</nav>
```

- [ ] **Step 2: Write js/engine/tabs.js**

```js
import { onRoute, navigate, currentRoute } from "./router.js";

export const EVIDENCE_TABS = {
  performance: ["mock-trend", "hint-independence", "thinking", "thinking-dimensions"],
  memory: ["retention", "revision-calendar", "forecast-panel"],
  consistency: ["activity-heatmap", "consistency", "time-invested"],
  log: ["history", "deferred"],
};

function applyTab(tab) {
  const active = EVIDENCE_TABS[tab] ? tab : "performance";
  document.querySelectorAll("#evidence-tabs [data-tab]").forEach((btn) => {
    const on = btn.dataset.tab === active;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-current", on ? "true" : "false");
  });
  document.querySelectorAll('[data-workspace-section="evidence"][data-evidence-tab]').forEach((section) => {
    // Both gates must pass: workspace visibility is legacy's, tab visibility is ours.
    section.dataset.tabHidden = section.dataset.evidenceTab === active ? "" : "true";
  });
}

export function initEvidenceTabs() {
  const bar = document.querySelector("#evidence-tabs");
  bar.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-tab]");
    if (btn) navigate({ workspace: "evidence", sub: btn.dataset.tab });
  });
  onRoute((route) => {
    bar.hidden = route.workspace !== "evidence";
    if (route.workspace === "evidence") applyTab(route.sub || "performance");
  });
}
```

- [ ] **Step 3: Reconcile with legacy visibility**

`switchWorkspace` sets `section.hidden = section.dataset.workspaceSection !== active`. Tab hiding must survive that. In legacy `switchWorkspace`, change that one line to respect the tab gate:

```js
section.hidden = section.dataset.workspaceSection !== active || section.dataset.tabHidden === "true";
```

In `tabs.js` `applyTab`, after setting `data-tab-hidden`, ALSO set `section.hidden` directly for evidence sections (so tab clicks — which don't call switchWorkspace — take effect):

```js
section.hidden = section.dataset.tabHidden === "true";
```

Scroll spy: `watchActiveSection`/`spyActiveSection` highlight per-section rail links; after Task 4 the evidence rail entries are the 4 tabs, so exclude evidence sections from the spy: in the spy's section-collection step, skip sections with `data-evidence-tab`.

`tabs.css`: horizontal segmented control under the topbar — sticky at top of the evidence area, `.active` gets accent underline + text emphasis, buttons min 32px tall, `transition: color var(--dur-feedback)`.

- [ ] **Step 4: Wire + palette entries**

`main.js`: `import { initEvidenceTabs } from "./engine/tabs.js"; initEvidenceTabs();` (before `startRouter()` so the first route paints tabs).
`js/engine/palette.js` `buildIndex`: add the 4 tabs:

```js
for (const tab of ["performance", "memory", "consistency", "log"]) {
  items.push({ id: `tab:${tab}`, group: "Go to", label: `Evidence · ${tab[0].toUpperCase()}${tab.slice(1)}`, hint: "", run: () => navigate({ workspace: "evidence", sub: tab }) });
}
```

(import `navigate` from router — palette already avoids legacy-cycle issues since router imports only WORKSPACE_META from legacy).

- [ ] **Step 5: Verify** — `g e` → Evidence opens on Performance tab (4 sections visible, others gone); click Memory → retention + calendar + forecast, hash `#/evidence/memory`; reload → same tab; Back → Performance. Today no longer shows the forecast. Deferred renders under Log after History (order fixed). Ctrl+K "memory" → jumps to the tab. Both themes; reduced-motion instant.

- [ ] **Step 6: Commit**

```bash
git add web_dashboard/index.html web_dashboard/js/engine/tabs.js web_dashboard/css/components/tabs.css web_dashboard/js/legacy/app.js web_dashboard/js/main.js web_dashboard/js/engine/palette.js
git commit -m "feat/dashboard: evidence workspace consolidated into 4 sub-tabs"
```

---

### Task 3: Today mission control + Practice gets nudges

**Files:**
- Modify: `web_dashboard/index.html` (`#nudges-panel` moves), `web_dashboard/js/features/motivation.js` (registration), `web_dashboard/js/legacy/app.js` (RENDERERS arrays)

**Interfaces:**
- Consumes: `RENDERERS.byWorkspace` arrays (legacy), `renderNudges`/`renderMotivation` (features/motivation.js).
- Produces: Today = next action, contract, trajectory, due queue + pace tiles (5 blocks). Practice = weakness lab, nudges, edge checklist.

- [ ] **Step 1: Move nudges panel**

In index.html: cut `<section class="panel" id="nudges-panel">…</section>` out of `#overview`; convert to a standalone practice section placed between `#weakness-lab` and `#edge-cases`:
`<section id="nudges" class="section" data-workspace-section="practice">` with a `.section-head` (eyebrow "Close it out", h3 "Almost done") + the `#nudge-cards` div. Delete the old panel wrapper.

- [ ] **Step 2: Re-register renderers**

`js/features/motivation.js`: change `RENDERERS.byWorkspace.today.push(renderNudges)` → `RENDERERS.byWorkspace.practice.push(renderNudges)`.
`js/legacy/app.js`: in the RENDERERS literal, move `renderForecast` from `today` to `evidence` (its section moved in Task 2 — do it here if Task 2 didn't).

- [ ] **Step 3: Verify** — Today shows exactly: next action, contract, trajectory, due queue, pace tiles (+ data warning when relevant). `g w` → Practice shows weakness lab, Almost done, edge checklist; nudge drill-down still opens. Evidence/Memory tab still renders forecast (renderer fires on first evidence visit).

- [ ] **Step 4: Commit**

```bash
git add web_dashboard/index.html web_dashboard/js/features/motivation.js web_dashboard/js/legacy/app.js
git commit -m "enhancement/dashboard: today reduced to mission control; nudges join practice"
```

---

### Task 4: Sidebar rebuild (collapsible groups, icon rail, persisted)

**Files:**
- Modify: `web_dashboard/index.html` — replace `<nav class="nav-list">…</nav>` markup entirely
- Create: `web_dashboard/js/engine/sidebar.js`, `web_dashboard/css/components/sidebar.css` (+ link)
- Modify: `web_dashboard/js/legacy/app.js` (nav-dependent code), `web_dashboard/js/main.js`

**Interfaces:**
- Consumes: `navigate`, `onRoute` (router); `EVIDENCE_TABS` (tabs.js); `WORKSPACE_META` (legacy).
- Produces: new rail markup contract used by legacy's spy/highlight code: workspace header links = `.rail-group > summary a[data-rail-workspace]`; child links = `a[data-rail-workspace][data-rail-target]` where target is `s:<sectionId>` or `tab:<tabId>`. Legacy's old `navLinks()`/`firstSectionOf()`/`setActiveSection()` are REWRITTEN here to the new selectors.

- [ ] **Step 1: New rail markup** (replaces the whole `nav.nav-list` block; groups are native `<details name>` is NOT used — groups open independently):

```html
<nav class="rail-nav" aria-label="Dashboard navigation">
  <details class="rail-group" data-group="today" open>
    <summary><a href="#/today" data-rail-workspace="today">Today</a></summary>
    <a href="#/today?s=overview" data-rail-workspace="today" data-rail-target="s:overview">Briefing</a>
    <a href="#/today?s=revisions" data-rail-workspace="today" data-rail-target="s:revisions">Due queue</a>
  </details>
  <details class="rail-group" data-group="plan" open>
    <summary><a href="#/plan" data-rail-workspace="plan">Plan</a></summary>
    <a href="#/plan?s=week-scoreboard" data-rail-workspace="plan" data-rail-target="s:week-scoreboard">Week</a>
    <a href="#/plan?s=month-milestones" data-rail-workspace="plan" data-rail-target="s:month-milestones">Month</a>
    <a href="#/plan?s=quarter-roadmap" data-rail-workspace="plan" data-rail-target="s:quarter-roadmap">Quarter</a>
  </details>
  <details class="rail-group" data-group="problems" open>
    <summary><a href="#/problems" data-rail-workspace="problems">Problems</a></summary>
    <a href="#/problems" data-rail-workspace="problems" data-rail-target="s:problem-browser">Browser</a>
  </details>
  <details class="rail-group" data-group="practice" open>
    <summary><a href="#/practice" data-rail-workspace="practice">Practice</a></summary>
    <a href="#/practice?s=weakness-lab" data-rail-workspace="practice" data-rail-target="s:weakness-lab">Weakness lab</a>
    <a href="#/practice?s=nudges" data-rail-workspace="practice" data-rail-target="s:nudges">Almost done</a>
    <a href="#/practice?s=edge-cases" data-rail-workspace="practice" data-rail-target="s:edge-cases">Edge checklist</a>
  </details>
  <details class="rail-group" data-group="curriculum" open>
    <summary><a href="#/curriculum" data-rail-workspace="curriculum">Curriculum</a></summary>
    <a href="#/curriculum?s=skills-constellation" data-rail-workspace="curriculum" data-rail-target="s:skills-constellation">Constellation</a>
    <a href="#/curriculum?s=stages" data-rail-workspace="curriculum" data-rail-target="s:stages">Stages</a>
    <a href="#/curriculum?s=promotion-ladder" data-rail-workspace="curriculum" data-rail-target="s:promotion-ladder">Ladder</a>
    <a href="#/curriculum?s=skills" data-rail-workspace="curriculum" data-rail-target="s:skills">Skills</a>
    <a href="#/curriculum?s=patterns" data-rail-workspace="curriculum" data-rail-target="s:patterns">Patterns</a>
  </details>
  <details class="rail-group" data-group="evidence" open>
    <summary><a href="#/evidence" data-rail-workspace="evidence">Evidence</a></summary>
    <a href="#/evidence/performance" data-rail-workspace="evidence" data-rail-target="tab:performance">Performance</a>
    <a href="#/evidence/memory" data-rail-workspace="evidence" data-rail-target="tab:memory">Memory</a>
    <a href="#/evidence/consistency" data-rail-workspace="evidence" data-rail-target="tab:consistency">Consistency</a>
    <a href="#/evidence/log" data-rail-workspace="evidence" data-rail-target="tab:log">Log</a>
  </details>
</nav>
<button type="button" id="rail-collapse" class="rail-collapse microlabel" aria-label="Collapse sidebar">⟨⟨</button>
```

(Place `#rail-collapse` in the `.rail-footer` next to the theme toggle.) Since all real navigation is href-driven now, links work with the router directly (hash hrefs) — NO click handlers needed; the router's hashchange path handles everything, including section scroll via the `s` param.

- [ ] **Step 2: Write js/engine/sidebar.js**

```js
import { onRoute } from "./router.js";

const GROUPS_KEY = "sidebar-groups";
const COLLAPSED_KEY = "sidebar-collapsed";

export function initSidebar() {
  const saved = JSON.parse(localStorage.getItem(GROUPS_KEY) || "{}");
  document.querySelectorAll(".rail-group").forEach((group) => {
    if (group.dataset.group in saved) group.open = saved[group.dataset.group];
    group.addEventListener("toggle", () => {
      const next = { ...JSON.parse(localStorage.getItem(GROUPS_KEY) || "{}"), [group.dataset.group]: group.open };
      localStorage.setItem(GROUPS_KEY, JSON.stringify(next));
    });
  });

  const collapseBtn = document.querySelector("#rail-collapse");
  const setCollapsed = (on) => {
    document.body.classList.toggle("rail-collapsed", on);
    localStorage.setItem(COLLAPSED_KEY, on ? "1" : "");
    collapseBtn.textContent = on ? "⟩⟩" : "⟨⟨";
  };
  setCollapsed(Boolean(localStorage.getItem(COLLAPSED_KEY)));
  collapseBtn.addEventListener("click", () => setCollapsed(!document.body.classList.contains("rail-collapsed")));

  onRoute((route) => {
    // Quiet state: the open workspace's group; loud state handled by legacy spy for
    // sections and by route.sub for evidence tabs.
    document.querySelectorAll(".rail-group").forEach((group) => {
      const isActive = group.dataset.group === route.workspace;
      group.classList.toggle("in-workspace", isActive);
      if (isActive) group.open = true;
    });
    document.querySelectorAll('[data-rail-target^="tab:"]').forEach((link) => {
      link.classList.toggle("active", route.workspace === "evidence" && link.dataset.railTarget === `tab:${route.sub || "performance"}`);
    });
  });
}
```

- [ ] **Step 3: Rewrite legacy nav-dependent code**

In `js/legacy/app.js`:
1. `navLinks()` → `return [...document.querySelectorAll('.rail-nav a[data-rail-target^="s:"]')];`
2. `firstSectionOf(workspace)` → first link matching `[data-rail-workspace="${workspace}"][data-rail-target^="s:"]`, return `link.dataset.railTarget.slice(2)`; evidence has none → return `""` (guard: `setActiveSection` already no-ops on empty).
3. `setActiveSection(sectionId)` — match by `link.dataset.railTarget === \`s:${sectionId}\`` instead of href.
4. `switchWorkspace` — the `[data-workspace-link]` highlight loop now targets nothing; replace with no-op removal (sidebar.js owns group highlighting). DELETE the duplicate-title suppression block (`is-duplicate-title`) and instead delete the duplicated `<h3>` headings from index.html: in `#overview` ("Mission briefing") and `#problem-browser` ("Problem browser") section-heads, remove the h3 (keep eyebrow + pill). Verify each workspace's first paint has no doubled title under the topbar.
5. The old `[data-workspace-link]` click-listener block in `main()` and the `dash:navigate` CustomEvent from Task 1 for nav links: remove the listener block entirely (rail links are plain hash links now). KEEP the `dash:navigate` event path — keyboard chords and palette still use it.
6. Scroll spy: already excludes evidence sections (Task 2). Confirm the spy calls `setActiveSection` only for the active workspace's sections.

- [ ] **Step 4: sidebar.css**

New-class styles only: `.rail-nav` column; `.rail-group summary` row (marker hidden, custom chevron via `::after` rotating 90° in `var(--dur-feedback)`); `.rail-group.in-workspace summary a` tint + 2px accent inset bar; child `a` indent, `.active` accent; `body.rail-collapsed .sidebar` narrows to 56px — child links hidden, summaries show two-letter monogram (`data-group` first letters via `::first-letter`-style or a `span.rail-icon` added per summary: simpler — add `<span class="rail-icon num">TD</span>` etc. inside each summary before the `<a>`, hidden when expanded, shown when collapsed); summary links get `title` attributes for collapsed-state tooltips. Grid: `.app-shell` sidebar column is legacy-styled — set width via `body.rail-collapsed .app-shell { grid-template-columns: 56px 1fr; }` ONLY if legacy uses grid-template-columns on `.app-shell`; verify with DevTools first and mirror whatever layout property legacy uses, from the new file (overriding the layout of `.app-shell` under a NEW body class is additive, not a legacy override).

- [ ] **Step 5: Wire** — main.js: `import { initSidebar } from "./engine/sidebar.js"; initSidebar();` before `startRouter()`.

- [ ] **Step 6: Verify** — groups collapse/expand and survive reload; navigating to a workspace auto-opens its group; collapse button → icon rail (56px) with monograms + title tooltips, survives reload; section links scroll + spy highlights; evidence child links switch tabs and highlight by route; no doubled titles anywhere; keyboard `g` chords + palette still navigate; `?` help unaffected. Both themes.

- [ ] **Step 7: Commit**

```bash
git add web_dashboard/index.html web_dashboard/js/engine/sidebar.js web_dashboard/css/components/sidebar.css web_dashboard/js/legacy/app.js web_dashboard/js/main.js
git commit -m "feat/dashboard: rebuilt sidebar - collapsible persisted groups, icon rail, route-aware highlight"
```

---

### Task 5: Unified filter bar

**Files:**
- Create: `web_dashboard/js/engine/filterbar.js`, `web_dashboard/css/components/filterbar.css` (+ link)
- Modify: `web_dashboard/index.html` — DELETE `#list-toolbar` and `.browser-toolbar` markup; add `#filter-bar` in the topbar
- Modify: `web_dashboard/js/legacy/app.js` — `currentFilters()`, browser listeners in `main()`, `WORKSPACE_META.*.toolbar`
- Create: `web_dashboard/js/tests/filters.test.js` (+ import in tests.html)

**Interfaces:**
- Consumes: `onRoute`, `navigate`, `currentRoute` (router); `browserState`, `applyFilters`-path via exported legacy setter (below).
- Produces: `initFilterBar()`; unified status vocabulary `["", "not_started", "solved", "failed", "mastered"]`; `mapStatus(unified, consumer)` where consumer ∈ `"browser" | "catalog"` — exported from filterbar.js and unit-tested. Legacy gets a new exported `setCatalogFilters({query, stage, status})` that updates state and runs the old applyFilters pipeline.

- [ ] **Step 1: Failing tests** — `js/tests/filters.test.js`:

```js
import { test, assertEq } from "./run.js";
import { mapStatus } from "../engine/filterbar.js";

test("browser consumer passes unified values through", () => {
  assertEq(mapStatus("solved", "browser"), "solved");
  assertEq(mapStatus("not_started", "browser"), "not_started");
});

test("catalog consumer maps solved->active", () => {
  assertEq(mapStatus("solved", "catalog"), "active");
  assertEq(mapStatus("failed", "catalog"), "failed");
  assertEq(mapStatus("mastered", "catalog"), "mastered");
  assertEq(mapStatus("", "catalog"), "");
});
```

Run → FAIL. (Catalog = legacy `problemMatchesStatus`, whose vocabulary is `completed|active|failed|mastered|not_started`; unified drops `completed` — it was ≈ solved∪failed∪mastered and earned nothing.)

- [ ] **Step 2: Legacy prep**

In `js/legacy/app.js`:
1. Add module-scoped `const catalogFilters = { query: "", stage: "", status: "" };`
2. Rewrite `currentFilters()` to `return { ...catalogFilters };` (it currently reads `#search/#stage-filter/#status-filter` DOM — those elements are being deleted).
3. Add + export:

```js
function setCatalogFilters(next) {
  Object.assign(catalogFilters, next);
  applyFilters();
}
```

4. Delete the `#search`/`#stage-filter`/`#status-filter`/`#browser-*` listener wiring from `main()` (elements gone). Keep `buildStageOptions()` but have it return the stage list (`stage_order`) instead of writing to `#stage-filter`; export it as `stageOptions()`.
5. Export `browserState` already exported (Phase 1) — plus export `renderProblemBrowser` for filterbar to trigger.
6. Delete `toolbar` handling in `switchWorkspace` (the `meta.toolbar` block); remove `toolbar:` keys from `WORKSPACE_META` entries.

- [ ] **Step 3: index.html** — delete `#list-toolbar` (topbar) and the `.browser-toolbar` block (problem browser). In the topbar, where `#list-toolbar` was:

```html
<div id="filter-bar" class="filter-bar" hidden>
  <input id="fb-search" type="search" placeholder="Search" aria-label="Search" />
  <select id="fb-stage" aria-label="Stage"><option value="">All stages</option></select>
  <select id="fb-status" aria-label="Status">
    <option value="">All statuses</option>
    <option value="not_started">Not started</option>
    <option value="solved">Solved (in revision)</option>
    <option value="failed">Recall failed</option>
    <option value="mastered">Mastered</option>
  </select>
  <select id="fb-difficulty" aria-label="Difficulty" hidden>
    <option value="">All difficulties</option><option>Easy</option><option>Medium</option><option>Hard</option>
  </select>
  <select id="fb-sort" aria-label="Sort" hidden>
    <option value="curriculum">Curriculum order</option><option value="frequency">Interview frequency</option>
  </select>
</div>
```

- [ ] **Step 4: Implement js/engine/filterbar.js**

```js
import { browserState, renderProblemBrowser, setCatalogFilters, stageOptions } from "../legacy/app.js";
import { onRoute, navigate, currentRoute } from "./router.js";

const SHOW = {
  problems: ["fb-search", "fb-difficulty", "fb-status", "fb-sort"],
  curriculum: ["fb-search", "fb-stage", "fb-status"],
  evidence: ["fb-search", "fb-stage", "fb-status"],
};

export function mapStatus(unified, consumer) {
  if (consumer === "catalog") return unified === "solved" ? "active" : unified;
  return unified;
}

function readControls() {
  return {
    q: document.querySelector("#fb-search").value.trim(),
    stage: document.querySelector("#fb-stage").value,
    status: document.querySelector("#fb-status").value,
    difficulty: document.querySelector("#fb-difficulty").value,
    sort: document.querySelector("#fb-sort").value,
  };
}

function push(workspace, values) {
  // Filters live in the URL (replace, not push — no history spam while typing).
  const params = {};
  if (values.q) params.q = values.q;
  if (values.stage) params.stage = values.stage;
  if (values.status) params.status = values.status;
  if (workspace === "problems") {
    if (values.difficulty) params.difficulty = values.difficulty;
    if (values.sort !== "curriculum") params.sort = values.sort;
  }
  navigate({ params: { ...currentRoute().params, ...clearFilterParams(), ...params } }, { replace: true });
}

function clearFilterParams() {
  return { q: "", stage: "", status: "", difficulty: "", sort: "" };
}

function applyToConsumers(workspace, params) {
  if (workspace === "problems") {
    browserState.search = params.q || "";
    browserState.difficulty = params.difficulty || "";
    browserState.status = mapStatus(params.status || "", "browser");
    browserState.sort = params.sort || "curriculum";
    renderProblemBrowser();
  } else {
    setCatalogFilters({ query: params.q || "", stage: params.stage || "", status: mapStatus(params.status || "", "catalog") });
  }
}

function syncControls(params) {
  document.querySelector("#fb-search").value = params.q || "";
  document.querySelector("#fb-stage").value = params.stage || "";
  document.querySelector("#fb-status").value = params.status || "";
  document.querySelector("#fb-difficulty").value = params.difficulty || "";
  document.querySelector("#fb-sort").value = params.sort || "curriculum";
}

export function initFilterBar() {
  const bar = document.querySelector("#filter-bar");
  const stageSelect = document.querySelector("#fb-stage");
  for (const stage of stageOptions()) {
    const option = document.createElement("option");
    option.value = stage;
    option.textContent = stage;
    stageSelect.append(option);
  }
  let debounceId = 0;
  bar.addEventListener("input", () => {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => push(currentRoute().workspace, readControls()), 150);
  });
  onRoute((route) => {
    const visible = SHOW[route.workspace] || null;
    bar.hidden = !visible;
    if (!visible) return;
    for (const el of bar.querySelectorAll("input, select")) el.hidden = !visible.includes(el.id);
    syncControls(route.params);
    applyToConsumers(route.workspace, route.params);
  });
}
```

CYCLE CHECK: filterbar imports legacy AND router; router imports legacy; legacy imports neither → no cycle. `applyToConsumers` runs on every route apply for filter workspaces — `applyFilters()` and `renderProblemBrowser()` are idempotent re-renders (verify no visible flicker; if flicker, add an early-return when params are unchanged from last apply — keep a `lastApplied` JSON string).

- [ ] **Step 5: Wire + tests green** — main.js: `import { initFilterBar } from "./engine/filterbar.js"; initFilterBar();` before `startRouter()`. tests.html: import filters.test.js. Run → `PASS (24)`.

- [ ] **Step 6: Verify** — Problems: search "kadane" filters table (URL gains `?q=kadane`), difficulty + status + sort work, tree intact; reload restores all four controls AND the filtered table; Curriculum: search dims constellation + filters skills/stages as before (old topbar behavior preserved via setCatalogFilters); Evidence: search filters history table; switching workspace swaps visible controls and re-applies that workspace's params; `/` still focuses the search box; status vocabulary identical in every workspace.

- [ ] **Step 7: Commit**

```bash
git add web_dashboard/index.html web_dashboard/js/engine/filterbar.js web_dashboard/css/components/filterbar.css web_dashboard/js/tests/filters.test.js web_dashboard/tests.html web_dashboard/js/legacy/app.js web_dashboard/js/main.js
git commit -m "feat/dashboard: unified contextual filter bar with url-persisted filters"
```

---

### Task 6: Phase-2 verification walk

**Files:**
- Modify: whatever the walk flags.

- [ ] **Step 1: tests.html** → `PASS (24)`.
- [ ] **Step 2: Route matrix** — direct-load each: `#/today`, `#/plan`, `#/problems?q=two&status=solved`, `#/practice`, `#/curriculum?s=patterns`, `#/evidence/log` → correct workspace/tab/filters/scroll on a COLD load each time. Back/forward across 5 navigations behaves.
- [ ] **Step 3: Playwright walk** — 6 workspaces (evidence ×4 tabs) × {dark, light} × reduced-motion: screenshots, zero console errors.
- [ ] **Step 4: Keyboard-only pass** — g-chords, j/k/Enter, /, t, f, ?, Ctrl+K, Tab through the rail (details/summary are natively focusable; child links reachable; collapse button reachable).
- [ ] **Step 5: Sidebar persistence** — collapse rail + close two groups + pick evidence tab + set a filter → reload → all restored.
- [ ] **Step 6: Fix findings, re-verify, commit**

```bash
git add -A web_dashboard
git commit -m "fix/dashboard: phase-2 verification walk fixes"
```

---

## Self-review notes (already applied)

- Spec coverage: sidebar rebuild w/ persisted groups + icon rail ✓ (T4), nav/DOM order fix ✓ (T2 moves #deferred), orphan #thinking-dimensions homed ✓ (T2 Performance tab), duplicate-title fix by construction ✓ (T4 step 3.4), Evidence 4 sub-tabs ✓ (T2), Today ≤7 ✓ (T3), one filter system + one status vocabulary ✓ (T5), URL per view incl. tab + filters restore ✓ (T1, T2, T5).
- Deviation from spec text: spec listed due queue off Today's first paint; kept it — it is today's recall work-list and the mission-control element count stays ≤7. Nudges moved to Practice (spec silent on destination; Practice is the drilling workspace).
- Type consistency: `navigate(partial, {replace})`/`onRoute(fn)`/`currentRoute()` used identically in T2/T4/T5 as defined in T1; `EVIDENCE_TABS` exported in T2, consumed in T4; `setCatalogFilters`/`stageOptions`/`renderProblemBrowser` exports defined in T5 step 2 before use in step 4; route param `s` for section scroll used in T1 step 4 and T4 markup.
- Known risks called out in-plan: hashchange re-entrancy (T1 note), tab/workspace double-gate on `hidden` (T2 step 3), app-shell collapsed-width override done under a new body class (T4 step 4), filter re-apply idempotency (T5 cycle check).
