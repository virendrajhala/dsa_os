# Dashboard Phase 1 — Capabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `web_dashboard/` to a native ES-module architecture and ship the Phase-1 capabilities: lazy rendering, explicit data-status banners, command palette, keyboard model, tooltip/crosshair + drill-down engines, motion system, and the four read-only feature packs (motivation, memory analytics, pace, focus mode).

**Architecture:** `legacy/app.js` (the current monolith, un-IIFE'd) keeps rendering all existing views; new code lives in small modules (`engine/`, `derive/`, `features/`) that import legacy's exported `state` and helpers. Pure derivations go in `js/derive/` and are unit-tested in a zero-dep browser harness (`tests.html`). No build step, no npm, latest Chrome/Firefox only.

**Tech Stack:** Vanilla ES modules, hand-rolled SVG, Popover API, `@starting-style`, same-document View Transitions, CSS nesting, localStorage (UI prefs only). Served by `make web-dashboard` → `scripts/serve_dashboard.py` on 127.0.0.1:8765.

## Global Constraints

- **Zero build step, zero dependencies.** No package.json, no node, no CDN. Ever.
- **Dashboard stays read-only.** `update_progress.py` is the only writer. localStorage allowed for UI prefs only: `theme`, `palette-frecency`, `whatif-hours`, sidebar state.
- **Python side untouched.** `/api/feed` contract unchanged; never recompute what the feed provides.
- **`file://` support is dropped** (accepted in spec). Everything verified via `make web-dashboard` at `http://127.0.0.1:8765/web_dashboard/`.
- **Read-only data derivations** use: `state.datasets.progress.completed[]` records — `{problem_id, completed_at: "YYYY-MM-DD", time_taken_minutes, hint_level_used, revision: {status: "ACTIVE"|"MASTERED"|..., stage: 0-4, completed: [dates], next_due: "YYYY-MM-DD", history: [{date, result: "PASS"|"FAIL", stage, ...}]}}`. Dates are date-only (no time).
- **Mature recall** = revision history entry with `stage >= 2` (aligned to existing R1–R4 policy in `progress/scoring.json`; mastered_after_stage=4).
- **Streak**: active day = ≥1 solve OR revision; **no grace** — a missed day breaks it.
- **Motion**: 120ms feedback / 200ms overlays / 280ms workspace switch; ease-out `cubic-bezier(0.16, 1, 0.3, 1)` entrances; exits ~2/3 duration; opacity+transform only; nothing in the keyboard critical path animates; ALL motion gated by `prefers-reduced-motion`.
- **New CSS** goes in per-component files under `web_dashboard/css/components/`, loaded after `legacy.css`. NEVER add override rules on legacy selectors (per the 2026-08-04 CSS-layers decision).
- **Commits**: conventional style `type/scope: subject` (see git log), no AI attribution of any kind, commit only what the task touched. Work happens on branch `feat/dashboard/worldclass-upgrade`.
- **Verification**: after every UI task, load `http://127.0.0.1:8765/web_dashboard/` (server: `make web-dashboard`, run in background) and check the listed expectations in BOTH themes. Use Playwright MCP or claude-in-chrome if available; otherwise ask the user to look.

## File Structure (end state of Phase 1)

```
web_dashboard/
  index.html                  # <script type="module" src="./js/main.js">
  tests.html                  # browser test harness (PASS/FAIL in <title>)
  css/
    legacy.css                # renamed styles.css, byte-identical
    tokens.css                # motion + future design tokens
    components/{palette,tooltip,focus,features,keyboard}.css
  js/
    main.js                   # entry: imports legacy + engines + features
    data.js                   # fetchFeedStatus() — explicit status, no port cliff
    svg.js                    # svgEl() — the one SVG helper
    legacy/app.js             # un-IIFE'd monolith, exports state + helpers
    engine/{motion,tooltip,drilldown,keyboard,palette}.js
    derive/{dates,activity,memory,pace,search}.js     # pure, tested
    features/{motivation,memory,pace,focus}.js        # thin UI over derive/
    tests/{run,activity.test,memory.test,pace.test,search.test}.js
```

---

### Task 1: ES-module conversion (files move, behavior identical)

**Files:**
- Move: `web_dashboard/app.js` → `web_dashboard/js/legacy/app.js`
- Move: `web_dashboard/styles.css` → `web_dashboard/css/legacy.css`
- Create: `web_dashboard/js/main.js`
- Modify: `web_dashboard/index.html` (stylesheet href + script tag)

**Interfaces:**
- Produces: `js/legacy/app.js` as an ES module exporting:
  `state`, `browserState`, `renderAll`, `switchWorkspace`, `setModal`, `toggleTheme`, `problemStatus`, `WORKSPACE_META`, `EDGE_CASE_GROUPS` (the edge-case checklist const near app.js:95), and `main` (NOT auto-invoked — main.js invokes it).
- Produces: `js/main.js` — the only script tag in index.html.

- [x] **Step 1: Move files with git mv**

```bash
cd /home/virendra/DSA/dsa_os/web_dashboard
mkdir -p js/legacy css
git mv app.js js/legacy/app.js
git mv styles.css css/legacy.css
```

- [x] **Step 2: Un-IIFE legacy/app.js**

At the top of `js/legacy/app.js`, delete line 1 `(function () {`. At the bottom, the file currently ends:

```js
  main();
})();
```

Replace those two lines with exports (main is no longer self-invoked):

```js
export {
  state,
  browserState,
  renderAll,
  switchWorkspace,
  setModal,
  toggleTheme,
  problemStatus,
  WORKSPACE_META,
  EDGE_CASE_GROUPS,
  main,
};
```

Then dedent is NOT required (JS doesn't care); leave inner indentation untouched to keep the diff reviewable. If the edge-case checklist const (app.js:95-130) has a different name, export it under that name and note it; if it is not a top-level const, wrap it: `const EDGE_CASE_GROUPS = <existing literal>;` and make the renderer use it.

- [x] **Step 3: Create js/main.js**

```js
import { main } from "./legacy/app.js";

main();
```

- [x] **Step 4: Update index.html**

Replace `<link rel="stylesheet" href="./styles.css" />` with `<link rel="stylesheet" href="./css/legacy.css" />`.
Replace `<script src="./app.js"></script>` with `<script type="module" src="./js/main.js"></script>`.

- [x] **Step 5: Verify identical behavior**

Run: `make web-dashboard` (background). Load `http://127.0.0.1:8765/web_dashboard/`.
Expected: zero console errors; Today renders with live feed pill; switch all 6 workspaces; open a problem modal from the browser table; toggle theme. All identical to before.

- [x] **Step 6: Commit**

```bash
git add -A web_dashboard
git commit -m "refactor/dashboard: convert to native ES modules, no behavior change"
```

---

### Task 2: Browser test harness

**Files:**
- Create: `web_dashboard/tests.html`
- Create: `web_dashboard/js/tests/run.js`

**Interfaces:**
- Produces: `test(name, fn)` and `assertEq(actual, expected, msg?)` from `js/tests/run.js`; test modules registered by import in `tests.html`. Page title becomes `PASS (n)` or `FAIL (n)` so Playwright can assert on `document.title`.

- [x] **Step 1: Write js/tests/run.js**

```js
const results = [];

export function test(name, fn) {
  try {
    fn();
    results.push({ name, ok: true });
  } catch (error) {
    results.push({ name, ok: false, error: String(error) });
  }
}

export function assertEq(actual, expected, msg = "") {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Error(`${msg} expected ${e}, got ${a}`);
}

export function report() {
  const fail = results.filter((r) => !r.ok);
  document.title = fail.length ? `FAIL (${fail.length})` : `PASS (${results.length})`;
  document.body.innerHTML = results
    .map((r) => `<p style="color:${r.ok ? "green" : "red"}">${r.ok ? "✓" : "✗"} ${r.name} ${r.error || ""}</p>`)
    .join("");
}
```

- [x] **Step 2: Write tests.html**

```html
<!doctype html>
<html><head><meta charset="utf-8"><title>running</title></head><body>
<script type="module">
  // Test modules are imported here; each calls test() at module top level.
  import { report } from "./js/tests/run.js";
  // import "./js/tests/activity.test.js";  ← added by later tasks
  report();
</script>
</body></html>
```

- [x] **Step 3: Verify**

Load `http://127.0.0.1:8765/web_dashboard/tests.html`. Expected: title `PASS (0)`.

- [x] **Step 4: Commit**

```bash
git add web_dashboard/tests.html web_dashboard/js/tests/run.js
git commit -m "test/dashboard: zero-dep browser test harness"
```

---

### Task 3: Pure derivations — dates, activity (streaks), memory (retention/maturity/forecast), pace, fuzzy search

**Files:**
- Create: `web_dashboard/js/derive/dates.js`, `activity.js`, `memory.js`, `pace.js`, `search.js`
- Create: `web_dashboard/js/tests/activity.test.js`, `memory.test.js`, `pace.test.js`, `search.test.js`
- Modify: `web_dashboard/tests.html` (import the 4 test modules)

**Interfaces:**
- Produces (exact signatures consumed by Tasks 9–14):
  - `dates.js`: `addDays(iso, n) -> iso`, `diffDays(a, b) -> int` (b-a), `todayISO() -> iso`
  - `activity.js`: `activeDaySet(completed) -> Set<iso>`, `streaks(daySet, todayIso) -> {current, max}`
  - `memory.js`: `matureRecallStats(completed) -> {pass, total, rate|null}`, `maturityBuckets(totalProblems, completed) -> {new, learning, young, mature}`, `dueForecast(completed, startIso, daysAhead=30) -> {overdueBefore, bars: [{offset, due, backlogIfIdle}]}`
  - `pace.js`: `paceProjection({solved, target, startIso, endIso, todayIso, whatIfPerWeek=null}) -> {velocityPerWeek, finishIso|null, onTrack}`, `fastestByDifficulty(entries) -> {Easy?, Medium?, Hard?}` where entries = `[{difficulty, minutes, problemId}]`, `nearComplete(groups, limit=4)` where groups = `[{id, name, done, total}]`
  - `search.js`: `fuzzyScore(query, text) -> number` (0 = no match, higher = better)

- [x] **Step 1: Write dates.js**

```js
export function addDays(iso, n) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function diffDays(a, b) {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86400000);
}

export function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
```

- [x] **Step 2: Write failing tests for activity.js**

`js/tests/activity.test.js`:

```js
import { test, assertEq } from "./run.js";
import { activeDaySet, streaks } from "../derive/activity.js";

const completed = [
  { completed_at: "2026-08-01", revision: { history: [{ date: "2026-08-03", result: "PASS", stage: 1 }] } },
  { completed_at: "2026-08-02", revision: {} },
];

test("activeDaySet unions solves and revisions", () => {
  assertEq([...activeDaySet(completed)].sort(), ["2026-08-01", "2026-08-02", "2026-08-03"]);
});

test("streak counts through today", () => {
  assertEq(streaks(new Set(["2026-08-01", "2026-08-02", "2026-08-03"]), "2026-08-03"), { current: 3, max: 3 });
});

test("streak survives if today not yet active (counts from yesterday)", () => {
  assertEq(streaks(new Set(["2026-08-01", "2026-08-02"]), "2026-08-03").current, 2);
});

test("no grace: gap breaks current streak, max remembers", () => {
  assertEq(streaks(new Set(["2026-07-28", "2026-07-29", "2026-08-02"]), "2026-08-02"), { current: 1, max: 2 });
});
```

Add `import "./js/tests/activity.test.js";` to tests.html (before `report()` — convert the inline script to import test modules first, then call report()).

- [x] **Step 3: Run tests.html — expect FAIL** (module not found → title FAIL or console error; confirm the tests do not pass vacuously).

- [x] **Step 4: Implement activity.js**

```js
import { addDays, diffDays } from "./dates.js";

export function activeDaySet(completed) {
  const days = new Set();
  for (const rec of completed || []) {
    if (rec.completed_at) days.add(rec.completed_at);
    for (const h of rec.revision?.history || []) if (h.date) days.add(h.date);
  }
  return days;
}

export function streaks(daySet, todayIso) {
  const sorted = [...daySet].sort();
  let max = 0;
  let run = 0;
  let prev = null;
  for (const day of sorted) {
    run = prev !== null && diffDays(prev, day) === 1 ? run + 1 : 1;
    if (run > max) max = run;
    prev = day;
  }
  let current = 0;
  let cursor = daySet.has(todayIso) ? todayIso : addDays(todayIso, -1);
  while (daySet.has(cursor)) {
    current += 1;
    cursor = addDays(cursor, -1);
  }
  return { current, max };
}
```

- [x] **Step 5: Write failing tests for memory.js**

`js/tests/memory.test.js`:

```js
import { test, assertEq } from "./run.js";
import { matureRecallStats, maturityBuckets, dueForecast } from "../derive/memory.js";

const completed = [
  { problem_id: "A", completed_at: "2026-07-01",
    revision: { status: "ACTIVE", stage: 2, next_due: "2026-08-05",
      history: [{ date: "2026-07-08", result: "PASS", stage: 1 }, { date: "2026-07-22", result: "PASS", stage: 2 }] } },
  { problem_id: "B", completed_at: "2026-07-02",
    revision: { status: "ACTIVE", stage: 1, next_due: "2026-08-02",
      history: [{ date: "2026-07-09", result: "FAIL", stage: 1 }] } },
  { problem_id: "C", completed_at: "2026-06-01", revision: { status: "MASTERED", stage: 4, history: [
      { date: "2026-06-08", result: "PASS", stage: 1 }, { date: "2026-06-22", result: "PASS", stage: 2 },
      { date: "2026-07-15", result: "FAIL", stage: 3 }, { date: "2026-07-16", result: "PASS", stage: 3 },
      { date: "2026-07-31", result: "PASS", stage: 4 } ] } },
];

test("mature recalls = history entries with stage >= 2", () => {
  // A: 1 mature (stage2 PASS). C: stage2 PASS, stage3 FAIL, stage3 PASS, stage4 PASS = 4. B: none.
  assertEq(matureRecallStats(completed), { pass: 4, total: 5, rate: 0.8 });
});

test("maturity buckets", () => {
  // total problems 10; completed 3 → new 7; B stage1 learning; A stage2 young; C mastered mature
  assertEq(maturityBuckets(10, completed), { new: 7, learning: 1, young: 1, mature: 1 });
});

test("dueForecast counts overdue + per-day dues + cumulative backlog", () => {
  const f = dueForecast(completed, "2026-08-04", 3);
  assertEq(f.overdueBefore, 1); // B due 08-02
  assertEq(f.bars[1], { offset: 1, due: 1, backlogIfIdle: 2 }); // A due 08-05
});

test("empty history yields null rate", () => {
  assertEq(matureRecallStats([]).rate, null);
});
```

Add the import to tests.html.

- [x] **Step 6: Run — expect FAIL. Then implement memory.js**

```js
import { diffDays } from "./dates.js";

export function matureRecallStats(completed) {
  let pass = 0;
  let total = 0;
  for (const rec of completed || []) {
    for (const h of rec.revision?.history || []) {
      if ((h.stage ?? 0) < 2) continue;
      total += 1;
      if (h.result === "PASS") pass += 1;
    }
  }
  return { pass, total, rate: total ? pass / total : null };
}

export function maturityBuckets(totalProblems, completed) {
  const buckets = { new: 0, learning: 0, young: 0, mature: 0 };
  for (const rec of completed || []) {
    const r = rec.revision || {};
    if (r.status === "MASTERED") buckets.mature += 1;
    else if ((r.stage ?? 0) >= 2) buckets.young += 1;
    else buckets.learning += 1;
  }
  buckets.new = Math.max(0, totalProblems - (completed || []).length);
  return buckets;
}

export function dueForecast(completed, startIso, daysAhead = 30) {
  const perDay = new Map();
  let overdueBefore = 0;
  for (const rec of completed || []) {
    const r = rec.revision || {};
    if (!r.next_due || r.status === "MASTERED") continue;
    const offset = diffDays(startIso, r.next_due);
    if (offset < 0) overdueBefore += 1;
    else if (offset < daysAhead) perDay.set(offset, (perDay.get(offset) || 0) + 1);
  }
  const bars = [];
  let backlog = overdueBefore;
  for (let offset = 0; offset < daysAhead; offset += 1) {
    const due = perDay.get(offset) || 0;
    backlog += due;
    bars.push({ offset, due, backlogIfIdle: backlog });
  }
  return { overdueBefore, bars };
}
```

- [x] **Step 7: Write failing tests for pace.js, then implement**

`js/tests/pace.test.js`:

```js
import { test, assertEq } from "./run.js";
import { paceProjection, fastestByDifficulty, nearComplete } from "../derive/pace.js";

test("paceProjection projects finish from velocity", () => {
  // 14 days elapsed, 10 solved → 5/week; 30 remaining → 6 weeks → finish +42d
  const p = paceProjection({ solved: 10, target: 40, startIso: "2026-07-21", endIso: "2026-10-25", todayIso: "2026-08-04" });
  assertEq(p.velocityPerWeek, 5);
  assertEq(p.finishIso, "2026-09-15");
  assertEq(p.onTrack, true);
});

test("what-if overrides velocity", () => {
  const p = paceProjection({ solved: 10, target: 40, startIso: "2026-07-21", endIso: "2026-08-10", todayIso: "2026-08-04", whatIfPerWeek: 2 });
  assertEq(p.onTrack, false);
});

test("zero velocity yields null finish", () => {
  assertEq(paceProjection({ solved: 0, target: 10, startIso: "2026-08-01", endIso: "2026-10-01", todayIso: "2026-08-04" }).finishIso, null);
});

test("fastestByDifficulty picks min minutes per difficulty", () => {
  assertEq(
    fastestByDifficulty([
      { difficulty: "Easy", minutes: 30, problemId: "A" },
      { difficulty: "Easy", minutes: 20, problemId: "B" },
      { difficulty: "Hard", minutes: 90, problemId: "C" },
    ]),
    { Easy: { difficulty: "Easy", minutes: 20, problemId: "B" }, Hard: { difficulty: "Hard", minutes: 90, problemId: "C" } }
  );
});

test("nearComplete ranks by fewest remaining, >=60% done, excludes complete", () => {
  const groups = [
    { id: "a", name: "A", done: 9, total: 10 },
    { id: "b", name: "B", done: 6, total: 10 },
    { id: "c", name: "C", done: 10, total: 10 },
    { id: "d", name: "D", done: 1, total: 10 },
  ];
  assertEq(nearComplete(groups).map((g) => g.id), ["a", "b"]);
});
```

Implement `derive/pace.js`:

```js
import { addDays, diffDays } from "./dates.js";

export function paceProjection({ solved, target, startIso, endIso, todayIso, whatIfPerWeek = null }) {
  const elapsedDays = Math.max(1, diffDays(startIso, todayIso));
  const velocityPerWeek = (solved / elapsedDays) * 7;
  const rate = whatIfPerWeek ?? velocityPerWeek;
  const remaining = Math.max(0, target - solved);
  if (rate <= 0) return { velocityPerWeek, finishIso: null, onTrack: false };
  const finishIso = addDays(todayIso, Math.ceil((remaining / rate) * 7));
  return { velocityPerWeek, finishIso, onTrack: finishIso <= endIso };
}

export function fastestByDifficulty(entries) {
  const best = {};
  for (const entry of entries || []) {
    if (!entry.difficulty || !(entry.minutes > 0)) continue;
    if (!best[entry.difficulty] || entry.minutes < best[entry.difficulty].minutes) best[entry.difficulty] = entry;
  }
  return best;
}

export function nearComplete(groups, limit = 4) {
  return (groups || [])
    .filter((g) => g.total > 0 && g.done < g.total && g.done / g.total >= 0.6)
    .map((g) => ({ ...g, remaining: g.total - g.done }))
    .sort((a, b) => a.remaining - b.remaining || b.done / b.total - a.done / a.total)
    .slice(0, limit);
}
```

- [x] **Step 8: Write failing tests for search.js, then implement**

`js/tests/search.test.js`:

```js
import { test, assertEq } from "./run.js";
import { fuzzyScore } from "../derive/search.js";

test("exact substring beats scattered subsequence", () => {
  const sub = fuzzyScore("heat", "Activity heatmap");
  const scattered = fuzzyScore("heat", "h-e-x-a-t"); // h,e,a,t as subsequence only
  if (!(sub > scattered && scattered > 0)) throw new Error(`sub=${sub} scattered=${scattered}`);
});

test("word-start matches score higher", () => {
  if (!(fuzzyScore("rq", "Revision Queue") > fuzzyScore("rq", "problem rq browser") * 0.5)) throw new Error("prefix bonus missing");
});

test("no subsequence -> 0", () => {
  assertEq(fuzzyScore("zzz", "Revision Queue"), 0);
});

test("empty query matches everything weakly", () => {
  if (!(fuzzyScore("", "anything") > 0)) throw new Error("empty query should match");
});
```

Implement `derive/search.js` (subsequence scorer with contiguity + word-start bonuses):

```js
export function fuzzyScore(query, text) {
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (!q) return 0.1;
  let score = 0;
  let ti = 0;
  let streak = 0;
  for (const ch of q) {
    const found = t.indexOf(ch, ti);
    if (found === -1) return 0;
    const wordStart = found === 0 || t[found - 1] === " " || t[found - 1] === "-";
    streak = found === ti ? streak + 1 : 1;
    score += 1 + streak * 2 + (wordStart ? 3 : 0);
    ti = found + 1;
  }
  return score / (1 + t.length / 50); // mild length normalization
}
```

- [x] **Step 9: Run tests.html — expect title `PASS (15)`** (all four suites). Fix until green.

- [x] **Step 10: Commit**

```bash
git add web_dashboard/js/derive web_dashboard/js/tests web_dashboard/tests.html
git commit -m "feat/dashboard: pure derivation modules with browser-harness tests

streaks (no grace), mature-recall retention, maturity buckets, 30d due
forecast with backlog-if-idle, pace projection, fuzzy scorer"
```

---

### Task 4: Lazy per-workspace rendering

**Files:**
- Modify: `web_dashboard/js/legacy/app.js` — `renderAll()` (app.js:5829) and `switchWorkspace()` (app.js:226)

**Interfaces:**
- Produces: exported `RENDERERS` = `{ global: [fn...], byWorkspace: { today: [...], plan: [...], problems: [...], practice: [...], curriculum: [...], evidence: [...] } }` and exported `markAllDirty()`. Later tasks push feature renderers into these arrays.
- Behavior contract: `renderAll()` runs global renderers + the ACTIVE workspace's renderers only; `switchWorkspace(ws)` renders `ws`'s renderers if dirty, then proceeds as before. Feed refresh (`visibilitychange`) calls `markAllDirty()` then `renderAll()`.

- [x] **Step 1: Build the registry in legacy/app.js**

Directly above `renderAll()`, add (mapping current renderAll body by the section→workspace attribution in index.html `data-workspace-section`):

```js
const RENDERERS = {
  global: [renderDataWarning],
  byWorkspace: {
    today: [renderNextAction, renderTrajectory, renderReadiness, renderDueQueue, renderForecast, renderPaceTiles, renderTodayContract],
    plan: [renderWeekScoreboard, renderMonthMilestones, renderQuarterRoadmap],
    problems: [renderProblemBrowser],
    practice: [renderWeaknessLab, renderEdgeCases],
    curriculum: [renderStages, renderPromotionLadder, renderConstellation, renderSkills, renderPatterns],
    evidence: [
      renderDeferredLearnings, renderThinkingBars, renderProblemTable, renderThinkingProfile,
      renderLearningNotes, renderHintIndependence, renderMockTrend, renderRetentionTiles,
      renderConsistency, renderTimeInvested, renderActivityHeatmap, renderRevisionCalendar,
    ],
  },
};
const renderedClean = new Set(); // workspaces whose renderers ran since last data change

function markAllDirty() {
  renderedClean.clear();
}

function renderWorkspace(workspace) {
  if (renderedClean.has(workspace)) return;
  (RENDERERS.byWorkspace[workspace] || []).forEach((fn) => fn());
  renderedClean.add(workspace);
}
```

- [x] **Step 2: Rewrite renderAll body**

```js
function renderAll() {
  $("#last-updated").textContent = `Updated ${state.datasets.progress.last_updated}`;
  $("#reference-date-pill").textContent = `Reference date ${referenceDate()}`;
  RENDERERS.global.forEach((fn) => fn());
  markAllDirty();
  switchWorkspace(state.activeWorkspace); // switchWorkspace calls renderWorkspace
}
```

In `switchWorkspace(workspace, targetHash)`, immediately after `state.activeWorkspace = active;` insert `renderWorkspace(active);`.

CAUTION: `buildStageOptions()` and any code that reads DOM built by renderers must still work — search for reads of `#stage-filter` etc.; those are built from datasets, not renders, so unaffected. The constellation `state.constellationFilter` logic assumed renderConstellation ran; it now runs on first curriculum visit — verify filters still attach (they're wired inside renderConstellation, so fine).

- [x] **Step 3: Add exports**

Append `RENDERERS, markAllDirty,` to the export block from Task 1.

- [x] **Step 4: Verify**

Reload dashboard. Expected: Today paints; DevTools → Elements: `#constellation` is EMPTY until you open Curriculum, then populates; `#problem-table` empty until Evidence. Switch through all 6 workspaces — every view renders on first visit. Toggle theme, use curriculum search filter, open problem modal — all work. Switch away and back — no duplicate content (renderers are idempotent: they rebuild innerHTML; confirm no view appends duplicates — if one does, it renders twice only when dirty, still fine).

- [x] **Step 5: Commit**

```bash
git add web_dashboard/js/legacy/app.js
git commit -m "perf/dashboard: lazy per-workspace rendering via render registry

only the active workspace renders on load/focus; views render on first
visit and re-render only after data refresh (markAllDirty)"
```

---

### Task 5: data.js — explicit feed status (kill the silent port cliff)

**Files:**
- Create: `web_dashboard/js/data.js`
- Modify: `web_dashboard/js/legacy/app.js` — `fetchFeed()` (app.js:399), `renderDataWarning()`, `main()`

**Interfaces:**
- Produces: `fetchFeedStatus() -> Promise<{feed: object|null, status: "ok"|"static-server"|"server-down"|"feed-error", detail: string}>` from `js/data.js`.

- [x] **Step 1: Write js/data.js**

```js
// The python server (scripts/serve_dashboard.py) owns /api/feed. Any http origin
// is allowed to TRY it — no port hardcode — but failures are classified so the
// banner can say exactly what is wrong instead of silently degrading.
export async function fetchFeedStatus() {
  if (window.location.protocol !== "http:" && window.location.protocol !== "https:") {
    return { feed: null, status: "static-server", detail: "Not served over http — run `make web-dashboard`." };
  }
  let response;
  try {
    response = await fetch("/api/feed", { cache: "no-store" });
  } catch (error) {
    return { feed: null, status: "server-down", detail: `No /api/feed at ${window.location.origin} — run \`make web-dashboard\` (port 8765).` };
  }
  if (!response.ok) {
    return { feed: null, status: response.status === 404 ? "static-server" : "feed-error", detail: `/api/feed returned ${response.status} — this origin is not the dashboard server. Run \`make web-dashboard\`.` };
  }
  try {
    const feed = await response.json();
    if (feed && !feed.error) return { feed, status: "ok", detail: "" };
    return { feed: null, status: "feed-error", detail: `Feed error: ${feed?.error || "empty payload"}` };
  } catch (error) {
    return { feed: null, status: "feed-error", detail: `Feed parse failed: ${error.message}` };
  }
}
```

- [x] **Step 2: Wire into legacy/app.js**

Add `import { fetchFeedStatus } from "../data.js";` at the top of `js/legacy/app.js`. Replace the body of `fetchFeed()` with:

```js
async function fetchFeed() {
  const result = await fetchFeedStatus();
  state.feedStatus = result;
  return result.feed;
}
```

Add `feedStatus: null,` to the `state` object literal. In `renderDataWarning()` (find it near the top of the render functions): when `state.feed` is null and `state.feedStatus`, show `state.feedStatus.detail` in the existing `#data-warning` banner instead of the current generic message; keep the dismiss button behavior.

