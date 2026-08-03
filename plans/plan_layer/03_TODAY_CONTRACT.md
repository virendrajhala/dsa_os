# Feature 03 — Today's Contract Card (Today workspace)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Requires Feature 02 complete (feed exposes `plan.today_contract`).

**Goal:** A three-line daily checklist in the Today briefing — solve / clear revisions / weekend mock — driven by `feed.plan.today_contract`.

**Architecture:** Pure view over the feed. New panel in `#overview` (index.html), one renderer in `app.js`, a few CSS rules. Renders the degraded banner without the server, an explanatory empty state when `feed.plan` is null or `{"error": ...}`, and an "outside quarter" state after 2026-10-25.

**Tech Stack:** Vanilla JS, CSS custom properties already defined in `styles.css`.

## Global constraints

- No client-side recomputation — every number comes from `feed.plan.today_contract`.
- Status never by color alone: ✓/○/– glyphs carry the state, color reinforces.
- There is no JS test suite in this repo; the quality gates are `node --check web_dashboard/app.js`, zero console errors with and without the server, and the manual checks in the final task.

**Feed contract consumed** (from `00_OVERVIEW.md`):

```json
"today_contract": {
  "in_quarter": true, "deload": false,
  "solve": {"planned": true, "done": false},
  "revisions": {"due": 4, "done_today": 1, "cleared": false},
  "mock": {"planned": false, "done": false}
}
```

---

### Task 1: Markup

**Files:**
- Modify: `web_dashboard/index.html` — inside `#overview`, insert directly AFTER the closing `</section>` of the Next Action panel (the `briefing-next` panel, index.html:97-106) and BEFORE the trajectory panel:

- [ ] **Step 1: Insert the panel**

```html
          <!-- 1b. Today's contract (plan layer: plans/plan_layer/03) -->
          <section class="panel" aria-labelledby="contract-heading">
            <div class="panel-head">
              <div>
                <p class="eyebrow microlabel">Plan vs actual</p>
                <h3 id="contract-heading">Today's contract</h3>
              </div>
              <span class="pill num" id="contract-count">-</span>
            </div>
            <div id="today-contract" class="contract-list"></div>
          </section>
```

- [ ] **Step 2: Check** — reload the page; an empty panel with heading "Today's contract" appears in Today. Commit with Task 2.

### Task 2: Renderer

**Files:**
- Modify: `web_dashboard/app.js` — add `renderTodayContract` next to the other Today renderers (immediately after `renderPaceTiles`, app.js:831-872); register it in `renderAll()` (app.js:4321) right after `renderPaceTiles();`.
- Modify: `web_dashboard/styles.css` — append the contract styles.

**Interfaces:**
- Consumes: `state.feed.plan` (Feature 02), existing helpers `$`, `feedAvailable`, `degradedBanner`, `empty`.
- Produces: `renderTodayContract()` — no return; also fills the `#contract-count` pill.

- [ ] **Step 1: Add the renderer**

