# Feature 04 — Plan Workspace (Week Scoreboard · Month Milestones · Quarter Roadmap)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Requires Feature 02 complete.

**Goal:** A new **Plan** workspace in the nav rail with three sections: this week's scoreboard, month-end skill milestones, and the quarter roadmap (burn-up chart + steering tiles + review-overload note).

**Architecture:** Pure view over `feed.plan`. One new `WORKSPACE_META` entry, one nav group, three `<section data-workspace-section="plan">` blocks, three renderers registered in `renderAll()`. The burn-up SVG follows the house chart style (`renderForecast`, app.js:720: viewBox, `make()` helper, `<title>` tooltips, `aria-label`, status color never alone).

**Tech Stack:** Vanilla JS, SVG, existing CSS tokens (`--series-1`, `--series-2`, `--good/--warn/--bad`, `.pace-tile`, `.panel`).

## Global constraints

- No client-side plan math beyond display transforms (scaling to pixels, date → x). All targets/actuals/projections arrive on the feed.
- Every plan section handles four states: degraded (no feed), no plan (`feed.plan == null`), plan error (`feed.plan.error`), outside quarter (`plan.week == null` / `today_contract.in_quarter == false`).
- Quality gates: `node --check`, zero console errors with and without server, manual checks per task.

**Feed contract consumed** (normative shapes in `00_OVERVIEW.md`): `plan.week`, `plan.weeks[]`, `plan.burnup` (planned points carry `date`, `start`, `cumulative`, `deload`), `plan.months[]`, `plan.quarter.daily_review_capacity`, plus existing `feed.review_forecast` for the overload note.

---

### Task 1: Workspace shell (nav + meta + sections)

**Files:**
- Modify: `web_dashboard/index.html`
- Modify: `web_dashboard/app.js` (`WORKSPACE_META`, app.js:128)

- [ ] **Step 1: Nav group.** In `index.html`, inside `<nav class="nav-list">`, insert AFTER the two Today links (after the `#revisions` link, index.html:23) and BEFORE `<span class="nav-group microlabel">Practice</span>`:

```html
          <span class="nav-group microlabel">Plan</span>
          <a href="#week-scoreboard" data-workspace-link="plan"><span class="nav-icon num" aria-hidden="true">WS</span><span class="nav-text">Week Scoreboard</span></a>
          <a href="#month-milestones" data-workspace-link="plan"><span class="nav-icon num" aria-hidden="true">MM</span><span class="nav-text">Month Milestones</span></a>
          <a href="#quarter-roadmap" data-workspace-link="plan"><span class="nav-icon num" aria-hidden="true">QR</span><span class="nav-text">Quarter Roadmap</span></a>
```

- [ ] **Step 2: Sections.** In `index.html`, insert after the closing `</section>` of `#overview` (index.html:159) — i.e. between the Today section and `#weakness-lab`:

```html
        <section id="week-scoreboard" class="section" data-workspace-section="plan">
          <div class="section-head">
            <div>
              <p class="eyebrow microlabel">This week</p>
              <h3>Week scoreboard</h3>
            </div>
            <span class="pill num" id="week-pill">-</span>
          </div>
          <div id="week-tiles" class="pace-tiles"></div>
          <div id="week-bars" class="weekbars" role="img"></div>
        </section>

        <section id="month-milestones" class="section" data-workspace-section="plan">
          <div class="section-head">
            <div>
              <p class="eyebrow microlabel">Skill targets</p>
              <h3>Month milestones</h3>
            </div>
          </div>
          <div id="milestone-board" class="milestone-board"></div>
          <p class="chart-note microlabel">Derived from curriculum order + weekly solve targets; statuses re-plan automatically as actuals move. Mastery = primary + one reinforcement at the quality bar.</p>
        </section>

        <section id="quarter-roadmap" class="section" data-workspace-section="plan">
          <div class="section-head">
            <div>
              <p class="eyebrow microlabel">2-3 month vision</p>
              <h3>Quarter roadmap</h3>
            </div>
            <span class="pill num" id="quarter-pill">-</span>
          </div>
          <div id="roadmap-tiles" class="pace-tiles"></div>
          <div id="burnup-chart" class="insight-chart" role="img"></div>
          <div id="burnup-legend" class="chart-legend"></div>
          <p id="overload-note" class="chart-note microlabel"></p>
        </section>
```