- [x] **Step 3: Verify**

Reload on :8765 → no banner, live pill present. Then `python3 -m http.server 9000` from repo root, open `http://127.0.0.1:9000/web_dashboard/` → banner explains "not the dashboard server / run make web-dashboard" (NOT silent). Kill that server.

- [x] **Step 4: Commit**

```bash
git add web_dashboard/js/data.js web_dashboard/js/legacy/app.js
git commit -m "fix/dashboard: explicit feed status banner replaces silent port cliff"
```

---

### Task 6: svg.js — single SVG helper

**Files:**
- Create: `web_dashboard/js/svg.js`
- Modify: `web_dashboard/js/legacy/app.js` — the five local helpers (near app.js:913, 1212, 1416, 5714 and `svgNode()` at 4660)

**Interfaces:**
- Produces: `svgEl(tag, attrs = {}, children = []) -> SVGElement` — sets attributes via `setAttribute`, appends children (nodes or strings→text nodes).

- [ ] **Step 1: Write js/svg.js**

```js
const SVG_NS = "http://www.w3.org/2000/svg";

export function svgEl(tag, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(key, String(value));
  }
  for (const child of children) {
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}
```

- [ ] **Step 2: Replace the duplicated local helpers**

`grep -n "svgNS\|createElementNS" js/legacy/app.js`. For each local `el(...)`/helper definition (approx lines 913, 1212, 1416, 5714) delete the local definition and adapt call sites to `svgEl` (signatures are near-identical; adjust argument shapes where a local helper took `(tag, attrs)` only). Replace `svgNode()` (app.js:4660) usages the same way. Import at top: `import { svgEl } from "../svg.js";`