```js
  // Today's contract: the plan layer's daily checklist. Pure view over
  // feed.plan.today_contract — planned/done flags are computed in Python.
  function renderTodayContract() {
    const host = $("#today-contract");
    if (!host) return;
    host.replaceChildren();
    const pillNode = $("#contract-count");
    if (pillNode) pillNode.textContent = "-";
    if (!feedAvailable()) {
      host.append(degradedBanner());
      return;
    }
    const plan = state.feed.plan;
    if (!plan || plan.error) {
      host.append(
        empty(
          plan && plan.error
            ? `Plan config error — ${plan.error}`
            : "No quarter plan. Author progress/plan.json to activate the daily contract.",
        ),
      );
      return;
    }
    const contract = plan.today_contract || {};
    if (!contract.in_quarter) {
      host.append(
        empty(
          `Outside the plan quarter (${plan.quarter.start} → ${plan.quarter.end}). ` +
            "Author the next quarter in progress/plan.json.",
        ),
      );
      return;
    }
    if (contract.deload) {
      const note = document.createElement("p");
      note.className = "contract-deload microlabel";
      note.textContent = "DELOAD WEEK — no new solves; revisions + the weekend mock only.";
      host.append(note);
    }
    const revisions = contract.revisions || {};
    const rows = [
      {
        label: "Solve one problem",
        planned: Boolean(contract.solve?.planned),
        done: Boolean(contract.solve?.done),
        note: contract.solve?.planned
          ? "morning slot · scheduler picks the problem"
          : contract.deload
            ? "deload — no new material"
            : "not planned today (revision-sweep day)",
      },
      {
        label: "Clear due revisions",
        planned: true,
        done: Boolean(revisions.cleared),
        note: `${revisions.due ?? 0} due · ${revisions.done_today ?? 0} recall${
          (revisions.done_today ?? 0) === 1 ? "" : "s"
        } done today`,
      },
      {
        label: "Weekend mock",
        planned: Boolean(contract.mock?.planned),
        done: Boolean(contract.mock?.done),
        note: contract.mock?.planned ? "45-min cap · no hints · record the verdict" : "weekend only",
      },
    ];
    rows.forEach((row) => {
      const item = document.createElement("div");
      item.className = "contract-row";
      const mark = document.createElement("span");
      mark.className = "contract-mark num";
      if (!row.planned) {
        mark.textContent = "–";
        mark.classList.add("skip");
      } else if (row.done) {
        mark.textContent = "✓";
        mark.classList.add("good");
      } else {
        mark.textContent = "○";
        mark.classList.add("pending");
      }
      const label = document.createElement("span");
      label.className = "contract-label";
      label.textContent = row.label;
      const note = document.createElement("small");
      note.className = "microlabel";
      note.textContent = row.note;
      item.append(mark, label, note);
      host.append(item);
    });
    const planned = rows.filter((row) => row.planned);
    const done = planned.filter((row) => row.done).length;
    if (pillNode) pillNode.textContent = `${done} of ${planned.length} done`;
  }
```

- [ ] **Step 2: Register it.** In `renderAll()` add `renderTodayContract();` on the line after `renderPaceTiles();`.

- [ ] **Step 3: Styles.** Append to `web_dashboard/styles.css`:

```css
/* Today's contract (plan layer) */
.contract-list { display: flex; flex-direction: column; }
.contract-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
}
.contract-row:last-child { border-bottom: 0; }
.contract-mark { width: 1.4em; text-align: center; }
.contract-mark.good { color: var(--good); }
.contract-mark.pending { color: var(--warn); }
.contract-mark.skip { color: var(--muted); }
.contract-label { flex: 1; }
.contract-deload { color: var(--warn); margin: 0 0 4px; }
```

- [ ] **Step 4: Syntax gate**

Run: `node --check web_dashboard/app.js`
Expected: no output (clean).

- [ ] **Step 5: Manual verification (falsifying paths, not just happy path)**

1. `python3 scripts/serve_dashboard.py` → open dashboard → contract shows three rows; the revision row's due count equals the Due queue count above it; pill shows "N of M done"; zero console errors.
2. On a weekday the mock row shows "–"/"weekend only". If today is Sat/Sun it shows "○".
3. Stop the server, reload (static open) → the card shows the degraded banner, no exceptions.
4. Temporarily rename `progress/plan.json` → reload with server → card shows the "No quarter plan" empty state (not an error); rename back.
5. Temporarily corrupt `plan.json` (set a week's `target_solves` to 9) → reload → card shows "Plan config error — plan.json: ..." and the REST of the dashboard still renders; restore the file.

- [ ] **Step 6: Commit**

```bash
git add web_dashboard/index.html web_dashboard/app.js web_dashboard/styles.css
git commit -m "feat/dashboard: today's contract card (plan layer)"
```
