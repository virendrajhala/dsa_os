(function () {
  const DATA = {
    progress: "../progress/progress.json",
    scoring: "../progress/scoring.json",
    curriculum: "../curriculum/curriculum.json",
    stages: "../curriculum/stages.json",
    skills: "../knowledge/skills.json",
    patternIndex: "../knowledge/patterns.json",
    mistakes: "../mistake_catalog.json",
  };

  const state = {
    datasets: null,
    problemsById: new Map(),
    completedById: new Map(),
    skillsById: new Map(),
    patternsById: new Map(),
    filteredProblems: [],
    analyticsView: "acquisition",
    activeWorkspace: "today",
    // Lazy-loaded on first problem-modal open; never in the critical Promise.all.
    graphPromise: null,
    reverseEdges: null,
  };

  const $ = (selector) => document.querySelector(selector);
  const today = new Date();
  const EDGE_CASE_GROUPS = [
    {
      title: "Size boundaries",
      items: ["Empty input, if allowed", "Single element input", "Two element input"],
    },
    {
      title: "Position boundaries",
      items: [
        "First index is the answer or triggers the key condition",
        "Last index is the answer or triggers the key condition",
      ],
    },
    {
      title: "Value boundaries",
      items: [
        "All negative values, when numbers can be negative",
        "All positive values, when sign matters",
        "Zeros mixed with positive/negative values",
        "Duplicate values",
      ],
    },
    {
      title: "Ordering and existence",
      items: [
        "Already sorted and reverse sorted input",
        "Minimum and maximum constraint sizes",
        "No valid answer exists",
      ],
    },
  ];
  const COMPLEXITY_GUIDE = [
    ["n <= 20", "Exponential / backtracking may be acceptable"],
    ["n <= 100", "O(n^3) may pass; O(n^4) is risky"],
    ["n <= 1,000", "O(n^2) is usually acceptable"],
    ["n <= 100,000", "Aim for O(n log n) or O(n)"],
    ["n >= 1,000,000", "Usually O(n) or O(log n) per query"],
    ["Repeated queries", "Precompute, prefix sums, hashing, heap, tree, or binary search"],
  ];

  function parseDate(value) {
    if (!value) return null;
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function isoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function daysBetween(a, b) {
    const day = 24 * 60 * 60 * 1000;
    return Math.round((parseDate(a) - parseDate(b)) / day);
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function debounce(fn, waitMs) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), waitMs);
    };
  }

  function avg(values) {
    const valid = values.filter((value) => typeof value === "number");
    if (!valid.length) return 0;
    return valid.reduce((sum, value) => sum + value, 0) / valid.length;
  }

  function text(value, fallback = "-") {
    return value === undefined || value === null || value === "" ? fallback : String(value);
  }

  function stageLabel(stage) {
    if (stage >= 4) return "MASTERED";
    return `R${stage + 1} due`;
  }

  function pill(label, tone = "") {
    const span = document.createElement("span");
    span.className = `pill ${tone}`.trim();
    span.textContent = label;
    return span;
  }

  function setModal(title, subtitle, eyebrow = "Details") {
    $("#modal-title").textContent = title;
    $("#modal-subtitle").textContent = subtitle;
    const eyebrowNode = $("#skill-modal .modal-head .eyebrow");
    if (eyebrowNode) eyebrowNode.textContent = eyebrow;
    const body = $("#modal-body");
    body.replaceChildren();
    return body;
  }

  function showModal() {
    const modal = $("#skill-modal");
    if (typeof modal.showModal === "function") {
      modal.showModal();
    } else {
      modal.setAttribute("open", "");
    }
  }

  function switchWorkspace(workspace, targetHash = "") {
    state.activeWorkspace = workspace || "today";
    document.querySelectorAll("[data-workspace-section]").forEach((section) => {
      section.hidden = section.dataset.workspaceSection !== state.activeWorkspace;
    });
    document.querySelectorAll(".workspace-tab").forEach((tab) => {
      const active = tab.dataset.workspace === state.activeWorkspace;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    document.querySelectorAll("[data-workspace-link]").forEach((link) => {
      link.classList.toggle("active", link.dataset.workspaceLink === state.activeWorkspace);
    });
    if (targetHash) {
      const target = document.querySelector(targetHash);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  async function fetchText(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load ${path}`);
    return response.text();
  }

  async function fetchJson(path) {
    return JSON.parse(await fetchText(path));
  }

  async function loadData() {
    const [progress, scoring, curriculum, stages, skills, patternIndex, mistakes] = await Promise.all([
      fetchJson(DATA.progress),
      fetchJson(DATA.scoring),
      fetchJson(DATA.curriculum),
      fetchJson(DATA.stages),
      fetchJson(DATA.skills),
      fetchJson(DATA.patternIndex),
      fetchJson(DATA.mistakes),
    ]);

    state.datasets = {
      progress,
      scoring,
      curriculum,
      stages,
      skills,
      patternIndex,
      mistakes,
    };
    state.problemsById = new Map(curriculum.problems.map((problem) => [problem.id, problem]));
    state.skillsById = new Map(Object.entries(skills.skills || {}));
    state.patternsById = new Map(Object.entries(patternIndex.patterns || {}));
    state.completedById = new Map(
      progress.completed
        .filter((record) => record && record.problem_id)
        .map((record) => [record.problem_id, record]),
    );
    state.filteredProblems = curriculum.problems;
  }

  function skillMeta(skillId) {
    return state.skillsById.get(skillId) || { id: skillId, name: skillId, description: "" };
  }

  function skillTitle(skillId) {
    const skill = skillMeta(skillId);
    return skill.name ? `${skill.name}` : skillId;
  }

  function skillLabel(skillId) {
    const skill = skillMeta(skillId);
    return skill.name ? `${skill.name} (${skillId})` : skillId;
  }

  function patternEntries() {
    const index = state.datasets.patternIndex || {};
    const patterns = index.patterns || {};
    const order = Array.isArray(index.pattern_order) ? index.pattern_order : Object.keys(patterns);
    return order
      .map((patternId) => patterns[patternId])
      .filter((pattern) => pattern && pattern.id);
  }

  function patternsForProblem(problemId) {
    return patternEntries().filter((pattern) =>
      Array.isArray(pattern.appears_in) && pattern.appears_in.includes(problemId),
    );
  }

  function patternsForSkill(skillId) {
    return patternEntries().filter((pattern) =>
      Array.isArray(pattern.skills) && pattern.skills.includes(skillId),
    );
  }

  function patternMatchesQuery(pattern, query) {
    if (!query) return true;
    const problems = (pattern.appears_in || [])
      .map((problemId) => state.problemsById.get(problemId)?.title || problemId)
      .join(" ");
    const skills = (pattern.skills || [])
      .map((skillId) => `${skillId} ${skillTitle(skillId)}`)
      .join(" ");
    const haystack = [
      pattern.id,
      pattern.name,
      pattern.idea_family,
      pattern.mental_model,
      pattern.core_invariant,
      pattern.proof_idea,
      pattern.complexity_reasoning,
      problems,
      skills,
      ...(pattern.recognition_signals || []),
      ...(pattern.contrast_with || []),
      ...(pattern.common_mistakes || []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  }

  function buildStageOptions() {
    const select = $("#stage-filter");
    state.datasets.stages.stage_order.forEach((stage) => {
      const option = document.createElement("option");
      option.value = stage;
      option.textContent = stage;
      select.append(option);
    });
  }

  function referenceDate() {
    const lastUpdated = parseDate(state.datasets.progress.last_updated);
    if (lastUpdated && lastUpdated > today) return isoDate(lastUpdated);
    return isoDate(today);
  }

  function unresolvedCompletions() {
    return [...state.completedById.values()].filter(
      (record) => !state.problemsById.has(record.problem_id),
    );
  }

  function getRevisionEntries() {
    const ref = referenceDate();
    return [...state.completedById.values()]
      .filter((record) => state.problemsById.has(record.problem_id))
      .map((record) => {
        const problem = state.problemsById.get(record.problem_id) || {};
        const revision = record.revision || {};
        const nextDue = revision.next_due;
        return {
          problem,
          record,
          revision,
          status: revision.status || "ACTIVE",
          stage: revision.stage || 0,
          nextDue,
          daysUntil: nextDue ? daysBetween(nextDue, ref) : null,
          historyCount: Array.isArray(revision.history) ? revision.history.length : 0,
        };
      })
      .sort((a, b) => {
        const aDue = a.nextDue || "9999-12-31";
        const bDue = b.nextDue || "9999-12-31";
        return aDue.localeCompare(bDue) || a.problem.id.localeCompare(b.problem.id);
      });
  }

  function dueEntries() {
    return getRevisionEntries().filter(
      (entry) =>
        ["ACTIVE", "FAILED"].includes(entry.status) &&
        entry.nextDue &&
        entry.daysUntil <= 0,
    );
  }

  function deferredLearningEntries() {
    return Array.isArray(state.datasets.progress.deferred_learnings)
      ? state.datasets.progress.deferred_learnings
      : [];
  }

  function openDeferredLearnings() {
    return deferredLearningEntries().filter((entry) => entry.status === "OPEN");
  }

  function deferredLearningMatchesQuery(entry, query) {
    if (!query) return true;
    const origin = state.problemsById.get(entry.origin_problem) || {};
    const resolved = entry.resolved_by_problem
      ? state.problemsById.get(entry.resolved_by_problem) || {}
      : {};
    const haystack = [
      entry.id,
      entry.origin_problem,
      origin.title,
      entry.resolved_by_problem,
      resolved.title,
      entry.skill,
      skillMeta(entry.skill).name,
      entry.category,
      entry.description,
      entry.evidence,
      entry.priority,
      entry.status,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  }

  function nextAction() {
    const due = dueEntries();
    if (due.length) {
      const entry = due[0];
      return {
        mode: entry.status === "FAILED" ? "revision retry" : "revision due",
        problem: entry.problem,
        reason: `${stageLabel(entry.stage)} for ${entry.nextDue}`,
        revision: entry,
      };
    }
    const current = state.problemsById.get(state.datasets.progress.current_problem);
    if (current) {
      return {
        mode: "current problem",
        problem: current,
        reason: "Current active problem remains unlocked.",
      };
    }
    const unsolved = state.datasets.curriculum.problems.find(
      (problem) => !state.completedById.has(problem.id),
    );
    return {
      mode: unsolved ? "next unsolved" : "complete",
      problem: unsolved,
      reason: unsolved ? "Earliest remaining problem." : "No remaining work.",
    };
  }

  // ---------------------------------------------------------------------
  // F23: system-derived interview-readiness estimator (informational only;
  // gates nothing). Mirrors scripts/_shared.py's compute_readiness family so
  // the dashboard and `revision_report.py` agree without a server round trip.
  // ---------------------------------------------------------------------
  function readinessConfig() {
    return state.datasets.scoring.readiness || {};
  }

  function coreSkillIdsInScope() {
    const { curriculum, stages, skills } = state.datasets;
    const cfg = readinessConfig();
    const stageOrder = stages.stage_order || [];
    const scopeCount = Number.isInteger(cfg.stage_scope_count) ? cfg.stage_scope_count : stageOrder.length;
    const scopeStages = new Set(stageOrder.slice(0, scopeCount));
    const coreSkillsFromProblems = new Set(
      curriculum.problems
        .filter((problem) => problem.importance === "CORE" && typeof problem.primary_skill === "string")
        .map((problem) => problem.primary_skill),
    );
    const result = new Set();
    Object.entries(skills.skills || {}).forEach(([skillId, skill]) => {
      if (skill.scope === "global") return;
      if (scopeStages.has(skill.stage) && coreSkillsFromProblems.has(skillId)) {
        result.add(skillId);
      }
    });
    return result;
  }

  function computeCoreMasteryStatus() {
    const skillProgress = state.datasets.progress.skill_progress || {};
    const coreIds = coreSkillIdsInScope();
    let mastered = 0;
    coreIds.forEach((id) => {
      if (skillProgress[id]?.mastered) mastered += 1;
    });
    const total = coreIds.size;
    return { mastered, total, fraction: total ? mastered / total : 0 };
  }

  function computeRevisionPassRate() {
    const completed = state.datasets.progress.completed || [];
    const events = completed.flatMap((record) => record.revision?.history || []);
    // REACTIVATED events are excluded: a system-scheduled prerequisite
    // reinforcement, not a graded recall attempt outcome.
    const passCount = events.filter((event) => event.result === "PASS").length;
    const failCount = events.filter((event) => event.result === "FAIL").length;
    const total = passCount + failCount;
    return { pass: passCount, total, fraction: total ? passCount / total : 0 };
  }

  function computeRecentMockStatus() {
    const cfg = readinessConfig();
    const entries = Array.isArray(state.datasets.progress.mock_interviews)
      ? state.datasets.progress.mock_interviews
      : [];
    const required = Number.isInteger(cfg.recent_mock_count) ? cfg.recent_mock_count : 3;
    const allowed = new Set(cfg.min_mock_verdicts || []);
    const recent = entries.length ? entries.slice(-required) : [];
    const met = entries.length >= required && recent.every((entry) => allowed.has(entry.verdict));
    return {
      recorded: entries.length,
      required,
      recentVerdicts: recent.map((entry) => entry.verdict),
      met,
    };
  }

  function skillMasteryDates() {
    const { skills, progress } = state.datasets;
    const skillProgress = progress.skill_progress || {};
    const dates = {};
    Object.entries(skills.skills || {}).forEach(([skillId, skill]) => {
      if (!skillProgress[skillId]?.mastered) return;
      const primaryRecord = state.completedById.get(skill.primary_validation_problem);
      const primaryDate = primaryRecord ? parseDate(primaryRecord.completed_at) : null;
      const reinforcementDates = (skill.reinforcement_problems || [])
        .map((problemId) => state.completedById.get(problemId))
        .filter(Boolean)
        .map((record) => parseDate(record.completed_at))
        .filter(Boolean);
      if (!primaryDate || !reinforcementDates.length) {
        dates[skillId] = null;
        return;
      }
      const earliestReinforcement = reinforcementDates.reduce((min, d) => (d < min ? d : min));
      dates[skillId] = primaryDate > earliestReinforcement ? primaryDate : earliestReinforcement;
    });
    return dates;
  }

  function computePace(onDate) {
    const cfg = readinessConfig();
    const windowDays = Number.isInteger(cfg.pace_window_days) ? cfg.pace_window_days : 28;
    const windowStart = new Date(onDate);
    windowStart.setDate(windowStart.getDate() - Math.max(windowDays - 1, 0));

    const completed = state.datasets.progress.completed || [];
    const problemsInWindow = completed.filter((record) => {
      const completedOn = parseDate(record.completed_at);
      return completedOn && completedOn >= windowStart && completedOn <= onDate;
    }).length;

    const masteryDates = skillMasteryDates();
    const skillsInWindow = Object.values(masteryDates).filter(
      (masteredOn) => masteredOn && masteredOn >= windowStart && masteredOn <= onDate,
    ).length;

    const weeks = windowDays / 7;
    return {
      windowDays,
      problemsInWindow,
      skillsInWindow,
      problemsPerWeek: weeks ? problemsInWindow / weeks : 0,
      skillsMasteredPerWeek: weeks ? skillsInWindow / weeks : 0,
    };
  }

  function projectReadinessDate(remainingCore, skillsMasteredPerWeek, onDate) {
    if (remainingCore <= 0) {
      return {
        status: "core_mastery_met",
        message: "core-skill mastery target already met; other thresholds do not accrue via pace",
      };
    }
    if (skillsMasteredPerWeek <= 0) {
      return { status: "no_pace", message: "no projection yet (need consistent weekly activity)" };
    }
    const weeksNeeded = remainingCore / skillsMasteredPerWeek;
    const projected = new Date(onDate);
    projected.setDate(projected.getDate() + Math.round(weeksNeeded * 7));
    const iso = isoDate(projected);
    return { status: "projected", date: iso, message: `interview-ready around ${iso}` };
  }

  function computeReadiness() {
    const cfg = readinessConfig();
    const coreFractionTarget = typeof cfg.core_skill_fraction === "number" ? cfg.core_skill_fraction : 0.8;
    const passRateTarget = typeof cfg.revision_pass_rate === "number" ? cfg.revision_pass_rate : 0.9;
    const onDate = parseDate(referenceDate());

    const core = computeCoreMasteryStatus();
    const passRate = computeRevisionPassRate();
    const mocks = computeRecentMockStatus();
    const pace = computePace(onDate);

    const coreMet = core.fraction >= coreFractionTarget;
    const passMet = passRate.total > 0 && passRate.fraction >= passRateTarget;
    const mocksMet = mocks.met;

    const coreSkillsNeeded = Math.ceil(coreFractionTarget * core.total);
    const remainingCore = Math.max(coreSkillsNeeded - core.mastered, 0);
    const projection = projectReadinessDate(remainingCore, pace.skillsMasteredPerWeek, onDate);

    return {
      core: { ...core, met: coreMet, target: coreFractionTarget },
      passRate: { ...passRate, met: passMet, target: passRateTarget },
      mocks: { ...mocks, met: mocksMet },
      pace,
      projection,
      allMet: coreMet && passMet && mocksMet,
    };
  }

  function renderReadiness() {
    const readiness = computeReadiness();
    const rows = $("#readiness-rows");
    rows.replaceChildren();

    const rowSpecs = [
      {
        label: "Core skill mastery",
        met: readiness.core.met,
        detail:
          `${readiness.core.mastered}/${readiness.core.total} skills - ` +
          `${(readiness.core.fraction * 100).toFixed(1)}% vs ${(readiness.core.target * 100).toFixed(0)}% target`,
      },
      {
        label: "Revision pass rate",
        met: readiness.passRate.met,
        detail:
          `${readiness.passRate.pass}/${readiness.passRate.total} - ` +
          `${(readiness.passRate.fraction * 100).toFixed(1)}% vs ${(readiness.passRate.target * 100).toFixed(0)}% target`,
      },
      {
        label: "Recent mocks",
        met: readiness.mocks.met,
        detail:
          readiness.mocks.recorded >= readiness.mocks.required
            ? `last ${readiness.mocks.required}: ${readiness.mocks.recentVerdicts.join(", ") || "none"}`
            : `${readiness.mocks.recorded}/${readiness.mocks.required} mocks recorded`,
      },
    ];

    rowSpecs.forEach((spec) => {
      const row = document.createElement("div");
      row.className = "readiness-row";
      const label = document.createElement("span");
      label.className = "readiness-row-label";
      label.textContent = spec.label;
      const detail = document.createElement("span");
      detail.className = "readiness-row-detail";
      detail.textContent = spec.detail;
      row.append(label, detail, pill(spec.met ? "MET" : "UNMET", spec.met ? "good" : "bad"));
      rows.append(row);
    });

    const overall = $("#readiness-overall");
    overall.textContent = readiness.allMet ? "All met" : "Not yet";
    overall.className = `pill ${readiness.allMet ? "good" : "warn"}`;

    $("#readiness-projection").textContent =
      `Pace (trailing ${readiness.pace.windowDays}d): ${readiness.pace.problemsPerWeek.toFixed(2)} problems/week, ` +
      `${readiness.pace.skillsMasteredPerWeek.toFixed(2)} skills mastered/week. ${readiness.projection.message}`;
  }

  function renderMetrics() {
    const { progress, curriculum, scoring } = state.datasets;
    const completed = state.completedById.size;
    const total = curriculum.problems.length;
    const revisions = getRevisionEntries();
    const masteredRevisions = revisions.filter((entry) => entry.status === "MASTERED").length;
    const activeRevisions = revisions.filter((entry) => entry.status === "ACTIVE").length;
    const failedRevisions = revisions.filter((entry) => entry.status === "FAILED").length;
    const confidenceAfter = progress.completed.map((record) => record.confidence_after);
    const latestConfidence = confidenceAfter.at(-1) || 0;
    const avgConfidence = avg(confidenceAfter);
    const competency = progress.competency_completion || {};
    const implementationEngineering = progress.implementation_engineering || {};
    const openDeferred = openDeferredLearnings();

    const metrics = [
      {
        label: "Problems completed",
        value: `${completed} / ${total}`,
        note: `${total ? ((completed / total) * 100).toFixed(1) : "0.0"}% curriculum coverage`,
      },
      {
        label: "Current stage",
        value: text(progress.current_stage),
        note: `${progress.stage_mastery?.[progress.current_stage]?.skills_mastered || 0} skills mastered in this stage`,
      },
      {
        label: "Skill mastery",
        value: `${competency.mastered_skills || 0} / ${competency.total_skills || 0}`,
        note: `${competency.percent || 0}% competency completion`,
      },
      {
        label: "Revision load",
        value: `${dueEntries().length} due`,
        note: `${activeRevisions} active, ${failedRevisions} failed, ${masteredRevisions} mastered`,
      },
      {
        label: "Deferred learning",
        value: `${openDeferred.length} open`,
        note: "Tracked as future evidence opportunities, not scheduled tasks",
      },
      {
        label: "Confidence",
        value: `${latestConfidence.toFixed(1)} / 10`,
        note: `Average after-session confidence ${avgConfidence.toFixed(2)} / 10`,
      },
      {
        label: "Weighted thinking",
        value: `${(progress.scores?.averages?.thinking_weighted || 0).toFixed(2)} / ${scoring.scale?.maximum || 4}`,
        note: "Weighted average across completed problems",
      },
      {
        label: "Implementation eng",
        value: `${Number(implementationEngineering.score || 0).toFixed(1)} / 10`,
        note: `${implementationEngineering.common_errors?.length || 0} recorded implementation errors`,
      },
      {
        label: "Interview score",
        value: `${(progress.scores?.averages?.interview_average || 0).toFixed(2)} / ${scoring.interview_scale?.maximum || 10}`,
        note: "Average interview readiness score",
      },
      {
        label: "Pattern evidence",
        value: `${patternEntries().length}`,
        note: "transferable thinking models in knowledge layer",
      },
    ];

    const grid = $("#metric-grid");
    grid.replaceChildren();
    const template = $("#metric-template");
    metrics.forEach((metric) => {
      const node = template.content.cloneNode(true);
      node.querySelector(".metric-label").textContent = metric.label;
      node.querySelector(".metric-value").textContent = metric.value;
      node.querySelector(".metric-note").textContent = metric.note;
      grid.append(node);
    });
  }

  function renderOperatingBoard() {
    const target = $("#operating-board");
    target.replaceChildren();
    const action = nextAction();
    const due = dueEntries();
    const latest = state.datasets.progress.completed.at(-1);
    const latestProblem = latest ? state.problemsById.get(latest.problem_id) : null;
    const openDeferred = openDeferredLearnings();
    const weakest = collectQuestionWeaknesses()[0];
    const currentStage = state.datasets.progress.current_stage;
    const stageMastery = state.datasets.progress.stage_mastery?.[currentStage] || {};
    const stageTotal = stageMastery.skills_total || 0;
    const stageDone = stageMastery.skills_mastered || 0;
    const stagePercent = stageTotal ? Math.round((stageDone / stageTotal) * 100) : 0;

    const cards = [
      {
        title: "Next best action",
        eyebrow: action.mode,
        value: action.problem ? `${action.problem.id} · ${action.problem.title}` : "No active problem",
        body: action.reason,
        tone: due.length ? "warn" : "good",
        cta: action.problem ? "Open details" : null,
        onClick: action.problem ? () => openProblemModal(action.problem.id) : null,
      },
      {
        title: "Revision pressure",
        eyebrow: "Spaced recall",
        value: `${due.length} due now`,
        body: due.length
          ? `${due[0].problem.id} has priority. ${due.length > 1 ? `${due.length - 1} more item${due.length === 2 ? "" : "s"} waiting.` : "Finish this before new work."}`
          : "No revision is due today.",
        tone: due.length ? "bad" : "good",
        cta: due.length ? "View queue" : "View schedule",
        onClick: () => document.querySelector("#revisions").scrollIntoView({ behavior: "smooth" }),
      },
      {
        title: "Latest evidence",
        eyebrow: "Last completion",
        value: latestProblem ? `${latest.problem_id} · ${latestProblem.title}` : "No solved problem yet",
        body: latest
          ? `${latest.confidence_before} -> ${latest.confidence_after} confidence · algorithm ${latest.algorithm_thinking_score}/10 · implementation ${latest.implementation_engineering_score}/10`
          : "Complete a problem to populate evidence.",
        tone: "info",
        cta: latest ? "Open problem" : null,
        onClick: latest ? () => openProblemModal(latest.problem_id) : null,
      },
      {
        title: "Learning attention",
        eyebrow: "Weakness + deferred",
        value: weakest ? weakest.title : `${openDeferred.length} open deferred`,
        body: weakest
          ? `${weakest.evidence.length} signal${weakest.evidence.length === 1 ? "" : "s"} · ${openDeferred.length} open deferred learning${openDeferred.length === 1 ? "" : "s"}`
          : openDeferred.length
            ? "Open deferred learnings are waiting for natural evidence."
            : "No open learning attention item.",
        tone: openDeferred.length || weakest ? "warn" : "good",
        cta: "Review focus",
        onClick: () => document.querySelector("#weakness-lab").scrollIntoView({ behavior: "smooth" }),
      },
      {
        title: "Stage mastery",
        eyebrow: currentStage,
        value: `${stagePercent}% complete`,
        body: `${stageDone}/${stageTotal} skills mastered in the active stage.`,
        tone: stagePercent >= 50 ? "good" : "info",
        cta: "View stage map",
        onClick: () => document.querySelector("#stages").scrollIntoView({ behavior: "smooth" }),
      },
    ];

    cards.forEach((item) => {
      const card = document.createElement("article");
      card.className = `operating-card ${item.tone || ""}`.trim();
      card.innerHTML = `
        <div>
          <p class="eyebrow">${item.eyebrow}</p>
          <h4>${item.title}</h4>
        </div>
        <strong>${item.value}</strong>
        <p>${item.body}</p>
      `;
      if (item.cta && item.onClick) {
        const button = document.createElement("button");
        button.className = "mini-button";
        button.type = "button";
        button.textContent = item.cta;
        button.addEventListener("click", item.onClick);
        card.append(button);
      }
      target.append(card);
    });
  }

  function renderNextAction() {
    const action = nextAction();
    $("#selection-mode").textContent = action.mode;
    const wrap = $("#next-action");
    wrap.replaceChildren();
    if (!action.problem) {
      wrap.append(empty("No active problem."));
      return;
    }

    const title = document.createElement("h4");
    title.className = "problem-title";
    title.textContent = `${action.problem.id} - ${action.problem.title}`;

    const meta = document.createElement("div");
    meta.className = "meta-row";
    meta.append(
      pill(action.problem.stage),
      pill(skillLabel(action.problem.primary_skill)),
      pill(action.problem.difficulty),
      pill(action.problem.problem_role || "ROLE"),
    );

    const reason = document.createElement("p");
    reason.textContent = action.reason;

    const notes = document.createElement("p");
    notes.textContent = action.problem.notes || "No notes recorded.";
    const openButton = document.createElement("button");
    openButton.className = "stage-skill-open";
    openButton.type = "button";
    openButton.textContent = "View problem details";
    openButton.addEventListener("click", () => openProblemModal(action.problem.id));
    wrap.append(title, meta, reason, notes, openButton);
  }

  function renderThinkingBars() {
    const dimensions = state.datasets.progress.scores?.averages?.thinking_dimensions || {};
    const labels = state.datasets.scoring.dimensions || {};
    const max = state.datasets.scoring.scale?.maximum || 4;
    const rows = Object.entries(dimensions).sort((a, b) => a[1] - b[1]);
    const target = $("#thinking-bars");
    target.replaceChildren();
    rows.forEach(([key, value]) => {
      const row = document.createElement("div");
      row.className = "bar-row";
      row.title = labels[key] || key;
      const name = document.createElement("span");
      name.className = "bar-name";
      name.textContent = key.replaceAll("_", " ");
      const track = document.createElement("div");
      track.className = "track";
      const fill = document.createElement("div");
      fill.className = "fill";
      fill.style.setProperty("--width", `${clamp((value / max) * 100, 0, 100)}%`);
      track.append(fill);
      const score = document.createElement("span");
      score.className = "bar-value";
      score.textContent = value.toFixed(2);
      row.append(name, track, score);
      target.append(row);
    });
  }

  function weaknessAdvice(key) {
    const advice = {
      brute_force: {
        title: "Starting with brute force",
        action: "First write the simple correct solution, then find what work is repeated.",
        query: "brute force",
      },
      pattern_detection: {
        title: "Finding the core rule",
        action: "Explain what must stay true after every step before thinking about patterns.",
        query: "invariant",
      },
      algorithm_design: {
        title: "Building the algorithm",
        action: "Decide what to track, why it is enough, and test the update rule on edge cases.",
        query: "state",
      },
      implementation: {
        title: "Writing code without breaking the idea",
        action: "Check starting values, loop bounds, update order, and return value.",
        query: "initialization",
      },
      complexity_analysis: {
        title: "Knowing time and space cost",
        action: "Connect time and space to the loops, data structures, and input size.",
        query: "complexity",
      },
      understanding: {
        title: "Understanding the question",
        action: "Say what is given, what to return, and what can go wrong before solving.",
        query: "constraint",
      },
      examples: {
        title: "Making useful examples",
        action: "Create a normal case, a tiny case, and a tricky case before coding.",
        query: "edge",
      },
      communication: {
        title: "Explaining the solution clearly",
        action: "Explain in this order: simple idea, repeated work, core rule, proof, complexity.",
        query: "proof",
      },
    };
    return advice[key] || {
      title: key.replaceAll("_", " "),
      action: "Practice this dimension on the next unlocked problem and record the failure mode.",
      query: key,
    };
  }

  function weaknessQuickCues(key) {
    const cues = {
      brute_force: {
        issue: "Skipping baseline",
        fix: "Write brute force first",
        drill: "Find repeated work",
      },
      pattern_detection: {
        issue: "Rule not visible",
        fix: "Name invariant",
        drill: "State after index i",
      },
      algorithm_design: {
        issue: "State unclear",
        fix: "Define what to track",
        drill: "Prove state is enough",
      },
      implementation: {
        issue: "Code breaks idea",
        fix: "Use blueprint",
        drill: "Init, loop, return",
      },
      complexity_analysis: {
        issue: "Cost unclear",
        fix: "Count loops + DS ops",
        drill: "n x work per step",
      },
      understanding: {
        issue: "Goal unclear",
        fix: "Restate input/output",
        drill: "Find failure case",
      },
      examples: {
        issue: "Weak dry run",
        fix: "Use tiny + tricky case",
        drill: "1, 2, edge",
      },
      communication: {
        issue: "Explanation scattered",
        fix: "Use interview order",
        drill: "Idea, proof, cost",
      },
    };
    return cues[key] || {
      issue: key.replaceAll("_", " "),
      fix: "Practice focused recall",
      drill: "Record exact miss",
    };
  }

  function classifyWeaknessText(text) {
    const lower = text.toLowerCase();
    const mappings = [
      [["brute", "repeated work", "baseline"], "brute_force"],
      [["example", "counterexample", "edge case"], "examples"],
      [["invariant", "proof", "correctness"], "pattern_detection"],
      [["greedy", "frontier", "decision", "state compression"], "algorithm_design"],
      [["complexity", "o(", "time", "space"], "complexity_analysis"],
      [["initialization", "loop", "implementation", "code", "return"], "implementation"],
      [["communicat", "explain", "interview"], "communication"],
      [["constraint", "input", "output", "scope"], "understanding"],
    ];
    return mappings
      .filter(([keywords]) => keywords.some((keyword) => lower.includes(keyword)))
      .map(([, dimension]) => dimension);
  }

  function normalizeWeaknessEntry(raw) {
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      return {
        text: String(raw.text || "").trim(),
        status: raw.status === "resolved" ? "resolved" : "open",
        source: ["session", "mock", "revision"].includes(raw.source) ? raw.source : "session",
        resolvedOn: typeof raw.resolved_on === "string" ? raw.resolved_on : null,
      };
    }
    let text = String(raw ?? "").trim();
    let status = "open";
    let source = "session";
    if (text.startsWith("Resolved: ")) {
      status = "resolved";
      text = text.slice("Resolved: ".length);
    } else if (text.startsWith("Mock: ")) {
      source = "mock";
      text = text.slice("Mock: ".length);
    }
    return { text, status, source, resolvedOn: null };
  }

  function collectQuestionWeaknesses() {
    const clusters = new Map();
    const addEvidence = (dimension, item) => {
      if (!clusters.has(dimension)) {
        clusters.set(dimension, {
          key: dimension,
          severity: 0,
          evidence: [],
          ...weaknessAdvice(dimension),
        });
      }
      const cluster = clusters.get(dimension);
      cluster.severity += item.severity;
      cluster.evidence.push(item);
    };

    Object.entries(state.datasets.progress.weaknesses_detected || {}).forEach(
      ([problemId, entries]) => {
        if (!Array.isArray(entries)) return;
        entries.forEach((raw) => {
          // F20a: entries are objects {text, status, source, resolved_on};
          // legacy plain strings normalize by prefix. Resolved entries no
          // longer inflate clusters.
          const entry = normalizeWeaknessEntry(raw);
          if (entry.status === "resolved" || !entry.text) return;
          classifyWeaknessText(entry.text).forEach((dimension) => {
            addEvidence(dimension, {
              source: "weaknesses_detected",
              problemId,
              text: entry.text,
              severity: 1.2,
            });
          });
        });
      },
    );

    state.datasets.progress.completed.forEach((record) => {
      const text = String(record.main_mistake || "").trim();
      if (!text || text.toLowerCase().includes("none recorded")) return;
      classifyWeaknessText(text).forEach((dimension) => {
        addEvidence(dimension, {
          source: "main_mistake",
          problemId: record.problem_id,
          text,
          severity: 1.1,
        });
      });
    });

    return [...clusters.values()].sort((a, b) => b.severity - a.severity);
  }

  function targetedProblemsForWeakness(weakness, limit = 4) {
    const query = weakness.query.toLowerCase();
    const completed = [];
    const open = [];
    state.datasets.curriculum.problems.forEach((problem) => {
      const haystack = [
        problem.title,
        problem.notes,
        problem.stage,
        problem.primary_skill,
        skillMeta(problem.primary_skill).name,
        skillMeta(problem.primary_skill).description,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(query)) return;
      if (state.completedById.has(problem.id)) completed.push(problem);
      else open.push(problem);
    });
    const currentStage = state.datasets.progress.current_stage;
    const currentStageOpen = open.filter((problem) => problem.stage === currentStage);
    const seen = new Set();
    return [...currentStageOpen, ...open, ...completed]
      .filter((problem) => {
        if (seen.has(problem.id)) return false;
        seen.add(problem.id);
        return true;
      })
      .slice(0, limit);
  }

  function buildMistakeSignals() {
    const profile = state.datasets.progress.thinking_profile || {};
    const completedMistakes = state.datasets.progress.completed
      .map((record) => ({
        problemId: record.problem_id,
        text: record.main_mistake,
      }))
      .filter((entry) => entry.text && !entry.text.toLowerCase().includes("none recorded"));
    const catalog = state.datasets.mistakes.entries || [];
    return {
      profileGaps: [...(profile.gaps || []), ...(profile.common_failures || [])],
      completedMistakes,
      catalog,
    };
  }

  function renderWeaknessLab() {
    const target = $("#weakness-grid");
    target.replaceChildren();
    const weakest = collectQuestionWeaknesses().slice(0, 4);

    weakest.forEach((weakness) => {
      const card = document.createElement("article");
      card.className = "prep-card";
      const problems = targetedProblemsForWeakness(weakness, 3);
      const cues = weaknessQuickCues(weakness.key);
      card.innerHTML = `
        <div class="section-head">
          <div>
            <h4>${weakness.title}</h4>
            <span class="small-muted">${weakness.evidence.length} question-level weakness signal${weakness.evidence.length === 1 ? "" : "s"}</span>
          </div>
          <span class="pill warn">focus</span>
        </div>
        <div class="weakness-cues">
          <div><span>Issue</span><strong>${cues.issue}</strong></div>
          <div><span>Fix</span><strong>${cues.fix}</strong></div>
          <div><span>Drill</span><strong>${cues.drill}</strong></div>
        </div>
      `;
      const summary = document.createElement("p");
      summary.className = "compact-line";
      summary.innerHTML = `<strong>Practice:</strong> ${problems.map((problem) => problem.id).join(", ") || "None"}`;
      const openButton = document.createElement("button");
      openButton.className = "stage-skill-open";
      openButton.type = "button";
      openButton.textContent = "View plan";
      openButton.addEventListener("click", () => openWeaknessModal(weakness));
      card.append(summary, openButton);
      target.append(card);
    });

    if (!weakest.length) {
      const emptyCard = document.createElement("article");
      emptyCard.className = "prep-card";
      emptyCard.append(
        empty(
          "No question-level weakness has been recorded yet. Add entries under progress.weaknesses_detected or completed problem main_mistake to generate targeted practice.",
        ),
      );
      target.append(emptyCard);
    }

    const mistakes = document.createElement("article");
    mistakes.className = "prep-card wide";
    mistakes.innerHTML = `
      <div class="section-head">
        <div>
          <h4>Frequent mistakes and correction drills</h4>
          <span class="small-muted">Short labels first; details stay inside review.</span>
        </div>
        <span class="pill bad">${combinedMistakeItems().length} signals</span>
      </div>
      <div class="weakness-cues">
        <div><span>Look for</span><strong>Repeated misses</strong></div>
        <div><span>Correct with</span><strong>One drill</strong></div>
        <div><span>Use on</span><strong>Next problem</strong></div>
      </div>
    `;
    const mistakeButton = document.createElement("button");
    mistakeButton.className = "stage-skill-open";
    mistakeButton.type = "button";
    mistakeButton.textContent = "View mistakes";
    mistakeButton.addEventListener("click", openMistakesModal);
    mistakes.append(mistakeButton);
    target.append(mistakes);

    const plan = document.createElement("article");
    plan.className = "prep-card";
    plan.innerHTML = `
      <div class="section-head">
        <h4>How to work on this</h4>
        <span class="pill good">routine</span>
      </div>
      <div class="weakness-cues">
        <div><span>Pick</span><strong>One weakness</strong></div>
        <div><span>Solve</span><strong>Without label first</strong></div>
        <div><span>Record</span><strong>Exact miss</strong></div>
      </div>
    `;
    const routineButton = document.createElement("button");
    routineButton.className = "stage-skill-open";
    routineButton.type = "button";
    routineButton.textContent = "View routine";
    routineButton.addEventListener("click", openRoutineModal);
    plan.append(routineButton);
    target.append(plan);
  }

  function renderDeferredLearnings() {
    const target = $("#deferred-grid");
    target.replaceChildren();
    const { query } = currentFilters();
    const entries = deferredLearningEntries().filter((entry) =>
      deferredLearningMatchesQuery(entry, query),
    );
    const open = entries.filter((entry) => entry.status === "OPEN");
    const resolved = entries.filter((entry) => entry.status === "RESOLVED");

    const summary = document.createElement("article");
    summary.className = "prep-card wide";
    summary.innerHTML = `
      <div class="section-head">
        <div>
          <h4>Unfinished learning memory</h4>
          <span class="small-muted">The curriculum still drives the next problem. These close only when future evidence appears naturally.</span>
        </div>
        <span class="pill warn">${open.length} open</span>
      </div>
      <p>Use this section to remember solved-problem learning that is worth strengthening later, without forcing extra revision sessions.</p>
    `;
    target.append(summary);

    if (!entries.length) {
      const emptyCard = document.createElement("article");
      emptyCard.className = "prep-card";
      emptyCard.append(empty("No deferred learnings match the current filters."));
      target.append(emptyCard);
      return;
    }

    open
      .sort((a, b) => {
        const priorityOrder = { HIGH: 0, MEDIUM: 1, LOW: 2 };
        return (
          (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3) ||
          String(a.created_on).localeCompare(String(b.created_on)) ||
          String(a.id).localeCompare(String(b.id))
        );
      })
      .forEach((entry) => target.append(buildDeferredLearningCard(entry)));

    if (resolved.length) {
      const resolvedCard = document.createElement("article");
      resolvedCard.className = "prep-card wide";
      resolvedCard.innerHTML = `
        <div class="section-head">
          <h4>Resolved by future evidence</h4>
          <span class="pill good">${resolved.length}</span>
        </div>
        <p>These were closed by later problems, revisions, or mentor verification.</p>
      `;
      const button = document.createElement("button");
      button.className = "stage-skill-open";
      button.type = "button";
      button.textContent = "View resolved evidence";
      button.addEventListener("click", () => openDeferredListModal("Resolved deferred learnings", resolved));
      resolvedCard.append(button);
      target.append(resolvedCard);
    }
  }

  function buildDeferredLearningCard(entry) {
    const origin = state.problemsById.get(entry.origin_problem);
    const card = document.createElement("article");
    card.className = "prep-card";
    card.innerHTML = `
      <div class="section-head">
        <div>
          <h4>${entry.id} · ${entry.category.replaceAll("_", " ")}</h4>
          <span class="small-muted">${entry.origin_problem}${origin ? ` - ${origin.title}` : ""}</span>
        </div>
        <span class="pill ${entry.priority === "HIGH" ? "bad" : entry.priority === "MEDIUM" ? "warn" : ""}">${entry.priority}</span>
      </div>
      <p>${entry.description}</p>
      <div class="meta-row">
        <span class="pill">${skillTitle(entry.skill)}</span>
        <span class="pill">${entry.created_on}</span>
      </div>
    `;
    const actions = document.createElement("div");
    actions.className = "meta-row";
    if (origin) {
      const originButton = document.createElement("button");
      originButton.className = "stage-skill-open";
      originButton.type = "button";
      originButton.textContent = `Open ${entry.origin_problem}`;
      originButton.addEventListener("click", () => openProblemModal(entry.origin_problem));
      actions.append(originButton);
    }
    const skillButton = document.createElement("button");
    skillButton.className = "stage-skill-open";
    skillButton.type = "button";
    skillButton.textContent = "View skill";
    skillButton.addEventListener("click", () => openSingleSkillModal(entry.skill));
    actions.append(skillButton);
    card.append(actions);
    return card;
  }

  function openDeferredListModal(title, entries) {
    const body = setModal(title, `${entries.length} deferred learning${entries.length === 1 ? "" : "s"}`, "Deferred learning");
    const list = document.createElement("div");
    list.className = "mistake-list single";
    entries.forEach((entry) => {
      const origin = state.problemsById.get(entry.origin_problem);
      const resolvedBy = entry.resolved_by_problem
        ? state.problemsById.get(entry.resolved_by_problem)
        : null;
      const node = document.createElement("article");
      node.className = "mistake-item";
      node.innerHTML = `
        <strong>${entry.id} · ${entry.category.replaceAll("_", " ")}</strong>
        <p>${entry.description}</p>
        <small>Origin: ${entry.origin_problem}${origin ? ` - ${origin.title}` : ""}</small>
        ${entry.evidence ? `<small>Evidence: ${entry.evidence}</small>` : ""}
        ${resolvedBy ? `<small>Resolved by: ${entry.resolved_by_problem} - ${resolvedBy.title}</small>` : ""}
      `;
      if (origin) {
        const button = document.createElement("button");
        button.className = "mini-button";
        button.type = "button";
        button.textContent = `Open ${entry.origin_problem}`;
        button.addEventListener("click", () => openProblemModal(entry.origin_problem));
        node.append(button);
      }
      list.append(node);
    });
    body.append(list);
    showModal();
  }

  function renderEdgeCases() {
    const target = $("#edge-case-grid");
    target.replaceChildren();
    const complexityCard = document.createElement("article");
    complexityCard.className = "prep-card wide";
    complexityCard.innerHTML = `
      <div class="section-head">
        <h4>Expected complexity from constraints</h4>
        <span class="pill warn">before coding</span>
      </div>
      <p>Use the input size to decide whether brute force is enough or optimization is required.</p>
      <div class="complexity-list">
        ${COMPLEXITY_GUIDE.map(
          ([constraint, complexity]) => `
            <div class="complexity-row">
              <strong>${constraint}</strong>
              <span>${complexity}</span>
            </div>
          `,
        ).join("")}
      </div>
      <p><strong>Space check:</strong> O(1) is ideal when possible; O(n) is common for hash maps, prefix arrays, visited sets, stacks, queues, and DP. For matrices or pair states, verify O(n^2) memory fits the constraints.</p>
    `;
    target.append(complexityCard);
    EDGE_CASE_GROUPS.forEach((group) => {
      const card = document.createElement("article");
      card.className = "prep-card";
      card.innerHTML = `
        <div class="section-head">
          <h4>${group.title}</h4>
          <span class="pill">${group.items.length} checks</span>
        </div>
        <ul class="routine-list">
          ${group.items.map((item) => `<li>${item}</li>`).join("")}
        </ul>
      `;
      target.append(card);
    });
  }

  function combinedMistakeItems() {
    const signals = buildMistakeSignals();
    return [
      ...signals.completedMistakes.map((entry) => ({
        title: entry.problemId,
        text: entry.text,
        fix: "Re-open this problem detail and restate the corrected reasoning in one paragraph.",
        problemId: entry.problemId,
      })),
      ...signals.profileGaps.map((text) => ({
        title: "Profile caution",
        text,
        fix: "Before coding, write the invariant and one edge-case check that could break it.",
      })),
      ...signals.catalog.map((entry) => ({
        title: entry.title,
        text: entry.symptom,
        fix: entry.fix,
        problemId: entry.source_problem,
      })),
    ];
  }

  function openMistakesModal() {
    // Same underlying list as the "Frequent mistakes" badge count.
    const allItems = combinedMistakeItems();
    const items = allItems.slice(-12);
    const body = setModal(
      "Frequent mistakes and correction drills",
      `${allItems.length} mistake signal${allItems.length === 1 ? "" : "s"}${allItems.length > items.length ? ` · showing latest ${items.length}` : ""}`,
      "Mistake review",
    );
    const list = document.createElement("div");
    list.className = "mistake-list single";
    items.forEach((item) => {
      const node = document.createElement("article");
      node.className = "mistake-item";
      node.innerHTML = `
        <strong>${item.title}</strong>
        <p>${item.text}</p>
        <small>${item.fix}</small>
      `;
      if (item.problemId) {
        const button = document.createElement("button");
        button.className = "mini-button";
        button.type = "button";
        button.textContent = `Open ${item.problemId}`;
        button.addEventListener("click", () => openProblemModal(item.problemId));
        node.append(button);
      }
      list.append(node);
    });
    body.append(list);
    showModal();
  }

  function openRoutineModal() {
    const body = setModal(
      "Targeted weakness practice routine",
      "Use this every time you work on a weakness-targeted problem",
      "Practice routine",
    );
    const card = document.createElement("article");
    card.className = "note-card";
    card.innerHTML = `
      <h4>Routine</h4>
      <ol class="routine-list">
        <li>Pick one focus weakness, not three.</li>
        <li>Attempt the next targeted problem without naming a pattern first.</li>
        <li>Write brute force, repeated work, invariant, proof, then code.</li>
        <li>Before implementation, check initialization, loop bounds, and return value.</li>
        <li>After solving, record the exact mistake and whether it repeated.</li>
      </ol>
    `;
    body.append(card);
    showModal();
  }

  function openWeaknessModal(weakness) {
    const problems = targetedProblemsForWeakness(weakness, 6);
    const body = setModal(
      weakness.title,
      `${weakness.evidence.length} question-level weakness signal${weakness.evidence.length === 1 ? "" : "s"}`,
      "Weakness plan",
    );
    const intro = document.createElement("div");
    intro.className = "modal-intro";
    intro.innerHTML = `
      <p>${weakness.action}</p>
      <div class="meta-row">
        <span class="pill warn">focus</span>
        <span class="pill">${weakness.key}</span>
      </div>
    `;
    body.append(intro);

    const drillCard = document.createElement("article");
    drillCard.className = "note-card";
    const prompts = weaknessAdvice(weakness.key);
    const promptText = {
      brute_force: [
        "What is the most direct correct solution?",
        "Where exactly is the repeated work?",
        "Which stored state removes that repeated work?",
      ],
      pattern_detection: [
        "What does the running variable mean after processing index i?",
        "What condition lets you discard prior state?",
        "What invariant would make the algorithm obviously correct?",
      ],
      algorithm_design: [
        "What decision is irreversible here?",
        "Why is the chosen state sufficient?",
        "What proof prevents a skipped candidate from mattering later?",
      ],
      implementation: [
        "Does the initial value represent a real valid state?",
        "Should the loop start at index 0 or 1?",
        "Which edge case proves the return value is correct?",
      ],
      understanding: [
        "What is the exact success condition?",
        "Which input constraint changes the required complexity?",
        "What edge case would break a casual interpretation?",
      ],
    }[weakness.key] || [prompts.action];
    drillCard.innerHTML = `
      <h4>Drill questions</h4>
      <ul>${promptText.map((prompt) => `<li>${prompt}</li>`).join("")}</ul>
    `;
    body.append(drillCard);

    body.append(buildProblemGroup("Target problems", problems, ""));

    const evidence = document.createElement("article");
    evidence.className = "note-card";
    evidence.innerHTML = `<h4>Question-level evidence</h4>`;
    const list = document.createElement("div");
    list.className = "mistake-list single";
    weakness.evidence.forEach((item) => {
      const node = document.createElement("article");
      node.className = "mistake-item";
      node.innerHTML = `
        <strong>${item.problemId} · ${item.source}</strong>
        <p>${item.text}</p>
      `;
      const button = document.createElement("button");
      button.className = "mini-button";
      button.type = "button";
      button.textContent = `Open ${item.problemId}`;
      button.addEventListener("click", () => openProblemModal(item.problemId));
      node.append(button);
      list.append(node);
    });
    evidence.append(list);
    body.append(evidence);
    showModal();
  }

  function renderStages() {
    const { progress, stages } = state.datasets;
    const board = $("#stage-board");
    board.replaceChildren();
    const { query, stage: selectedStage } = currentFilters();
    stages.stage_order
      .filter((stageName) => !selectedStage || stageName === selectedStage)
      .filter((stageName) => stageMatchesQuery(stageName, query))
      .forEach((stageName) => {
      const stageNumber = stages.stage_order.indexOf(stageName) + 1;
      const mastery = progress.stage_mastery?.[stageName] || {};
      const details = stages.stages[stageName] || {};
      const total = mastery.skills_total || details.skills?.length || 0;
      const mastered = mastery.skills_mastered || 0;
      const percent = total ? (mastered / total) * 100 : 0;
      const stageProblems = state.datasets.curriculum.problems.filter(
        (problem) => problem.stage === stageName,
      );
      const solvedStageProblems = stageProblems.filter((problem) =>
        state.completedById.has(problem.id),
      );
      const card = document.createElement("article");
      card.className = `stage-card ${stageName === progress.current_stage ? "active" : ""}`;
      const skills = details.skills || [];
      const masteredSkillNames = skills
        .filter((skillId) => progress.skill_progress?.[skillId]?.mastered)
        .map((skillId) => skillTitle(skillId));
      const nextSkill = skills.find((skillId) => !progress.skill_progress?.[skillId]?.mastered);
      const statusClass =
        stageName === progress.current_stage
          ? "current"
          : mastery.status === "mastered"
            ? "mastered"
            : mastery.status === "locked"
              ? "locked"
              : "open";
      card.innerHTML = `
        <div class="stage-rail ${statusClass}">
          <span class="stage-number">${stageNumber}</span>
          <span class="stage-line"></span>
        </div>
        <div class="stage-content">
          <div class="stage-card-head">
            <div>
              <p class="eyebrow">Stage ${stageNumber}</p>
              <h4>${stageName}</h4>
            </div>
            <span class="pill ${mastery.status === "mastered" ? "good" : mastery.status === "locked" ? "" : "warn"}">${mastery.status || "unknown"}</span>
          </div>
          <p class="stage-goal">${details.goal || "No goal recorded."}</p>
          <div class="stage-progress-box">
            <div class="stage-progress-head">
              <strong>${Math.round(percent)}%</strong>
              <span>${mastered}/${total} skills mastered</span>
            </div>
            <div class="track"><div class="fill" style="--width:${percent}%"></div></div>
          </div>
          <div class="stage-stat-grid">
            <div>
              <span>Problems</span>
              <strong>${solvedStageProblems.length}/${stageProblems.length}</strong>
            </div>
            <div>
              <span>Next skill</span>
              <strong>${nextSkill ? skillTitle(nextSkill) : "Stage complete"}</strong>
            </div>
            <div>
              <span>Mastered skills</span>
              <strong>${masteredSkillNames.length || 0}</strong>
            </div>
          </div>
        </div>
      `;
      const visibleSkills = skills.filter((skillId) => skillMatchesQuery(skillId, query));
      const button = document.createElement("button");
      button.className = "stage-skill-open";
      button.type = "button";
      button.textContent = `View ${visibleSkills.length}/${skills.length} skills`;
      button.addEventListener("click", () => openSkillModal(stageName));
      card.append(button);
      board.append(card);
    });
    if (!board.children.length) {
      board.append(empty("No stages match the current filters."));
    }
  }

  function openSkillModal(stageName) {
    const { progress, stages } = state.datasets;
    const { query } = currentFilters();
    const details = stages.stages[stageName] || {};
    const stageNumber = stages.stage_order.indexOf(stageName) + 1;
    const mastery = progress.stage_mastery?.[stageName] || {};
    const skills = (details.skills || []).filter((skillId) => skillMatchesQuery(skillId, query));
    const body = setModal(
      `Stage ${stageNumber}: ${stageName}`,
      `${mastery.skills_mastered || 0}/${mastery.skills_total || details.skills?.length || 0} skills mastered · ${mastery.status || "unknown"}`,
      "Stage skills",
    );

    const intro = document.createElement("div");
    intro.className = "modal-intro";
    intro.innerHTML = `
      <p>${details.goal || "No stage goal recorded."}</p>
      <div class="meta-row">
        <span class="pill">${skills.length} visible skills</span>
        <span class="pill">${query ? `filtered by "${query}"` : "no search filter"}</span>
      </div>
    `;
    body.append(intro);

    const list = document.createElement("div");
    list.className = "modal-skill-list";
    skills.forEach((skillId) => {
      const row = buildSkillDetailRow(skillId);
      list.append(row);
    });
    if (!skills.length) {
      list.append(empty("No skills match the current search filter."));
    }
    body.append(list);

    showModal();
  }

  function openSingleSkillModal(skillId) {
    const skillInfo = skillMeta(skillId);
    const problems = state.datasets.curriculum.problems.filter(
      (problem) => problem.primary_skill === skillId,
    );
    const solved = problems.filter((problem) => state.completedById.has(problem.id));
    const skill = state.datasets.progress.skill_progress?.[skillId] || {};
    const body = setModal(
      `${skillInfo.name || skillId}`,
      `${skillId} · ${solved.length}/${problems.length} problems completed · ${skill.mastered ? "mastered" : "learning"}`,
      "Skill details",
    );
    const intro = document.createElement("div");
    intro.className = "modal-intro";
    intro.innerHTML = `
      <p>${skillInfo.description || "No skill description recorded."}</p>
      <div class="meta-row">
        <span class="pill ${skill.mastered ? "good" : ""}">${skill.mastered ? "mastered" : "learning"}</span>
        <span class="pill">primary ${skill.primary_solved ? "done" : "open"}</span>
        <span class="pill">reinforcement ${skill.reinforcement_attempted ? "done" : "open"}</span>
        <span class="pill">score ${skill.primary_weighted_score ?? "-"}</span>
      </div>
    `;
    body.append(intro, buildSkillDetailRow(skillId));
    const skillPatterns = patternsForSkill(skillId);
    if (skillPatterns.length) {
      body.append(patternListCard("Linked patterns", skillPatterns));
    }
    showModal();
  }

  function buildSkillDetailRow(skillId) {
    const progress = state.datasets.progress;
    const skillInfo = skillMeta(skillId);
    const skill = progress.skill_progress?.[skillId] || {};
    const problems = state.datasets.curriculum.problems.filter(
      (problem) => problem.primary_skill === skillId,
    );
    const solved = problems.filter((problem) => state.completedById.has(problem.id));
    const remaining = problems.filter((problem) => !state.completedById.has(problem.id));
    const nextOpen = problems.find((problem) => !state.completedById.has(problem.id));
    const row = document.createElement("article");
    row.className = "modal-skill-row";
    row.innerHTML = `
      <div class="stage-skill-main">
        <div>
          <strong>${skillInfo.name || skillId}</strong>
          <span>${skillId}</span>
        </div>
        <span>${solved.length}/${problems.length} problems</span>
      </div>
      <p>${skillInfo.description || "No skill description recorded."}</p>
      <div class="meta-row">
        <span class="pill ${skill.mastered ? "good" : ""}">${skill.mastered ? "mastered" : "learning"}</span>
        <span class="pill">primary ${skill.primary_solved ? "done" : "open"}</span>
        <span class="pill">reinforcement ${skill.reinforcement_attempted ? "done" : "open"}</span>
        <span class="pill">score ${skill.primary_weighted_score ?? "-"}</span>
      </div>
      <p>${nextOpen ? `Next: ${nextOpen.id} - ${nextOpen.title}` : "All related problems in this skill are completed."}</p>
    `;
    row.append(buildProblemGroup("Solved", solved, "good"));
    row.append(buildProblemGroup("Remaining", remaining, ""));
    return row;
  }

  function buildProblemGroup(title, problems, tone) {
    const details = document.createElement("details");
    details.className = "problem-group";
    const summary = document.createElement("summary");
    summary.textContent = `${title} (${problems.length})`;
    if (tone) summary.className = tone;
    const list = document.createElement("div");
    list.className = "problem-chip-list";
    if (!problems.length) {
      list.append(empty(`No ${title.toLowerCase()} problems.`));
    } else {
      problems.forEach((problem) => {
        const item = document.createElement("button");
        item.className = "problem-chip";
        item.type = "button";
        item.innerHTML = `
          <strong>${problem.id}</strong>
          <span>${problem.title}</span>
          <small>${problem.difficulty} · ${problem.problem_role || "role"}${problem.original_number ? ` · LC ${problem.original_number}` : ""}</small>
        `;
        item.addEventListener("click", () => openProblemModal(problem.id));
        list.append(item);
      });
    }
    details.append(summary, list);
    return details;
  }

  function renderRevisionLanes() {
    const entries = getRevisionEntries();
    const due = entries.filter((entry) => entry.nextDue && entry.daysUntil <= 0);
    const lanes = [
      { key: "due", label: "Due now", entries: entries.filter((entry) => entry.nextDue && entry.daysUntil <= 0) },
      { key: "r1", label: "R1", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage === 0) },
      { key: "r2", label: "R2", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage === 1) },
      { key: "r3", label: "R3", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage === 2) },
      { key: "r4", label: "R4", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage >= 3) },
      { key: "mastered", label: "Mastered", entries: entries.filter((entry) => entry.status === "MASTERED") },
    ];

    const wrap = $("#revision-lanes");
    wrap.replaceChildren();
    const consoleNode = document.createElement("div");
    consoleNode.className = "revision-console";

    const queue = document.createElement("article");
    queue.className = "revision-focus";
    const topDue = due[0] || entries.find((entry) => entry.nextDue && entry.status !== "MASTERED");
    queue.innerHTML = `
      <div>
        <p class="eyebrow">${due.length ? "Urgent recall" : "Next scheduled recall"}</p>
        <h4>${topDue ? `${topDue.problem.id} · ${topDue.problem.title}` : "No active revisions"}</h4>
        <p>${topDue ? `${stageLabel(topDue.stage)} · ${topDue.nextDue || "maintenance"} · ${topDue.status}` : "All active recall queues are empty."}</p>
      </div>
      <div class="revision-focus-score">
        <strong>${due.length}</strong>
        <span>due now</span>
      </div>
    `;
    if (topDue) {
      const button = document.createElement("button");
      button.className = "stage-skill-open";
      button.type = "button";
      button.textContent = "Open revision problem";
      button.addEventListener("click", () => openProblemModal(topDue.problem.id));
      queue.append(button);
    }
    consoleNode.append(queue);

    const ladder = document.createElement("div");
    ladder.className = "revision-ladder";
    lanes.forEach((lane) => {
      const node = document.createElement("button");
      node.className = `lane ${lane.key === "due" && lane.entries.length ? "urgent" : ""}`.trim();
      node.type = "button";
      const next = lane.entries[0];
      const totalActive = Math.max(entries.filter((entry) => entry.status !== "MASTERED").length, 1);
      const width = Math.max(6, Math.round((lane.entries.length / totalActive) * 100));
      node.innerHTML = `
        <div>
          <strong>${lane.label}</strong>
          <span class="lane-count">${lane.entries.length}</span>
        </div>
        <div class="progress-track"><span style="width:${width}%"></span></div>
        <small class="small-muted">${next ? `${next.problem.id} · ${next.nextDue || "maintenance"}` : "No items"}</small>
      `;
      node.addEventListener("click", () => openRevisionListModal(lane.label, lane.entries));
      ladder.append(node);
    });
    consoleNode.append(ladder);

    const summary = document.createElement("div");
    summary.className = "revision-summary-grid";
    const active = entries.filter((entry) => entry.status === "ACTIVE").length;
    const failed = entries.filter((entry) => entry.status === "FAILED").length;
    const mastered = entries.filter((entry) => entry.status === "MASTERED").length;
    const nextDates = entries.filter((entry) => entry.nextDue).slice(0, 3);
    summary.innerHTML = `
      <article class="revision-stat"><span>Active</span><strong>${active}</strong><small>normal recall queue</small></article>
      <article class="revision-stat"><span>Failed</span><strong>${failed}</strong><small>retry tomorrow policy</small></article>
      <article class="revision-stat"><span>Mastered</span><strong>${mastered}</strong><small>maintenance only</small></article>
      <article class="revision-stat wide"><span>Next dates</span><strong>${nextDates.map((entry) => entry.nextDue).join(" · ") || "None"}</strong><small>${nextDates.map((entry) => entry.problem.id).join(", ") || "No upcoming active revisions"}</small></article>
    `;
    consoleNode.append(summary);
    wrap.append(consoleNode);
  }

  function renderRevisionCalendar() {
    const target = $("#revision-calendar");
    target.replaceChildren();
    const upcoming = getRevisionEntries()
      .filter((entry) => entry.nextDue && entry.status !== "MASTERED")
      .slice(0, 10);
    if (!upcoming.length) {
      target.append(empty("No scheduled active revisions."));
      return;
    }
    upcoming.forEach((entry) => {
      const item = document.createElement("div");
      item.className = "timeline-item";
      const tone = entry.status === "FAILED" ? "bad" : entry.daysUntil <= 0 ? "warn" : "";
      item.innerHTML = `
        <div>
          <span class="pill ${tone}">${entry.nextDue}</span>
        </div>
        <div>
          <strong>${entry.problem.id} - ${entry.problem.title}</strong>
          <p>${stageLabel(entry.stage)} · ${entry.status} · ${entry.daysUntil <= 0 ? "due now" : `${entry.daysUntil} days left`}</p>
        </div>
      `;
      item.addEventListener("click", () => openProblemModal(entry.problem.id));
      item.tabIndex = 0;
      target.append(item);
    });
  }

  function openRevisionListModal(title, entries) {
    const body = setModal(title, `${entries.length} revision item${entries.length === 1 ? "" : "s"}`, "Revision details");
    if (!entries.length) {
      body.append(empty("No problems in this revision bucket."));
      showModal();
      return;
    }
    const list = document.createElement("div");
    list.className = "problem-chip-list";
    entries.forEach((entry) => {
      const item = document.createElement("button");
      item.className = "problem-chip";
      item.type = "button";
      item.innerHTML = `
        <strong>${entry.problem.id}</strong>
        <span>${entry.problem.title}</span>
        <small>${entry.status} · ${stageLabel(entry.stage)} · ${entry.nextDue || "maintenance"}</small>
      `;
      item.addEventListener("click", () => openProblemModal(entry.problem.id));
      list.append(item);
    });
    body.append(list);
    showModal();
  }

  function renderSkills() {
    const target = $("#skill-grid");
    target.replaceChildren();
    const { progress, stages } = state.datasets;
    const { query, stage: selectedStage } = currentFilters();
    const stageSkills = selectedStage
      ? stages.stages[selectedStage]?.skills || []
      : Object.keys(progress.skill_progress || {});
    const visibleSkills = stageSkills.filter((skillId) => skillMatchesQuery(skillId, query));

    if (!visibleSkills.length) {
      target.append(empty("No skills match the current filters."));
      return;
    }

    const summaries = visibleSkills.map((skillId) => skillSummary(skillId));
    const mastered = summaries.filter((item) => item.mastered);
    const inProgress = summaries.filter((item) => !item.mastered && item.solved > 0);
    const untouched = summaries.filter((item) => !item.mastered && item.solved === 0);
    const recommended = recommendedSkillSummary(summaries, [...inProgress, ...untouched]);

    const workbench = document.createElement("div");
    workbench.className = "skill-workbench";
    workbench.innerHTML = `
      <div class="skill-summary-strip">
        ${skillSummaryStat("Visible skills", visibleSkills.length, selectedStage || "all stages")}
        ${skillSummaryStat("Mastered", mastered.length, `${Math.round((mastered.length / visibleSkills.length) * 100)}% complete`)}
        ${skillSummaryStat("In progress", inProgress.length, "already started")}
        ${skillSummaryStat("Not started", untouched.length, "future coverage")}
      </div>
    `;

    if (recommended) {
      const spotlight = buildSkillSpotlight(recommended);
      workbench.append(spotlight);
    }

    const lanes = document.createElement("div");
    lanes.className = "skill-lanes";
    lanes.append(buildSkillLane("Continue next", inProgress, "Skills where some related problems are already solved."));
    lanes.append(
      buildSkillLane("Start later", untouched, "Skills still waiting for the first problem.", {
        order: "curriculum",
      }),
    );
    lanes.append(buildSkillLane("Already mastered", mastered, "Skills marked as mastered in progress tracking."));
    workbench.append(lanes);
    target.append(workbench);
  }

  function skillSummaryStat(label, value, note) {
    return `
      <article class="skill-stat">
        <span>${label}</span>
        <strong>${value}</strong>
        <small>${note}</small>
      </article>
    `;
  }

  function recommendedSkillSummary(allSummaries, openSummaries) {
    const currentProblemId = state.datasets.progress.current_problem;
    const currentProblem = currentProblemId ? state.problemsById.get(currentProblemId) : null;
    if (currentProblem) {
      const currentSkill = allSummaries.find((summary) => summary.id === currentProblem.primary_skill);
      if (currentSkill) return currentSkill;
    }
    const orderMap = skillCurriculumOrder();
    return [...openSummaries].sort((a, b) => {
      const byOrder = (orderMap.get(a.id) ?? 9999) - (orderMap.get(b.id) ?? 9999);
      if (byOrder !== 0) return byOrder;
      return b.progress - a.progress || a.name.localeCompare(b.name);
    })[0];
  }

  function skillSummary(skillId) {
    const skillInfo = skillMeta(skillId);
    const skill = state.datasets.progress.skill_progress?.[skillId] || {};
    const problems = state.datasets.curriculum.problems.filter(
      (problem) => problem.primary_skill === skillId,
    );
    const solvedProblems = problems.filter((problem) => state.completedById.has(problem.id));
    const nextOpen = problems.find((problem) => !state.completedById.has(problem.id));
    const total = problems.length;
    const solved = solvedProblems.length;
    return {
      id: skillId,
      name: skillInfo.name || skillId,
      description: skillInfo.description || "No skill description recorded.",
      mastered: Boolean(skill.mastered),
      primarySolved: Boolean(skill.primary_solved),
      reinforcementAttempted: Boolean(skill.reinforcement_attempted),
      score: skill.primary_weighted_score ?? "-",
      total,
      solved,
      progress: total ? solved / total : 0,
      nextOpen,
    };
  }

  function buildSkillSpotlight(summary) {
    const card = document.createElement("article");
    card.className = "skill-spotlight";
    card.innerHTML = `
      <div>
        <p class="eyebrow">Recommended focus</p>
        <h4>${summary.name}</h4>
        <p>${summary.description}</p>
      </div>
      <div class="skill-spotlight-side">
        <strong>${summary.solved}/${summary.total}</strong>
        <span>problems completed</span>
        <div class="progress-track"><span style="width: ${Math.round(summary.progress * 100)}%"></span></div>
      </div>
    `;
    const button = document.createElement("button");
    button.className = "stage-skill-open";
    button.type = "button";
    button.textContent = summary.nextOpen
      ? `Open ${summary.nextOpen.id}: ${summary.nextOpen.title}`
      : "View problems and learnings";
    button.addEventListener("click", () => openSingleSkillModal(summary.id));
    card.append(button);
    return card;
  }

  function buildSkillLane(title, summaries, subtitle, options = {}) {
    const lane = document.createElement("section");
    lane.className = "skill-lane";
    const orderMap = skillCurriculumOrder();
    const sorted = [...summaries].sort((a, b) => {
      if (options.order === "curriculum") {
        return (orderMap.get(a.id) ?? 9999) - (orderMap.get(b.id) ?? 9999);
      }
      return b.progress - a.progress || a.name.localeCompare(b.name);
    });
    lane.innerHTML = `
      <div class="section-head">
        <div>
          <h4>${title}</h4>
          <p>${subtitle}</p>
        </div>
        <span class="pill">${summaries.length}</span>
      </div>
    `;
    const list = document.createElement("div");
    list.className = "skill-row-list";
    sorted.slice(0, 5).forEach((summary) => list.append(buildSkillCompactRow(summary)));
    if (!summaries.length) {
      list.append(empty("No skills in this lane for the current filters."));
    }
    lane.append(list);
    if (sorted.length > 5) {
      const button = document.createElement("button");
      button.className = "stage-skill-open";
      button.type = "button";
      button.textContent = `View all ${sorted.length} skills`;
      button.addEventListener("click", () => openSkillLaneModal(title, sorted, subtitle));
      lane.append(button);
    }
    return lane;
  }

  function openSkillLaneModal(title, summaries, subtitle) {
    const body = setModal(title, `${summaries.length} skills`, "Skill lane");
    const intro = document.createElement("div");
    intro.className = "modal-intro";
    intro.innerHTML = `<p>${subtitle}</p>`;
    const list = document.createElement("div");
    list.className = "skill-row-list";
    summaries.forEach((summary) => list.append(buildSkillCompactRow(summary)));
    body.append(intro, list);
    showModal();
  }

  function skillCurriculumOrder() {
    const { stages } = state.datasets;
    const order = new Map();
    stages.stage_order.forEach((stageName) => {
      (stages.stages[stageName]?.skills || []).forEach((skillId) => {
        if (!order.has(skillId)) {
          order.set(skillId, order.size);
        }
      });
    });
    return order;
  }

  function buildSkillCompactRow(summary) {
    const row = document.createElement("button");
    row.className = "skill-compact-row";
    row.type = "button";
    row.innerHTML = `
      <div>
        <strong>${summary.name}</strong>
        <span>${summary.id}</span>
      </div>
      <div class="skill-row-progress">
        <span>${summary.solved}/${summary.total} problems</span>
        <div class="progress-track"><span style="width: ${Math.round(summary.progress * 100)}%"></span></div>
      </div>
      <div class="skill-row-next">
        <span>${summary.nextOpen ? `Next ${summary.nextOpen.id}` : "Coverage complete"}</span>
        <small>${summary.mastered ? "mastered" : "learning"} · score ${summary.score}</small>
      </div>
    `;
    row.addEventListener("click", () => openSingleSkillModal(summary.id));
    return row;
  }

  function renderPatterns() {
    const target = $("#pattern-grid");
    target.replaceChildren();
    const { query, stage: selectedStage } = currentFilters();
    const visiblePatterns = patternEntries().filter((pattern) => {
      if (!patternMatchesQuery(pattern, query)) return false;
      if (!selectedStage) return true;
      return (pattern.appears_in || []).some(
        (problemId) => state.problemsById.get(problemId)?.stage === selectedStage,
      );
    });

    if (!visiblePatterns.length) {
      target.append(empty("No patterns match the current filters."));
      return;
    }

    const workbench = document.createElement("div");
    workbench.className = "skill-workbench";
    const solvedPatternCount = visiblePatterns.filter((pattern) =>
      (pattern.appears_in || []).some((problemId) => state.completedById.has(problemId)),
    ).length;
    workbench.innerHTML = `
      <div class="skill-summary-strip">
        ${skillSummaryStat("Visible patterns", visiblePatterns.length, selectedStage || "all stages")}
        ${skillSummaryStat("Seen in solved work", solvedPatternCount, "linked to completed problems")}
        ${skillSummaryStat("Knowledge layer", "stable", "not learner state")}
        ${skillSummaryStat("Scheduler impact", "none", "mentor context only")}
      </div>
    `;

    const guide = document.createElement("article");
    guide.className = "pattern-transfer-guide";
    guide.innerHTML = `
      <div>
        <p class="eyebrow">How to use this section</p>
        <h4>Pattern transfer workflow</h4>
        <p>Scan for the trigger first. If the state and trap also match, open the pattern and map it to the current problem.</p>
      </div>
      <ol>
        <li><strong>Trigger</strong><span>What problem signal appears?</span></li>
        <li><strong>State</strong><span>What must be remembered?</span></li>
        <li><strong>Proof</strong><span>What stays true?</span></li>
        <li><strong>Trap</strong><span>What mistake looks tempting?</span></li>
      </ol>
    `;
    workbench.append(guide);

    const lanes = document.createElement("div");
    lanes.className = "skill-lanes pattern-lanes";
    const byFamily = new Map();
    visiblePatterns.forEach((pattern) => {
      const family = pattern.idea_family || "Other";
      if (!byFamily.has(family)) byFamily.set(family, []);
      byFamily.get(family).push(pattern);
    });
    [...byFamily.entries()].forEach(([family, patterns]) => {
      const lane = document.createElement("section");
      lane.className = "skill-lane";
      lane.innerHTML = `
        <div class="section-head">
          <div>
            <h4>${family}</h4>
            <p>${patternFamilyGuide(family)}</p>
          </div>
          <span class="pill">${patterns.length}</span>
        </div>
      `;
      const list = document.createElement("div");
      list.className = "skill-row-list";
      patterns.forEach((pattern) => list.append(buildPatternCompactRow(pattern)));
      lane.append(list);
      lanes.append(lane);
    });
    workbench.append(lanes);
    target.append(workbench);
  }

  function buildPatternCompactRow(pattern) {
    const row = document.createElement("button");
    row.className = "pattern-transfer-row";
    row.type = "button";
    const solved = (pattern.appears_in || []).filter((problemId) => state.completedById.has(problemId));
    const linkedTotal = (pattern.appears_in || []).length;
    const cues = patternQuickCues(pattern);
    row.innerHTML = `
      <div class="pattern-row-title">
        <span class="pill">${pattern.id}</span>
        <strong>${pattern.name}</strong>
        <small>${pattern.idea_family || "Conceptual pattern"}</small>
      </div>
      <div class="pattern-row-cues">
        <div><span>Trigger</span><strong>${cues.trigger}</strong></div>
        <div><span>State</span><strong>${cues.state}</strong></div>
        <div><span>Trap</span><strong>${cues.trap}</strong></div>
      </div>
      <div class="pattern-row-footer">
        <span>${solved.length}/${linkedTotal} solved examples</span>
        <div class="progress-track"><span style="width: ${linkedTotal ? Math.round((solved.length / linkedTotal) * 100) : 0}%"></span></div>
        <small>Open transfer guide</small>
      </div>
    `;
    row.addEventListener("click", () => openPatternModal(pattern.id));
    return row;
  }

  function patternQuickCues(pattern) {
    // Derived from patterns.json fields so PAT-010+ works without code edits.
    return {
      trigger: shortCue((pattern.recognition_signals || [])[0], "Open details"),
      state: shortCue(pattern.core_invariant || patternDecisionCue(pattern), "Maintained state"),
      trap: shortCue((pattern.common_mistakes || [])[0], "Wrong mental model"),
    };
  }

  function shortCue(value, fallback) {
    if (!value) return fallback;
    const text = String(value).replace(/\s+/g, " ").trim();
    if (text.length <= 42) return text;
    return `${text.slice(0, 39).trim()}...`;
  }

  function patternFamilyGuide(family) {
    const guides = {
      "Maintaining stable truth": "Invariant-first problems.",
      "Tracking extremes": "Best/worst state problems.",
      "Accumulating prefix information": "Best past value problems.",
      "Local optimality": "Sum independent local wins.",
      "Growing a region": "Expandable reach/coverage.",
      "Discarding impossible candidates": "Failure eliminates ranges.",
      "Constraint propagation": "Multiple constraints must merge.",
      "State construction": "Repeated lookup question.",
    };
    return guides[family] || "Reusable recognition models, not algorithm labels.";
  }

  function patternDecisionCue(pattern) {
    const name = (pattern.name || "").toLowerCase();
    if (name.includes("query")) return "Name the repeated question, then store the minimal answer state.";
    if (name.includes("candidate")) return "Track the current hypothesis separately from the scan pointer.";
    if (name.includes("frontier")) return "Maintain the farthest useful boundary seen so far.";
    if (name.includes("constraint")) return "Satisfy each independent constraint, then merge requirements.";
    if (name.includes("extremum") || name.includes("prefix")) return "Keep only the historical extreme that can improve future choices.";
    if (name.includes("competing")) return "Preserve both states when one operation can flip their roles.";
    if (name.includes("invariant")) return "Define the state meaning first, then derive updates from it.";
    return pattern.core_invariant || pattern.mental_model || "Open to inspect the maintained state.";
  }

  function simplePatternLabel(pattern) {
    return pattern.name || pattern.id;
  }

  function simplePatternHint(pattern) {
    return shortCue(
      pattern.core_invariant || (pattern.recognition_signals || [])[0],
      pattern.idea_family || "Related thinking model",
    );
  }

  function openPatternModal(patternId) {
    const pattern = state.patternsById.get(patternId);
    if (!pattern) return;
    const body = setModal(
      pattern.name,
      `${pattern.id} · ${pattern.idea_family || "Knowledge layer"}`,
      "Pattern detail",
    );
    const intro = document.createElement("div");
    intro.className = "modal-intro";
    intro.innerHTML = `
      <p>${pattern.mental_model || "No mental model recorded."}</p>
      <div class="meta-row">
        <span class="pill">knowledge layer</span>
        <span class="pill">${(pattern.appears_in || []).length} problems</span>
        <span class="pill">${(pattern.skills || []).length} skills</span>
      </div>
    `;
    body.append(intro);

    body.append(
      detailCard("Developer transfer guide", [
        ["Recognize when", ((pattern.recognition_signals || [])[0]) || "-"],
        ["Maintain", patternDecisionCue(pattern)],
        ["Prove with", pattern.core_invariant || "-"],
        ["Avoid confusing with", (pattern.contrast_with || []).join(", ") || "-"],
      ]),
      detailListCard("More recognition signals", (pattern.recognition_signals || []).slice(1)),
      detailCard("Reasoning", [
        ["Core invariant", pattern.core_invariant || "-"],
        ["Proof idea", pattern.proof_idea || "-"],
        ["Complexity reasoning", pattern.complexity_reasoning || "-"],
      ]),
      detailListCard("Contrast with", pattern.contrast_with || []),
      detailListCard("Common mistakes", pattern.common_mistakes || []),
      buildProblemGroup(
        "Appears in",
        (pattern.appears_in || [])
          .map((problemId) => state.problemsById.get(problemId))
          .filter(Boolean),
        "",
      ),
    );

    const skillsCard = document.createElement("article");
    skillsCard.className = "note-card";
    skillsCard.innerHTML = `<h4>Linked skills</h4>`;
    const skillButtons = document.createElement("div");
    skillButtons.className = "problem-chip-list";
    (pattern.skills || []).forEach((skillId) => {
      const button = document.createElement("button");
      button.className = "problem-chip";
      button.type = "button";
      button.innerHTML = `
        <strong>${skillTitle(skillId)}</strong>
        <span>${skillId}</span>
        <small>${skillMeta(skillId).description || ""}</small>
      `;
      button.addEventListener("click", () => openSingleSkillModal(skillId));
      skillButtons.append(button);
    });
    skillsCard.append(skillButtons);
    body.append(skillsCard);

    const related = (pattern.related_patterns || [])
      .map((relatedId) => state.patternsById.get(relatedId))
      .filter(Boolean);
    if (related.length) {
      body.append(patternListCard("Related patterns", related));
    }
    showModal();
  }

  function patternListCard(title, patterns) {
    const card = document.createElement("article");
    card.className = "note-card";
    card.innerHTML = `<h4>${title}</h4>`;
    const list = document.createElement("div");
    list.className = "problem-chip-list";
    patterns.forEach((pattern) => {
      const button = document.createElement("button");
      button.className = "problem-chip";
      button.type = "button";
      button.innerHTML = `
        <strong>${simplePatternLabel(pattern)}</strong>
        <span>${pattern.id} · ${pattern.name}</span>
        <small>${simplePatternHint(pattern)}</small>
      `;
      button.addEventListener("click", () => openPatternModal(pattern.id));
      list.append(button);
    });
    card.append(list);
    return card;
  }

  function problemStatus(problem) {
    const record = state.completedById.get(problem.id);
    if (!record) return "not_started";
    const status = record.revision?.status;
    if (status === "FAILED") return "failed";
    if (status === "MASTERED") return "mastered";
    return "active";
  }

  function currentFilters() {
    return {
      query: $("#search").value.trim().toLowerCase(),
      stage: $("#stage-filter").value,
      status: $("#status-filter").value,
    };
  }

  function problemMatchesQuery(problem, query) {
    if (!query) return true;
    const record = state.completedById.get(problem.id);
    const lesson = state.datasets.progress.lessons_learned?.[problem.id] || {};
    const deferredForProblem = deferredLearningEntries().filter(
      (entry) => entry.origin_problem === problem.id || entry.resolved_by_problem === problem.id,
    );
    const problemPatterns = patternsForProblem(problem.id);
    const haystack = [
      problem.id,
      problem.title,
      problem.stage,
      problem.primary_skill,
      skillMeta(problem.primary_skill).name,
      problem.difficulty,
      problem.problem_role,
      problem.importance,
      problem.notes,
      record?.thinking_breakthrough,
      record?.main_mistake,
      lesson.core_mental_model,
      lesson.primary_invariant,
      lesson.implementation_lesson,
      lesson.interview_takeaway,
      ...deferredForProblem.flatMap((entry) => [
        entry.id,
        entry.category,
        entry.description,
        entry.evidence,
      ]),
      ...problemPatterns.flatMap((pattern) => [
        pattern.id,
        pattern.name,
        pattern.idea_family,
        pattern.mental_model,
        pattern.core_invariant,
      ]),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  }

  function skillMatchesQuery(skillId, query) {
    if (!query) return true;
    if (skillId.toLowerCase().includes(query)) return true;
    const skill = skillMeta(skillId);
    if (`${skill.name || ""} ${skill.description || ""}`.toLowerCase().includes(query)) {
      return true;
    }
    if (patternsForSkill(skillId).some((pattern) => patternMatchesQuery(pattern, query))) {
      return true;
    }
    return state.datasets.curriculum.problems
      .filter((problem) => problem.primary_skill === skillId)
      .some((problem) => problemMatchesQuery(problem, query));
  }

  function stageMatchesQuery(stageName, query) {
    if (!query) return true;
    const details = state.datasets.stages.stages[stageName] || {};
    const stageText = [
      stageName,
      details.goal,
      ...(details.entry_requirements || []),
      ...(details.exit_requirements || []),
      ...(details.mastery_criteria || []),
      ...(details.common_failure_modes || []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    if (stageText.includes(query)) return true;
    return (details.skills || []).some((skillId) => skillMatchesQuery(skillId, query));
  }

  function problemMatchesStatus(problem, status) {
    if (!status) return true;
    const record = state.completedById.get(problem.id);
    if (status === "completed") return Boolean(record);
    return problemStatus(problem) === status;
  }

  function problemMatchesStrictQuery(problem, query) {
    if (!query) return true;
    const record = state.completedById.get(problem.id);
    const lesson = state.datasets.progress.lessons_learned?.[problem.id] || {};
    const haystack = [
      problem.id,
      problem.title,
      problem.stage,
      problem.primary_skill,
      skillMeta(problem.primary_skill).name,
      problem.difficulty,
      problem.problem_role,
      record?.thinking_breakthrough,
      record?.main_mistake,
      lesson.core_mental_model,
      lesson.primary_invariant,
      lesson.implementation_lesson,
      lesson.interview_takeaway,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  }

  function applyFilters() {
    const { query, stage, status } = currentFilters();
    state.filteredProblems = state.datasets.curriculum.problems.filter((problem) => {
      return (
        problemMatchesQuery(problem, query) &&
        (!stage || problem.stage === stage) &&
        problemMatchesStatus(problem, status)
      );
    });
    renderStages();
    renderWeaknessLab();
    renderDeferredLearnings();
    renderProblemTable();
    renderSkills();
    renderPatterns();
    renderThinkingProfile();
    renderLearningNotes();
  }

  function renderProblemTable() {
    const body = $("#problem-table");
    body.replaceChildren();
    const currentProblem = state.datasets.progress.current_problem;
    const { query } = currentFilters();
    const visibleProblems = query
      ? strictHistoryProblems(query) || state.filteredProblems
      : state.filteredProblems;
    const rows = visibleProblems
      .filter((problem) => state.completedById.has(problem.id) || problem.id === currentProblem)
      .slice(0, 120);
    if (!rows.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="8">No completed/current problems match the current filters.</td>`;
      body.append(tr);
      return;
    }
    rows.forEach((problem) => {
      const record = state.completedById.get(problem.id);
      const revision = record?.revision || {};
      const tr = document.createElement("tr");
      const revisionText = record
        ? `${revision.status || "-"} · stage ${revision.stage ?? 0} · ${revision.next_due || "no due"}`
        : "not completed";
      tr.innerHTML = `
        <td><strong>${problem.id}</strong><br /><span class="small-muted">${problem.title}</span></td>
        <td>${problem.stage}</td>
        <td><strong>${skillTitle(problem.primary_skill)}</strong><br /><span class="small-muted">${problem.primary_skill}</span></td>
        <td>${record?.completed_at || "-"}</td>
        <td>${revisionText}</td>
        <td>${record ? `${record.confidence_before} -> ${record.confidence_after}` : "-"}</td>
        <td>${record?.hint_level_used ?? "-"}</td>
        <td>${record?.thinking_breakthrough || problem.notes || "-"}</td>
      `;
      tr.addEventListener("click", () => openProblemModal(problem.id));
      tr.tabIndex = 0;
      tr.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openProblemModal(problem.id);
        }
      });
      body.append(tr);
    });
  }

  function strictHistoryProblems(query) {
    const matches = state.filteredProblems.filter((problem) =>
      problemMatchesStrictQuery(problem, query),
    );
    return matches.length ? matches : null;
  }

  function openProblemModal(problemId) {
    const problem = state.problemsById.get(problemId);
    if (!problem) return;
    const record = state.completedById.get(problemId);
    const revision = record?.revision || {};
    const lesson = state.datasets.progress.lessons_learned?.[problemId];
    const deferredForProblem = deferredLearningEntries().filter(
      (entry) => entry.origin_problem === problemId || entry.resolved_by_problem === problemId,
    );
    const problemPatterns = patternsForProblem(problemId);
    const body = setModal(
      `${problem.id} - ${problem.title}`,
      `${problem.stage} · ${skillLabel(problem.primary_skill)} · ${problem.difficulty}${problem.lc_id ? ` · LC ${problem.lc_id}` : problem.original_number ? ` · #${problem.original_number} (source index)` : ""}`,
      "Problem detail",
    );

    const overview = document.createElement("div");
    overview.className = "modal-intro";
    overview.innerHTML = `
      <p>${problem.notes || "No problem note recorded."}</p>
      <div class="meta-row">
        <span class="pill ${record ? "good" : ""}">${record ? "completed" : "not started"}</span>
        <span class="pill">${problem.problem_role || "role"}</span>
        <span class="pill">${problem.importance || "importance"}</span>
        <span class="pill">revision ${revision.status || "not active"}</span>
      </div>
    `;
    body.append(overview);

    const grid = document.createElement("div");
    grid.className = "detail-grid";
    grid.append(
      detailCard(
        "Progress",
        [
          ["Completed", record?.completed_at || "Not yet"],
          ["Confidence", record ? `${record.confidence_before} -> ${record.confidence_after}` : "-"],
          ["Algorithm Thinking", record?.algorithm_thinking_score != null ? `${record.algorithm_thinking_score} / 10` : "-"],
          ["Implementation Engineering", record?.implementation_engineering_score != null ? `${record.implementation_engineering_score} / 10` : "-"],
          ["Hint level", record?.hint_level_used ?? "-"],
          ["Time", record?.time_taken_minutes ? `${record.time_taken_minutes} min` : "-"],
        ],
      ),
      detailCard(
        "Revision",
        [
          ["Status", revision.status || "-"],
          ["Stage", revision.stage ?? "-"],
          ["Next due", revision.next_due || "-"],
          ["Passes", Array.isArray(revision.completed) ? revision.completed.join(", ") || "None" : "None"],
        ],
      ),
      detailCard(
        "Learning signal",
        [
          ["Breakthrough", record?.thinking_breakthrough || "-"],
          ["Mistake", record?.main_mistake || "-"],
        ],
      ),
    );
    body.append(grid);

    if (lesson) {
      const lessonCard = document.createElement("article");
      lessonCard.className = "note-card";
      lessonCard.innerHTML = `
        <h4>Permanent learning note</h4>
        <ul>
          ${Object.entries(lesson)
            .filter(([, value]) => typeof value === "string")
            .map(([key, value]) => `<li><strong>${key.replaceAll("_", " ")}:</strong> ${value}</li>`)
            .join("")}
        </ul>
      `;
      body.append(lessonCard);
    }

    if (record?.session_summary) {
      body.append(detailObjectCard("Session summary", record.session_summary));
    }
    if (record?.variable_semantics) {
      body.append(detailObjectCard("Variable semantics", record.variable_semantics));
    }
    if (Array.isArray(record?.conceptual_discoveries) && record.conceptual_discoveries.length) {
      body.append(detailListCard("Conceptual discoveries", record.conceptual_discoveries));
    }
    if (Array.isArray(record?.implementation_discoveries) && record.implementation_discoveries.length) {
      body.append(detailListCard("Implementation discoveries", record.implementation_discoveries));
    }
    if (record?.revision_material) {
      const revisionMaterial = document.createElement("article");
      revisionMaterial.className = "note-card";
      revisionMaterial.innerHTML = `
        <h4>Revision material</h4>
        <p>${record.revision_material.focus || "Verify reasoning before syntax."}</p>
        <ul>
          ${(record.revision_material.questions || [])
            .map((question) => `<li>${question}</li>`)
            .join("")}
        </ul>
      `;
      body.append(revisionMaterial);
    }

    if (deferredForProblem.length) {
      const deferredCard = document.createElement("article");
      deferredCard.className = "note-card";
      deferredCard.innerHTML = `
        <h4>Deferred learnings</h4>
        <ul>
          ${deferredForProblem
            .map(
              (entry) =>
                `<li><strong>${entry.id} · ${entry.status}:</strong> ${entry.description}${entry.evidence ? ` Evidence: ${entry.evidence}` : ""}</li>`,
            )
            .join("")}
        </ul>
      `;
      body.append(deferredCard);
    }

    if (problemPatterns.length) {
      body.append(patternListCard("Linked patterns", problemPatterns));
    }

    const history = revision.history || [];
    if (history.length) {
      const historyCard = document.createElement("article");
      historyCard.className = "note-card";
      historyCard.innerHTML = `
        <h4>Revision history</h4>
        <ul class="revision-history-list">
          ${history.map((event) => revisionHistoryItem(event)).join("")}
        </ul>
      `;
      body.append(historyCard);
    }

    appendDependencyCard(body, problem);
    showModal();
  }

  function revisionHistoryItem(event) {
    const recall = event.thinking_score && typeof event.thinking_score === "object"
      ? Object.entries(event.thinking_score)
          .filter(([, value]) => typeof value === "number")
          .map(([key, value]) => `${key.replaceAll("_", " ")} ${value}`)
          .join(" · ")
      : "";
    const details = [
      event.misconception_corrected
        ? `<p><strong>Misconception corrected:</strong> ${event.misconception_corrected}</p>`
        : "",
      event.notes ? `<p>${event.notes}</p>` : "",
      recall ? `<p class="small-muted">Recall: ${recall}</p>` : "",
    ].join("");
    return `
      <li>
        <strong>${event.date}</strong>: ${event.result} stage ${event.stage}
        · confidence ${event.confidence ?? "-"} · hint ${event.hint_level ?? "-"}
        ${details}
      </li>
    `;
  }

  function ensureDependencyGraph() {
    if (!state.graphPromise) {
      state.graphPromise = fetchJson("../curriculum/dependency_graph.json")
        .then((graph) => {
          const problemUnlocks = new Map();
          Object.entries(graph.problem_dependencies || {}).forEach(([problemId, deps]) => {
            (Array.isArray(deps) ? deps : []).forEach((dep) => {
              if (!problemUnlocks.has(dep)) problemUnlocks.set(dep, []);
              problemUnlocks.get(dep).push(problemId);
            });
          });
          const skillUnlocks = new Map();
          Object.entries(graph.skill_dependencies || {}).forEach(([skillId, deps]) => {
            (Array.isArray(deps) ? deps : []).forEach((dep) => {
              if (!skillUnlocks.has(dep)) skillUnlocks.set(dep, []);
              skillUnlocks.get(dep).push(skillId);
            });
          });
          state.reverseEdges = { problemUnlocks, skillUnlocks };
          return state.reverseEdges;
        })
        .catch(() => null);
    }
    return state.graphPromise;
  }

  function appendDependencyCard(body, problem) {
    const card = document.createElement("article");
    card.className = "note-card";
    body.append(card);
    ensureDependencyGraph().then((edges) => {
      if (!edges) {
        card.remove();
        return;
      }
      const unlockedProblems = edges.problemUnlocks.get(problem.id) || [];
      const unlockedSkills = edges.skillUnlocks.get(problem.primary_skill) || [];
      if (!unlockedProblems.length && !unlockedSkills.length) {
        card.remove();
        return;
      }
      const problemLine = unlockedProblems.length
        ? `<p><strong>Unlocks problems:</strong> ${unlockedProblems
            .map((id) => `${id}${state.problemsById.get(id) ? ` (${state.problemsById.get(id).title})` : ""}`)
            .join(", ")}</p>`
        : "";
      const skillLine = unlockedSkills.length
        ? `<p><strong>Its skill unlocks:</strong> ${unlockedSkills.map((id) => skillLabel(id)).join(", ")}</p>`
        : "";
      card.innerHTML = `<h4>Dependency context</h4>${problemLine}${skillLine}`;
    });
  }

  function detailObjectCard(title, values) {
    const card = document.createElement("article");
    card.className = "note-card";
    card.innerHTML = `
      <h4>${title}</h4>
      <ul>
        ${Object.entries(values)
          .map(([key, value]) => `<li><strong>${key.replaceAll("_", " ")}:</strong> ${value}</li>`)
          .join("")}
      </ul>
    `;
    return card;
  }

  function detailListCard(title, values) {
    const card = document.createElement("article");
    card.className = "note-card";
    card.innerHTML = `
      <h4>${title}</h4>
      <ul>${values.map((value) => `<li>${value}</li>`).join("")}</ul>
    `;
    return card;
  }

  function detailCard(title, rows) {
    const card = document.createElement("article");
    card.className = "note-card";
    const list = rows
      .map(([key, value]) => `<li><strong>${key}:</strong> ${value}</li>`)
      .join("");
    card.innerHTML = `<h4>${title}</h4><ul>${list}</ul>`;
    return card;
  }

  function renderThinkingProfile() {
    const profile = state.datasets.progress.thinking_profile || {};
    const target = $("#thinking-profile");
    target.replaceChildren();
    [
      ["Strengths", profile.strengths || [], "good"],
      ["Cautions", profile.gaps || [], "warn"],
      ["Common failures", profile.common_failures || [], "bad"],
    ].forEach(([title, items, tone]) => {
      const card = document.createElement("article");
      card.className = "note-card";
      card.append(pill(title, tone));
      const ul = document.createElement("ul");
      items.slice(-6).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        ul.append(li);
      });
      card.append(ul);
      target.append(card);
    });
  }

  function renderLearningNotes() {
    const target = $("#learning-notes");
    target.replaceChildren();
    const { query } = currentFilters();
    const lessons = state.datasets.progress.lessons_learned || {};
    const lessonEntries = Object.entries(lessons).filter(([, lesson]) => {
      if (!query) return true;
      return Object.values(lesson)
        .filter((value) => typeof value === "string")
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
    lessonEntries
      .slice(query ? 0 : -4)
      .forEach(([problemId, lesson]) => {
        const card = document.createElement("article");
        card.className = "note-card";
        card.innerHTML = `
          <h4>${problemId}</h4>
          <p>${lesson.major_breakthrough || lesson.implementation_lesson || lesson.interview_takeaway || lesson.core_mental_model || "No lesson text."}</p>
        `;
        target.append(card);
      });

    const mistakes = state.datasets.mistakes.entries || [];
    const visibleMistakes = mistakes.filter((mistake) => {
      if (!query) return true;
      return Object.values(mistake)
        .filter((value) => typeof value === "string")
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
    visibleMistakes.slice(query ? 0 : -4).forEach((mistake) => {
      const card = document.createElement("article");
      card.className = "note-card";
      card.innerHTML = `
        <h4>${mistake.id} · ${mistake.title}</h4>
        <p>${mistake.fix}</p>
      `;
      target.append(card);
    });
    if (!target.children.length) {
      target.append(empty("No learning notes match the current search."));
    }
  }

  function renderAnalytics() {
    const target = $("#analytics-grid");
    target.replaceChildren();
    const { progress, curriculum, stages, scoring } = state.datasets;
    const completed = [...state.completedById.values()];
    const skillProgress = progress.skill_progress || {};
    const skillEntries = Object.entries(skillProgress);
    const masteredSkills = skillEntries.filter(([, skill]) => skill.mastered);
    const startedSkills = skillEntries.filter(([, skill]) => skill.primary_solved || skill.reinforcement_attempted);
    const primarySolved = skillEntries.filter(([, skill]) => skill.primary_solved);
    const reinforcement = skillEntries.filter(([, skill]) => skill.reinforcement_attempted);
    const revisions = getRevisionEntries();
    const revisionEvents = completed.flatMap((record) => record.revision?.history || []);
    const revisionPasses = revisionEvents.filter((event) => event.result === "PASS").length;
    const revisionFailures = revisionEvents.filter((event) => event.result === "FAIL").length;
    const confidenceLift = avg(completed.map((record) => (record.confidence_after || 0) - (record.confidence_before || 0)));
    const hintAverage = avg(completed.map((record) => record.hint_level_used));
    const timeAverage = avg(completed.map((record) => record.time_taken_minutes));
    const activeRevisions = revisions.filter((entry) => entry.status === "ACTIVE").length;
    const dueNow = dueEntries().length;
    const openDeferred = openDeferredLearnings();
    const masteredTopics = masteredSkills
      .map(([skillId]) => skillTitle(skillId))
      .slice(0, 8);

    const shell = document.createElement("div");
    shell.className = "analytics-console";
    const header = document.createElement("div");
    header.className = "analytics-console-head";
    header.innerHTML = `
      <div>
        <p class="eyebrow">Analytics overview</p>
        <h4>Preparation health</h4>
      </div>
      <div class="analytics-tabs" role="tablist" aria-label="Analytics views">
        ${analyticsTab("acquisition", "Acquisition")}
        ${analyticsTab("retention", "Retention")}
        ${analyticsTab("performance", "Performance")}
        ${analyticsTab("risks", "Risks")}
      </div>
    `;
    const body = document.createElement("div");
    body.className = "analytics-layout";
    const cards = [
      [
        analyticsSkillCard("Skill achievement", [
        ["Started", startedSkills.length, skillEntries.length],
        ["Primary solved", primarySolved.length, skillEntries.length],
        ["Reinforced", reinforcement.length, skillEntries.length],
        ["Mastered", masteredSkills.length, skillEntries.length],
        ]),
        ["acquisition"],
      ],
      [
        analyticsListCard(
        "Mastered topics",
        masteredTopics.length
          ? masteredTopics
          : ["No mastered topics yet. Complete primary and reinforcement problems to unlock this list."],
        masteredTopics.length ? `${masteredTopics.length} shown` : "0 mastered",
        ),
        ["retention", "acquisition"],
      ],
      [analyticsPerformanceCard(scoring), ["performance"]],
      [analyticsScoreGraph(scoring), ["performance"]],
      [analyticsConsistencyLineChart(completed), ["performance"]],
      [analyticsRevisionCard(revisionPasses, revisionFailures, activeRevisions, dueNow), ["retention", "risks"]],
      [analyticsStageCoverageCard(stages), ["acquisition"]],
      [analyticsStageDistributionChart(stages), ["acquisition"]],
      [
        analyticsSignalCard("Preparation behavior", [
        ["Avg confidence lift", `${confidenceLift.toFixed(2)} / 10`],
        ["Avg hint level", `${hintAverage.toFixed(2)}`],
        ["Avg solve time", `${timeAverage.toFixed(0)} min`],
        ["Completed days", `${uniqueSolvedDays(completed).length}`],
        ]),
        ["performance"],
      ],
      [
        analyticsSignalCard("Deferred learning loop", [
        ["Open", openDeferred.length],
        ["Resolved", deferredLearningEntries().filter((entry) => entry.status === "RESOLVED").length],
        ["High priority", openDeferred.filter((entry) => entry.priority === "HIGH").length],
        ["Evidence linked", deferredLearningEntries().filter((entry) => entry.evidence).length],
        ]),
        ["retention", "risks"],
      ],
      [analyticsFocusCard(), ["risks"]],
    ];
    cards
      .filter(([, views]) => views.includes(state.analyticsView))
      .forEach(([card]) => body.append(card));
    shell.append(header, body);
    target.append(shell);
    target.querySelectorAll(".analytics-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        state.analyticsView = tab.dataset.view;
        renderAnalytics();
      });
    });
  }

  function analyticsTab(view, label) {
    return `
      <button class="analytics-tab ${state.analyticsView === view ? "active" : ""}" type="button" role="tab" aria-selected="${state.analyticsView === view ? "true" : "false"}" data-view="${view}">
        ${label}
      </button>
    `;
  }

  function analyticsSkillCard(title, rows) {
    const card = document.createElement("article");
    card.className = "analytics-card";
    card.innerHTML = `<h4>${title}</h4><div class="analytics-bars"></div>`;
    const bars = card.querySelector(".analytics-bars");
    rows.forEach(([label, value, total]) => {
      const percent = total ? Math.round((value / total) * 100) : 0;
      bars.append(analyticsBar(label, `${value}/${total}`, percent));
    });
    return card;
  }

  function analyticsPerformanceCard(scoring) {
    const averages = state.datasets.progress.scores?.averages || {};
    const thinkingMax = scoring.scale?.maximum || 4;
    const interviewMax = scoring.interview_scale?.maximum || 10;
    const completed = [...state.completedById.values()];
    const algorithmAvg = avg(completed.map((record) => record.algorithm_thinking_score));
    const implementationAvg = avg(completed.map((record) => record.implementation_engineering_score));
    const dimensions = [
      ["Algorithm Thinking", algorithmAvg || 0, 10],
      ["Implementation Eng", implementationAvg || 0, 10],
      ["Thinking", averages.thinking_weighted || 0, thinkingMax],
      ["Interview", averages.interview_average || 0, interviewMax],
      ["Confidence before", averages.confidence_before || 0, 10],
      ["Confidence after", averages.confidence_after || 0, 10],
    ];
    const card = document.createElement("article");
    card.className = "analytics-card";
    card.innerHTML = `<h4>Performance</h4><div class="analytics-bars"></div>`;
    const bars = card.querySelector(".analytics-bars");
    dimensions.forEach(([label, value, max]) => {
      bars.append(analyticsBar(label, `${Number(value).toFixed(2)} / ${max}`, max ? Math.round((value / max) * 100) : 0));
    });
    return card;
  }

  function analyticsRevisionCard(passes, failures, active, dueNow) {
    const total = passes + failures;
    const passRate = total ? Math.round((passes / total) * 100) : 0;
    const card = document.createElement("article");
    card.className = "analytics-card";
    card.innerHTML = `
      <h4>Revision impact</h4>
      <div class="analytics-kpi-grid">
        ${kpi("Pass rate", `${passRate}%`)}
        ${kpi("Passes", passes)}
        ${kpi("Failures", failures)}
        ${kpi("Active", active)}
      </div>
      <p>${dueNow ? `${dueNow} revision item${dueNow === 1 ? "" : "s"} need attention now.` : "No due revision pressure right now."}</p>
    `;
    return card;
  }

  function analyticsStageCoverageCard(stages) {
    const card = document.createElement("article");
    card.className = "analytics-card wide";
    card.innerHTML = `<h4>Stage coverage</h4><div class="stage-mini-bars"></div>`;
    const wrap = card.querySelector(".stage-mini-bars");
    stages.stage_order.forEach((stageName, index) => {
      const problems = state.datasets.curriculum.problems.filter((problem) => problem.stage === stageName);
      const solved = problems.filter((problem) => state.completedById.has(problem.id)).length;
      const percent = problems.length ? Math.round((solved / problems.length) * 100) : 0;
      wrap.append(analyticsBar(`${index + 1}. ${stageName}`, `${solved}/${problems.length}`, percent));
    });
    return card;
  }

  function analyticsStageDistributionChart(stages) {
    const card = document.createElement("article");
    card.className = "analytics-card wide";
    card.innerHTML = `<h4>Problem distribution by stage</h4><div class="column-chart"></div>`;
    const wrap = card.querySelector(".column-chart");
    const rows = stages.stage_order.map((stageName) => {
      const total = state.datasets.curriculum.problems.filter((problem) => problem.stage === stageName).length;
      const solved = state.datasets.curriculum.problems.filter(
        (problem) => problem.stage === stageName && state.completedById.has(problem.id),
      ).length;
      return { stageName, total, solved };
    });
    const maxTotal = Math.max(...rows.map((row) => row.total), 1);
    rows.forEach((row, index) => {
      const height = Math.max(6, Math.round((row.total / maxTotal) * 100));
      const solvedHeight = row.total ? Math.round((row.solved / row.total) * height) : 0;
      const bar = document.createElement("div");
      bar.className = "column-bar";
      bar.innerHTML = `
        <div class="column-track" style="--height:${height}%">
          <span style="--height:${solvedHeight}%"></span>
        </div>
        <strong>${index + 1}</strong>
        <small>${row.solved}/${row.total}</small>
      `;
      bar.title = row.stageName;
      wrap.append(bar);
    });
    return card;
  }

  function analyticsScoreGraph(scoring) {
    const dimensions = state.datasets.progress.scores?.averages?.thinking_dimensions || {};
    const max = scoring.scale?.maximum || 4;
    const card = document.createElement("article");
    card.className = "analytics-card wide";
    card.innerHTML = `<h4>Thinking dimension graph</h4><div class="radar-list"></div>`;
    const list = card.querySelector(".radar-list");
    Object.entries(dimensions).forEach(([label, value]) => {
      list.append(analyticsBar(label.replaceAll("_", " "), `${Number(value).toFixed(2)} / ${max}`, Math.round((value / max) * 100)));
    });
    return card;
  }

  function analyticsConsistencyLineChart(completed) {
    const timeline = cumulativeCompletionTimeline(completed);
    const card = document.createElement("article");
    card.className = "analytics-card wide";
    if (!timeline.length) {
      card.innerHTML = `
        <h4>Showing-up graph</h4>
        <p>Complete the first problem to start the consistency graph.</p>
      `;
      return card;
    }
    // Rolling last-30-days window (today-29 .. today), not the first 30 days.
    const xMaxDays = 29;
    const yMax = 100;
    const endDate = referenceDate();
    const startDate = addDays(endDate, -xMaxDays);
    const windowPoints = timeline.filter((point) => point.date >= startDate && point.date <= endDate);
    if (!windowPoints.length) {
      card.innerHTML = `
        <h4>Showing-up graph</h4>
        <p>No completions in the last 30 days. The cumulative count resumes with the next solve.</p>
      `;
      return card;
    }
    const problemPoints = linePoints(windowPoints, "problems", yMax, xMaxDays, startDate);
    const skillPoints = linePoints(windowPoints, "skills", yMax, xMaxDays, startDate);
    const last = windowPoints.at(-1);
    const midDate = addDays(startDate, Math.floor(xMaxDays / 2));
    card.innerHTML = `
      <div class="section-head">
        <div>
          <h4>Showing-up graph</h4>
          <p>X-axis is the rolling last-30-days window. Y-axis is a fixed 100-count target. Progress stays proportional to that perspective.</p>
        </div>
        <span class="pill good">${windowPoints.length} active day${windowPoints.length === 1 ? "" : "s"} in window</span>
      </div>
      <div class="line-chart-wrap">
        <span class="axis-title y">Cumulative count</span>
        <div class="line-y-axis">
          ${lineTicks(yMax).map((tick) => `<span>${tick}</span>`).join("")}
        </div>
        <div class="line-chart" role="img" aria-label="Cumulative completed problems and skills over time">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none">
            <polyline class="line-area problems" points="${problemPoints} 100,100 0,100" />
            <polyline class="line-stroke problems" points="${problemPoints}" />
            <polyline class="line-stroke skills" points="${skillPoints}" />
          </svg>
          <div class="line-axis">
            <span>${startDate}</span>
            <span>${midDate}</span>
            <span>${endDate}</span>
          </div>
        </div>
        <span class="axis-title x">Rolling 30-day study window</span>
      </div>
      <div class="chart-legend">
        ${legendItem("Problems completed", last.problems, "#1a73e8")}
        ${legendItem("Skills touched", last.skills, "#0f766e")}
        ${legendItem("Y-axis target", yMax, "#dfe8f0")}
      </div>
    `;
    return card;
  }

  function analyticsSignalCard(title, rows) {
    const card = document.createElement("article");
    card.className = "analytics-card";
    card.innerHTML = `
      <h4>${title}</h4>
      <div class="analytics-kpi-grid">
        ${rows.map(([label, value]) => kpi(label, value)).join("")}
      </div>
    `;
    return card;
  }

  function analyticsFocusCard() {
    const profile = state.datasets.progress.thinking_profile || {};
    const gaps = [...(profile.gaps || []), ...(profile.common_failures || [])].slice(-5);
    const card = document.createElement("article");
    card.className = "analytics-card";
    card.innerHTML = `
      <h4>Focus risks</h4>
      <ul>${(gaps.length ? gaps : ["No focus risks recorded yet."]).map((item) => `<li>${item}</li>`).join("")}</ul>
    `;
    return card;
  }

  function analyticsListCard(title, items, badge) {
    const card = document.createElement("article");
    card.className = "analytics-card";
    card.innerHTML = `
      <div class="section-head">
        <h4>${title}</h4>
        <span class="pill good">${badge}</span>
      </div>
      <ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>
    `;
    return card;
  }

  function analyticsBar(label, value, percent) {
    const row = document.createElement("div");
    row.className = "analytics-bar";
    row.innerHTML = `
      <div>
        <strong>${label}</strong>
        <span>${value}</span>
      </div>
      <div class="track"><div class="fill" style="--width:${clamp(percent, 0, 100)}%"></div></div>
    `;
    return row;
  }

  function kpi(label, value) {
    return `<div class="analytics-kpi"><span>${label}</span><strong>${value}</strong></div>`;
  }

  function uniqueSolvedDays(records) {
    return [...new Set(records.map((record) => record.completed_at).filter(Boolean))];
  }

  function cumulativeCompletionTimeline(records) {
    const byDate = new Map();
    records
      .filter((record) => record.completed_at)
      .sort((a, b) => a.completed_at.localeCompare(b.completed_at))
      .forEach((record) => {
        if (!byDate.has(record.completed_at)) byDate.set(record.completed_at, []);
        byDate.get(record.completed_at).push(record);
      });
    const skills = new Set();
    let problems = 0;
    return [...byDate.entries()].map(([date, dayRecords]) => {
      problems += dayRecords.length;
      dayRecords.forEach((record) => {
        const problem = state.problemsById.get(record.problem_id);
        if (problem?.primary_skill) skills.add(problem.primary_skill);
      });
      return { date, problems, skills: skills.size };
    });
  }

  function linePoints(points, key, maxValue, maxDays, startDate) {
    const start = parseDate(startDate || points[0].date);
    if (points.length === 1 && !startDate) {
      const y = 100 - (clamp(points[0][key], 0, maxValue) / maxValue) * 92;
      return `0,${y.toFixed(2)}`;
    }
    return points
      .map((point) => {
        const elapsedDays = Math.max(
          0,
          Math.round((parseDate(point.date) - start) / (24 * 60 * 60 * 1000)),
        );
        const x = clamp((elapsedDays / maxDays) * 100, 0, 100);
        const y = 100 - (clamp(point[key], 0, maxValue) / maxValue) * 92;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
  }

  function lineTicks(maxValue) {
    const top = Math.max(maxValue, 1);
    const mid = Math.round(top / 2);
    return [top, mid, 0];
  }

  function addDays(dateValue, days) {
    const date = parseDate(dateValue);
    date.setDate(date.getDate() + days);
    return isoDate(date);
  }

  function legendItem(label, value, color) {
    return `<span><i style="background:${color}"></i>${label}: ${value}</span>`;
  }

  function empty(message) {
    const div = document.createElement("div");
    div.className = "empty";
    div.textContent = message;
    return div;
  }

  function renderDataWarning() {
    const banner = $("#data-warning");
    const unresolved = unresolvedCompletions();
    if (!unresolved.length) {
      banner.hidden = true;
      return;
    }
    const ids = unresolved.map((record) => record.problem_id).join(", ");
    $("#data-warning-text").textContent =
      `${unresolved.length} completion${unresolved.length === 1 ? "" : "s"} reference unknown problem_id(s) (${ids}) and were excluded from revision views.`;
    banner.hidden = false;
  }

  function renderAll() {
    $("#last-updated").textContent = `Updated ${state.datasets.progress.last_updated}`;
    $("#reference-date-pill").textContent = `Reference date ${referenceDate()}`;
    renderDataWarning();
    renderOperatingBoard();
    renderMetrics();
    renderReadiness();
    renderNextAction();
    renderThinkingBars();
    renderWeaknessLab();
    renderDeferredLearnings();
    renderEdgeCases();
    renderStages();
    renderRevisionLanes();
    renderRevisionCalendar();
    renderSkills();
    renderPatterns();
    renderProblemTable();
    renderThinkingProfile();
    renderLearningNotes();
    renderAnalytics();
    switchWorkspace(state.activeWorkspace);
  }

  async function main() {
    try {
      await loadData();
      buildStageOptions();
      renderAll();
      $("#data-warning-dismiss").addEventListener("click", () => {
        $("#data-warning").hidden = true;
      });
      $("#search").addEventListener("input", debounce(applyFilters, 150));
      $("#stage-filter").addEventListener("change", applyFilters);
      $("#status-filter").addEventListener("change", applyFilters);
      document.querySelectorAll(".workspace-tab").forEach((tab) => {
        tab.addEventListener("click", () => switchWorkspace(tab.dataset.workspace));
      });
      document.querySelectorAll("[data-workspace-link]").forEach((link) => {
        link.addEventListener("click", (event) => {
          event.preventDefault();
          switchWorkspace(link.dataset.workspaceLink, link.getAttribute("href"));
        });
      });
      $("#modal-close").addEventListener("click", () => $("#skill-modal").close());
      $("#skill-modal").addEventListener("click", (event) => {
        if (event.target === $("#skill-modal")) {
          $("#skill-modal").close();
        }
      });
    } catch (error) {
      document.body.innerHTML = `<main class="main"><section class="panel"><h2>Dashboard load failed</h2><p>${error.message}</p><p>Run it through <code>make web-dashboard</code> so the JSON files can be fetched.</p></section></main>`;
      console.error(error);
    }
  }

  main();
})();