- [ ] **Step 3: Verify** — every chart still draws: forecast, week bars, burnup, thinking bars, hint chart, sparklines, heatmap, calendar, consistency, time chart, trajectory, constellation. Both themes. Zero console errors.

- [ ] **Step 4: Commit**

```bash
git add web_dashboard/js/svg.js web_dashboard/js/legacy/app.js
git commit -m "refactor/dashboard: single svgEl helper replaces five local copies"
```

---

### Task 7: Motion foundation (tokens.css + motion.js + view transitions)

**Files:**
- Create: `web_dashboard/css/tokens.css` (loaded BEFORE legacy.css in index.html)
- Create: `web_dashboard/js/engine/motion.js`
- Modify: `web_dashboard/index.html` (link tag), `web_dashboard/js/legacy/app.js` (`switchWorkspace` wrap, headline count-ups)

**Interfaces:**
- Produces: `motion.js` exports `reducedMotion() -> bool`, `viewSwitch(fn)` (wraps `document.startViewTransition` when available/allowed, else calls fn), `animateCount(el, value, {format} = {})` (counts up once, ~500ms, writes final formatted value; instant under reduced motion).
- Produces: CSS custom props `--dur-feedback: 120ms; --dur-overlay: 200ms; --dur-view: 280ms; --ease-out: cubic-bezier(0.16, 1, 0.3, 1);`