- [ ] **Step 3: Workspace meta.** In `app.js` `WORKSPACE_META` (app.js:128), add after the `today` entry:

```js
    plan: {
      eyebrow: "Plan",
      title: "Quarter plan",
      subtitle: "Weekly targets, month-end skill milestones, and the burn-up to the quarter goal.",
      toolbar: false,
    },
```

- [ ] **Step 4: Check** — `node --check web_dashboard/app.js`; reload: a Plan nav group appears; clicking it shows the three (still empty) sections. Commit together with Task 2 or as `feat/dashboard: plan workspace shell`.

---

### Task 2: Week scoreboard renderer

**Files:**
- Modify: `web_dashboard/app.js` (add `planBlock`, `planStateMessage`, `renderWeekScoreboard`; register in `renderAll()` after `renderTodayContract();`)
- Modify: `web_dashboard/styles.css`

**Interfaces:**
- Produces: `planBlock() -> object|null` and `planStateMessage(plan) -> string|null` — shared by Tasks 2-4 and reused by Features 05/06 patterns; `renderWeekScoreboard()`.

- [ ] **Step 1: Shared plan-state helpers** (add once, near `feedNextAction`, app.js:390):

```js
  function planBlock() {
    return feedAvailable() ? state.feed.plan : null;
  }

  // One string per non-renderable plan state; null when the plan is usable.
  function planStateMessage(plan) {
    if (!plan) return "No quarter plan. Author progress/plan.json to activate this view.";
    if (plan.error) return `Plan config error — ${plan.error}`;
    return null;
  }
```

- [ ] **Step 2: Renderer:**

```js
  function renderWeekScoreboard() {
    const tiles = $("#week-tiles");
    const bars = $("#week-bars");
    const pillNode = $("#week-pill");
    if (!tiles || !bars) return;
    tiles.replaceChildren();
    bars.replaceChildren();
    if (pillNode) pillNode.textContent = "-";
    if (!feedAvailable()) {
      tiles.append(degradedBanner());
      return;
    }
    const plan = planBlock();
    const message = planStateMessage(plan);
    if (message) {
      tiles.append(empty(message));
      return;
    }
    const week = plan.week;
    if (!week) {
      tiles.append(empty(`Outside the plan quarter (${plan.quarter.start} → ${plan.quarter.end}).`));
      return;
    }
    if (pillNode) {
      pillNode.textContent = `W${week.week}${week.deload ? " · DELOAD" : ""} · ${week.days_remaining}d left`;
    }
    const tileData = [
      {
        label: "Solves",
        value: `${week.actual_solves} / ${week.target_solves}`,
        note: `expected by today ${week.expected_to_date}`,
        tone: week.on_track ? "good" : "warn",
        flag: week.on_track ? "✓ on track" : "⚠ behind",
      },
      {
        label: "Revisions",
        value: String(week.revisions_done),
        note: `${week.revisions_passed} passed`,
      },
      {
        label: "Mock",
        value: week.mock_planned ? (week.mock_done ? "✓ done" : "○ pending") : "–",
        note: week.mock_planned ? "one per weekend" : "not planned",
        tone: week.mock_done ? "good" : "",
      },
      {
        label: "Skills mastered",
        value: String(week.skills_mastered.length),
        note: week.skills_mastered.join(", ") || "none yet this week",
      },
    ];
    tileData.forEach((tile) => {
      const node = document.createElement("div");
      node.className = "pace-tile";
      const label = document.createElement("span");
      label.className = "microlabel";
      label.textContent = tile.label;
      const value = document.createElement("strong");
      value.className = `num ${tile.tone || ""}`.trim();
      value.textContent = tile.value;
      const note = document.createElement("small");
      note.className = "microlabel";
      note.textContent = tile.flag ? `${tile.flag} · ${tile.note}` : tile.note;
      node.append(label, value, note);
      tiles.append(node);
    });

    // Mini bars: one column per started week, target (outline) vs actual (fill).
    const rows = plan.weeks || [];
    if (!rows.length) return;
    const svgNS = "http://www.w3.org/2000/svg";
    const W = 660;
    const H = 120;
    const PAD = 12;
    const bandW = (W - PAD * 2) / Math.max(rows.length, 1);
    const barW = Math.min(bandW - 8, 34);
    const maxTarget = Math.max(1, ...rows.map((row) => Math.max(row.target_solves, row.actual_solves)));
    const plotH = H - 34;
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "weekbars-svg");
    const make = (name, attrs, textContent) => {
      const el = document.createElementNS(svgNS, name);
      Object.entries(attrs).forEach(([key, val]) => el.setAttribute(key, String(val)));
      if (textContent != null) el.textContent = textContent;
      return el;
    };
    rows.forEach((row, index) => {
      const x = PAD + index * bandW + (bandW - barW) / 2;
      const targetH = (plotH * row.target_solves) / maxTarget;
      const actualH = (plotH * row.actual_solves) / maxTarget;
      const baseline = H - 22;
      if (row.target_solves > 0) {
        svg.append(make("rect", {
          x, y: baseline - targetH, width: barW, height: Math.max(targetH, 1),
          rx: 3, class: "weekbar-target",
        }));
      }
      const actual = make("rect", {
        x: x + 3, y: baseline - actualH, width: Math.max(barW - 6, 4),
        height: Math.max(actualH, row.actual_solves ? 3 : 0), rx: 3,
        class: row.actual_solves >= row.target_solves ? "weekbar-actual good" : "weekbar-actual",
      });
      actual.append(make("title", {},
        `W${row.week} (${row.start}): ${row.actual_solves} of ${row.target_solves} solves` +
        `${row.deload ? " · deload" : ""}${row.mock_done ? " · mock done" : ""}`));
      svg.append(actual);
      svg.append(make("text", {
        x: x + barW / 2, y: H - 8, "text-anchor": "middle", class: "forecast-axis",
      }, row.deload ? `W${row.week}·D` : `W${row.week}`));
    });
    bars.append(svg);
    bars.setAttribute("aria-label",
      `Weekly solves, target versus actual, for ${rows.length} started week${rows.length === 1 ? "" : "s"}.`);
  }
```

