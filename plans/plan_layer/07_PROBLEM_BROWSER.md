# Feature 07 — Problem Browser (LeetCode-style list, skill-wise navigation)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Independent of Features 01-06 except Task 1 touches the same feed function — if Feature 02 is already merged, append after its keys.

**Goal:** A "Problems" workspace: left panel = stages → skills tree; clicking a skill (or stage, or "All problems") shows its problem list in the center — id, title, difficulty, role, importance, status, lock state — like browsing LeetCode, but organized by the curriculum.

**Architecture:** Static-data view (works without the server): problems from `curriculum.json`, grouping from `knowledge/skills.json` (`primary_validation_problem`, `reinforcement_problems[]`, `challenge_problems[]` — the real "sub-skill-wise" structure of this curriculum), status derived from `progress.completed[*].revision` (pure display transform). The one scheduler-derived fact — is a problem unlocked — comes from a new feed key `unlocked_problems` computed by `is_problem_unlocked` (`_shared.py:1064`) with the real `challenge_stage_gate`; without the feed the lock column simply shows "–" (never a client-side guess: the repo rule forbids re-implementing scheduler logic in JS).

**Tech Stack:** Python stdlib (one feed key + tests), vanilla JS, existing CSS tokens.

## Global constraints

- Same as `00_OVERVIEW.md`: no scheduler logic in JS; status glyph + text, never color alone; `node --check` + zero console errors with AND without the server; tests in `scripts/test_plan_feed.py` (or `test_dashboard_feed.py` if 01/02 not yet executed); concise commits, no Co-Authored-By.
- Rendering 582 rows at once is fine (the history table already renders full lists); no virtualization.

## Status derivation (display transform — the ONLY logic the JS may own)

From the latest completion record per problem (`state.completedById`):

| Condition | Status text | Glyph |
|---|---|---|
| no record | `Not started` | `·` |
| `revision.status == "MASTERED"` | `Mastered` | `★` |
| `revision.status == "FAILED"` | `Recall failed — retry due <next_due>` | `✗` |
| `revision.status == "ACTIVE"` | `Solved · R<stage+1> due <next_due>` | `✓` |
| record but no revision dict | `Solved` | `✓` |

---

### Task 1: Feed key `unlocked_problems`

**Files:**
- Modify: `scripts/_shared.py` (inside `build_dashboard_feed`, with the other feed keys)
- Modify: `scripts/test_plan_feed.py` (append class; if Features 01-02 are not executed yet, put the class in `scripts/test_dashboard_feed.py` instead — the `_state`/`_completed` fixtures there are equivalent)

**Interfaces:**
- Consumes: `is_problem_unlocked(problem, completed_ids, problem_deps, challenge_gate)` (`_shared.py:1064`), `challenge_stage_gate(state.curriculum)` (constructed exactly as `select_next_problem` does at `_shared.py:1224`), `problem_dependencies_map(state.graph)`, `completed_problem_ids(state.progress)`.
- Produces: `feed["unlocked_problems"]: list[str]` — sorted ids of not-yet-completed problems whose prerequisites are met (completed problems are trivially "done", not listed).

- [ ] **Step 1: Failing test:**

```python
class UnlockedProblemsTests(unittest.TestCase):
    def test_unlocked_excludes_completed_and_locked(self):
        progress = _progress([_completed("OBS-001", "2026-07-09")])
        feed = build_dashboard_feed(_state(progress), date(2026, 7, 28))
        unlocked = feed["unlocked_problems"]
        self.assertIsInstance(unlocked, list)
        self.assertNotIn("OBS-001", unlocked)          # completed, not "unlocked"
        self.assertTrue(unlocked, "something must be workable")
        # A deep State-Transition DP problem cannot be unlocked after one solve.
        self.assertNotIn("DP-050", unlocked)

    def test_unlocked_matches_scheduler_helper(self):
        from _shared import (
            challenge_stage_gate, completed_problem_ids, is_problem_unlocked,
            problem_dependencies_map, problem_lookup,
        )
        progress = _progress([_completed("OBS-001", "2026-07-09")])
        state = _state(progress)
        feed = build_dashboard_feed(state, date(2026, 7, 28))
        completed = completed_problem_ids(progress)
        deps = problem_dependencies_map(state.graph)
        gate = challenge_stage_gate(state.curriculum)
        for problem_id, problem in problem_lookup(state.curriculum).items():
            expected = problem_id not in completed and is_problem_unlocked(
                problem, completed, deps, gate)
            self.assertEqual(problem_id in set(feed["unlocked_problems"]), expected,
                             f"{problem_id} disagrees with is_problem_unlocked")
```

- [ ] **Step 2: Verify failure** (`KeyError: 'unlocked_problems'`), then **Step 3: Implement.** In `build_dashboard_feed`, alongside the other key assignments (after the `policy` key or after the Feature-02 block):