- [ ] **Step 1: Write css/tokens.css**

```css
:root {
  --dur-feedback: 120ms;
  --dur-overlay: 200ms;
  --dur-view: 280ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

@media (prefers-reduced-motion: reduce) {
  :root { --dur-feedback: 0ms; --dur-overlay: 0ms; --dur-view: 0ms; }
  ::view-transition-group(*),
  ::view-transition-old(*),
  ::view-transition-new(*) { animation: none !important; }
}

::view-transition-old(root) { animation-duration: calc(var(--dur-view) * 0.66); }
::view-transition-new(root) { animation-duration: var(--dur-view); animation-timing-function: var(--ease-out); }
```

Add `<link rel="stylesheet" href="./css/tokens.css" />` ABOVE the legacy.css link in index.html.

- [ ] **Step 2: Write js/engine/motion.js**

```js
export function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function viewSwitch(fn) {
  if (reducedMotion() || !document.startViewTransition) {
    fn();
    return;
  }
  document.startViewTransition(fn);
}

export function animateCount(el, value, { format = (v) => String(v) } = {}) {
  if (el.dataset.counted === String(value)) return; // once per value per load
  el.dataset.counted = String(value);
  if (reducedMotion() || !(value > 0)) {
    el.textContent = format(value);
    return;
  }
  const start = performance.now();
  const dur = 500;
  const tick = (now) => {
    const t = Math.min(1, (now - start) / dur);
    el.textContent = format(Math.round(value * (1 - Math.pow(1 - t, 3))));
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
```

- [ ] **Step 3: Wire workspace switches**

In legacy `main()`, find the nav click handler that calls `switchWorkspace` (search `data-workspace-link` listeners near the end of app.js). Wrap the call: `viewSwitch(() => switchWorkspace(ws, hash))` (import from `../engine/motion.js`). Do NOT wrap the scroll-spy or initial render.