- [ ] **Step 3: Register** in `renderAll()` after `renderTodayContract();`: add `renderWeekScoreboard();`

- [ ] **Step 4: Styles** (append to `styles.css`):

```css
/* Plan workspace */
.weekbars { margin-top: 12px; }
.weekbars-svg { width: 100%; height: auto; }
.weekbar-target { fill: none; stroke: var(--muted); stroke-width: 1.5; }
.weekbar-actual { fill: var(--series-1); }
.weekbar-actual.good { fill: var(--good); }
.pace-tile .good { color: var(--good); }
.pace-tile .warn { color: var(--warn); }
```

- [ ] **Step 5: Verify** — `node --check`; with server: tiles match `plan.week` numbers from `curl -s http://127.0.0.1:8765/api/feed | python3 -m json.tool` (spot-check `actual_solves`); without server: degraded banner. Commit:

```bash
git add web_dashboard/index.html web_dashboard/app.js web_dashboard/styles.css
git commit -m "feat/dashboard: plan workspace + week scoreboard"
```

---

### Task 3: Month milestones renderer

**Files:**
- Modify: `web_dashboard/app.js` (add `renderMonthMilestones`; register after `renderWeekScoreboard();`)
- Modify: `web_dashboard/styles.css`

Status glyphs (never color alone): done `✓` · on_track `→` · at_risk `⚠` · missed `✗`.

- [ ] **Step 1: Renderer:**