```python
    # Problem browser (plans/plan_layer/07): the one scheduler-derived fact the
    # browser needs. Completed problems are excluded — they are "done", and the
    # UI derives their status from the completion record.
    completed_ids = completed_problem_ids(state.progress)
    problem_deps = problem_dependencies_map(state.graph)
    challenge_gate = challenge_stage_gate(state.curriculum)
    feed["unlocked_problems"] = sorted(
        problem_id
        for problem_id, problem in problems.items()
        if problem_id not in completed_ids
        and is_problem_unlocked(problem, completed_ids, problem_deps, challenge_gate)
    )
```

(`problems = problem_lookup(state.curriculum)` already exists at the top of `build_dashboard_feed`, `_shared.py:2262`.)

- [ ] **Step 4:** `make test` green. **Step 5: Commit** — `git commit -am "feat/feed: expose unlocked problems for the browser"`

---

### Task 2: Workspace shell (nav + sections)

**Files:**
- Modify: `web_dashboard/index.html`
- Modify: `web_dashboard/app.js` (`WORKSPACE_META`, app.js:128)

- [ ] **Step 1: Nav.** In `<nav class="nav-list">`, after the Plan group (Feature 04) — or after the Today links if Feature 04 is not merged yet:

```html
          <span class="nav-group microlabel">Problems</span>
          <a href="#problem-browser" data-workspace-link="problems"><span class="nav-icon num" aria-hidden="true">PB</span><span class="nav-text">Browse Problems</span></a>
```

- [ ] **Step 2: Section.** After the `#quarter-roadmap` section (or after `#overview` if Feature 04 absent):

```html
        <section id="problem-browser" class="section" data-workspace-section="problems">
          <div class="section-head">
            <div>
              <p class="eyebrow microlabel">Curriculum catalog</p>
              <h3>Problem browser</h3>
            </div>
            <span class="pill num" id="browser-count">-</span>
          </div>
          <div class="browser-toolbar">
            <input id="browser-search" type="search" placeholder="Search id or title" aria-label="Search problems" />
            <select id="browser-difficulty" aria-label="Filter by difficulty">
              <option value="">All difficulties</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
            <select id="browser-status" aria-label="Filter by status">
              <option value="">All statuses</option>
              <option value="not_started">Not started</option>
              <option value="solved">Solved (in revision)</option>
              <option value="failed">Recall failed</option>
              <option value="mastered">Mastered</option>
            </select>
          </div>
          <div class="browser-layout">
            <aside id="browser-tree" class="browser-tree" aria-label="Stages and skills"></aside>
            <div class="table-wrap browser-table">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Title</th>
                    <th>Difficulty</th>
                    <th>Role</th>
                    <th>Importance</th>
                    <th>Status</th>
                    <th>Lock</th>
                  </tr>
                </thead>
                <tbody id="browser-rows"></tbody>
              </table>
            </div>
          </div>
        </section>
```

- [ ] **Step 3: Workspace meta** (after the `plan` entry, or after `today` if 04 absent):

```js
    problems: {
      eyebrow: "Problems",
      title: "Problem browser",
      subtitle: "Every curriculum problem, organized by stage and skill, with live status.",
      toolbar: false,
    },
```

- [ ] **Step 4:** `node --check`; the empty section renders under a Problems nav group. Commit with Task 3.

---

### Task 3: Tree + list renderers

**Files:**
- Modify: `web_dashboard/app.js`
- Modify: `web_dashboard/styles.css`

**Interfaces:**
- Consumes: `state.datasets` (curriculum/skills/stages), `state.completedById`, `state.problemsById`, `state.feed?.unlocked_problems`, `openProblemModal(problemId)` (existing, see call sites app.js:531,715), helpers `$`, `pill`, `empty`, `text`.
- Produces: `renderProblemBrowser()` registered in `renderAll()` (after `renderPatterns();`); module-level `browserState = { selection: {kind: "all"}, search: "", difficulty: "", status: "" }`.

- [ ] **Step 1: Add state + helpers** (near the other state, app.js:12-26 area is `const state` — add a separate `const browserState = { selection: { kind: "all" }, search: "", difficulty: "", status: "" };` below it):