- [ ] **Step 4: Verify** — clicking between workspaces cross-fades (~280ms); with DevTools "emulate prefers-reduced-motion" it switches instantly. Keyboard/theme unaffected. No animation on initial page load.

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/css/tokens.css web_dashboard/js/engine/motion.js web_dashboard/index.html web_dashboard/js/legacy/app.js
git commit -m "feat/dashboard: motion tokens, view-transition workspace switches, count-up util"
```

---

### Task 8: Tooltip + crosshair engine

**Files:**
- Create: `web_dashboard/js/engine/tooltip.js`, `web_dashboard/css/components/tooltip.css` (+ link in index.html)
- Modify: `web_dashboard/js/legacy/app.js` — heatmap, calendar, forecast, hint chart, time chart, burnup renderers

**Interfaces:**
- Produces: `initTooltips()` (delegated singleton; call once from main.js), and the convention: any element with `data-tip="<html string>"` shows a pointer-following tooltip on hover/focus. `attachCrosshair(svg, points, renderTip)` adds a vertical crosshair line + shared tooltip across a time-series SVG, where points = `[{x, label, values: [{name, text}]}]` in SVG user units.

- [ ] **Step 1: Write css/components/tooltip.css**

```css
.dt-tooltip {
  position: fixed;
  inset: auto auto 0 0;
  margin: 0;
  border: 0;
  padding: 6px 9px;
  max-width: 320px;
  border-radius: 6px;
  background: light-dark(#1c2330, #0b1017);
  color: #e8edf5;
  font: 12px/1.45 system-ui, sans-serif;
  box-shadow: 0 4px 16px rgb(0 0 0 / 0.35);
  pointer-events: none;
  z-index: 1000;
  opacity: 0;
  transition: opacity var(--dur-feedback);
}
.dt-tooltip.show { opacity: 1; }
.dt-crosshair { stroke: currentColor; stroke-width: 1; opacity: 0.35; pointer-events: none; }
```

- [ ] **Step 2: Write js/engine/tooltip.js**

```js
let tipEl = null;

function ensureTip() {
  if (!tipEl) {
    tipEl = document.createElement("div");
    tipEl.className = "dt-tooltip";
    document.body.append(tipEl);
  }
  return tipEl;
}

function place(clientX, clientY) {
  const tip = ensureTip();
  const pad = 12;
  const rect = tip.getBoundingClientRect();
  const x = Math.min(clientX + pad, window.innerWidth - rect.width - pad);
  const y = clientY - rect.height - pad < 0 ? clientY + pad : clientY - rect.height - pad;
  tip.style.transform = `translate(${x}px, ${y}px)`;
}

export function showTip(html, clientX, clientY) {
  const tip = ensureTip();
  tip.innerHTML = html;
  tip.classList.add("show");
  place(clientX, clientY);
}

export function hideTip() {
  ensureTip().classList.remove("show");
}

export function initTooltips() {
  document.addEventListener("pointerover", (e) => {
    const host = e.target.closest("[data-tip]");
    if (host) showTip(host.dataset.tip, e.clientX, e.clientY);
  });
  document.addEventListener("pointermove", (e) => {
    const host = e.target.closest("[data-tip]");
    if (host) place(e.clientX, e.clientY);
    else hideTip();
  });
  document.addEventListener("pointerout", (e) => {
    if (e.target.closest?.("[data-tip]")) hideTip();
  });
  // Keyboard parity: focus shows the tooltip under the focused element.
  document.addEventListener("focusin", (e) => {
    const host = e.target.closest("[data-tip]");
    if (!host) return hideTip();
    const r = host.getBoundingClientRect();
    showTip(host.dataset.tip, r.left + r.width / 2, r.top);
  });
}

export function attachCrosshair(svg, points, renderTip) {
  if (!points?.length) return;
  const ns = "http://www.w3.org/2000/svg";
  const line = document.createElementNS(ns, "line");
  line.setAttribute("class", "dt-crosshair");
  line.setAttribute("y1", "0");
  line.setAttribute("y2", "100%");
  line.style.display = "none";
  svg.append(line);
  svg.addEventListener("pointermove", (e) => {
    const rect = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const sx = ((e.clientX - rect.left) / rect.width) * (vb?.width || rect.width);
    let nearest = points[0];
    for (const p of points) if (Math.abs(p.x - sx) < Math.abs(nearest.x - sx)) nearest = p;
    line.setAttribute("x1", nearest.x);
    line.setAttribute("x2", nearest.x);
    line.setAttribute("y1", vb ? 0 : 0);
    line.setAttribute("y2", vb ? vb.height : rect.height);
    line.style.display = "";
    showTip(renderTip(nearest), e.clientX, e.clientY);
  });
  svg.addEventListener("pointerleave", () => {
    line.style.display = "none";
    hideTip();
  });
}
```

- [ ] **Step 3: Wire it**

`main.js`: `import { initTooltips } from "./engine/tooltip.js"; initTooltips();`
In legacy renderers add `data-tip` attributes (escape values with the existing escaping approach — set via `el.dataset.tip = text`, never innerHTML interpolation):
- heatmap cells (app.js:5179): `"{date} — {n} solves, {m} revisions"`
- revision calendar day cells (app.js:5339): list of due problem ids
- forecast bars (app.js:886): `"{date}: {n} due"`
- hint chart + time chart + burnup: call `attachCrosshair(svg, points, fn)` after building each SVG, mapping each x-position to its values.

- [ ] **Step 4: Verify** — hover each listed chart: tooltip follows pointer, crosshair snaps to nearest point on the three line/bar time-series; tab-focusing a calendar cell shows its tooltip; reduced-motion still shows tooltips (opacity transition collapses). Both themes readable.

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/js/engine/tooltip.js web_dashboard/css/components/tooltip.css web_dashboard/index.html web_dashboard/js/legacy/app.js web_dashboard/js/main.js
git commit -m "feat/dashboard: shared tooltip + crosshair engine wired to charts"
```

---

### Task 9: Drill-down engine (no dead pixels)

**Files:**
- Create: `web_dashboard/js/engine/drilldown.js`
- Modify: `web_dashboard/js/legacy/app.js` — heatmap, calendar, forecast, retention tiles renderers

**Interfaces:**
- Consumes: `setModal(title, subtitle, eyebrow)` and `state` from legacy; `problemStatus(problemId)`.
- Produces: `openProblemList({title, subtitle, items})` where items = `[{problemId, note}]` — fills the existing `#skill-modal` with a linked list; clicking an item opens the existing problem modal (legacy's problem-modal opener — find it near app.js:4101, export it as `openProblemModal(problemId)` from legacy).

- [ ] **Step 1: Export legacy problem-modal opener**

In legacy/app.js find the function that renders a problem into the modal (app.js:~4101). If it isn't a single function taking a problem id, wrap it: `function openProblemModal(problemId) { <existing invocation path> }` and add to exports.

- [ ] **Step 2: Write js/engine/drilldown.js**

```js
import { state, setModal, problemStatus, openProblemModal } from "../legacy/app.js";

export function openProblemList({ title, subtitle = "", items }) {
  const body = setModal(title, subtitle, "Drill-down");
  const list = document.createElement("div");
  list.className = "stack";
  if (!items.length) list.innerHTML = `<p class="small-muted">Nothing here.</p>`;
  for (const item of items) {
    const problem = state.problemsById.get(item.problemId);
    const row = document.createElement("button");
    row.type = "button";
    row.className = "drill-row";
    const status = problemStatus(item.problemId);
    row.textContent = `${status.glyph} ${item.problemId} ${problem?.title || ""} ${item.note || ""}`;
    row.addEventListener("click", () => openProblemModal(item.problemId));
    list.append(row);
  }
  body.append(list);
}
```

NOTE: check `setModal`'s actual return (app.js:168) — if it doesn't return the body element, follow legacy's pattern: call `setModal(...)` then fill `$("#modal-body")`. Match whatever every other modal-filler in legacy does.

- [ ] **Step 3: Wire click targets in legacy renderers**

- Heatmap cell click → `openProblemList({title: date, items: [solves and revisions that date]})` (derive by scanning `state.completedById` values: `completed_at === date` or a `revision.history` entry with that date).
- Calendar day click already shows a detail pane — ADD problem links there using `openProblemModal`.
- Forecast bar click → problems whose `revision.next_due` is that date.
- Retention tiles click → the problems in that tile's bucket (the renderer already has the per-bucket lists in scope; pass them).
Make each clickable element a `<button type="button">` or set `tabindex="0"` + Enter handler — every drill target must be keyboard-reachable.

- [ ] **Step 4: Verify** — click a heatmap cell → modal lists that day's activity; click through to a problem modal; Esc closes (existing dialog behavior). Same for forecast bar and a retention tile. All reachable by Tab+Enter.

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/js/engine/drilldown.js web_dashboard/js/legacy/app.js
git commit -m "feat/dashboard: universal drill-down - heatmap, calendar, forecast, retention open underlying problems"
```

---

### Task 10: Keyboard model + shortcut help

**Files:**
- Create: `web_dashboard/js/engine/keyboard.js`, `web_dashboard/css/components/keyboard.css` (+ link)
- Modify: `web_dashboard/js/main.js`

**Interfaces:**
- Consumes: `switchWorkspace`, `toggleTheme`, `state` from legacy; `viewSwitch` from motion.
- Produces: `initKeyboard({onFocusMode})` — global router. Bindings: `g t/p/b/w/c/e` workspaces (today/plan/problems(b)/practice(w)/curriculum/evidence), `j/k`+`Enter` roving selection over the visible list (due queue on Today, browser rows on Problems), `/` focus the visible search input, `t` theme, `f` focus mode, `?` help overlay, `Escape` closes overlay. Exposes `registerList(selector, {itemSelector, onEnter})` used by later tasks.

- [ ] **Step 1: Write js/engine/keyboard.js**

```js
import { state, switchWorkspace, toggleTheme } from "../legacy/app.js";
import { viewSwitch } from "./motion.js";

const CHORD_TIMEOUT_MS = 900;
const GO = { t: "today", p: "plan", b: "problems", w: "practice", c: "curriculum", e: "evidence" };
let pendingChord = null;
let chordTimer = 0;
const lists = [];
let listPos = -1;

function typingContext(e) {
  const t = e.target;
  return t.closest?.("input, textarea, select, [contenteditable]") || document.querySelector("dialog[open]");
}

export function registerList(selector, { itemSelector, onEnter }) {
  lists.push({ selector, itemSelector, onEnter });
}

function activeList() {
  return lists.find((l) => {
    const host = document.querySelector(l.selector);
    return host && host.offsetParent !== null;
  });
}

function moveSelection(delta) {
  const list = activeList();
  if (!list) return;
  const items = [...document.querySelectorAll(`${list.selector} ${list.itemSelector}`)];
  if (!items.length) return;
  listPos = Math.max(0, Math.min(items.length - 1, listPos + delta));
  items.forEach((el, i) => el.classList.toggle("kb-selected", i === listPos));
  items[listPos].scrollIntoView({ block: "nearest" });
}

export function initKeyboard({ onFocusMode, onHelp } = {}) {
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (typingContext(e)) return;
    if (pendingChord === "g") {
      pendingChord = null;
      clearTimeout(chordTimer);
      const ws = GO[e.key];
      if (ws) {
        e.preventDefault();
        viewSwitch(() => switchWorkspace(ws));
        listPos = -1;
      }
      return;
    }
    switch (e.key) {
      case "g":
        pendingChord = "g";
        chordTimer = setTimeout(() => { pendingChord = null; }, CHORD_TIMEOUT_MS);
        break;
      case "j": moveSelection(1); break;
      case "k": moveSelection(-1); break;
      case "Enter": {
        const list = activeList();
        const sel = list && document.querySelector(`${list.selector} .kb-selected`);
        if (sel) { e.preventDefault(); list.onEnter(sel); }
        break;
      }
      case "/": {
        const search = [...document.querySelectorAll('input[type="search"]')].find((i) => i.offsetParent !== null);
        if (search) { e.preventDefault(); search.focus(); }
        break;
      }
      case "t": toggleTheme(); break;
      case "f": onFocusMode?.(); break;
      case "?": onHelp?.(); break;
    }
  });
}
```

- [ ] **Step 2: Help overlay** — in keyboard.css style `.kb-selected { outline: 2px solid var(--accent, #60a5fa); outline-offset: -2px; }` and a `.kb-help` popover. In main.js build the overlay with the native Popover API:

```js
const help = document.createElement("div");
help.className = "kb-help";
help.popover = "auto";
help.innerHTML = `<h3>Keyboard</h3><dl>
  <dt>g then t/p/b/w/c/e</dt><dd>Go to workspace</dd>
  <dt>j / k / Enter</dt><dd>Move through visible list, open</dd>
  <dt>/</dt><dd>Search</dd><dt>t</dt><dd>Theme</dd>
  <dt>f</dt><dd>Focus mode</dd><dt>Ctrl+K</dt><dd>Command palette</dd>
  <dt>?</dt><dd>This help</dd></dl>`;
document.body.append(help);
initKeyboard({ onHelp: () => help.togglePopover(), onFocusMode: () => {} }); // focus mode wired in Task 14
```

Register the two lists in main.js:

```js
registerList("#due-queue", { itemSelector: ".due-item, [data-problem-id]", onEnter: (el) => el.click() });
registerList("#browser-rows", { itemSelector: "tr", onEnter: (el) => el.querySelector("a, button")?.click() || el.click() });
```

(Inspect the due-queue renderer's actual item class and use it; the browser rows are `<tr>` in `#browser-rows`.)

- [ ] **Step 3: Verify** — `g e` jumps to Evidence, `g t` back; on Today `j/j/k` moves a visible highlight through due queue, Enter opens it; `/` focuses search on Curriculum; `t` flips theme; `?` toggles help; typing in the search box does NOT trigger shortcuts; with modal open only Esc works.

- [ ] **Step 4: Commit**

```bash
git add web_dashboard/js/engine/keyboard.js web_dashboard/css/components/keyboard.css web_dashboard/js/main.js web_dashboard/index.html
git commit -m "feat/dashboard: keyboard model - g-chords, j/k list nav, help overlay"
```

---

### Task 11: Command palette (Ctrl+K)

**Files:**
- Create: `web_dashboard/js/engine/palette.js`, `web_dashboard/css/components/palette.css` (+ link)
- Modify: `web_dashboard/js/main.js`

**Interfaces:**
- Consumes: `fuzzyScore` from `derive/search.js`; `state`, `WORKSPACE_META`, `switchWorkspace`, `toggleTheme`, `openProblemModal` from legacy; `viewSwitch` from motion.
- Produces: `initPalette({actions})` — binds Ctrl+K/Cmd+K. `actions` = `[{id, label, hint, run}]` (main.js passes theme toggle, focus mode, help).

- [ ] **Step 1: Write js/engine/palette.js**

```js
import { fuzzyScore } from "../derive/search.js";
import { state, WORKSPACE_META, switchWorkspace, openProblemModal } from "../legacy/app.js";
import { viewSwitch } from "./motion.js";

const FRECENCY_KEY = "palette-frecency";
const frecency = JSON.parse(localStorage.getItem(FRECENCY_KEY) || "{}");

function bump(id) {
  frecency[id] = (frecency[id] || 0) * 0.9 + 1;
  localStorage.setItem(FRECENCY_KEY, JSON.stringify(frecency));
}

function buildIndex(actions) {
  const items = [];
  for (const [ws, meta] of Object.entries(WORKSPACE_META)) {
    items.push({ id: `go:${ws}`, group: "Go to", label: meta.title, hint: `g ${ws === "problems" ? "b" : ws === "practice" ? "w" : ws[0]}`, run: () => viewSwitch(() => switchWorkspace(ws)) });
  }
  for (const a of actions) items.push({ ...a, group: "Actions" });
  for (const [id, problem] of state.problemsById) {
    items.push({ id: `p:${id}`, group: "Problems", label: `${id} ${problem.title || ""}`, hint: "", run: () => openProblemModal(id) });
  }
  for (const [id, skill] of state.skillsById) {
    items.push({ id: `s:${id}`, group: "Skills", label: skill.name || id, hint: "", run: () => viewSwitch(() => switchWorkspace("curriculum")) });
  }
  return items;
}

function rank(items, query) {
  const scored = items
    .map((item) => ({ item, score: fuzzyScore(query, item.label) * (1 + Math.log1p(frecency[item.id] || 0)) }))
    .filter((r) => r.score > 0);
  scored.sort((a, b) => b.score - a.score);
  if (!query) {
    // Empty query: recents (by frecency) then Go-to + Actions, never problems dump.
    return scored.filter((r) => r.item.group !== "Problems" && r.item.group !== "Skills").slice(0, 12);
  }
  return scored.slice(0, 12);
}

export function initPalette({ actions = [] } = {}) {
  const dialog = document.createElement("dialog");
  dialog.className = "palette";
  dialog.innerHTML = `<input type="search" placeholder="Type a command or search…" autofocus />
    <ul role="listbox"></ul>`;
  document.body.append(dialog);
  const input = dialog.querySelector("input");
  const listEl = dialog.querySelector("ul");
  let rows = [];
  let cursor = 0;

  const paint = () => {
    const groups = new Map();
    rows.forEach((r, i) => {
      if (!groups.has(r.item.group)) groups.set(r.item.group, []);
      groups.get(r.item.group).push({ ...r, i });
    });
    listEl.innerHTML = "";
    for (const [group, members] of groups) {
      const head = document.createElement("li");
      head.className = "palette-group";
      head.textContent = group;
      listEl.append(head);
      for (const m of members) {
        const li = document.createElement("li");
        li.className = m.i === cursor ? "sel" : "";
        li.setAttribute("role", "option");
        const label = document.createElement("span");
        label.textContent = m.item.label;
        const hint = document.createElement("kbd");
        hint.textContent = m.item.hint || "";
        li.append(label, hint);
        li.addEventListener("click", () => execute(m.i));
        listEl.append(li);
      }
    }
  };

  const refresh = () => {
    rows = rank(buildIndex(actions), input.value.trim());
    cursor = 0;
    paint();
  };

  const execute = (i) => {
    const row = rows[i];
    if (!row) return;
    dialog.close();
    bump(row.item.id);
    row.item.run();
  };

  input.addEventListener("input", refresh);
  dialog.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || (e.key === "Tab" && !e.shiftKey)) { e.preventDefault(); cursor = Math.min(rows.length - 1, cursor + 1); paint(); }
    else if (e.key === "ArrowUp" || (e.key === "Tab" && e.shiftKey)) { e.preventDefault(); cursor = Math.max(0, cursor - 1); paint(); }
    else if (e.key === "Enter") { e.preventDefault(); execute(cursor); }
    else if (e.key === "Escape" && input.value) { e.preventDefault(); input.value = ""; refresh(); }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      input.value = "";
      refresh();
      dialog.showModal();
      input.focus();
    }
  });
}
```

- [ ] **Step 2: palette.css** — top-layer dialog, 560px wide, top-15vh, instant open (`@starting-style` fade of var(--dur-overlay) on the dialog is acceptable, no scale), `.palette-group` microlabel style, `.sel` highlighted row, `kbd` right-aligned muted. Style `::backdrop` with a translucent scrim.

- [ ] **Step 3: Wire in main.js**

```js
initPalette({ actions: [
  { id: "act:theme", label: "Toggle theme", hint: "t", run: toggleTheme },
  { id: "act:help", label: "Keyboard help", hint: "?", run: () => help.togglePopover() },
  { id: "act:focus", label: "Focus mode", hint: "f", run: () => {} }, // wired in Task 14
] });
```

- [ ] **Step 4: Verify** — Ctrl+K opens with recents/actions (no problem dump on empty query); typing "revq" finds Revision-related views via fuzzy; typing a problem id substring finds the problem, Enter opens its modal; frecency: run "Toggle theme" twice, reopen — it ranks above other actions on empty query; Esc clears query first, second Esc closes; arrows + Tab navigate.

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/js/engine/palette.js web_dashboard/css/components/palette.css web_dashboard/js/main.js web_dashboard/index.html
git commit -m "feat/dashboard: ctrl+k command palette - fuzzy, frecency, grouped results"
```

---

### Task 12: Motivation pack (streaks, badges, bests, nudges)

**Files:**
- Create: `web_dashboard/js/features/motivation.js`, `web_dashboard/css/components/features.css` (+ link)
- Modify: `web_dashboard/index.html` (three small mount points), `web_dashboard/js/legacy/app.js` (register renderer)

**Interfaces:**
- Consumes: `activeDaySet`, `streaks` (derive/activity.js); `fastestByDifficulty`, `nearComplete` (derive/pace.js); `animateCount` (motion); `state`, `RENDERERS` (legacy); `openProblemList` (drilldown).
- Produces: `renderMotivation()` registered into `RENDERERS.byWorkspace.evidence` (streaks+badges+bests mounts live in the heatmap/consistency sections) and `renderNudges()` into `RENDERERS.byWorkspace.today`.

- [ ] **Step 1: Mount points in index.html**

Inside `#activity-heatmap` section, after the `.section-head` div: `<div id="streak-strip" class="streak-strip"></div>` and after `#heatmap-legend`: `<div id="badge-strip" class="badge-strip"></div>`.
Inside `#consistency` section, at the end: `<div id="bests-card" class="bests-card"></div>`.
In `#overview` after the pace-tiles panel: `<section class="panel" id="nudges-panel" aria-labelledby="nudges-heading"><div class="panel-head"><div><p class="eyebrow microlabel">Close it out</p><h3 id="nudges-heading">Almost done</h3></div></div><div id="nudge-cards" class="pace-tiles"></div></section>`.

- [ ] **Step 2: Write js/features/motivation.js**

```js
import { state, RENDERERS } from "../legacy/app.js";
import { activeDaySet, streaks } from "../derive/activity.js";
import { fastestByDifficulty, nearComplete } from "../derive/pace.js";
import { todayISO } from "../derive/dates.js";
import { animateCount } from "../engine/motion.js";
import { openProblemList } from "../engine/drilldown.js";

function referenceToday() {
  return state.feed?.reference_date || todayISO(); // check feed field name; fall back to local date
}

export function renderMotivation() {
  const completed = state.datasets.progress.completed || [];
  const days = activeDaySet(completed);
  const { current, max } = streaks(days, referenceToday());

  const strip = document.querySelector("#streak-strip");
  strip.innerHTML = `<div class="streak-num"><strong class="num" id="streak-current">0</strong><span class="microlabel">day streak</span></div>
    <div class="streak-num"><strong class="num" id="streak-max">0</strong><span class="microlabel">longest</span></div>
    <div class="streak-num"><strong class="num" id="streak-days">0</strong><span class="microlabel">active days</span></div>`;
  animateCount(strip.querySelector("#streak-current"), current);
  animateCount(strip.querySelector("#streak-max"), max);
  animateCount(strip.querySelector("#streak-days"), days.size);

  // Badges: a month earns a badge when every week of that month met its solve
  // target per feed.plan (weeks[] with target + actual). Hide when no plan.
  const badgeHost = document.querySelector("#badge-strip");
  const weeks = state.feed?.plan?.weeks || null;
  if (!weeks) badgeHost.hidden = true;
  else {
    const byMonth = new Map();
    for (const week of weeks) {
      const month = (week.start || week.start_date || "").slice(0, 7);
      if (!month) continue;
      if (!byMonth.has(month)) byMonth.set(month, []);
      byMonth.get(month).push(week);
    }
    badgeHost.hidden = false;
    badgeHost.innerHTML = "";
    for (const [month, ws] of [...byMonth].sort()) {
      const done = ws.every((w) => (w.actual_solves ?? w.actual ?? 0) >= (w.target_solves ?? w.target ?? 0));
      const past = ws.every((w) => (w.end || w.end_date || "") < referenceToday());
      const badge = document.createElement("span");
      badge.className = `badge ${done ? "earned" : past ? "missed" : "open"}`;
      badge.textContent = month;
      badgeHost.append(badge);
    }
  }

  // Personal bests
  const entries = completed
    .map((rec) => ({ problemId: rec.problem_id, minutes: rec.time_taken_minutes, difficulty: state.problemsById.get(rec.problem_id)?.difficulty }))
    .filter((e) => e.difficulty);
  const bests = fastestByDifficulty(entries);
  const mocks = state.datasets.progress.mock_interviews || [];
  const bestMock = mocks.length ? Math.max(...mocks.map((m) => m.score ?? m.overall ?? 0)) : null;
  const bestsHost = document.querySelector("#bests-card");
  bestsHost.innerHTML = `<h4 class="microlabel">Personal bests</h4>` +
    ["Easy", "Medium", "Hard"].map((d) => bests[d]
      ? `<div class="best-row"><span>${d}</span><strong class="num">${bests[d].minutes}m</strong><small>${bests[d].problemId}</small></div>`
      : "").join("") +
    (bestMock !== null ? `<div class="best-row"><span>Best mock</span><strong class="num">${bestMock}</strong></div>` : "") +
    `<div class="best-row"><span>Longest streak</span><strong class="num">${max}d</strong></div>`;
}

export function renderNudges() {
  // groups from skills.json problem groupings joined with completion state
  const groups = [...state.skillsById.values()].map((skill) => {
    const ids = skill.problems || skill.problem_ids || [];
    return { id: skill.id, name: skill.name || skill.id, total: ids.length, done: ids.filter((id) => state.completedById.has(id)).length, ids };
  });
  const top = nearComplete(groups);
  const host = document.querySelector("#nudge-cards");
  const panel = document.querySelector("#nudges-panel");
  panel.hidden = top.length === 0;
  host.innerHTML = "";
  for (const g of top) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "metric-card nudge-card";
    card.innerHTML = `<span class="metric-label">${g.name}</span><strong class="metric-value num">${g.remaining} to finish</strong><small class="metric-note num">${g.done}/${g.total}</small>`;
    card.addEventListener("click", () => openProblemList({
      title: g.name,
      subtitle: `${g.remaining} remaining`,
      items: g.ids.filter((id) => !state.completedById.has(id)).map((id) => ({ problemId: id })),
    }));
    host.append(card);
  }
}

RENDERERS.byWorkspace.evidence.push(renderMotivation);
RENDERERS.byWorkspace.today.push(renderNudges);
```

Import the module for its side effect in main.js: `import "./features/motivation.js";` (BEFORE `main()` runs so registration precedes first render).
IMPORTANT: field-name guesses above (`feed.plan.weeks`, `skill.problems`, `problem.difficulty`, `feed.reference_date`) MUST be verified against reality before wiring: run `curl -s localhost:8765/api/feed | python3 -m json.tool | head -80` and inspect `state.skillsById`/`state.problemsById` entries in DevTools console. Adjust names to the real ones; the fallback chains (`??`) are not a substitute for checking.

- [ ] **Step 3: features.css** — `.streak-strip` horizontal flex with large `.num`; `.badge` pill with `.earned` accent / `.missed` muted / `.open` outline; `.best-row` grid; `.nudge-card` clickable metric-card affordance (cursor, hover raise 120ms). New selectors only — zero overrides of legacy classes.

- [ ] **Step 4: Verify** — Evidence → heatmap section shows streak strip with counts matching visible heatmap (spot-check: count the trailing consecutive active days by eye); badges render or hide cleanly when plan absent; bests show real fastest times (cross-check one against Problem History); no mock recorded → mock row absent. Today shows "Almost done" nudges; clicking one lists the remaining problems. Reduced-motion: numbers appear instantly.

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/js/features/motivation.js web_dashboard/css/components/features.css web_dashboard/index.html web_dashboard/js/main.js web_dashboard/js/legacy/app.js
git commit -m "feat/dashboard: motivation pack - streaks, monthly badges, personal bests, nudges"
```

---

### Task 13: Memory pack (retention gauge, maturity donut, 30d forecast)

**Files:**
- Create: `web_dashboard/js/features/memory.js`
- Modify: `web_dashboard/index.html` (mounts in `#retention` section), `web_dashboard/js/legacy/app.js` (`renderForecast` app.js:886)

**Interfaces:**
- Consumes: `matureRecallStats`, `maturityBuckets`, `dueForecast` (derive/memory.js); `svgEl`; `state`, `RENDERERS`; `openProblemList`; tooltip `data-tip` convention.
- Produces: `renderMemoryPack()` registered into `RENDERERS.byWorkspace.evidence`; forecast horizon change lives inside legacy `renderForecast`.

- [ ] **Step 1: Mounts** — in `#retention` section before `#retention-tiles`: `<div id="memory-gauges" class="memory-gauges"><div id="retention-gauge"></div><div id="maturity-donut"></div></div>`.

- [ ] **Step 2: Write js/features/memory.js**

Retention gauge: SVG arc (semicircle), needle at `rate`, target tick at 0.9, center text `${(rate*100).toFixed(0)}%` (or "–" when null), sublabel `${pass}/${total} mature recalls`. Maturity donut: 4 segments (new/learning/young/mature) via `svgEl` circle strokes (stroke-dasharray technique used by existing charts); center shows total problems; `pointerover` on a segment swaps center text to that bucket's count+label, `pointerout` restores; click a segment → `openProblemList` with that bucket's problems (new = curriculum problems not in `completedById`). Register: `RENDERERS.byWorkspace.evidence.push(renderMemoryPack);` and import for side effect in main.js.

```js
// segment click example (bucket → items)
const bucketItems = {
  mature: completed.filter((r) => r.revision?.status === "MASTERED"),
  young: completed.filter((r) => r.revision?.status !== "MASTERED" && (r.revision?.stage ?? 0) >= 2),
  learning: completed.filter((r) => r.revision?.status !== "MASTERED" && (r.revision?.stage ?? 0) < 2),
};
```

- [ ] **Step 3: Extend forecast to 30 days with backlog shading**

In legacy `renderForecast` (app.js:886): change the horizon from 14 to 30, and overlay a stepped line/area of `backlogIfIdle` from `dueForecast(state.datasets.progress.completed, referenceDate(), 30)` behind the bars (muted warn-tint fill, `data-tip` per point "backlog if idle: N"). Keep existing bars + their tooltips/click-through from Tasks 8-9. Update the section's `.eyebrow` text "Next 14 days" → "Next 30 days" in index.html.

- [ ] **Step 4: Verify** — Evidence: gauge shows plausible % (cross-check: count PASS/(PASS+FAIL) for stage≥2 entries in one completed record); donut counts sum to total curriculum problems; hover swaps center stat; click "young" lists stage-2/3 problems. Today: forecast now spans 30 days, backlog line monotonically rises across due bars, tooltips show both numbers.

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/js/features/memory.js web_dashboard/index.html web_dashboard/js/legacy/app.js web_dashboard/js/main.js
git commit -m "feat/dashboard: memory pack - true-retention gauge, maturity donut, 30d forecast with idle backlog"
```

---

### Task 14: Pace projection + focus mode

**Files:**
- Create: `web_dashboard/js/features/pace.js`, `web_dashboard/js/features/focus.js`, `web_dashboard/css/components/focus.css` (+ link)
- Modify: `web_dashboard/js/legacy/app.js` (`renderQuarterRoadmap` app.js:1345), `web_dashboard/js/main.js` (wire `f` + palette action), `web_dashboard/index.html` (what-if slider mount in `#quarter-roadmap`)

**Interfaces:**
- Consumes: `paceProjection` (derive/pace.js); `state`, `RENDERERS`, `EDGE_CASE_GROUPS` (legacy); `reducedMotion` (motion).
- Produces: `renderPacePanel()` registered into `RENDERERS.byWorkspace.plan`; `toggleFocusMode()` exported from focus.js, wired to key `f` and palette action `act:focus`.

- [ ] **Step 1: Pace panel**

Mount in `#quarter-roadmap` after `#burnup-chart`: `<div id="pace-projection" class="pace-projection"></div>`. In `js/features/pace.js`: read the quarter numbers the roadmap already uses — from `state.feed.plan` (target solves, start/end dates, actual solved). Render: `At current pace (X.X solves/wk): finish ~<date>` + on-track/behind pill + what-if slider `<input type="range" min="1" max="15">` initialized from `localStorage["whatif-hours"]`; on input, recompute a second line `At N/wk: finish ~<date>` and persist. Draw the projection as a dashed line extension on `#burnup-chart`'s SVG from the last actual point to the projected finish (import `svgEl`; append to the existing svg element after legacy renders — run AFTER `renderQuarterRoadmap` by registry order: `RENDERERS.byWorkspace.plan.push(renderPacePanel)`).
When `state.feed?.plan` is absent: panel hidden (matches legacy's no-plan empty state).

- [ ] **Step 2: Focus mode**

`js/features/focus.js`:

```js
import { state, EDGE_CASE_GROUPS } from "../legacy/app.js";

let overlay = null;
let timerId = 0;

function typicalMinutes(difficulty) {
  const times = (state.datasets.progress.completed || [])
    .filter((r) => state.problemsById.get(r.problem_id)?.difficulty === difficulty && r.time_taken_minutes > 0)
    .map((r) => r.time_taken_minutes)
    .sort((a, b) => a - b);
  return times.length ? times[Math.floor(times.length / 2)] : null;
}

export function toggleFocusMode() {
  if (overlay) return closeFocus();
  const action = state.feed?.next_action;
  const problemId = action?.problem_id || null; // verify field name in /api/feed
  const problem = problemId ? state.problemsById.get(problemId) : null;
  overlay = document.createElement("div");
  overlay.className = "focus-overlay";
  overlay.innerHTML = problem
    ? `<p class="microlabel">${action.mode || "SOLVE"}</p>
       <h1>${problemId} — ${problem.title || ""}</h1>
       <p class="focus-timer num" id="focus-timer">00:00</p>
       <p class="microlabel" id="focus-typical"></p>
       <details><summary>Edge-case checklist</summary><div id="focus-edges"></div></details>
       <p class="microlabel">Esc to exit — record via the mentor CLI</p>`
    : `<h1>No next action</h1><p class="microlabel">Queue is empty. Esc to exit.</p>`;
  document.body.append(overlay);
  document.body.classList.add("focus-active");
  if (problem) {
    const typical = typicalMinutes(problem.difficulty);
    if (typical) overlay.querySelector("#focus-typical").textContent = `typical for ${problem.difficulty}: ${typical}m`;
    const edges = overlay.querySelector("#focus-edges");
    for (const group of EDGE_CASE_GROUPS) {
      edges.insertAdjacentHTML("beforeend", `<h4>${group.title}</h4><ul>${group.items.map((i) => `<li>${i}</li>`).join("")}</ul>`);
    }
    const start = Date.now();
    timerId = setInterval(() => {
      const s = Math.floor((Date.now() - start) / 1000);
      overlay.querySelector("#focus-timer").textContent =
        `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    }, 1000);
  }
  document.addEventListener("keydown", escClose);
}