```js
  const MILESTONE_STATUS = {
    done: { glyph: "✓", label: "done", tone: "good" },
    on_track: { glyph: "→", label: "on track", tone: "" },
    at_risk: { glyph: "⚠", label: "at risk", tone: "warn" },
    missed: { glyph: "✗", label: "missed", tone: "bad" },
  };

  function renderMonthMilestones() {
    const host = $("#milestone-board");
    if (!host) return;
    host.replaceChildren();
    if (!feedAvailable()) {
      host.append(degradedBanner());
      return;
    }
    const plan = planBlock();
    const message = planStateMessage(plan);
    if (message) {
      host.append(empty(message));
      return;
    }
    const months = plan.months || [];
    if (!months.length) {
      host.append(empty("No month milestones inside this quarter."));
      return;
    }
    months.forEach((month) => {
      const card = document.createElement("article");
      card.className = "milestone-card";
      const head = document.createElement("div");
      head.className = "milestone-head";
      const title = document.createElement("h4");
      title.textContent = `By ${month.milestone_date}`;
      const meta = document.createElement("span");
      meta.className = "pill num";
      meta.textContent = `${month.actual_solves} / ${month.expected_solves} solves`;
      head.append(title, meta);
      card.append(head);
      if (month.stage_note) {
        const note = document.createElement("p");
        note.className = "microlabel";
        note.textContent = month.stage_note;
        card.append(note);
      }
      const list = document.createElement("div");
      list.className = "milestone-skills";
      month.skills.forEach((skill) => {
        const status = MILESTONE_STATUS[skill.status] || MILESTONE_STATUS.on_track;
        const chip = document.createElement("span");
        chip.className = `skill-chip ${status.tone}`.trim();
        chip.textContent = `${status.glyph} ${skill.name || skill.skill_id}`;
        chip.title = `${skill.skill_id} · ${skill.stage} · ${status.label}`;
        list.append(chip);
      });
      card.append(list);
      const summary = document.createElement("small");
      summary.className = "microlabel";
      const counts = month.skills.reduce((acc, skill) => {
        acc[skill.status] = (acc[skill.status] || 0) + 1;
        return acc;
      }, {});
      summary.textContent = Object.entries(MILESTONE_STATUS)
        .filter(([key]) => counts[key])
        .map(([key, spec]) => `${counts[key]} ${spec.label}`)
        .join(" · ");
      card.append(summary);
      host.append(card);
    });
  }
```

- [ ] **Step 2: Register** in `renderAll()`; **styles:**

```css
.milestone-board { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
.milestone-card { background: var(--surface-2); border: 1px solid var(--line); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.milestone-head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.milestone-skills { display: flex; flex-wrap: wrap; gap: 6px; }
.skill-chip { font-size: 12px; padding: 3px 8px; border-radius: 999px; border: 1px solid var(--line); }
.skill-chip.good { color: var(--good); border-color: var(--good); }
.skill-chip.warn { color: var(--warn); border-color: var(--warn); }
.skill-chip.bad { color: var(--bad); border-color: var(--bad); }
```

- [ ] **Step 3: Verify** — chips show glyph + name; hover tooltip carries skill id/stage/status; behind-plan state (current live data) shows `⚠` chips. Commit `feat/dashboard: month milestone board`.

---

### Task 4: Quarter roadmap (burn-up + steering tiles + overload note)

**Files:**
- Modify: `web_dashboard/app.js` (add `renderQuarterRoadmap`; register after `renderMonthMilestones();`)
- Modify: `web_dashboard/styles.css`

**Display transforms only:** x = days since quarter start (feed dates → px), y = cumulative counts scaled to `target_total`. The projection segment is a straight dashed line from (today, `actual_total`) to (quarter end, `projected_total`) — both endpoints computed in Python.

- [ ] **Step 1: Renderer:**