```js
  // Problem-browser status: pure display transform of the completion record.
  // Scheduling truth (what to do NOW) stays with feed.next_action.
  function problemStatus(problemId) {
    const record = state.completedById.get(problemId);
    if (!record) return { key: "not_started", glyph: "·", label: "Not started" };
    const revision = record.revision || null;
    if (!revision) return { key: "solved", glyph: "✓", label: "Solved" };
    if (revision.status === "MASTERED") {
      return { key: "mastered", glyph: "★", label: "Mastered" };
    }
    if (revision.status === "FAILED") {
      return {
        key: "failed", glyph: "✗",
        label: `Recall failed — retry due ${text(revision.next_due)}`,
      };
    }
    return {
      key: "solved", glyph: "✓",
      label: `Solved · R${(revision.stage ?? 0) + 1} due ${text(revision.next_due)}`,
    };
  }

  function browserProblemsForSelection() {
    const all = state.datasets.curriculum.problems || [];
    const sel = browserState.selection;
    if (sel.kind === "stage") return all.filter((problem) => problem.stage === sel.stage);
    if (sel.kind === "skill") {
      const skill = state.skillsById.get(sel.skillId) || {};
      const ordered = [
        skill.primary_validation_problem,
        ...(skill.reinforcement_problems || []),
        ...(skill.challenge_problems || []),
      ].filter(Boolean);
      return ordered.map((id) => state.problemsById.get(id)).filter(Boolean);
    }
    return all;
  }
```

- [ ] **Step 2: Tree renderer** — stages in `stages.stage_order`, each expandable to its skills (from `stages.stages[name].skills`, skipping ids missing from `skills.json` and the meta-skill SK-IE-00), with solved/total counts per skill computed from `state.completedById`:

```js
  function renderBrowserTree() {
    const host = $("#browser-tree");
    if (!host) return;
    host.replaceChildren();
    const stageOrder = state.datasets.stages.stage_order || [];
    const stageDefs = state.datasets.stages.stages || {};
    const problems = state.datasets.curriculum.problems || [];
    const solvedIn = (list) => list.filter((id) => state.completedById.has(id)).length;

    const allButton = document.createElement("button");
    allButton.type = "button";
    allButton.className = `tree-item tree-all ${browserState.selection.kind === "all" ? "active" : ""}`.trim();
    allButton.textContent = `All problems (${problems.length})`;
    allButton.addEventListener("click", () => {
      browserState.selection = { kind: "all" };
      renderProblemBrowser();
    });
    host.append(allButton);

    stageOrder.forEach((stageName) => {
      const details = document.createElement("details");
      details.className = "tree-stage";
      details.open =
        (browserState.selection.kind === "stage" && browserState.selection.stage === stageName) ||
        (browserState.selection.kind === "skill" &&
          (state.skillsById.get(browserState.selection.skillId) || {}).stage === stageName);
      const summary = document.createElement("summary");
      const stageButton = document.createElement("button");
      stageButton.type = "button";
      stageButton.className = `tree-item ${
        browserState.selection.kind === "stage" && browserState.selection.stage === stageName ? "active" : ""
      }`.trim();
      const stageProblemIds = problems.filter((p) => p.stage === stageName).map((p) => p.id);
      stageButton.textContent = `${stageName} · ${solvedIn(stageProblemIds)}/${stageProblemIds.length}`;
      stageButton.addEventListener("click", (event) => {
        event.preventDefault();
        browserState.selection = { kind: "stage", stage: stageName };
        renderProblemBrowser();
      });
      summary.append(stageButton);
      details.append(summary);

      (stageDefs[stageName]?.skills || []).forEach((skillId) => {
        const skill = state.skillsById.get(skillId);
        if (!skill || skill.scope === "meta") return;
        const ids = [
          skill.primary_validation_problem,
          ...(skill.reinforcement_problems || []),
          ...(skill.challenge_problems || []),
        ].filter(Boolean);
        const skillButton = document.createElement("button");
        skillButton.type = "button";
        skillButton.className = `tree-item tree-skill ${
          browserState.selection.kind === "skill" && browserState.selection.skillId === skillId ? "active" : ""
        }`.trim();
        skillButton.textContent = `${skill.name} · ${solvedIn(ids)}/${ids.length}`;
        skillButton.title = skillId;
        skillButton.addEventListener("click", () => {
          browserState.selection = { kind: "skill", skillId };
          renderProblemBrowser();
        });
        details.append(skillButton);
      });
      host.append(details);
    });
  }
```

- [ ] **Step 3: List renderer + wiring:**

