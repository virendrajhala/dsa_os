# Feature 05 — Promotion Ladder (Curriculum workspace)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Requires Feature 02 complete (feed exposes `promotion`).

**Goal:** Surface the previously invisible promotion ladder: per stage — mastery progress (the real gate), quality-bar pass rate, and the cumulative volume guideline from `scoring.promotion_thresholds`.

**Architecture:** Pure view over `feed.promotion`. One section in the Curriculum workspace, one renderer, table-first (matches the a11y rule: tables are the accessible data view).

**Honesty rule (verified mechanism — copy into the UI copy):** stage advancement happens when all the stage's skills are mastered (`determine_stage`, `_shared.py:866`). `minimum_weighted_score` is the per-problem quality bar counted by `passed/attempted`; `minimum_completed_problems` is a cumulative volume guideline. The card must never present the count as a promotion gate.

**Feed contract consumed:**

```json
"promotion": {
  "current_stage": "Observation", "total_completed": 13,
  "stages": [{"stage": "Observation", "status": "in_progress",
              "skills_mastered": 4, "skills_total": 7,
              "attempted": 13, "passed": 13,
              "minimum_weighted_score": 2.4, "minimum_completed_problems": 23}]
}
```

---

### Task 1: Section + renderer

**Files:**
- Modify: `web_dashboard/index.html` — nav link + section
- Modify: `web_dashboard/app.js` — `renderPromotionLadder`, registered in `renderAll()` after `renderStages();`
- Modify: `web_dashboard/styles.css`

- [ ] **Step 1: Nav link.** In the Curriculum nav group, after the `#stages` link (index.html:29):

```html
          <a href="#promotion-ladder" data-workspace-link="curriculum"><span class="nav-icon num" aria-hidden="true">PL</span><span class="nav-text">Promotion Ladder</span></a>
```

- [ ] **Step 2: Section.** In `index.html`, after the closing `</section>` of `#stages` (index.html:211):

```html
        <section id="promotion-ladder" class="section" data-workspace-section="curriculum">
          <div class="section-head">
            <div>
              <p class="eyebrow microlabel">Exit criteria</p>
              <h3>Promotion ladder</h3>
            </div>
            <span class="pill num" id="ladder-pill">-</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Status</th>
                  <th>Skills</th>
                  <th>Quality bar</th>
                  <th>Volume guideline</th>
                </tr>
              </thead>
              <tbody id="ladder-table"></tbody>
            </table>
          </div>
          <p class="chart-note microlabel">A stage unlocks the next by mastering all its skills. The quality bar counts solves at or above the stage's minimum weighted score; the volume column is the cumulative-solve guideline, not a gate.</p>
        </section>
```

- [ ] **Step 3: Renderer** (add near `renderStages`, register in `renderAll()` right after `renderStages();`):

```js
  const LADDER_STATUS = {
    mastered: { label: "✓ mastered", tone: "good" },
    in_progress: { label: "● in progress", tone: "warn" },
    locked: { label: "○ locked", tone: "" },
  };

  function renderPromotionLadder() {
    const body = $("#ladder-table");
    if (!body) return;
    body.replaceChildren();
    const pillNode = $("#ladder-pill");
    if (pillNode) pillNode.textContent = "-";
    if (!feedAvailable()) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.append(degradedBanner());
      row.append(cell);
      body.append(row);
      return;
    }
    const promotion = state.feed.promotion || {};
    const stages = promotion.stages || [];
    if (pillNode) {
      pillNode.textContent = `${promotion.current_stage || "-"} · ${promotion.total_completed ?? 0} solves total`;
    }
    stages.forEach((stage) => {
      const spec = LADDER_STATUS[stage.status] || LADDER_STATUS.locked;
      const row = document.createElement("tr");
      if (stage.stage === promotion.current_stage) row.className = "ladder-current";

      const name = document.createElement("td");
      name.textContent = stage.stage;
      const status = document.createElement("td");
      status.append(pill(spec.label, spec.tone));
      const skills = document.createElement("td");
      skills.className = "num";
      skills.textContent = `${stage.skills_mastered} / ${stage.skills_total}`;
      const quality = document.createElement("td");
      quality.className = "num";
      quality.textContent = stage.attempted
        ? `${stage.passed} / ${stage.attempted} ≥ ${stage.minimum_weighted_score ?? "-"}`
        : `— (bar ${stage.minimum_weighted_score ?? "-"})`;
      const volume = document.createElement("td");
      volume.className = "num";
      if (stage.minimum_completed_problems != null) {
        const total = promotion.total_completed ?? 0;
        const met = total >= stage.minimum_completed_problems;
        volume.textContent = `${total} / ${stage.minimum_completed_problems}${met ? " ✓" : ""}`;
      } else {
        volume.textContent = "—";
      }
      row.append(name, status, skills, quality, volume);
      body.append(row);
    });
  }
```

- [ ] **Step 4: Styles:**

```css
.ladder-current { background: color-mix(in srgb, var(--accent) 8%, transparent); }
.ladder-current td:first-child { font-weight: 600; }
```

(If `color-mix` renders oddly in the target browser, fall back to `background: var(--surface-2);`.)

- [ ] **Step 5: Verify (falsifying checks)**
1. `node --check web_dashboard/app.js` clean.
2. With server: 13 rows; Observation row shows `4 / 7` skills and quality `13 / 13 ≥ 2.4` (matches `curl -s http://127.0.0.1:8765/api/feed | python3 -c "import json,sys; print(json.load(sys.stdin)['promotion']['stages'][0])"`); every stage after the first non-mastered one shows "○ locked".
3. Volume column reads `13 / 23` for Observation with no ✓ (13 < 23).
4. Without server: single degraded-banner row, no exceptions.

- [ ] **Step 6: Commit**

```bash
git add web_dashboard/index.html web_dashboard/app.js web_dashboard/styles.css
git commit -m "feat/dashboard: promotion ladder surfaces stage exit criteria"
```