```js
  function renderQuarterRoadmap() {
    const tiles = $("#roadmap-tiles");
    const chart = $("#burnup-chart");
    const legendHost = $("#burnup-legend");
    const overload = $("#overload-note");
    const pillNode = $("#quarter-pill");
    if (!tiles || !chart) return;
    tiles.replaceChildren();
    chart.replaceChildren();
    if (legendHost) legendHost.replaceChildren();
    if (overload) overload.textContent = "";
    if (pillNode) pillNode.textContent = "-";
    if (!feedAvailable()) {
      chart.append(degradedBanner());
      return;
    }
    const plan = planBlock();
    const message = planStateMessage(plan);
    if (message) {
      chart.append(empty(message));
      return;
    }
    const burnup = plan.burnup;
    if (pillNode) pillNode.textContent = `${plan.quarter.start} → ${plan.quarter.end}`;

    const gap = burnup.target_total - burnup.projected_total;
    const tileData = [
      { label: "Quarter target", value: String(burnup.target_total), note: `${burnup.target_mocks} mocks` },
      { label: "Done", value: String(burnup.actual_total), note: `${burnup.mocks_done} mocks so far` },
      {
        label: "Projected landing",
        value: String(burnup.projected_total),
        note: gap > 0 ? `⚠ ${Math.round(gap)} short at current pace` : "✓ on pace",
        tone: gap > 0 ? "warn" : "good",
      },
      {
        label: "Required / week",
        value: burnup.required_per_week == null ? "–" : String(burnup.required_per_week),
        note: burnup.required_per_week == null ? "quarter ended" : `${burnup.weeks_remaining} weeks left`,
      },
    ];
    tileData.forEach((tile) => {
      const node = document.createElement("div");
      node.className = "pace-tile";
      const label = document.createElement("span");
      label.className = "microlabel";
      label.textContent = tile.label;
      const value = document.createElement("strong");
      value.className = `num ${tile.tone || ""}`.trim();
      value.textContent = tile.value;
      const note = document.createElement("small");
      note.className = "microlabel";
      note.textContent = tile.note;
      node.append(label, value, note);
      tiles.append(node);
    });

    // Burn-up SVG.
    const svgNS = "http://www.w3.org/2000/svg";
    const W = 660;
    const H = 220;
    const PAD_L = 34;
    const PAD_R = 12;
    const PAD_T = 14;
    const PAD_B = 26;
    const start = parseDate(burnup.start);
    const end = parseDate(burnup.end);
    const totalDays = Math.max(1, Math.round((end - start) / 86400000));
    const yMax = Math.max(burnup.target_total, burnup.projected_total, 1);
    const xFor = (isoDay) =>
      PAD_L + clamp(Math.round((parseDate(isoDay) - start) / 86400000) / totalDays, 0, 1) * (W - PAD_L - PAD_R);
    const yFor = (count) => H - PAD_B - clamp(count / yMax, 0, 1) * (H - PAD_T - PAD_B);
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "burnup-svg");
    const make = (name, attrs, textContent) => {
      const el = document.createElementNS(svgNS, name);
      Object.entries(attrs).forEach(([key, val]) => el.setAttribute(key, String(val)));
      if (textContent != null) el.textContent = textContent;
      return el;
    };

    // deload bands first (recessive background)
    (burnup.planned || []).filter((week) => week.deload).forEach((week) => {
      svg.append(make("rect", {
        x: xFor(week.start), y: PAD_T,
        width: Math.max(xFor(week.date) - xFor(week.start), 2),
        height: H - PAD_T - PAD_B, class: "burnup-deload",
      }));
    });
    // gridline at target + axis ticks
    svg.append(make("line", {
      x1: PAD_L, y1: yFor(burnup.target_total), x2: W - PAD_R, y2: yFor(burnup.target_total),
      class: "burnup-target-line",
    }));
    svg.append(make("text", { x: 2, y: yFor(burnup.target_total) + 4, class: "forecast-axis" },
      String(burnup.target_total)));
    svg.append(make("text", { x: 2, y: yFor(0) + 4, class: "forecast-axis" }, "0"));
    svg.append(make("line", {
      x1: PAD_L, y1: H - PAD_B, x2: W - PAD_R, y2: H - PAD_B, class: "forecast-baseline",
    }));

    const toPoints = (entries) =>
      entries.map((entry) => `${xFor(entry.date).toFixed(1)},${yFor(entry.cumulative).toFixed(1)}`).join(" ");
    // planned staircase from origin
    svg.append(make("polyline", {
      points: `${xFor(burnup.start).toFixed(1)},${yFor(0).toFixed(1)} ${toPoints(burnup.planned || [])}`,
      class: "burnup-planned", fill: "none",
    }));
    // actual line from origin
    const actualEntries = burnup.actual || [];
    svg.append(make("polyline", {
      points: `${xFor(burnup.start).toFixed(1)},${yFor(0).toFixed(1)} ${toPoints(actualEntries)}`,
      class: "burnup-actual", fill: "none",
    }));
    // today marker + projection
    const todayIso = state.feed.reference_date;
    const clampedToday = parseDate(todayIso) > end ? burnup.end : todayIso;
    svg.append(make("line", {
      x1: xFor(clampedToday), y1: PAD_T, x2: xFor(clampedToday), y2: H - PAD_B, class: "burnup-today",
    }));
    if (burnup.required_per_week != null) {
      svg.append(make("line", {
        x1: xFor(clampedToday), y1: yFor(burnup.actual_total),
        x2: xFor(burnup.end), y2: yFor(burnup.projected_total),
        class: "burnup-projection",
      }));
    }
    // month milestone ticks
    (plan.months || []).forEach((month) => {
      svg.append(make("line", {
        x1: xFor(month.milestone_date), y1: H - PAD_B, x2: xFor(month.milestone_date), y2: H - PAD_B + 6,
        class: "burnup-tick",
      }));
      svg.append(make("text", {
        x: xFor(month.milestone_date), y: H - 8, "text-anchor": "middle", class: "forecast-axis",
      }, month.month.slice(5)));
    });
    chart.append(svg);
    chart.setAttribute("aria-label",
      `Quarter burn-up: ${burnup.actual_total} of ${burnup.target_total} solves done; ` +
      `projected ${burnup.projected_total} by ${burnup.end}` +
      (burnup.required_per_week != null ? `; ${burnup.required_per_week} per week required.` : "."));

    if (legendHost) {
      legendHost.append(chartLegend([
        { label: "planned", shape: "line", color: "var(--muted)" },
        { label: `actual · ${burnup.actual_total}`, shape: "line", color: "var(--series-1)" },
        { label: `projection · ${burnup.projected_total}`, shape: "line", color: "var(--series-2)" },
      ]));
    }

    // Review-overload note: forecast days whose recall load exceeds capacity.
    if (overload) {
      const capacity = plan.quarter.daily_review_capacity || 0;
      const heavy = capacity
        ? (state.feed.review_forecast || []).filter((day) => (day.count || 0) > capacity)
        : [];
      overload.textContent = heavy.length
        ? `⚠ Review overload ahead (more than ${capacity}/day): ${heavy
            .map((day) => `${day.date} (${day.count})`)
            .join(", ")}. Front-load recalls or lean on the deload week.`
        : capacity
          ? `Review load fits within ${capacity}/day for the next 14 days.`
          : "";
    }
  }
```

