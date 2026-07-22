# Dashboard Redesign — Design Spec ("Mission Deck")

> Companion plan: `plans/DASHBOARD_REDESIGN_PLAN.md` (task-by-task, agent-executable).
> Date: 2026-07-22. Status: awaiting owner approval.

## 1. Subject, audience, job

A solo learner's nightly DSA cockpit. One user, localhost, evening sessions.
The page's single job: **answer "what do I do right now, and am I on
trajectory for interviews?" in under 5 seconds** — then support drill-down.

## 2. Research grounding

Four principles drawn from learning-analytics and dashboard-design research,
each of which shaped a concrete decision below:

1. **Dashboards must serve self-regulated learning, not monitoring.** Recent
   LAD research (systematic review, Springer/JLA 2024-25) finds effective
   student-facing dashboards align every indicator with a pedagogical action
   rather than restating activity. → Every module below must name the action
   it drives; anything that can't is cut.
2. **The spaced-repetition canon** (Anki statistics practice): the metrics
   that matter are *retention rate* (healthy band ~85-90%), *young vs mature
   retention* split, and *forward review load*. A sliding retention rate is
   the early-warning signal; forward load prevents overwhelm. → New
   retention split + 14-day review-load forecast, both leading indicators.
3. **Leading over lagging; no vanity.** A metric earns pixels only if the
   answer to "does this change a decision today?" is yes. → Metric census
   in §4 with keep/cut/add verdicts.
4. **Glanceability + progressive disclosure.** First view answers "am I
   okay?" with 3-5 KPIs; everything granular is one click deeper (NN/g:
   progressive disclosure cuts cognitive load dramatically). → Today is a
   5-element briefing; tables/detail live behind modals and deeper tabs.

