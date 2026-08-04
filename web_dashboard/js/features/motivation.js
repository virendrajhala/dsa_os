import { state, RENDERERS } from "../legacy/app.js";
import { activeDaySet, streaks } from "../derive/activity.js";
import { fastestByDifficulty, nearComplete } from "../derive/pace.js";
import { addDays, todayISO } from "../derive/dates.js";
import { animateCount } from "../engine/motion.js";
import { openProblemList } from "../engine/drilldown.js";

function referenceToday() {
  return state.feed?.reference_date || todayISO();
}

// Verified against /api/feed: weeks[] = {week, start, deload, target_solves,
// actual_solves, mock_done}. There is no week-end field; a week ends 6 days
// after its start.
function weekEnd(week) {
  return week.start ? addDays(week.start, 6) : "";
}

// Verified against knowledge/skills.json: a skill's problems live in
// primary_validation_problem + reinforcement_problems + challenge_problems.
function skillProblemIds(skill) {
  return [
    skill.primary_validation_problem,
    ...(skill.reinforcement_problems || []),
    ...(skill.challenge_problems || []),
  ].filter(Boolean);
}

function mockAverage(mock) {
  const values = Object.values(mock.scores || {}).filter((v) => typeof v === "number");
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
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
  // target per feed.plan.weeks. Hidden entirely when no plan is available.
  const badgeHost = document.querySelector("#badge-strip");
  const weeks = state.feed?.plan?.weeks || null;
  if (!weeks || !weeks.length) badgeHost.hidden = true;
  else {
    const byMonth = new Map();
    for (const week of weeks) {
      const month = (week.start || "").slice(0, 7);
      if (!month) continue;
      if (!byMonth.has(month)) byMonth.set(month, []);
      byMonth.get(month).push(week);
    }
    badgeHost.hidden = false;
    badgeHost.innerHTML = "";
    for (const [month, ws] of [...byMonth].sort()) {
      const done = ws.every((w) => (w.actual_solves ?? 0) >= (w.target_solves ?? 0));
      const past = ws.every((w) => weekEnd(w) < referenceToday());
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
  const mocks = state.feed?.mock_history || [];
  const mockAvgs = mocks.map(mockAverage).filter((v) => v !== null);
  const bestMock = mockAvgs.length ? Math.max(...mockAvgs) : null;
  const bestsHost = document.querySelector("#bests-card");
  bestsHost.innerHTML = `<h4 class="microlabel">Personal bests</h4>` +
    ["Easy", "Medium", "Hard"].map((d) => bests[d]
      ? `<div class="best-row"><span>${d}</span><strong class="num">${bests[d].minutes}m</strong><small>${bests[d].problemId}</small></div>`
      : "").join("") +
    (bestMock !== null ? `<div class="best-row"><span>Best mock</span><strong class="num">${bestMock.toFixed(1)}/4</strong></div>` : "") +
    `<div class="best-row"><span>Longest streak</span><strong class="num">${max}d</strong></div>`;
}

export function renderNudges() {
  const groups = [...state.skillsById.values()].map((skill) => {
    const ids = skillProblemIds(skill);
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