function escClose(e) {
  if (e.key === "Escape") closeFocus();
}

function closeFocus() {
  clearInterval(timerId);
  overlay?.remove();
  overlay = null;
  document.body.classList.remove("focus-active");
  document.removeEventListener("keydown", escClose);
}
```

Check `EDGE_CASE_GROUPS`'s real shape (app.js:95-130) and adapt the loop (`group.title`/`group.items` may be named differently). Check `feed.next_action` field names via `curl -s localhost:8765/api/feed | python3 -c "import json,sys; f=json.load(sys.stdin); print(json.dumps(f.get('next_action'), indent=1))"`. Fallback when feed is null: top item of the due queue derivation is NOT available statically — show the no-next-action state with detail "live feed required".

`focus.css`: `.focus-overlay` — `position: fixed; inset: 0;` opaque `background: light-dark(#fbfcfe, #0b1017);` centered column, huge timer (`clamp(3rem, 10vw, 6rem)` mono), entrance fade via `@starting-style` at `var(--dur-overlay)`; `body.focus-active .app-shell { visibility: hidden; }`.

- [ ] **Step 3: Wire** — main.js: `import { toggleFocusMode } from "./features/focus.js";` pass as `onFocusMode` to `initKeyboard` and as the palette `act:focus` run. Import `./features/pace.js` for side effect.

- [ ] **Step 4: Verify** — Plan: projection line extends burnup, finish date sane vs solved-count math; slider changes the what-if line and survives reload. `f` opens focus mode showing the same problem as Today's next action; timer ticks; typical-minutes matches median of that difficulty; Esc exits and restores the dashboard; `f` with server down shows the live-feed-required state.

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/js/features/pace.js web_dashboard/js/features/focus.js web_dashboard/css/components/focus.css web_dashboard/index.html web_dashboard/js/main.js web_dashboard/js/legacy/app.js
git commit -m "feat/dashboard: pace projection with what-if slider + zero-chrome focus mode"
```

---

### Task 15: Full verification walk + polish fixes

**Files:**
- Modify: whatever the walk flags.

- [ ] **Step 1: Test harness green** — `tests.html` → title `PASS (…)`.
- [ ] **Step 2: Playwright walk** — for each of the 6 workspaces × {dark, light} × {motion, reduced-motion}: screenshot, console-error check (must be zero), spot-check tooltips + one drill-down per workspace.
- [ ] **Step 3: Keyboard-only pass** — with the mouse untouched: `g` chords to every workspace; `j/k/Enter` due queue + browser table; Ctrl+K to a problem modal and back; `?` help; `t` theme; `f` focus in/out. Everything reachable.
- [ ] **Step 4: Perf check** — DevTools console: on a fresh load of Today, confirm `#constellation` and `#problem-table` are empty until their workspaces open (registry works).
- [ ] **Step 5: Fix whatever surfaced, re-verify, commit**

```bash
git add -A web_dashboard
git commit -m "fix/dashboard: phase-1 verification walk fixes"
```

---

## Self-review notes (already applied)

- Spec coverage: palette ✓ (T11), keyboard ✓ (T10), drill-down+tooltips ✓ (T8-9), motion ✓ (T7), motivation ✓ (T12), memory ✓ (T13), pace ✓ (T14), focus ✓ (T14), lazy render ✓ (T4), data banner ✓ (T5), svg dedup ✓ (T6), module conversion ✓ (T1). Phase-2/3 items (sidebar, Evidence tabs, URL routing, CSS rebuild) intentionally absent.
- Known verify-at-runtime points are called out explicitly where field names could not be confirmed from static reading (`feed.plan.weeks`, `feed.next_action.*`, `skill.problems`, `EDGE_CASE_GROUPS` shape) — each has a listed inspection command; they are verification steps, not open design questions.
- Type consistency: `openProblemList({title, subtitle, items:[{problemId, note}]})` used identically in T9/T12/T13; `RENDERERS.byWorkspace.<ws>.push(fn)` used in T12/T13/T14 matches T4's export; `svgEl(tag, attrs, children)` matches T6.