```js
  function renderProblemBrowser() {
    renderBrowserTree();
    const body = $("#browser-rows");
    if (!body) return;
    body.replaceChildren();
    const unlocked = feedAvailable() ? new Set(state.feed.unlocked_problems || []) : null;
    const query = browserState.search.trim().toLowerCase();

    let rows = browserProblemsForSelection();
    if (browserState.difficulty) {
      rows = rows.filter((problem) => problem.difficulty === browserState.difficulty);
    }
    if (browserState.status) {
      rows = rows.filter((problem) => problemStatus(problem.id).key === browserState.status);
    }
    if (query) {
      rows = rows.filter((problem) =>
        problem.id.toLowerCase().includes(query) ||
        (problem.title || "").toLowerCase().includes(query));
    }

    const counter = $("#browser-count");
    if (counter) {
      const solved = rows.filter((problem) => state.completedById.has(problem.id)).length;
      counter.textContent = `${solved} / ${rows.length} solved`;
    }
    if (!rows.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 7;
      cell.append(empty("No problems match this view."));
      row.append(cell);
      body.append(row);
      return;
    }

    rows.forEach((problem) => {
      const status = problemStatus(problem.id);
      const row = document.createElement("tr");
      row.className = `browser-row status-${status.key}`;
      row.tabIndex = 0;
      const open = () => openProblemModal(problem.id);
      row.addEventListener("click", open);
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter") open();
      });

      const id = document.createElement("td");
      id.className = "num";
      id.textContent = problem.id;
      const title = document.createElement("td");
      title.textContent = problem.title || "-";
      const difficulty = document.createElement("td");
      difficulty.append(pill(problem.difficulty || "-",
        problem.difficulty === "Easy" ? "good" : problem.difficulty === "Hard" ? "bad" : ""));
      const role = document.createElement("td");
      role.textContent = (problem.problem_role || "-").toLowerCase();
      const importance = document.createElement("td");
      importance.textContent = (problem.importance || "-").toLowerCase();
      const statusCell = document.createElement("td");
      statusCell.textContent = `${status.glyph} ${status.label}`;
      const lock = document.createElement("td");
      lock.className = "num";
      if (state.completedById.has(problem.id)) lock.textContent = "";
      else if (!unlocked) lock.textContent = "–";           // no feed: unknown, never guessed
      else lock.textContent = unlocked.has(problem.id) ? "open" : "🔒";
      row.append(id, title, difficulty, role, importance, statusCell, lock);
      body.append(row);
    });
  }
```

Wire the three filter controls in `main()` (next to the other listeners, app.js:4370):

```js
      const browserSearch = $("#browser-search");
      if (browserSearch) browserSearch.addEventListener("input", debounce(() => {
        browserState.search = browserSearch.value;
        renderProblemBrowser();
      }, 150));
      const browserDifficulty = $("#browser-difficulty");
      if (browserDifficulty) browserDifficulty.addEventListener("change", () => {
        browserState.difficulty = browserDifficulty.value;
        renderProblemBrowser();
      });
      const browserStatus = $("#browser-status");
      if (browserStatus) browserStatus.addEventListener("change", () => {
        browserState.status = browserStatus.value;
        renderProblemBrowser();
      });
```

Register `renderProblemBrowser();` in `renderAll()` after `renderPatterns();`.

- [ ] **Step 4: Styles:**

```css
/* Problem browser */
.browser-toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.browser-layout { display: grid; grid-template-columns: 260px 1fr; gap: 14px; align-items: start; }
.browser-tree { display: flex; flex-direction: column; gap: 2px; max-height: 70vh; overflow-y: auto; position: sticky; top: 12px; }
.tree-item { display: block; width: 100%; text-align: left; background: none; border: 0; color: var(--text); padding: 6px 8px; border-radius: 6px; cursor: pointer; font: inherit; }
.tree-item:hover { background: var(--surface-2); }
.tree-item.active { background: var(--surface-2); color: var(--accent); font-weight: 600; }
.tree-skill { padding-left: 22px; font-size: 13px; }
.tree-stage summary { list-style: none; cursor: pointer; }
.tree-stage summary::-webkit-details-marker { display: none; }
.browser-row { cursor: pointer; }
.browser-row:focus { outline: 2px solid var(--accent); outline-offset: -2px; }
.browser-row.status-mastered td:first-child { color: var(--good); }
@media (max-width: 900px) { .browser-layout { grid-template-columns: 1fr; } .browser-tree { position: static; max-height: none; } }
```

- [ ] **Step 5: Verify (falsifying checks)**
1. `node --check` clean.
2. "All problems (582)"; Observation stage shows `13/25` solved (current data); a skill click shows primary first, then reinforcements, then challenges — verify OBS skill counts against `knowledge/skills.json`.
3. Status column: CPX-004 reads `✓ Solved · R1 due …` matching `progress.json`; a random DP problem reads `· Not started` with 🔒.
4. Filters compose (e.g. stage=click Observation + difficulty=Medium + status=solved).
5. Row click opens the existing problem modal; Enter key on a focused row does too.
6. Without the server: everything renders, lock column shows "–", zero console errors.
7. Both themes readable at 1024px; layout stacks below 900px.

- [ ] **Step 6: Commit**

```bash
git add web_dashboard/index.html web_dashboard/app.js web_dashboard/styles.css
git commit -m "feat/dashboard: problem browser with skill tree and live status"
```