Sources: [LAD systematic review](https://dl.acm.org/doi/10.1007/s10639-023-12401-4),
[LAD design for self-regulation (JLA)](https://learning-analytics.info/index.php/JLA/article/view/8529),
[Anki Manual — Statistics](https://docs.ankiweb.net/stats.html),
[retention-rate guidance](https://mikeydoes.com/glossary/retention-rate/),
[vanity vs actionable metrics](https://www.secoda.co/blog/what-is-the-difference-between-vanity-and-actionable-metrics/),
[dashboard design principles (UXPin)](https://www.uxpin.com/studio/blog/dashboard-design-principles/),
[progressive disclosure (UXPin)](https://www.uxpin.com/studio/blog/what-is-progressive-disclosure/).

## 3. The architectural decision: Python is the brain

Today `app.js` re-implements scheduler/readiness/pace logic (~250 lines of
mirrors of `_shared.py`) and has already drifted once: `nextAction()` doesn't
know weekend mocks, skill continuity, or stage order, so the dashboard can
contradict `next_problem.py` on a Saturday.

**Decision: the dashboard becomes a pure view.** `serve_dashboard.py` gains a
`GET /api/feed` endpoint that computes everything derived — next action,
revision queue, forecast, readiness, pace, retention, hint trajectory, mock
history — by calling the same `_shared.py` functions the CLI uses. The JS
mirrors are deleted. If the feed is unreachable (e.g. file:// open), the
dashboard shows a "start the server" banner and degrades to the static views
(tables, history, curriculum) that read raw JSON directly.

Feed contract (all fields required; `null` where unknown):

```json
{
  "generated_at": "2026-07-22T21:04:00",
  "reference_date": "2026-07-22",
  "next_action": {
    "mode": "revision | mock_due | resume_current_problem | current_skill | current_stage | earliest_unlocked | complete  (verbatim SelectionResult.mode from _shared.select_next_problem — never renamed)",
    "problem_id": "OBS-005", "title": "...", "url": "https://...",
    "reason": "R2 recall is due.", "stage_label": "R2"
  },
  "revision_queue": [
    {"problem_id": "...", "title": "...", "stage": 1, "stage_label": "R2",
     "next_due": "2026-07-18", "status": "ACTIVE", "kind": "revision", "overdue": true}
  ],
  "review_forecast": [
    {"date": "2026-07-22", "count": 2, "overdue": true, "problem_ids": ["..."]}
  ],
  "readiness": {
    "gates": {
      "core_mastery": {"met": false, "current": 0.018, "target": 0.8, "mastered": 1, "total": 57},
      "revision_pass": {"met": true, "current": 1.0, "target": 0.9},
      "mocks": {"met": false, "current": 0, "required": 3, "verdicts": []}
    },
    "projected_date": "2027-09-15",
    "pace": {"problems_per_week": 2.5, "skills_per_week": 0.75, "window_days": 28}
  },
  "retention": {
    "overall_pass_rate": 1.0, "young_pass_rate": 1.0, "mature_pass_rate": null,
    "counts": {"young_pass": 6, "young_total": 6, "mature_pass": 0, "mature_total": 0}
  },
  "hint_trajectory": [{"date": "2026-07-10", "hint_level": 2, "problem_id": "OBS-003"}],
  "mock_history": [
    {"date": "2026-07-19", "problem_id": "CPX-003", "verdict": "hire",
     "duration_minutes": 44,
     "scores": {"problem_solving": 3, "communication": 3, "code_quality": 2,
                 "testing": 3, "time_management": 3}}
  ],
  "policy": {"mastered_after_stage": 4,
              "intervals": {"R1": 3, "R2": 7, "R3": 21, "R4": 60}}
}
```

Definitions: *young* = revision history events attempted at stages R1-R2,
*mature* = R3+ (Anki's ≥21-day analog; our R3 is the 21-day stage).
`review_forecast` covers `reference_date .. +13d`; overdue items are folded
into day 0 with `overdue: true`. `revision_queue[].kind` distinguishes
`revision | quarterly_maintenance | reactivated` (same taxonomy as
`_shared.py` due-entry kinds). When `next_action.mode` is one of the four
solve modes, the feed adds `"code_gate": {"solution_expected":
"solutions/<ID>.py", "solution_exists": false}` so the briefing reminds the
learner the F9 gate will fire.

### 3b. End-to-end alignment matrix (repo mechanism → dashboard surface)

The dashboard must tell the same story as the CLI for every mechanism in the
system. This matrix is the completeness contract; the final review task
checks each row.

| Repo mechanism (source of truth) | Feed/data | Dashboard surface |
|---|---|---|
| Scheduler priority: overdue revisions → weekend mock → current/new (`select_next_problem`) | `next_action` | Today: Next Action card, all four modes rendered distinctly |
| Revision protocol R1-R4, PASS gates, FAIL retry (`apply_revision_result`, `revision_policy`) | `revision_queue`, `policy` | Today: due queue with policy-driven stage pills; problem modal: per-event recall scores + misconception |
| Quarterly maintenance (90d, deterministic subset) | `revision_queue.kind = quarterly_maintenance` | Today: due queue shows "Q-maint" pill (distinct from R-stages) |
| Reactivation (`--reactivate-problem`, weak prerequisites) | `revision_queue.kind = reactivated` | Today: due queue "reactivated" pill; problem modal history shows the reactivation event + reason |
| Weekend mock protocol (`is_mock_due`, `select_mock_problem`, mock_interview_protocol.md) | `next_action.mode = mock_due`, `mock_history` | Today: mock briefing card (45-min cap · no hints · unseen problem); Evidence: mock trend (verdicts + 5 rubric dims) |
| Mentor-graded scoring pass (F7, `mentor_scores`) | raw `progress.json` | Problem modal: self vs mentor score columns with divergence >2 highlighted |
| Code-execution gate (F9, `solutions/<ID>.py`, `run_checks.py`) | `next_action.code_gate` | Today: Next Action shows "solution file: present/required"; problem modal links the solution path |
| Hint ladder + mastery discount (F6, `hint_levels`, `hint_mastery_discount`) | `hint_trajectory`, `policy` | Evidence: hint-independence chart with 0-2 / 3-4 / 5-7 bands matching the discount tiers |
| Readiness estimator (F23, gates + projection) | `readiness` | Today: trajectory strip (the hero) |
| Weakness loop (F20, structured entries, `source: mock/revision.fail`) | raw `progress.json` | Practice: weakness lab, source-tagged; resolved entries excluded |
| Deferred learning (open loops + evidence to close) | raw `progress.json` | Evidence: deferred list with resolve-evidence requirement in copy |
| Mistake catalog (F14, taxonomy A-E, provenance) | `mistake_catalog.json` | Mistakes modal: taxonomy chip + source problem link |
| Curriculum DAG + stage order (F18) | `dependency_graph.json` | Curriculum: constellation + "unlocks next" in problem modal |
| Interview scope (DSA-only, playbook per-topic) | static | No system-design/behavioral modules anywhere (out of scope) |

Rule: **the dashboard never recomputes what `_shared.py` can compute** — it
renders the feed. Client-side computation is allowed only for pure display
transforms (rolling means for the hint chart, date grouping for calendars).

## 4. Metric census (keep / cut / add)

| Metric / module | Verdict | Decision it drives |
|---|---|---|
| Next action (scheduler-true) | KEEP, fix parity | what to open right now |
| Revision due queue | KEEP | today's recall work |
| Readiness gates + projected date | KEEP, promote to hero strip | pace/strategy adjustment |
| Pace (problems/wk, skills/wk) | KEEP as stat tiles | volume adjustment |
| Thinking dimension bars | KEEP (Evidence) | which dimension to drill |
| Weakness lab | KEEP (Practice) | targeted drilling |
| Showing-up 30-day chart | KEEP (Evidence) | consistency check |
| Stage map / skills / patterns | KEEP (Curriculum), constellation added | unlock planning |
| Mistake catalog badge/modal | KEEP | recurring-error review |
| Deferred learning | KEEP (Evidence) | close open loops |
| **Review-load forecast (14d)** | **ADD** | schedule tomorrow's session size; spot pile-ups before they land |
| **Retention split (young/mature)** | **ADD** | sliding mature retention = intervals failing → revise strategy |
| **Hint-independence trajectory** | **ADD** | falling hint levels = interview-ready autonomy; rising = slow down |
| **Mock trend (verdicts + 5 dims)** | **ADD** | the goal metric; which rubric dimension to train next |
| **Skill constellation (DAG map)** | **ADD** (signature) | see prerequisite paths and what mastering X unlocks |
| Analytics workspace shell | CUT (dissolve into Evidence) | restated Today/Evidence content |
| Duplicate nav (sidebar anchors + tab row) | CUT (single nav) | — |
| Permanent search/filter toolbar | CUT (contextual: list views only) | — |
| `analyticsPerformanceCard` (dup of thinking profile) | CUT | — |

No streak counters or badges: gamification pressure without a decision
attached; the 30-day cadence chart already answers "am I showing up".

## 5. Information architecture

Four workspaces (was five), one navigation (slim left rail, workspace groups
with section links; the topbar tab row is deleted):

- **Today** — the mission briefing (§6).
- **Practice** — weakness lab, edge-case checklist.
- **Curriculum** — skill constellation, stage meters, skills table, patterns.
- **Evidence** — problem history, thinking profile, hint independence,
  mock trend, consistency chart, deferred learning.

Search + stage/status filters render only on views with lists (Curriculum,
Evidence). Modals (problem, skill, weakness, mistakes) keep their current
function, restyled, plus two additions in the problem modal: (a) self vs
mentor score columns with any divergence > 2 highlighted (F7 data,
currently unrendered), (b) a `solutions/<ID>.py` link when the completion
passed the code gate.

## 6. Today = mission briefing (glance layer)

Five elements, in order; nothing else:

1. **Next Action card** — from `feed.next_action`, one per mode:
   - `revision`: problem, stage label, due date, "Start recall" link.
   - `mock_due`: distinct treatment (accent border, "MOCK" eyebrow), the
     selected unseen problem, and the protocol reminder line: "45-minute cap
     · no hints · verdict at the end".
   - solve modes (`resume_current_problem` / `current_skill` /
     `current_stage` / `earliest_unlocked`): one shared "solve" treatment —
     problem + scheduler reason + code-gate reminder.
2. **Trajectory strip** — the readiness story on one horizontal line:
   three gate stations (core mastery %, revision pass %, last-3 mocks) each
   showing current/target and met-state, ending in the projected-ready date.
   Data: `feed.readiness`. This is the "am I okay?" element.
3. **Due queue** — today's + overdue revisions (compact list, stage pills).
4. **Review-load forecast** — 14-day bar chart from `feed.review_forecast`;
   overdue bucket rendered in `serious` status color with an icon + label
   (never color alone).
5. **Pace tiles** — problems/week, skills/week, sessions-last-30d; small
   mono numerals with a muted trend note.

## 7. Visual identity ("engineer's lab notebook meets flight deck")

Deliberately avoids the stock AI looks (cream+serif+terracotta, near-black +
single acid accent, broadsheet hairlines). Identity carriers: mono-numeral
typography, a faint graph-paper texture, and the constellation — not one neon
accent color.

**Surfaces & tokens** (CSS custom properties, dark-first with light theme;
`data-theme` attribute + `prefers-color-scheme` default, persisted in
localStorage):

```css
:root[data-theme="dark"], :root:not([data-theme="light"]) {
  --bg: #0e1620;        /* ink blue-black, not near-black */
  --surface: #16212e;   /* panels */
  --surface-2: #1d2a3a; /* nested cards */
  --line: #263548;
  --text: #e8eef5;
  --muted: #8fa1b3;
  --good: #34d399; --warn: #fbbf24; --bad: #f87171;  /* status: icon+label always */
  --accent: #3987e5;    /* interactive affordances only, never a series color-by-rank */
}
:root[data-theme="light"] {
  --bg: #f6f8f7; --surface: #ffffff; --surface-2: #f0f3f2;
  --line: #dde3ea; --text: #1f2937; --muted: #5b6b7b;
  --good: #137333; --warn: #b45309; --bad: #b42318; --accent: #2a78d6;
}
```

**Data series palette** — validated with the dataviz six-checks validator
against exactly these surfaces (dark `#0E1620`: all PASS; light `#F6F8F7`:
PASS with contrast WARN on slots 3/4/5 → **relief rule: those series always
carry direct labels in light mode**). Assign in fixed slot order, never
cycled; ≥4 simultaneous series on scatter-like forms → fold to "Other":

| Slot | Dark | Light |
|---|---|---|
| 1 blue | `#3987e5` | `#2a78d6` |
| 2 orange | `#d95926` | `#eb6834` |
| 3 aqua | `#199e70` | `#1baf7a` |
| 4 yellow | `#c98500` | `#eda100` |
| 5 magenta | `#d55181` | `#e87ba4` |
| 6 green | `#008300` | `#008300` |
| 7 violet | `#9085e9` | `#4a3aa7` |
| 8 red | `#e66767` | `#e34948` |

**Typography** — no CDN fonts (offline-first localhost):
- Body/UI: `system-ui, -apple-system, "Segoe UI", sans-serif`.
- Identity carrier: mono stack `ui-monospace, "JetBrains Mono", "Cascadia
  Code", "Fira Code", monospace` for ALL numerals (tabular-nums), stage
  pills, statuses, eyebrows, and axis labels.
- Micro-labels: uppercase, 11px, 0.08em tracking, muted.
- Headers: system sans, 600-700 weight, tight (-0.01em).

**Texture**: graph-paper grid (two `repeating-linear-gradient`s at ~4% alpha,
24px cell) behind the Today briefing band only.

**Motion**: one orchestrated moment — trajectory strip draws in on load
(300ms, 80ms stagger, transform+opacity). Constellation hover highlights the
prerequisite path. Everything else static. `prefers-reduced-motion: reduce`
disables both.

**Chart specs** (dataviz method): 2px lines, 4px rounded data-ends anchored
to baseline, ≥8px markers, 2px surface gaps between adjacent fills, legends
whenever ≥2 series, hover tooltip layer on every plot, recessive grid, one
axis per chart (never dual-axis), text in text tokens never series colors.
Tables (history, skills) remain as the accessible data view.

## 8. Signature element: the Skill Constellation

An SVG map of the real curriculum DAG (93 skills, 13 stage-banded columns,
edges from `dependency_graph.json.skill_dependencies`). Node encoding:
- fill: mastered → `--good`; in-progress (current skill) → `--accent` ring;
  unlocked (all prereqs mastered) → outlined; locked → 25% opacity.
- radius ∝ problem count (min 5px, max 11px).
- hover: raises the node, highlights ancestor edges (prerequisite path) and
  direct dependents; tooltip with name, stage, n problems, state.
- click: opens the existing skill modal.
Layout is computed, not hand-placed: x = stage column, y = order within
stage (`skill_order`), giving a stable left-to-right "climb". Horizontal
scroll container on narrow viewports. The existing skills table remains
directly below as the table view (a11y + relief rule).

## 9. Correctness folds (ride along)

- `today` recomputed per render + on `visibilitychange` (currently frozen at
  page load — stale after midnight).
- R-labels, R-buckets, and mastery stage in JS derived from
  `feed.policy` / fetched `scoring.json` `revision_policy` (currently
  hardcoded `stage >= 4`, fixed R1-R4 buckets at `app.js:108,1728`).
- Delete dead code from dissolved Analytics after migration.

## 10. Accessibility & quality floor

Keyboard focus visible on all interactive elements; modals trap focus (native
`<dialog>`); status never color-alone (icon + label); charts have table
equivalents; both themes pass the palette validator; layout usable at 1024px
and readable at 768px (rail collapses to icons); `node --check` clean; zero
console errors on load with the server running AND without it (degraded
mode).

## 11. Out of scope

Mobile-first layout, auth, remote hosting, build tooling/frameworks (repo
rule: vanilla JS + stdlib Python only), editing progress data from the UI
(the dashboard stays read-only; `update_progress.py` is the only writer).

## 12. Risks

- **Feed/CLI drift** — mitigated structurally: feed calls the same
  `_shared.py` functions; parity pinned by tests (plan Task 1).
- **app.js size** — redesign trims mirrors (~250 lines) but adds modules;
  acceptable; splitting files is out of scope (repo keeps single-file).
- **SVG DAG legibility at 93 nodes** — stage-banded columns + hover
  isolation; fallback is the table right below it.