Note: `chartLegend` already exists (used by `renderConsistency`, app.js:4241). If its signature differs from `[{label, shape, color}]`, match the existing call site exactly — do not modify `chartLegend` itself.

- [ ] **Step 2: Register** in `renderAll()`; **styles:**

```css
.burnup-svg { width: 100%; height: auto; }
.burnup-planned { stroke: var(--muted); stroke-width: 2; stroke-dasharray: 5 4; }
.burnup-actual { stroke: var(--series-1); stroke-width: 2.5; }
.burnup-projection { stroke: var(--series-2); stroke-width: 2; stroke-dasharray: 3 4; }
.burnup-today { stroke: var(--accent); stroke-width: 1; opacity: 0.6; }
.burnup-target-line { stroke: var(--line); stroke-width: 1; }
.burnup-deload { fill: var(--muted); opacity: 0.08; }
.burnup-tick { stroke: var(--muted); stroke-width: 1; }
```

- [ ] **Step 3: Verify (falsifying checks)**
1. `curl -s http://127.0.0.1:8765/api/feed | python3 -c "import json,sys; b=json.load(sys.stdin)['plan']['burnup']; print(b['actual_total'], b['projected_total'], b['required_per_week'])"` — the three tiles show exactly these numbers.
2. The actual line must sit visibly below the planned staircase (current live data is behind plan) and the projection endpoint must land at `projected_total`, not at the target.
3. Deload bands appear at W4/W8/W12 positions; month ticks at 08, 09, 10.
4. Without the server: degraded banner, no console errors.
5. Both themes readable (toggle Theme).

- [ ] **Step 4: Commit**

```bash
git add web_dashboard/app.js web_dashboard/styles.css
git commit -m "feat/dashboard: quarter roadmap burn-up with projection and overload note"
```
