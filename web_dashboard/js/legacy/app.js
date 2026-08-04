  import { fetchFeedStatus } from "../data.js";
  import { svgEl } from "../svg.js";

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
    // Computed view model from GET /api/feed (the Python brain). null when the
    // server is not running — the page then degrades to the static views.
    feed: null,
    feedStatus: null,
    frequency: null,
    problemsById: new Map(),
    completedById: new Map(),
    skillsById: new Map(),
    patternsById: new Map(),
    filteredProblems: [],
    activeWorkspace: "today",
    // The single section the rail highlights; kept in sync by the scroll spy.
    activeSection: "",
    // Set by the constellation on draw so the toolbar filters can dim its stars
    // without forcing a re-render (which would reset pan and zoom).
    constellationFilter: null,
    // Lazy-loaded on first problem-modal open; never in the critical Promise.all.
    graphPromise: null,
    reverseEdges: null,
  };

  const browserState = { selection: { kind: "all" }, search: "", difficulty: "", status: "", sort: "curriculum" };

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

  const FREQUENCY_TIERS = {
    very_high: { glyph: "★★★", label: "very high" },
    high: { glyph: "★★", label: "high" },
    medium: { glyph: "★", label: "medium" },
    low: { glyph: "·", label: "low" },
  };

  function frequencyFor(problem) {
    if (!state.frequency || !problem.url || !problem.url.includes("/problems/")) return null;
    const slug = problem.url.split("/problems/")[1].split("/")[0];
    return state.frequency.problems?.[slug] || null;
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

  const $ = (selector) => document.querySelector(selector);
  // Recomputed on every render (not frozen at page load): a session that
  // crosses midnight must not keep showing yesterday's reference date.
  function todayDate() {
    return new Date();
  }
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

  function text(value, fallback = "-") {
    return value === undefined || value === null || value === "" ? fallback : String(value);
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

  const WORKSPACE_META = {
    today: {
      eyebrow: "Today",
      title: "Mission briefing",
      subtitle: "What to do right now, and whether you are on trajectory for interviews.",
      toolbar: false,
    },
    plan: {
      eyebrow: "Plan",
      title: "Quarter plan",
      subtitle: "Weekly targets, month-end skill milestones, and the burn-up to the quarter goal.",
      toolbar: false,
    },
    problems: {
      eyebrow: "Problems",
      title: "Problem browser",
      subtitle: "Every curriculum problem, organized by stage and skill, with live status.",
      toolbar: false,
    },
    practice: {
      eyebrow: "Practice",
      title: "Weakness lab",
      subtitle: "Targeted drilling from recorded mistakes and the edge-case checklist.",
      toolbar: false,
    },
    curriculum: {
      eyebrow: "Curriculum",
      title: "Skill map",
      subtitle: "The prerequisite constellation, stage meters, skills, and patterns.",
      toolbar: true,
    },
    evidence: {
      eyebrow: "Evidence",
      title: "Learning evidence",
      subtitle: "History, thinking profile, hint independence, mock trend, retention.",
      toolbar: true,
    },
  };

  function switchWorkspace(workspace, targetHash = "") {
    const active = WORKSPACE_META[workspace] ? workspace : "today";
    state.activeWorkspace = active;
    renderWorkspace(active);
    document.querySelectorAll("[data-workspace-section]").forEach((section) => {
      section.hidden = section.dataset.workspaceSection !== active;
    });
    // Membership in the open workspace is a *quiet* state. Which single section
    // you are looking at is the loud one - see setActiveSection below.
    document.querySelectorAll("[data-workspace-link]").forEach((link) => {
      link.classList.toggle("in-workspace", link.dataset.workspaceLink === active);
    });

    const meta = WORKSPACE_META[active];
    const eyebrow = $("#workspace-eyebrow");
    const title = $("#workspace-title");
    const subtitle = $("#workspace-subtitle");
    if (eyebrow) eyebrow.textContent = meta.eyebrow;
    if (title) title.textContent = meta.title;
    if (subtitle) subtitle.textContent = meta.subtitle;
    // Several workspaces open on a section whose heading repeats the workspace
    // title verbatim ("Mission briefing" over "Mission briefing"). Suppress the
    // duplicate heading but keep its pill, which carries real data.
    document.querySelectorAll("[data-workspace-section] .section-head").forEach((head) => {
      const heading = head.querySelector("h3");
      const duplicate =
        Boolean(heading) && heading.textContent.trim().toLowerCase() === meta.title.toLowerCase();
      head.classList.toggle("is-duplicate-title", duplicate);
    });

    // Search + filters are contextual: only the list-bearing workspaces show them.
    const toolbar = $("#list-toolbar");
    if (toolbar) {
      toolbar.hidden = !meta.toolbar;
      toolbar.closest(".topbar")?.classList.toggle("topbar-has-toolbar", Boolean(meta.toolbar));
    }

    if (targetHash) {
      const target = document.querySelector(targetHash);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveSection(targetHash.slice(1));
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
      setActiveSection(firstSectionOf(active));
    }
  }

  // ---------------------------------------------------------------------------
  // Nav highlighting has two levels. Every link in the open workspace gets the
  // quiet `in-workspace` treatment; exactly one link - the section actually on
  // screen - gets `active`. Previously workspace membership set `active`, so all
  // five Curriculum links lit at once and the rail never told you where you were.
  // ---------------------------------------------------------------------------

  function navLinks() {
    return [...document.querySelectorAll(".nav-list a[data-workspace-link]")];
  }

  function firstSectionOf(workspace) {
    const link = navLinks().find((item) => item.dataset.workspaceLink === workspace);
    return link ? link.getAttribute("href").slice(1) : "";
  }

  function setActiveSection(sectionId) {
    if (!sectionId || sectionId === state.activeSection) return;
    state.activeSection = sectionId;
    navLinks().forEach((link) => {
      const isActive = link.getAttribute("href") === `#${sectionId}`;
      link.classList.toggle("active", isActive);
      if (isActive) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  }

  // Scroll spy: the active section is the last one whose top has passed under the
  // sticky topbar. Only sections that own a nav link are considered, so sections
  // nested inside another (revisions inside overview) never steal the highlight.
  function spyActiveSection() {
    const line = ($(".main .topbar")?.getBoundingClientRect().height || 0) + 24;
    let winner = "";
    navLinks().forEach((link) => {
      if (link.dataset.workspaceLink !== state.activeWorkspace) return;
      const section = document.querySelector(link.getAttribute("href"));
      if (!section || section.hidden) return;
      if (section.getBoundingClientRect().top <= line) winner = section.id;
    });
    // Scrolled above the first section: keep the workspace's first entry lit
    // rather than leaving the rail blank.
    setActiveSection(winner || firstSectionOf(state.activeWorkspace));
  }

  function watchActiveSection() {
    let queued = false;
    const onScroll = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        spyActiveSection();
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    onScroll();
  }

  // Theme: persisted choice wins, else the OS preference; dark is the design
  // default when neither says otherwise.
  function initTheme() {
    const stored = localStorage.getItem("theme");
    const prefersLight =
      window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    const theme = stored || (prefersLight ? "light" : "dark");
    document.documentElement.setAttribute("data-theme", theme);
  }

  function toggleTheme() {
    const current =
      document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  }

  async function fetchText(path) {
    if (window.location.protocol === "file:") {
      throw new Error("Local file mode cannot fetch dashboard data.");
    }
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
    state.feed = await fetchFeed();
    // Interview-frequency snapshot is optional: generated by
    // scripts/fetch_interview_frequency.py; absence degrades to "–".
    state.frequency = await fetchJson("../curriculum/interview_frequency.json").catch(() => null);
  }

  // The live briefing. Returns null (never throws) when the server is not
  // running or the feed errors, so the static views still render — but the
  // classified status lands in state.feedStatus for the banner.
  async function fetchFeed() {
    const result = await fetchFeedStatus();
    state.feedStatus = result;
    return result.feed;
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
    // Prefer the server feed's reference date so the UI and the CLI agree on
    // "today"; fall back to the local clock for the static/degraded view.
    if (state.feed && state.feed.reference_date) return state.feed.reference_date;
    const now = todayDate();
    const lastUpdated = parseDate(state.datasets.progress.last_updated);
    if (lastUpdated && lastUpdated > now) return isoDate(lastUpdated);
    return isoDate(now);
  }

  function unresolvedCompletions() {
    return [...state.completedById.values()].filter(
      (record) => !state.problemsById.has(record.problem_id),
    );
  }

  function deferredLearningEntries() {
    return Array.isArray(state.datasets.progress.deferred_learnings)
      ? state.datasets.progress.deferred_learnings
      : [];
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

  const FEED_REQUIRED_MESSAGE =
    "Live briefing needs the server — run `python3 scripts/serve_dashboard.py`";

  function feedAvailable() {
    return state.feed != null;
  }

  // Display adapter over feed.next_action (resolves the problem object by id).
  // Not a scheduler: the mode/reason/id are computed once, in Python.
  function feedNextAction() {
    if (!feedAvailable()) return null;
    const action = state.feed.next_action || {};
    return {
      mode: action.mode || "unknown",
      reason: action.reason || "",
      stageLabel: action.stage_label || null,
      codeGate: action.code_gate || null,
      problem: action.problem_id ? state.problemsById.get(action.problem_id) || null : null,
    };
  }

  function planBlock() {
    return feedAvailable() ? state.feed.plan : null;
  }

  // One string per non-renderable plan state; null when the plan is usable.
  function planStateMessage(plan) {
    if (!plan) return "No quarter plan. Author progress/plan.json to activate this view.";
    if (plan.error) return `Plan config error — ${plan.error}`;
    return null;
  }

  function degradedBanner(message = FEED_REQUIRED_MESSAGE) {
    const banner = document.createElement("div");
    banner.className = "degraded-banner";
    banner.setAttribute("role", "status");
    banner.textContent = message;
    return banner;
  }

  // The trajectory strip is the readiness visual; this renders the two pieces
  // of chrome around it. The per-gate rows it used to build went into a
  // permanently-hidden container — the strip's stations already say the same
  // thing, and its aria-label is the text equivalent.
  function renderReadiness() {
    const overall = $("#readiness-overall");
    const projection = $("#readiness-projection");

    if (!feedAvailable()) {
      if (overall) {
        overall.textContent = "Offline";
        overall.className = "pill warn";
      }
      if (projection) projection.textContent = "";
      return;
    }

    const readiness = state.feed.readiness || {};
    if (overall) {
      const gateValues = Object.values(readiness.gates || {});
      const metCount = gateValues.filter((gate) => gate && gate.met).length;
      overall.textContent = readiness.all_met
        ? "All gates met"
        : `${metCount} of ${gateValues.length} gates met`;
      overall.className = `pill ${readiness.all_met ? "good" : "warn"}`;
    }
    if (projection) {
      const pace = readiness.pace || {};
      projection.textContent =
        `Pace (trailing ${pace.window_days ?? 0}d): ${Number(pace.problems_per_week || 0).toFixed(2)} problems/week, ` +
        `${Number(pace.skills_per_week || 0).toFixed(2)} skills mastered/week. ${readiness.projection_message || ""}`;
    }
  }

  const REVISION_FAMILY = new Set(["revision", "reactivation", "quarterly_maintenance"]);
  const NEXT_MODE_LABEL = {
    revision: "REVISION",
    reactivation: "REACTIVATED",
    quarterly_maintenance: "Q-MAINT",
    mock_due: "MOCK",
    resume_current_problem: "SOLVE",
    current_skill: "SOLVE",
    current_stage: "SOLVE",
    earliest_unlocked: "SOLVE",
    complete: "COMPLETE",
  };

  function formatPct(value) {
    return `${((Number(value) || 0) * 100).toFixed(0)}%`;
  }

  function weekdayShort(isoDay) {
    const parsed = parseDate(isoDay);
    if (!parsed) return "";
    return ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"][parsed.getDay()];
  }

  function renderNextAction() {
    const wrap = $("#next-action");
    if (!wrap) return;
    const panel = wrap.closest(".briefing-next");
    if (panel) panel.classList.remove("is-mock");
    wrap.replaceChildren();
    const modeLabel = $("#selection-mode");

    if (!feedAvailable()) {
      if (modeLabel) modeLabel.textContent = "offline";
      wrap.append(degradedBanner());
      return;
    }

    const action = feedNextAction();
    const mode = action.mode;
    if (modeLabel) modeLabel.textContent = NEXT_MODE_LABEL[mode] || mode;

    if (!action.problem) {
      wrap.append(empty(action.reason || "No active problem — the unlocked curriculum is complete."));
      return;
    }

    const problem = action.problem;
    const title = document.createElement("h4");
    title.className = "problem-title";
    title.textContent = `${problem.id} · ${problem.title}`;

    const meta = document.createElement("div");
    meta.className = "meta-row";
    if (mode !== "mock_due") {
      meta.append(pill(problem.difficulty), pill(skillLabel(problem.primary_skill)));
    }
    if (action.stageLabel) meta.append(pill(action.stageLabel, "accent"));

    const reason = document.createElement("p");
    reason.className = "next-reason";
    reason.textContent = action.reason;

    wrap.append(title, meta, reason);

    if (mode === "mock_due") {
      if (panel) panel.classList.add("is-mock");
      const protocol = document.createElement("p");
      protocol.className = "next-protocol microlabel";
      protocol.textContent = "45-minute cap · no hints · verdict at the end";
      wrap.append(protocol);
    } else if (action.codeGate) {
      const gate = document.createElement("p");
      gate.className = "next-codegate microlabel";
      gate.textContent = action.codeGate.solution_exists
        ? `Solution file present · ${action.codeGate.solution_expected}`
        : `Solution file will be required · ${action.codeGate.solution_expected}`;
      wrap.append(gate);
    }

    const cta = document.createElement("button");
    cta.className = "stage-skill-open primary-action";
    cta.type = "button";
    cta.textContent = REVISION_FAMILY.has(mode)
      ? "Start recall"
      : mode === "mock_due"
        ? "Open mock problem"
        : "Open problem";
    cta.addEventListener("click", () => openProblemModal(problem.id));
    wrap.append(cta);
  }

  function renderTrajectory() {
    const host = $("#trajectory-strip");
    if (!host) return;
    host.replaceChildren();
    if (!feedAvailable()) {
      host.removeAttribute("aria-label");
      host.append(degradedBanner());
      return;
    }
    const readiness = state.feed.readiness || {};
    const gates = readiness.gates || {};
    // Each station reads as one headline number, what it is made of, and what
    // it has to reach. Never "1/60 / 80%" — a count and a percentage either
    // side of the same slash is unreadable.
    const core = gates.core_mastery || {};
    const pass = gates.revision_pass || {};
    const mocks = gates.mocks || {};
    const verdicts = mocks.verdicts || [];
    const stations = [
      {
        label: "Core skills",
        met: !!core.met,
        value: formatPct(core.current),
        detail: `${core.mastered ?? 0} of ${core.total ?? 0} mastered`,
        target: formatPct(core.target),
      },
      {
        label: "Revision pass",
        met: !!pass.met,
        value: formatPct(pass.current),
        detail: "of graded recalls",
        target: formatPct(pass.target),
      },
      {
        label: "Recent mocks",
        met: !!mocks.met,
        value: `${mocks.current ?? 0} of ${mocks.required ?? 0}`,
        detail: verdicts.length ? verdicts.join(", ") : "none recorded yet",
        target: "hire or better",
      },
    ];

    const line = document.createElement("div");
    line.className = "trajectory-line";
    stations.forEach((station, index) => {
      const node = document.createElement("div");
      node.className = `trajectory-station ${station.met ? "met" : "unmet"}`;
      node.style.setProperty("--stagger", `${index * 80}ms`);

      const dot = document.createElement("span");
      dot.className = "station-dot";
      dot.setAttribute("aria-hidden", "true");
      dot.textContent = station.met ? "✓" : "";
      const label = document.createElement("span");
      label.className = "station-label microlabel";
      label.textContent = station.label;
      const value = document.createElement("span");
      value.className = "station-value num";
      value.textContent = station.value;
      const detail = document.createElement("span");
      detail.className = "station-detail num";
      detail.textContent = station.detail;
      const target = document.createElement("span");
      target.className = "station-target microlabel";
      target.textContent = station.met
        ? `met · target ${station.target}`
        : `needs ${station.target}`;
      node.append(dot, label, value, detail, target);
      line.append(node);
    });

    const terminus = document.createElement("div");
    terminus.className = "trajectory-terminus";
    terminus.style.setProperty("--stagger", `${stations.length * 80}ms`);
    const projected = readiness.projected_date;
    const tLabel = document.createElement("span");
    tLabel.className = "station-label microlabel";
    tLabel.textContent = "Projected ready";
    const tDate = document.createElement("span");
    tDate.className = "terminus-date num";
    tDate.textContent = projected || "—";
    terminus.append(tLabel, tDate);
    line.append(terminus);
    host.append(line);

    host.setAttribute(
      "aria-label",
      `Interview readiness. ${stations
        .map((s) => `${s.label}: ${s.value}, ${s.detail}, target ${s.target}, ${s.met ? "met" : "not met"}`)
        .join(". ")}. Projected ready ${projected || "unknown"}.`,
    );
  }

  // The backlog badge makes the scheduling rule legible: recall is deferred
  // while the queue is at or under revision_backlog_threshold, and takes over
  // past it. Without this the queue just reads "3 overdue" and the learner
  // cannot tell whether they are meant to clear it now.
  function renderBacklogBadge(dueCount) {
    const badge = $("#due-queue-load");
    if (!badge) return;
    if (!feedAvailable()) {
      badge.textContent = "offline";
      badge.className = "pill num warn";
      return;
    }
    const threshold = state.feed.policy?.revision_backlog_threshold;
    if (typeof threshold !== "number") {
      badge.textContent = `${dueCount} due`;
      badge.className = "pill num";
      return;
    }
    const over = dueCount > threshold;
    if (threshold === 0) {
      // Strict revision-first: there is no allowance to count against.
      badge.textContent = dueCount ? `${dueCount} due · recall first` : "none due";
      badge.className = `pill num ${dueCount ? "warn" : "good"}`;
      return;
    }
    badge.textContent = `${dueCount} of ${threshold} · ${over ? "recall first" : "new work unlocked"}`;
    badge.className = `pill num ${over ? "warn" : "good"}`;
  }

  function renderDueQueue() {
    const host = $("#due-queue");
    if (!host) return;
    host.replaceChildren();
    if (!feedAvailable()) {
      renderBacklogBadge(0);
      host.append(degradedBanner());
      return;
    }
    const queue = state.feed.revision_queue || [];
    renderBacklogBadge(queue.length);
    if (!queue.length) {
      host.append(empty("Nothing due today — new work is unlocked."));
      return;
    }
    const threshold = state.feed.policy?.revision_backlog_threshold;
    if (typeof threshold === "number") {
      const note = document.createElement("p");
      note.className = "chart-note microlabel";
      note.textContent =
        threshold === 0
          ? "Recall is served before new problems while anything is due."
          : queue.length > threshold
            ? `Backlog is over the threshold of ${threshold}, so recall is served before new problems until it drains.`
            : `Up to ${threshold} due items may wait while you take new problems. These stay scheduled.`;
      host.append(note);
    }
    queue.forEach((item) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = `due-row${item.overdue ? " overdue" : ""}`;

      const title = document.createElement("span");
      title.className = "due-title";
      title.textContent = item.title || item.problem_id;

      const tone =
        item.kind === "quarterly_maintenance" ? "" : item.kind === "reactivated" ? "warn" : "accent";
      // A reactivated row keeps its R-stage but must say so in words: it is a
      // forced prerequisite reinforcement, not an ordinary scheduled recall,
      // and tone alone would leave that readable only by color.
      const kind = pill(
        item.kind === "reactivated"
          ? `${item.stage_label || "R?"} · reactivated`
          : item.stage_label || item.kind,
        tone,
      );
      kind.classList.add("num");

      const due = document.createElement("span");
      due.className = "due-date num";
      due.textContent = item.next_due;

      const flag = document.createElement("span");
      flag.className = "due-flag";
      if (item.overdue) flag.textContent = "⚠ overdue";

      row.append(title, kind, due, flag);
      row.addEventListener("click", () => openProblemModal(item.problem_id));
      host.append(row);
    });
  }

  function renderForecast() {
    const host = $("#forecast-chart");
    if (!host) return;
    host.replaceChildren();
    if (!feedAvailable()) {
      host.removeAttribute("aria-label");
      host.append(degradedBanner());
      return;
    }
    const days = state.feed.review_forecast || [];
    const totalDue = days.reduce((sum, day) => sum + (day.count || 0), 0);
    if (!totalDue) {
      host.append(empty("Nothing due in the next 14 days."));
      return;
    }

    const W = 660;
    const H = 170;
    const PAD_X = 10;
    const PAD_TOP = 22;
    const PAD_BOTTOM = 26;
    const maxCount = Math.max(1, ...days.map((day) => day.count || 0));
    const bandW = (W - PAD_X * 2) / days.length;
    const barW = Math.min(bandW - 2, 30);
    const plotH = H - PAD_TOP - PAD_BOTTOM;

    const svg = svgEl("svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "forecast-svg");


    // baseline
    svg.append(
      svgEl("line", {
        x1: PAD_X,
        y1: H - PAD_BOTTOM,
        x2: W - PAD_X,
        y2: H - PAD_BOTTOM,
        class: "forecast-baseline",
      }),
    );

    days.forEach((day, index) => {
      const x = PAD_X + index * bandW + (bandW - barW) / 2;
      const count = day.count || 0;
      const h = count ? Math.max(4, (plotH * count) / maxCount) : 0;
      const y = H - PAD_BOTTOM - h;
      if (count) {
        const rect = svgEl("rect", {
          x,
          y,
          width: barW,
          height: h,
          rx: 4,
          class: day.overdue ? "forecast-bar overdue" : "forecast-bar",
        });
        rect.append(
          svgEl(
            "title",
            {},
            `${day.date}: ${count} review${count === 1 ? "" : "s"}${
              day.overdue ? " (includes overdue)" : ""
            }${day.problem_ids?.length ? ` — ${day.problem_ids.join(", ")}` : ""}`,
          ),
        );
        svg.append(rect);
        svg.append(
          svgEl(
            "text",
            { x: x + barW / 2, y: y - 6, "text-anchor": "middle", class: "forecast-count" },
            day.overdue ? `⚠ ${count}` : String(count),
          ),
        );
      }
      svg.append(
        svgEl(
          "text",
          { x: x + barW / 2, y: H - 9, "text-anchor": "middle", class: "forecast-axis" },
          weekdayShort(day.date),
        ),
      );
    });

    host.append(svg);
    host.setAttribute(
      "aria-label",
      `Fourteen-day review forecast: ${totalDue} review${totalDue === 1 ? "" : "s"} scheduled${
        days[0]?.overdue ? `, including overdue items today` : ""
      }.`,
    );
  }

  function sessionsInWindow(days) {
    const ref = parseDate(referenceDate()) || todayDate();
    const start = new Date(ref);
    start.setDate(start.getDate() - (days - 1));
    const seen = new Set();
    (state.datasets.progress.completed || []).forEach((record) => {
      const when = parseDate(record.completed_at);
      if (when && when >= start && when <= ref) seen.add(record.completed_at);
    });
    return seen.size;
  }

  function renderPaceTiles() {
    const host = $("#pace-tiles");
    if (!host) return;
    host.replaceChildren();
    if (!feedAvailable()) {
      host.append(degradedBanner());
      return;
    }
    const pace = (state.feed.readiness || {}).pace || {};
    const tiles = [
      {
        label: "Problems / week",
        value: Number(pace.problems_per_week || 0).toFixed(2),
        note: `trailing ${pace.window_days ?? 0}d`,
      },
      {
        label: "Skills / week",
        value: Number(pace.skills_per_week || 0).toFixed(2),
        note: "mastered",
      },
      {
        label: "Sessions · 30d",
        value: String(sessionsInWindow(30)),
        note: "days with a solve",
      },
    ];
    tiles.forEach((tile) => {
      const node = document.createElement("div");
      node.className = "pace-tile";
      const label = document.createElement("span");
      label.className = "microlabel";
      label.textContent = tile.label;
      const value = document.createElement("strong");
      value.className = "num";
      value.textContent = tile.value;
      const note = document.createElement("small");
      note.className = "microlabel";
      note.textContent = tile.note;
      node.append(label, value, note);
      host.append(node);
    });
  }

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

    const rows = plan.weeks || [];
    if (!rows.length) return;
    const W = 660;
    const H = 120;
    const PAD = 12;
    const bandW = (W - PAD * 2) / Math.max(rows.length, 1);
    const barW = Math.min(bandW - 8, 34);
    const maxTarget = Math.max(1, ...rows.map((row) => Math.max(row.target_solves, row.actual_solves)));
    const plotH = H - 34;
    const svg = svgEl("svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "weekbars-svg");
    rows.forEach((row, index) => {
      const x = PAD + index * bandW + (bandW - barW) / 2;
      const targetH = (plotH * row.target_solves) / maxTarget;
      const actualH = (plotH * row.actual_solves) / maxTarget;
      const baseline = H - 22;
      if (row.target_solves > 0) {
        svg.append(
          svgEl("rect", {
            x,
            y: baseline - targetH,
            width: barW,
            height: Math.max(targetH, 1),
            rx: 3,
            class: "weekbar-target",
          }),
        );
      }
      const actual = svgEl("rect", {
        x: x + 3,
        y: baseline - actualH,
        width: Math.max(barW - 6, 4),
        height: Math.max(actualH, row.actual_solves ? 3 : 0),
        rx: 3,
        class: row.actual_solves >= row.target_solves ? "weekbar-actual good" : "weekbar-actual",
      });
      actual.append(
        svgEl(
          "title",
          {},
          `W${row.week} (${row.start}): ${row.actual_solves} of ${row.target_solves} solves` +
            `${row.deload ? " · deload" : ""}${row.mock_done ? " · mock done" : ""}`,
        ),
      );
      svg.append(actual);
      svg.append(
        svgEl(
          "text",
          {
            x: x + barW / 2,
            y: H - 8,
            "text-anchor": "middle",
            class: "forecast-axis",
          },
          row.deload ? `W${row.week}·D` : `W${row.week}`,
        ),
      );
    });
    bars.append(svg);
    bars.setAttribute(
      "aria-label",
      `Weekly solves, target versus actual, for ${rows.length} started week${rows.length === 1 ? "" : "s"}.`,
    );
  }

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
    const svg = svgEl("svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "burnup-svg");
    const withTitle = (el, title) => {
      el.append(svgEl("title", {}, title));
      return el;
    };

    (burnup.planned || [])
      .filter((week) => week.deload)
      .forEach((week) => {
        const deloadEnd = week.end || week.date;
        svg.append(
          withTitle(
            svgEl("rect", {
              x: xFor(week.start),
              y: PAD_T,
              width: Math.max(xFor(week.date) - xFor(week.start), 2),
              height: H - PAD_T - PAD_B,
              class: "burnup-deload",
            }),
            `Deload week: ${week.start} to ${deloadEnd}`,
          ),
        );
      });
    svg.append(
      withTitle(
        svgEl("line", {
          x1: PAD_L,
          y1: yFor(burnup.target_total),
          x2: W - PAD_R,
          y2: yFor(burnup.target_total),
          class: "burnup-target-line",
        }),
        `Quarter target: ${burnup.target_total}`,
      ),
    );
    svg.append(svgEl("text", { x: 2, y: yFor(burnup.target_total) + 4, class: "forecast-axis" }, String(burnup.target_total)));
    svg.append(svgEl("text", { x: 2, y: yFor(0) + 4, class: "forecast-axis" }, "0"));
    svg.append(
      svgEl("line", {
        x1: PAD_L,
        y1: H - PAD_B,
        x2: W - PAD_R,
        y2: H - PAD_B,
        class: "forecast-baseline",
      }),
    );

    const toPoints = (entries) =>
      entries.map((entry) => `${xFor(entry.date).toFixed(1)},${yFor(entry.cumulative).toFixed(1)}`).join(" ");
    svg.append(
      withTitle(
        svgEl("polyline", {
          points: `${xFor(burnup.start).toFixed(1)},${yFor(0).toFixed(1)} ${toPoints(burnup.planned || [])}`,
          class: "burnup-planned",
          fill: "none",
        }),
        `Planned target: ${burnup.target_total} by ${burnup.end}`,
      ),
    );
    const actualEntries = burnup.actual || [];
    svg.append(
      withTitle(
        svgEl("polyline", {
          points: `${xFor(burnup.start).toFixed(1)},${yFor(0).toFixed(1)} ${toPoints(actualEntries)}`,
          class: "burnup-actual",
          fill: "none",
        }),
        `Actual solves: ${burnup.actual_total}`,
      ),
    );
    const todayIso = state.feed.reference_date;
    const clampedToday = parseDate(todayIso) > end ? burnup.end : todayIso;
    svg.append(
      withTitle(
        svgEl("line", {
          x1: xFor(clampedToday),
          y1: PAD_T,
          x2: xFor(clampedToday),
          y2: H - PAD_B,
          class: "burnup-today",
        }),
        `Reference date: ${todayIso}`,
      ),
    );
    if (burnup.required_per_week != null) {
      svg.append(
        withTitle(
          svgEl("line", {
            x1: xFor(clampedToday),
            y1: yFor(burnup.actual_total),
            x2: xFor(burnup.end),
            y2: yFor(burnup.projected_total),
            class: "burnup-projection",
          }),
          `Projected landing: ${burnup.projected_total} by ${burnup.end}`,
        ),
      );
    }
    (plan.months || []).forEach((month) => {
      const monthSolves =
        month.actual_solves != null && month.expected_solves != null
          ? `: ${month.actual_solves} of ${month.expected_solves} solves`
          : "";
      svg.append(
        withTitle(
          svgEl("line", {
            x1: xFor(month.milestone_date),
            y1: H - PAD_B,
            x2: xFor(month.milestone_date),
            y2: H - PAD_B + 6,
            class: "burnup-tick",
          }),
          `Month milestone ${month.milestone_date}${monthSolves}`,
        ),
      );
      svg.append(
        svgEl(
          "text",
          {
            x: xFor(month.milestone_date),
            y: H - 8,
            "text-anchor": "middle",
            class: "forecast-axis",
          },
          month.month.slice(5),
        ),
      );
    });
    chart.append(svg);
    chart.setAttribute(
      "aria-label",
      `Quarter burn-up: ${burnup.actual_total} of ${burnup.target_total} solves done; ` +
        `projected ${burnup.projected_total} by ${burnup.end}` +
        (burnup.required_per_week != null ? `; ${burnup.required_per_week} per week required.` : "."),
    );

    if (legendHost) {
      legendHost.append(
        chartLegend([
          { label: "planned", shape: "line", color: "var(--muted)" },
          { label: `actual · ${burnup.actual_total}`, shape: "line", color: "var(--series-1)" },
          { label: `projection · ${burnup.projected_total}`, shape: "line", color: "var(--series-2)" },
        ]),
      );
    }

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

  function renderThinkingBars() {
    const dimensions = state.datasets.progress.scores?.averages?.thinking_dimensions || {};
    const labels = state.datasets.scoring.dimensions || {};
    const max = state.datasets.scoring.scale?.maximum || 4;
    const rows = Object.entries(dimensions).sort((a, b) => a[1] - b[1]);
    const target = $("#thinking-bars");
    target.replaceChildren();
    if (!rows.length) {
      target.removeAttribute("aria-label");
      target.append(empty("No scored solves yet — dimension averages appear after the first completion."));
      return;
    }
    target.setAttribute(
      "aria-label",
      `Thinking dimension averages out of ${max}, weakest first: ${rows
        .map(([key, value]) => `${key.replaceAll("_", " ")} ${value.toFixed(2)}`)
        .join(", ")}.`,
    );
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
              // F20 provenance: keep the entry's own source so the lab can
              // show where the signal came from (mock vs revision vs session).
              source: entry.source,
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
          source: "solve",
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
      const sources = document.createElement("div");
      sources.className = "meta-row source-chips";
      [...new Set(weakness.evidence.map((item) => item.source).filter(Boolean))].forEach((source) => {
        const chip = pill(source, "");
        chip.classList.add("microlabel");
        sources.append(chip);
      });
      if (sources.children.length) card.append(sources);

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
        taxonomy: entry.taxonomy,
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
      // F14 taxonomy: catalog entries carry their error class (A-E); the chip
      // names it so the code is never the only thing shown.
      if (item.taxonomy) {
        const labels = state.datasets.scoring.error_taxonomy || {};
        const chip = pill(`${item.taxonomy} · ${labels[item.taxonomy] || "uncategorised"}`, "");
        chip.classList.add("microlabel");
        node.prepend(chip);
      }
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
        <strong>${item.problemId}</strong>
        <span class="pill microlabel">${item.source}</span>
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
            <span class="pill ${mastery.status === "mastered" ? "good" : mastery.status === "locked" ? "" : "warn"}">${stageStatusLabel(mastery.status)}</span>
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

  const LADDER_STATUS = {
    mastered: { label: "✓ mastered", tone: "good" },
    in_progress: { label: "● in progress", tone: "warn" },
    locked: { label: "○ locked", tone: "" },
  };

  // Stage status arrives from the feed as a snake_case enum. It is a wire value,
  // never display copy - the stage cards were printing `in_progress` verbatim.
  const STAGE_STATUS_LABEL = {
    mastered: "Mastered",
    in_progress: "In progress",
    locked: "Locked",
    open: "Open",
  };

  function stageStatusLabel(status) {
    return STAGE_STATUS_LABEL[status] || String(status || "unknown").replace(/_/g, " ");
  }

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

  // ---------------------------------------------------------------------------
  // Skill constellation (design section 8): the real curriculum DAG as a
  // stage-banded SVG map. Layout is computed from skill_order + stage_order,
  // never hand-placed; edges come from dependency_graph.json.skill_dependencies.
  // ---------------------------------------------------------------------------

  // Concentric rings, one per stage, innermost = stage 1. This replaced a
  // 13-column grid that could not be read: only 15 of 93 skills fitted on
  // screen at a usable zoom, so panning was mandatory and nothing was legible.
  // Rings fix that geometrically - circumference grows with radius, which is
  // exactly where the big stages are (stage 10 carries 17 skills), and 56% of
  // the edges are intra-stage, which become short arcs along a ring instead of
  // invisible verticals down a column.
  const CONSTELLATION = {
    W: 880,
    H: 780,
    R_INNER: 78,
    R_OUTER: 336,
    // Angular wedge kept clear at 12 o'clock so the stage labels stacking up
    // the vertical axis never collide with a star.
    LABEL_WEDGE_DEG: 17,
    R_MIN: 4,
    R_MAX: 12,
    LABEL_MAX: 22,
    MIN_K: 0.35,
    MAX_K: 4,
  };

  // Same skill, same place, every render - derived from the id, never random.
  // Perfectly even spacing reads as a dial; a little scatter reads as a sky.
  function skillJitter(skillId) {
    let hash = 0;
    for (let index = 0; index < skillId.length; index += 1) {
      hash = (hash * 31 + skillId.charCodeAt(index)) | 0;
    }
    return {
      angle: (((hash >>> 3) % 1000) / 1000) * 2 - 1,
      radius: (((hash >>> 13) % 1000) / 1000) * 2 - 1,
    };
  }

  function constellationLayout() {
    const stages = state.datasets.stages.stage_order || [];
    const order = state.datasets.skills.skill_order || [];
    const byStage = new Map(stages.map((stage) => [stage, []]));
    order.forEach((skillId) => {
      const stage = skillMeta(skillId)?.stage;
      if (byStage.has(stage)) byStage.get(stage).push(skillId);
    });

    const { W, H, R_INNER, R_OUTER, LABEL_WEDGE_DEG } = CONSTELLATION;
    const cx = W / 2;
    const cy = H / 2;
    const rings = Math.max(1, stages.length);
    const step = rings > 1 ? (R_OUTER - R_INNER) / (rings - 1) : 0;
    const wedge = (LABEL_WEDGE_DEG * Math.PI) / 180;
    const sweep = Math.PI * 2 - wedge;
    const start = -Math.PI / 2 + wedge / 2;

    const pos = new Map();
    const ringRadius = new Map();
    stages.forEach((stage, ring) => {
      const radius = R_INNER + ring * step;
      ringRadius.set(stage, radius);
      const members = byStage.get(stage);
      const slot = sweep / Math.max(1, members.length);
      members.forEach((skillId, index) => {
        const noise = skillJitter(skillId);
        // Half-slot stagger on alternate rings so stars never line up into
        // spokes radiating from the centre.
        const stagger = ring % 2 ? slot / 2 : 0;
        const angle = start + stagger + (index + 0.5) * slot + noise.angle * slot * 0.16;
        const r = radius + noise.radius * Math.min(9, step * 0.22);
        pos.set(skillId, {
          x: cx + r * Math.cos(angle),
          y: cy + r * Math.sin(angle),
          angle,
          radius: r,
          ring,
        });
      });
    });

    return { pos, byStage, stages, ringRadius, cx, cy, step, width: W, height: H };
  }
  const CONSTELLATION_STATE_LABEL = {
    mastered: "mastered",
    current: "current skill",
    unlocked: "unlocked",
    locked: "locked",
  };


  function skillProblemCount(skillId) {
    return state.datasets.curriculum.problems.filter((problem) => problem.primary_skill === skillId)
      .length;
  }

  function isSkillMastered(skillId) {
    return Boolean(state.datasets.progress.skill_progress?.[skillId]?.mastered);
  }

  // The skill the learner is on right now — read off the scheduler's current
  // problem, not re-derived from stage order.
  function currentSkillId() {
    const current = state.datasets.progress.current_problem;
    return current ? state.problemsById.get(current)?.primary_skill || null : null;
  }

  function constellationNodeState(skillId, deps, current) {
    if (isSkillMastered(skillId)) return "mastered";
    if (skillId === current) return "current";
    const prerequisites = deps[skillId] || [];
    return prerequisites.every((prereq) => isSkillMastered(prereq)) ? "unlocked" : "locked";
  }

  function skillAncestors(skillId, deps, seen = new Set()) {
    (deps[skillId] || []).forEach((prereq) => {
      if (seen.has(prereq)) return;
      seen.add(prereq);
      skillAncestors(prereq, deps, seen);
    });
    return seen;
  }

  function renderConstellation() {
    const host = $("#constellation");
    if (!host) return;
    host.replaceChildren();
    const badge = $("#constellation-count");
    const legendHost = $("#constellation-legend");
    if (legendHost) legendHost.replaceChildren();
    host.append(empty("Loading the prerequisite map…"));

    ensureDependencyGraph().then((edges) => {
      const deps = edges?.skillDeps;
      host.replaceChildren();
      if (!deps) {
        host.append(empty("Prerequisite map unavailable — dependency_graph.json could not be read."));
        return;
      }
      drawConstellation(host, legendHost, badge, deps);
    });
  }

  // The map is a star chart on its own dark plate - a fixed surface in both
  // themes. That is not decoration: a 1px prerequisite edge that disappears
  // against white reads clearly against ink, so the graph is legible at all.
  // Structure is the substrate (stage bands, labelled nodes, traceable edges),
  // progress is the light painted onto it, and the frontier is the only thing
  // carrying full weight.


  // The map is a star chart on its own dark plate - a fixed surface in both
  // themes. That is not decoration: a 1px prerequisite edge that disappears
  // against white reads clearly against ink.
  function drawConstellation(host, legendHost, badge, deps) {
    const layout = constellationLayout();
    const { pos, byStage, stages, ringRadius, cx, cy } = layout;
    const { R_MIN, R_MAX } = CONSTELLATION;
    const ids = [...pos.keys()];
    if (!ids.length) {
      host.append(empty("No skills in the curriculum yet."));
      return;
    }

    const current = currentSkillId();
    const counts = new Map(ids.map((id) => [id, skillProblemCount(id)]));
    const maxCount = Math.max(1, ...counts.values());
    // Radius is the star's magnitude: how much of the curriculum rides on it.
    const radius = (id) => R_MIN + ((R_MAX - R_MIN) * Math.min(counts.get(id), maxCount)) / maxCount;
    const nodeStates = new Map(ids.map((id) => [id, constellationNodeState(id, deps, current)]));
    const dependents = new Map(ids.map((id) => [id, []]));
    ids.forEach((id) => {
      (deps[id] || []).forEach((prereq) => {
        if (dependents.has(prereq)) dependents.get(prereq).push(id);
      });
    });

    const plate = document.createElement("div");
    plate.className = "constellation-plate";
    plate.tabIndex = 0;
    plate.setAttribute("role", "application");
    plate.setAttribute(
      "aria-label",
      "Skill map. Arrow keys pan, plus and minus zoom, f fits, c centres on unlocked skills.",
    );

    const svg = svgEl("svg", {
      class: "constellation-svg",
      role: "group",
      "aria-label": `Skill prerequisite map: ${ids.length} skills across ${stages.length} stages.`,
    });
    const viewport = svgEl("g", { class: "constellation-viewport" });

    // --- rings -------------------------------------------------------------
    const ringLayer = svgEl("g", { class: "constellation-rings" });
    stages.forEach((stage, ring) => {
      const done = byStage.get(stage).filter((id) => isSkillMastered(id)).length;
      const total = byStage.get(stage).length;
      const circle = svgEl("circle", { cx, cy, r: ringRadius.get(stage), class: "constellation-ring" });
      circle.append(svgEl("title", {}, `Stage ${ring + 1} · ${stage} · ${done}/${total} mastered`));
      ringLayer.append(circle);
    });
    viewport.append(ringLayer);

    // --- frontier ----------------------------------------------------------
    // The shell you are currently breaking through: the mean radius of the
    // skills whose prerequisites are all done.
    const frontierIds = ids.filter((id) => {
      const nodeState = nodeStates.get(id);
      return nodeState === "unlocked" || nodeState === "current";
    });
    if (frontierIds.length) {
      const meanRadius =
        frontierIds.reduce((sum, id) => sum + pos.get(id).radius, 0) / frontierIds.length;
      viewport.append(
        svgEl("circle", { cx, cy, r: meanRadius, class: "constellation-frontier" }),
      );
      // Sits at 6 o'clock: 12 o'clock is the stage-number axis.
      viewport.append(
        svgEl(
          "text",
          { x: cx, y: cy + meanRadius + 14, "text-anchor": "middle", class: "constellation-frontier-label" },
          "frontier",
        ),
      );
    }

    // --- stage figures -----------------------------------------------------
    // A stage whose skills are all mastered draws itself as a figure. Locked
    // stages show the same shape as a faint ghost, so the map has structure
    // from day one and completing a stage lights up something already familiar.
    const figureLayer = svgEl("g", { class: "constellation-figures" });
    stages.forEach((stage) => {
      const members = byStage.get(stage).filter((id) => pos.has(id));
      if (members.length < 2) return;
      const earned = members.every((id) => isSkillMastered(id));
      figureLayer.append(
        svgEl("polyline", {
          points: members.map((id) => `${pos.get(id).x.toFixed(1)},${pos.get(id).y.toFixed(1)}`).join(" "),
          class: `constellation-figure ${earned ? "earned" : "ghost"}`,
        }),
      );
    });
    viewport.append(figureLayer);

    // --- edges -------------------------------------------------------------
    // 137 edges drawn at full strength is spaghetti, not structure. They sit at
    // low opacity so the graph reads as connective texture, and the path for
    // whichever star you touch comes up to full strength.
    const edgeLayer = svgEl("g", { class: "constellation-edges" });
    const edgeIndex = [];
    ids.forEach((id) => {
      (deps[id] || []).forEach((prereq) => {
        const from = pos.get(prereq);
        const to = pos.get(id);
        if (!from || !to) return;
        const targetState = nodeStates.get(id);
        const tone =
          targetState === "current" || targetState === "unlocked"
            ? "to-frontier"
            : isSkillMastered(prereq)
              ? "from-mastered"
              : "base";
        // Bow every edge towards the centre so same-ring links read as arcs and
        // cross-ring links never cut straight through the middle of the map.
        const midX = (from.x + to.x) / 2;
        const midY = (from.y + to.y) / 2;
        const pull = 0.72;
        const path = svgEl("path", {
          d: `M ${from.x.toFixed(1)} ${from.y.toFixed(1)} Q ${(cx + (midX - cx) * pull).toFixed(1)} ${(cy + (midY - cy) * pull).toFixed(1)} ${to.x.toFixed(1)} ${to.y.toFixed(1)}`,
          class: `constellation-edge ${tone}`,
        });
        edgeLayer.append(path);
        edgeIndex.push({ path, from: prereq, to: id });
      });
    });
    viewport.append(edgeLayer);

    // --- stars -------------------------------------------------------------
    const nodeLayer = svgEl("g", { class: "constellation-nodes" });
    const nodeIndex = new Map();
    ids.forEach((id) => {
      const point = pos.get(id);
      const nodeState = nodeStates.get(id);
      const count = counts.get(id);
      const title = skillTitle(id);
      const r = radius(id);
      const description =
        `${title} · ${skillMeta(id)?.stage || "unstaged"} · ` +
        `${count} problem${count === 1 ? "" : "s"} · ${CONSTELLATION_STATE_LABEL[nodeState]}`;

      const group = svgEl("g", { class: `constellation-star ${nodeState}` });
      if (nodeState === "mastered" || nodeState === "current") {
        group.append(svgEl("circle", { cx: point.x, cy: point.y, r: r * 2.8, class: "constellation-halo" }));
      }
      const node = svgEl("circle", {
        cx: point.x,
        cy: point.y,
        r,
        class: "constellation-node",
        tabindex: "0",
        role: "button",
        "aria-label": description,
      });
      node.append(svgEl("title", {}, description));

      // Labels read outward from the centre, so they never cross the rings.
      const outward = r + 7;
      const facingRight = Math.cos(point.angle) >= 0;
      const label = svgEl(
        "text",
        {
          x: point.x + Math.cos(point.angle) * outward,
          y: point.y + Math.sin(point.angle) * outward + 3.5,
          "text-anchor": facingRight ? "start" : "end",
          class: "constellation-label",
        },
        truncateLabel(title),
      );
      group.append(node, label);
      nodeLayer.append(group);
      nodeIndex.set(id, group);

      const isolate = () => {
        const related = new Set([id, ...skillAncestors(id, deps), ...(dependents.get(id) || [])]);
        svg.classList.add("is-isolating");
        edgeIndex.forEach(({ path, from, to }) => {
          path.classList.toggle("lit", related.has(from) && related.has(to));
        });
        nodeIndex.forEach((other, otherId) => other.classList.toggle("faded", !related.has(otherId)));
      };
      const restore = () => {
        svg.classList.remove("is-isolating");
        edgeIndex.forEach(({ path }) => path.classList.remove("lit"));
        nodeIndex.forEach((other) => other.classList.remove("faded"));
      };
      node.addEventListener("mouseenter", isolate);
      node.addEventListener("mouseleave", restore);
      node.addEventListener("focus", isolate);
      node.addEventListener("blur", restore);
      node.addEventListener("click", () => openSingleSkillModal(id));
      node.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        openSingleSkillModal(id);
      });
    });
    viewport.append(nodeLayer);

    // --- stage axis --------------------------------------------------------
    // Numbers only. Full stage names were tried here and cannot work: the
    // cleared wedge is angular, so at the inner radii it is ~23px of arc while
    // the names are ~150px wide - they sprawled straight over the stars. A
    // numeral fits the wedge at every radius; the name is on the ring's
    // tooltip, and the stage board below carries the detail.
    const stageLayer = svgEl("g", { class: "constellation-stage-labels" });
    stages.forEach((stage, ring) => {
      const r = ringRadius.get(stage);
      const done = byStage.get(stage).filter((id) => isSkillMastered(id)).length;
      const total = byStage.get(stage).length;
      const text = svgEl(
        "text",
        {
          x: cx,
          y: cy - r + 3.2,
          "text-anchor": "middle",
          class: `constellation-stage ${done === total ? "complete" : done ? "started" : ""}`,
        },
        String(ring + 1),
      );
      text.append(svgEl("title", {}, `Stage ${ring + 1} · ${stage} · ${done}/${total} mastered`));
      stageLayer.append(text);
    });
    viewport.append(stageLayer);

    // --- centre readout ----------------------------------------------------
    // The innermost ring leaves a hole; the map's headline number belongs in it.
    const masteredTotal = ids.filter((id) => isSkillMastered(id)).length;
    const core = svgEl("g", { class: "constellation-core" });
    core.append(
      svgEl("text", { x: cx, y: cy - 4, "text-anchor": "middle", class: "constellation-core-value" }, `${masteredTotal}/${ids.length}`),
    );
    core.append(
      svgEl("text", { x: cx, y: cy + 13, "text-anchor": "middle", class: "constellation-core-label" }, "mastered"),
    );
    viewport.append(core);

    svg.append(viewport);
    plate.append(svg);

    const controls = buildConstellationControls();
    const minimap = buildConstellationMinimap(layout, nodeStates, radius);
    plate.append(controls.element, minimap.element);
    host.append(plate);

    attachConstellationViewport({
      plate,
      viewport,
      layout,
      controls,
      minimap,
      focusIds: { current, mastered: ids.filter((id) => isSkillMastered(id)) },
    });

    state.constellationFilter = () => applyConstellationFilters(nodeIndex);
    state.constellationFilter();

    const masteredCount = ids.filter((id) => isSkillMastered(id)).length;
    if (badge) {
      badge.textContent = `${ids.length} skills · ${masteredCount} mastered`;
      badge.className = "pill num";
    }
    if (legendHost) {
      legendHost.append(
        ...["mastered", "current", "unlocked", "locked"].map((nodeState) => {
          const item = document.createElement("span");
          const mark = document.createElement("i");
          mark.className = `legend-node ${nodeState}`;
          item.append(mark, document.createTextNode(CONSTELLATION_STATE_LABEL[nodeState]));
          return item;
        }),
      );
      const hint = document.createElement("span");
      hint.className = "microlabel";
      hint.textContent = "stage 1 at the centre · hover a star to trace its prerequisites · enter opens it";
      legendHost.append(hint);
    }
  }

  function buildConstellationControls() {
    const element = document.createElement("div");
    element.className = "constellation-controls";
    const make = (label, aria) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "constellation-control";
      button.textContent = label;
      button.setAttribute("aria-label", aria);
      element.append(button);
      return button;
    };
    return {
      element,
      out: make("−", "Zoom out"),
      in: make("+", "Zoom in"),
      fit: make("fit", "Fit the whole map"),
      focus: make("⌖", "Centre on what is unlocked now"),
    };
  }

  function buildConstellationMinimap(layout, nodeStates, radius) {
    const { pos, width, height } = layout;
    const element = svgEl("svg", {
      class: "constellation-minimap",
      viewBox: `0 0 ${width} ${height}`,
      preserveAspectRatio: "none",
      "aria-hidden": "true",
    });
    // The graph is far wider than it is tall; letting the box keep its own
    // aspect ratio would letterbox the map into a sliver. Height follows width.
    const MINIMAP_W = 168;
    element.style.width = `${MINIMAP_W}px`;
    element.style.height = `${Math.round((MINIMAP_W * height) / width)}px`;
    element.append(svgEl("rect", { x: 0, y: 0, width, height, class: "constellation-minimap-bg" }));
    pos.forEach((point, id) => {
      element.append(
        svgEl("circle", {
          cx: point.x,
          cy: point.y,
          // Radii are in graph units shown at ~1/20 scale, so true-size dots
          // would land well under a pixel. Draw them far above scale.
          r: Math.max(26, radius(id) * 2),
          class: `constellation-minimap-dot ${nodeStates.get(id)}`,
        }),
      );
    });
    const frame = svgEl("rect", { class: "constellation-minimap-frame" });
    element.append(frame);
    return { element, frame };
  }

  // Pan/zoom over the whole map. Rings open FITTED, not focused: the whole
  // curriculum is meant to be visible at once, which is the thing the old
  // column layout could never do. Zoom is for reading detail, not for finding
  // your way around.
  function attachConstellationViewport({ plate, viewport, layout, controls, minimap, focusIds }) {
    const { MIN_K, MAX_K } = CONSTELLATION;
    const view = { k: 1, tx: 0, ty: 0 };

    const size = () => ({ w: plate.clientWidth, h: plate.clientHeight });

    function clampPan() {
      const { w, h } = size();
      const scaledW = layout.width * view.k;
      const scaledH = layout.height * view.k;
      // Keep a margin of content on screen; centre it outright when it all fits.
      view.tx = scaledW <= w ? (w - scaledW) / 2 : clamp(view.tx, w - scaledW - 40, 40);
      view.ty = scaledH <= h ? (h - scaledH) / 2 : clamp(view.ty, h - scaledH - 40, 60);
    }

    function apply() {
      clampPan();
      viewport.setAttribute("transform", `translate(${view.tx} ${view.ty}) scale(${view.k})`);
      // Star labels are set in screen pixels, so they must be counter-scaled or
      // they turn into billboards on zoom-in and vanish on zoom-out.
      plate.style.setProperty("--constellation-k", String(view.k));
      const { w, h } = size();
      minimap.frame.setAttribute("x", -view.tx / view.k);
      minimap.frame.setAttribute("y", -view.ty / view.k);
      minimap.frame.setAttribute("width", w / view.k);
      minimap.frame.setAttribute("height", h / view.k);
    }

    function zoomAt(px, py, factor) {
      const next = clamp(view.k * factor, MIN_K, MAX_K);
      if (next === view.k) return;
      view.tx = px - (px - view.tx) * (next / view.k);
      view.ty = py - (py - view.ty) * (next / view.k);
      view.k = next;
      apply();
    }

    function fit() {
      const { w, h } = size();
      view.k = clamp(Math.min(w / layout.width, h / layout.height), MIN_K, MAX_K);
      view.tx = (w - layout.width * view.k) / 2;
      view.ty = (h - layout.height * view.k) / 2;
      apply();
    }

    // Zoom in on where you actually are. The current skill is a real place; the
    // centroid of "unlocked" is not, because a skill with no prerequisites
    // counts as unlocked wherever it sits.
    function focusTarget() {
      if (focusIds.current && layout.pos.has(focusIds.current)) {
        return layout.pos.get(focusIds.current);
      }
      const mastered = focusIds.mastered.map((id) => layout.pos.get(id)).filter(Boolean);
      if (mastered.length) {
        return mastered.reduce((deepest, point) => (point.radius > deepest.radius ? point : deepest));
      }
      return { x: layout.cx, y: layout.cy };
    }

    function focusFrontier() {
      const target = focusTarget();
      const { w, h } = size();
      view.k = clamp(1.85, MIN_K, MAX_K);
      view.tx = w / 2 - target.x * view.k;
      view.ty = h / 2 - target.y * view.k;
      apply();
    }

    plate.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        const rect = plate.getBoundingClientRect();
        zoomAt(event.clientX - rect.left, event.clientY - rect.top, event.deltaY < 0 ? 1.12 : 1 / 1.12);
      },
      { passive: false },
    );

    let dragging = null;
    plate.addEventListener("pointerdown", (event) => {
      // Let the stars keep their own click/focus behaviour.
      if (event.target.closest(".constellation-node, .constellation-control")) return;
      dragging = { x: event.clientX, y: event.clientY, tx: view.tx, ty: view.ty };
      plate.setPointerCapture(event.pointerId);
      plate.classList.add("is-panning");
    });
    plate.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      view.tx = dragging.tx + (event.clientX - dragging.x);
      view.ty = dragging.ty + (event.clientY - dragging.y);
      apply();
    });
    const endDrag = () => {
      dragging = null;
      plate.classList.remove("is-panning");
    };
    plate.addEventListener("pointerup", endDrag);
    plate.addEventListener("pointercancel", endDrag);

    plate.addEventListener("keydown", (event) => {
      const step = 60;
      const keys = {
        ArrowLeft: () => (view.tx += step),
        ArrowRight: () => (view.tx -= step),
        ArrowUp: () => (view.ty += step),
        ArrowDown: () => (view.ty -= step),
      };
      if (keys[event.key]) {
        event.preventDefault();
        keys[event.key]();
        apply();
        return;
      }
      const { w, h } = size();
      if (event.key === "+" || event.key === "=") zoomAt(w / 2, h / 2, 1.2);
      else if (event.key === "-") zoomAt(w / 2, h / 2, 1 / 1.2);
      else if (event.key === "f") fit();
      else if (event.key === "c") focusFrontier();
    });

    controls.in.addEventListener("click", () => {
      const { w, h } = size();
      zoomAt(w / 2, h / 2, 1.2);
    });
    controls.out.addEventListener("click", () => {
      const { w, h } = size();
      zoomAt(w / 2, h / 2, 1 / 1.2);
    });
    controls.fit.addEventListener("click", fit);
    controls.focus.addEventListener("click", focusFrontier);
    window.addEventListener("resize", apply, { passive: true });

    // The map is drawn while the Curriculum workspace is still hidden, so the
    // plate has no measurable size yet and an immediate fit() would clamp to
    // minimum zoom. Fit on the first frame the plate actually has a box.
    let fitted = false;
    const observer = new ResizeObserver(() => {
      const { w, h } = size();
      if (!w || !h) return;
      if (!fitted) {
        fitted = true;
        fit();
      } else {
        apply();
      }
    });
    observer.observe(plate);
    apply();
  }

  function applyConstellationFilters(nodeIndex) {
    const { query, stage: selectedStage } = currentFilters();
    const hasFilter = Boolean(query) || Boolean(selectedStage);
    nodeIndex.forEach((group, id) => {
      if (!hasFilter) {
        group.classList.remove("filtered-out");
        return;
      }
      const matchesStage = !selectedStage || skillMeta(id)?.stage === selectedStage;
      const matchesQuery = !query || skillMatchesQuery(id, query);
      group.classList.toggle("filtered-out", !(matchesStage && matchesQuery));
    });
  }

  function truncateLabel(text) {
    const max = CONSTELLATION.LABEL_MAX;
    return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
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
    if (browserState.sort === "frequency") {
      const rank = { very_high: 0, high: 1, medium: 2, low: 3 };
      rows = [...rows].sort((a, b) => {
        const fa = frequencyFor(a);
        const fb = frequencyFor(b);
        if (!fa && !fb) return 0;
        if (!fa) return 1;
        if (!fb) return -1;
        return (rank[fa.tier] ?? 9) - (rank[fb.tier] ?? 9) || fb.companies - fa.companies;
      });
    }

    const counter = $("#browser-count");
    if (counter) {
      const solved = rows.filter((problem) => state.completedById.has(problem.id)).length;
      counter.textContent = `${solved} / ${rows.length} solved`;
    }
    if (!rows.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 8;
      cell.append(empty("No problems match this view."));
      row.append(cell);
      body.append(row);
    } else {
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
        const asked = document.createElement("td");
        asked.className = "num freq-cell";
        const freq = frequencyFor(problem);
        if (!freq) {
          asked.textContent = "–";
        } else {
          const spec = FREQUENCY_TIERS[freq.tier] || FREQUENCY_TIERS.low;
          asked.textContent = spec.glyph;
          asked.title =
            `${spec.label} · listed by ${freq.companies} companies` +
            (freq.top_companies?.length ? ` · top: ${freq.top_companies.join(", ")}` : "");
          asked.setAttribute("aria-label", `asked frequency ${spec.label}`);
        }
        const statusCell = document.createElement("td");
        statusCell.className = "status-cell";
        const statusPrimary = {
          not_started: "Not started",
          solved: "Solved",
          failed: "Recall failed",
          mastered: "Mastered",
        }[status.key] || status.label;
        const statusBadge = document.createElement("span");
        statusBadge.className = `status-badge status-${status.key}`;
        statusBadge.textContent = `${status.glyph} ${statusPrimary}`;
        statusCell.append(statusBadge);
        const statusDetail = status.label.startsWith(statusPrimary)
          ? status.label.slice(statusPrimary.length).replace(/^[ ·—-]+/, "")
          : status.label;
        statusCell.setAttribute("aria-label", `${statusPrimary}${statusDetail ? `, ${statusDetail}` : ""}`);
        if (statusDetail) {
          const detail = document.createElement("small");
          detail.className = "status-detail";
          detail.textContent = statusDetail;
          statusCell.append(detail);
        }
        const lock = document.createElement("td");
        lock.className = "num";
        if (state.completedById.has(problem.id)) lock.textContent = "";
        else if (!unlocked) lock.textContent = "–";
        else lock.textContent = unlocked.has(problem.id) ? "open" : "🔒";
        row.append(id, title, statusCell, difficulty, asked, role, importance, lock);
        body.append(row);
      });
    }

    const note = $("#frequency-note");
    if (note) {
      note.textContent = state.frequency
        ? `"Asked" = community snapshot from ${state.frequency.source} (${state.frequency.retrieved_at}); approximate, not live LeetCode data.`
        : `"Asked" column unavailable — run make refresh-frequency to generate curriculum/interview_frequency.json.`;
    }
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
    const displayStatus = problemStatus(problem.id).key;
    if (status === "active") return displayStatus === "solved";
    return displayStatus === status;
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
    // The map dims in place instead of re-rendering, so it keeps your pan/zoom.
    state.constellationFilter?.();
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

    if (record) body.append(codeGateCard(problem.id, record));
    const solutionCard = renderSolutionCode(problem.id);
    if (solutionCard) body.append(solutionCard);
    if (record?.mentor_scores) body.append(mentorScoreCard(record));

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

  // F9 code-execution gate: a new solve is only recorded once
  // solutions/<ID>.py runs its embedded asserts — unless the session was
  // logged with --no-code, which update_progress.py notes on the record.
  // Show the learner's actual solution code, per problem, Java or Python. Each
  // stored file (feed.solution_files) is fetched and rendered inline; without
  // the server the fetch fails and the block says so.
  function renderSolutionCode(problemId) {
    const files = (state.feed?.solution_files || []).filter((f) => f.problem_id === problemId);
    if (!files.length) return null;

    const card = document.createElement("article");
    card.className = "note-card";
    const heading = document.createElement("h4");
    heading.textContent = files.length > 1 ? "Your solutions" : "Your solution";
    card.append(heading);

    files.forEach((file) => {
      const block = document.createElement("div");
      block.className = "solution-file";

      const head = document.createElement("div");
      head.className = "solution-file-head";
      const name = document.createElement("span");
      name.className = "num solution-file-name";
      name.textContent = file.path;
      const lang = pill(file.language, "");
      lang.classList.add("microlabel");
      head.append(name, lang);

      const pre = document.createElement("pre");
      pre.className = "solution-code";
      const code = document.createElement("code");
      code.textContent = "Loading…";
      pre.append(code);
      block.append(head, pre);
      card.append(block);

      // Relative to /web_dashboard/, so ../solutions/<file> under the server.
      fetch(`../${file.path}`)
        .then((response) => {
          if (!response.ok) throw new Error(String(response.status));
          return response.text();
        })
        .then((text) => {
          code.textContent = text;
        })
        .catch(() => {
          code.textContent = `Code view needs the server — open ${file.path} directly, or run python3 scripts/serve_dashboard.py`;
          code.classList.add("solution-code-error");
        });
    });

    return card;
  }

  function codeGateCard(problemId, record) {
    const notes = Array.isArray(record.notes) ? record.notes : record.notes ? [record.notes] : [];
    const whiteboard = notes.some((note) => String(note).includes("--no-code"));
    const card = document.createElement("article");
    card.className = "note-card";

    const heading = document.createElement("h4");
    heading.textContent = "Code-execution gate";

    // Link the files that actually exist (feed.solution_files); otherwise show
    // the expected path as plain text rather than a dead link.
    const files = (state.feed?.solution_files || []).filter((f) => f.problem_id === problemId);
    const path = document.createElement("p");
    path.className = "num solution-path";
    if (files.length) {
      files.forEach((file, index) => {
        if (index) path.append(document.createTextNode(" · "));
        const link = document.createElement("a");
        link.href = `../${file.path}`;
        link.textContent = file.path;
        path.append(link);
      });
    } else {
      path.textContent = `solutions/${problemId}.py`;
    }

    // The record only ever proves the negative: update_progress.py notes a
    // --no-code bypass but writes nothing when the gate passes, and records
    // predating F9 have no note at all. Say what is known, claim nothing else.
    const status = document.createElement("p");
    status.className = `gate-status microlabel ${whiteboard ? "warn" : ""}`.trim();
    status.textContent = whiteboard
      ? "⚠ whiteboard session — recorded with --no-code, no solution file was executed"
      : "· no --no-code override on this record";

    card.append(heading, path, status);
    return card;
  }

  // F7 mentor-graded pass: self and mentor side by side. A gap wider than the
  // divergence threshold is the signal to discuss, not to average away.
  const MENTOR_DIVERGENCE = 2;

  function mentorScoreBlock(title, selfScores, mentorScores, max) {
    const dimensions = [...new Set([...Object.keys(selfScores), ...Object.keys(mentorScores)])];
    if (!dimensions.length) return null;
    const wrap = document.createElement("div");
    wrap.className = "mentor-block";
    const table = document.createElement("table");
    table.className = "mentor-table";
    table.innerHTML = `
      <caption class="microlabel">${title} · out of ${max}</caption>
      <thead>
        <tr>
          <th scope="col">Dimension</th>
          <th scope="col">Self</th>
          <th scope="col">Mentor</th>
          <th scope="col">Gap</th>
        </tr>
      </thead>
    `;
    const tbody = document.createElement("tbody");
    dimensions.forEach((dimension) => {
      const selfValue = selfScores[dimension];
      const mentorValue = mentorScores[dimension];
      const comparable = typeof selfValue === "number" && typeof mentorValue === "number";
      const gap = comparable ? Math.abs(selfValue - mentorValue) : null;
      const row = document.createElement("tr");
      row.innerHTML = `
        <th scope="row">${dimension.replaceAll("_", " ")}</th>
        <td class="num">${text(selfValue)}</td>
        <td class="num">${text(mentorValue)}</td>
      `;
      const gapCell = document.createElement("td");
      if (gap != null && gap > MENTOR_DIVERGENCE) {
        const chip = pill(`discuss · ${gap}`, "warn");
        chip.classList.add("num");
        gapCell.append(chip);
      } else {
        gapCell.className = "num";
        gapCell.textContent = gap == null ? "-" : String(gap);
      }
      row.append(gapCell);
      tbody.append(row);
    });
    table.append(tbody);
    wrap.append(table);
    return wrap;
  }

  function mentorScoreCard(record) {
    const mentor = record.mentor_scores || {};
    const scoring = state.datasets.scoring || {};
    const card = document.createElement("article");
    card.className = "note-card";
    const heading = document.createElement("h4");
    heading.textContent = "Self vs mentor scores";
    card.append(heading);

    const blocks = [
      mentorScoreBlock(
        "Thinking",
        record.thinking_score || {},
        mentor.thinking_score || {},
        scoring.scale?.maximum || 4,
      ),
      mentorScoreBlock(
        "Interview",
        record.interview_score || {},
        mentor.interview_score || {},
        scoring.interview_scale?.maximum || 10,
      ),
    ].filter(Boolean);
    if (!blocks.length) {
      card.append(empty("A mentor pass was recorded but carried no dimension scores."));
      return card;
    }
    blocks.forEach((block) => card.append(block));
    card.append(
      chartNote(
        `Any dimension more than ${MENTOR_DIVERGENCE} apart is flagged to discuss — the gap is the lesson.`,
      ),
    );
    return card;
  }

  function revisionHistoryItem(event) {
    const recall = event.thinking_score && typeof event.thinking_score === "object"
      ? Object.entries(event.thinking_score)
          .filter(([, value]) => typeof value === "number")
          .map(([key, value]) => `${key.replaceAll("_", " ")} ${value}`)
          .join(" · ")
      : "";
    const details = [
      // A reactivation carries why it was re-opened and what it was demoted
      // from; without that the event reads as an unexplained stage reset.
      event.reason
        ? `<p><strong>Reason:</strong> ${event.reason}${
            event.prior_status
              ? ` <span class="small-muted">(was ${event.prior_status} at stage ${event.prior_stage ?? "-"})</span>`
              : ""
          }</p>`
        : "",
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
          // Forward skill edges kept raw for the constellation (design section 8:
          // the map is the real dependency_graph.json DAG, not a re-derivation).
          state.reverseEdges = {
            problemUnlocks,
            skillUnlocks,
            skillDeps: graph.skill_dependencies || {},
          };
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

  // ---------------------------------------------------------------------------
  // Evidence workspace (design section 5): the leading indicators that say
  // whether the practice is working — hint independence, mock verdict trend,
  // young/mature retention split, and the 30-day showing-up chart. All four
  // read the feed or raw datasets; none of them recompute scheduler logic.
  // ---------------------------------------------------------------------------

  const HINT_MAX_FALLBACK = 7;
  // The ladder's top rung comes from scoring.json hint_levels, so widening the
  // ladder there does not silently clip this chart.
  function hintMax() {
    const levels = Object.keys(state.datasets.scoring?.hint_levels || {})
      .map(Number)
      .filter(Number.isFinite);
    return levels.length ? Math.max(...levels) : HINT_MAX_FALLBACK;
  }
  const HINT_BAND_FALLBACK = [
    { from: 0, to: 2, name: "independent", note: "full mastery credit", tone: "good" },
    { from: 3, to: 4, name: "guided", note: "half credit", tone: "warn" },
    { from: 5, to: 7, name: "rescued", note: "attempt only", tone: "bad" },
  ];
  const HINT_BAND_STYLE = {
    1: { name: "independent", note: "full mastery credit", tone: "good" },
    0.5: { name: "guided", note: "half credit", tone: "warn" },
    0: { name: "rescued", note: "attempt only", tone: "bad" },
  };
  const MOCK_VERDICT_TONE = {
    strong_hire: "good",
    hire: "good",
    no_hire: "warn",
    strong_no_hire: "bad",
  };
  const MOCK_SCORE_MAX = 4;


  // Bands mirror scoring.json `hint_mastery_discount`: consecutive hint levels
  // carrying the same mastery weight form one band, so the chart can never
  // disagree with the tier the scorer actually applies.
  function hintBands() {
    const discount = state.datasets.scoring?.hint_mastery_discount || {};
    const top = hintMax();
    const bands = [];
    for (let level = 0; level <= top; level += 1) {
      const weight = discount[String(level)];
      if (typeof weight !== "number") return HINT_BAND_FALLBACK;
      const last = bands.at(-1);
      if (last && last.weight === weight) last.to = level;
      else bands.push({ from: level, to: level, weight });
    }
    return bands.map((band) => ({
      ...band,
      ...(HINT_BAND_STYLE[band.weight] || { name: `weight ${band.weight}`, note: "", tone: "" }),
    }));
  }

  // Pure display transform (design section 3b allows rolling means client-side).
  function rollingMean(values, window) {
    return values.map((_, index) => {
      const slice = values.slice(Math.max(0, index - window + 1), index + 1);
      return slice.reduce((sum, value) => sum + value, 0) / slice.length;
    });
  }

  function chartLegend(entries) {
    const legend = document.createElement("div");
    legend.className = "chart-legend";
    entries.forEach(({ label, shape, color }) => {
      const item = document.createElement("span");
      const mark = document.createElement("i");
      mark.className = `legend-${shape || "dot"}`;
      mark.style.background = color;
      item.append(mark, document.createTextNode(label));
      legend.append(item);
    });
    return legend;
  }

  function chartNote(message) {
    const note = document.createElement("p");
    note.className = "chart-note microlabel";
    note.textContent = message;
    return note;
  }

  function renderHintIndependence() {
    const host = $("#hint-chart");
    if (!host) return;
    host.replaceChildren();
    const badge = $("#hint-latest");
    if (!feedAvailable()) {
      host.removeAttribute("aria-label");
      if (badge) {
        badge.textContent = "offline";
        badge.className = "pill num warn";
      }
      host.append(degradedBanner());
      return;
    }

    const points = state.feed.hint_trajectory || [];
    if (!points.length) {
      host.removeAttribute("aria-label");
      if (badge) {
        badge.textContent = "0 solves";
        badge.className = "pill num";
      }
      host.append(empty("No solves recorded yet — the trajectory starts with your first completion."));
      return;
    }

    const top = hintMax();
    const levels = points.map((point) => clamp(Number(point.hint_level) || 0, 0, top));
    const means = rollingMean(levels, 5);
    const bands = hintBands();
    const bandFor = (level) => bands.find((band) => level >= band.from && level <= band.to);
    const latest = levels.at(-1);
    const latestBand = bandFor(latest);
    if (badge) {
      badge.textContent = `latest ${latest} · ${latestBand ? latestBand.name : "unbanded"}`;
      badge.className = `pill num ${latestBand?.tone || ""}`.trim();
    }

    const W = 660;
    const H = 220;
    const PAD_L = 30;
    const PAD_R = 118;
    const PAD_TOP = 12;
    const PAD_BOTTOM = 30;
    const plotW = W - PAD_L - PAD_R;
    const plotH = H - PAD_TOP - PAD_BOTTOM;
    const xAt = (index) =>
      PAD_L + (points.length === 1 ? plotW / 2 : (plotW * index) / (points.length - 1));
    const yAt = (level) => PAD_TOP + plotH - (plotH * clamp(level, 0, top)) / top;

    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "insight-svg" });

    // Mastery-tier bands, tinted; the name beside each carries the meaning so
    // the tier is never communicated by color alone.
    bands.forEach((band) => {
      const bandTop = yAt(Math.min(top, band.to + 0.5));
      const bottom = yAt(Math.max(0, band.from - 0.5));
      svg.append(
        svgEl("rect", {
          x: PAD_L,
          y: bandTop,
          width: plotW,
          height: Math.max(1, bottom - bandTop),
          class: `hint-band ${band.tone}`.trim(),
        }),
      );
      // A hairline at each band edge: the 4% tint alone is deliberately faint.
      if (bandTop > PAD_TOP) {
        svg.append(
          svgEl("line", {
            x1: PAD_L,
            y1: bandTop,
            x2: PAD_L + plotW,
            y2: bandTop,
            class: "hint-band-edge",
          }),
        );
      }
      svg.append(
        svgEl(
          "text",
          { x: W - PAD_R + 10, y: (bandTop + bottom) / 2 + 4, class: "insight-band-label" },
          `${band.name} ${band.from}-${band.to}`,
        ),
      );
    });

    // Recessive y ticks at the band edges.
    const ticks = [...new Set([0, ...bands.map((band) => band.from), top])].sort((a, b) => a - b);
    ticks.forEach((tick) => {
      svg.append(
        svgEl(
          "text",
          { x: PAD_L - 8, y: yAt(tick) + 4, "text-anchor": "end", class: "insight-axis" },
          String(tick),
        ),
      );
    });
    svg.append(
      svgEl("line", {
        x1: PAD_L,
        y1: yAt(0),
        x2: PAD_L + plotW,
        y2: yAt(0),
        class: "insight-baseline",
      }),
    );

    // Rolling mean is the trend line; raw solves are the markers.
    svg.append(
      svgEl("polyline", {
        points: means.map((mean, index) => `${xAt(index).toFixed(1)},${yAt(mean).toFixed(1)}`).join(" "),
        class: "insight-line",
      }),
    );
    points.forEach((point, index) => {
      const band = bandFor(levels[index]);
      const label = `${point.problem_id || "solve"} · ${point.date} · hint ${levels[index]}${
        band ? ` (${band.name})` : ""
      }`;
      svg.append(
        svgEl("circle", {
          cx: xAt(index),
          cy: yAt(levels[index]),
          r: 4,
          class: "insight-marker",
        }),
      );
      // The hover target is generous even though the mark is 8px.
      const hit = svgEl("circle", {
        cx: xAt(index),
        cy: yAt(levels[index]),
        r: 13,
        class: "insight-hit",
      });
      hit.append(svgEl("title", {}, label));
      svg.append(hit);
    });

    // Dated x ticks: first, middle, last.
    const tickIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
    tickIndexes.forEach((index) => {
      svg.append(
        svgEl(
          "text",
          {
            x: xAt(index),
            y: H - 10,
            "text-anchor": index === 0 ? "start" : index === points.length - 1 ? "end" : "middle",
            class: "insight-axis",
          },
          points[index].date,
        ),
      );
    });

    host.append(svg);
    host.append(
      chartLegend([
        { label: "solve · hint level used", shape: "dot", color: "var(--series-1)" },
        { label: "5-solve rolling mean", shape: "line", color: "var(--series-1)" },
      ]),
    );
    host.append(
      chartNote(
        "Lower is better. Bands mirror hint_mastery_discount in scoring.json: independent solves earn full skill-mastery credit, guided half, rescued none.",
      ),
    );
    host.setAttribute(
      "aria-label",
      `Hint independence over ${points.length} solve${points.length === 1 ? "" : "s"}. ` +
        `Latest hint level ${latest}${latestBand ? ` (${latestBand.name})` : ""}. ` +
        `Rolling mean now ${means.at(-1).toFixed(1)} of a maximum ${top}.`,
    );
  }

  function mockSparkline(dimension, mocks) {
    // An ungraded dimension is null, never 0: coercing it would draw a
    // catastrophic drop where the truth is "this mock did not score it".
    const values = mocks.map((mock) => {
      const raw = mock.scores?.[dimension];
      return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
    });
    const graded = values.filter((value) => value != null);
    const latest = [...values].reverse().find((value) => value != null) ?? null;
    const card = document.createElement("article");
    card.className = "sparkline-card";

    const label = document.createElement("span");
    label.className = "microlabel";
    label.textContent = dimension.replaceAll("_", " ");

    const W = 120;
    const H = 34;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "sparkline-svg" });
    const xAt = (index) => (values.length === 1 ? W / 2 : (W * index) / (values.length - 1));
    const yAt = (value) => H - 3 - ((H - 6) * clamp(value, 0, MOCK_SCORE_MAX)) / MOCK_SCORE_MAX;
    // Gaps break the line into segments rather than dragging it to the floor.
    let segment = [];
    const flush = () => {
      if (segment.length > 1) {
        svg.append(svgEl("polyline", { points: segment.join(" "), class: "sparkline-stroke" }));
      }
      segment = [];
    };
    values.forEach((value, index) => {
      if (value == null) {
        flush();
        return;
      }
      segment.push(`${xAt(index).toFixed(1)},${yAt(value).toFixed(1)}`);
    });
    flush();
    const lastGradedIndex = values.reduce((last, value, index) => (value != null ? index : last), -1);
    if (lastGradedIndex >= 0) {
      svg.append(
        svgEl("circle", {
          cx: xAt(lastGradedIndex),
          cy: yAt(values[lastGradedIndex]),
          r: 4,
          class: "sparkline-end",
        }),
      );
    }

    const value = document.createElement("strong");
    value.className = "num";
    value.textContent = latest == null ? "not graded" : `${latest} / ${MOCK_SCORE_MAX}`;

    card.append(label, svg, value);
    if (graded.length < values.length) {
      const gap = document.createElement("small");
      gap.className = "microlabel";
      gap.textContent = `${values.length - graded.length} of ${values.length} mocks ungraded`;
      card.append(gap);
    }
    card.setAttribute(
      "aria-label",
      `${dimension.replaceAll("_", " ")}: ${values
        .map((entry) => (entry == null ? "not graded" : entry))
        .join(", ")} out of ${MOCK_SCORE_MAX} across ${values.length} mock${
        values.length === 1 ? "" : "s"
      }.`,
    );
    card.setAttribute("role", "img");
    return card;
  }

  function renderMockTrend() {
    const host = $("#mock-trend-body");
    if (!host) return;
    host.replaceChildren();
    if (!feedAvailable()) {
      host.append(degradedBanner());
      return;
    }
    const mocks = state.feed.mock_history || [];
    if (!mocks.length) {
      host.append(empty("No mocks recorded yet — the first weekend mock is scheduled automatically."));
      return;
    }

    const timeline = document.createElement("div");
    timeline.className = "mock-timeline";
    mocks.forEach((mock) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "mock-row";

      const tone = MOCK_VERDICT_TONE[mock.verdict] || "";
      const dot = document.createElement("span");
      dot.className = `mock-dot ${tone}`.trim();
      dot.setAttribute("aria-hidden", "true");

      const date = document.createElement("span");
      date.className = "mock-date num";
      date.textContent = mock.date || "undated";

      const problem = state.problemsById.get(mock.problem_id);
      const title = document.createElement("span");
      title.className = "mock-problem";
      title.textContent = problem
        ? `${mock.problem_id} · ${problem.title}`
        : mock.problem_id || "problem not in curriculum";

      // The verdict always carries its own text chip — never color alone.
      const chip = pill(String(mock.verdict || "unscored").replaceAll("_", " "), tone);
      chip.classList.add("num");

      const duration = document.createElement("span");
      duration.className = "mock-duration num";
      duration.textContent = mock.duration_minutes != null ? `${mock.duration_minutes} min` : "—";

      row.append(dot, date, title, chip, duration);
      if (mock.problem_id) row.addEventListener("click", () => openProblemModal(mock.problem_id));
      timeline.append(row);
    });
    host.append(timeline);

    const dimensions = [];
    mocks.forEach((mock) => {
      Object.keys(mock.scores || {}).forEach((key) => {
        if (!dimensions.includes(key)) dimensions.push(key);
      });
    });
    if (!dimensions.length) {
      host.append(chartNote("Rubric scores appear once a mock is graded on the five dimensions."));
      return;
    }
    const grid = document.createElement("div");
    grid.className = "sparkline-grid";
    dimensions.forEach((dimension) => grid.append(mockSparkline(dimension, mocks)));
    host.append(grid, chartNote(`Rubric dimensions, 1-${MOCK_SCORE_MAX}, oldest to newest mock.`));
  }

  function renderRetentionTiles() {
    const host = $("#retention-tiles");
    if (!host) return;
    host.replaceChildren();
    if (!feedAvailable()) {
      host.append(degradedBanner());
      return;
    }
    const retention = state.feed.retention || {};
    const counts = retention.counts || {};
    const target = state.feed.readiness?.gates?.revision_pass?.target ?? 0.9;
    // "Mature" is whatever the policy says R3+ is, so the copy tracks
    // scoring.json's revision_policy instead of restating it from memory.
    const intervals = state.feed.policy?.intervals || {};
    const matureDays = Object.entries(intervals)
      .filter(([label]) => Number(label.replace("R", "")) >= 3)
      .map(([, days]) => `${days}-day`);
    const matureNote = matureDays.length
      ? `${matureDays.join(" and ")} intervals`
      : "long intervals";
    const youngDays = Object.entries(intervals)
      .filter(([label]) => Number(label.replace("R", "")) <= 2)
      .map(([, days]) => `${days}-day`);
    const youngNote = youngDays.length
      ? `${youngDays.join(" and ")} intervals`
      : "short intervals";
    const youngTotal = counts.young_total || 0;
    const matureTotal = counts.mature_total || 0;
    const youngPass = counts.young_pass || 0;
    const maturePass = counts.mature_pass || 0;

    const tiles = [
      {
        label: "Overall recall",
        rate: retention.overall_pass_rate,
        detail: `${youngPass + maturePass}/${youngTotal + matureTotal} reviews passed`,
        note: `target ≥ ${formatPct(target)}`,
      },
      {
        label: "Young · R1-R2",
        rate: retention.young_pass_rate,
        detail: youngTotal ? `${youngPass}/${youngTotal} reviews passed` : "no R1-R2 reviews yet",
        note: youngNote,
      },
      {
        label: "Mature · R3+",
        rate: retention.mature_pass_rate,
        detail: matureTotal ? `${maturePass}/${matureTotal} reviews passed` : "no R3+ reviews yet",
        note: matureNote,
      },
    ];

    tiles.forEach((tile) => {
      const node = document.createElement("article");
      node.className = "retention-tile";

      const label = document.createElement("span");
      label.className = "microlabel";
      label.textContent = tile.label;

      const value = document.createElement("strong");
      value.className = "num";
      value.textContent = tile.rate == null ? "—" : formatPct(tile.rate);

      // The tone drives the tile's top rule too, so the colour states what the
      // status text states rather than repeating the tile's position in the row.
      const status = document.createElement("span");
      if (tile.rate == null) {
        status.className = "retention-status microlabel";
        status.textContent = "· not enough data";
      } else if (tile.rate >= target) {
        status.className = "retention-status microlabel good";
        status.textContent = "✓ healthy";
        node.dataset.tone = "good";
      } else {
        status.className = "retention-status microlabel bad";
        status.textContent = "⚠ below target";
        node.dataset.tone = "bad";
      }

      const detail = document.createElement("small");
      detail.className = "num";
      detail.textContent = tile.detail;

      const note = document.createElement("small");
      note.className = "microlabel";
      note.textContent = tile.note;

      node.append(label, value, status, detail, note);
      host.append(node);
    });
  }

  // ---------------------------------------------------------------------------
  // Revision calendar (Evidence): a month grid over feed.revision_calendar.
  // A day with recall work shows a count; clicking or Entering it lists the
  // topics due that day. Built as a WAI-ARIA grid — the container is a table
  // with role="grid", day buttons carry a roving tabindex, and arrow keys /
  // Home / End move focus. Python projects the schedule; this only renders it.
  // ---------------------------------------------------------------------------

  const CAL_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const CAL_DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  // View month is component-local; default set on first render to the month of
  // the earliest scheduled item (or the reference month when nothing is due).
  const calendarView = { year: null, month: null, selected: null };

  function calendarByDate() {
    const map = new Map();
    (state.feed?.revision_calendar || []).forEach((day) => map.set(day.date, day.items || []));
    return map;
  }

  function calendarMonthKey(year, month) {
    return `${year}-${String(month + 1).padStart(2, "0")}`;
  }

  // ---------------------------------------------------------------------------
  // Activity heatmap (Evidence): a GitHub/LeetCode-style year grid over
  // feed.activity_heatmap. Each day is a square split on the diagonal — the
  // lower-left triangle's intensity is problems solved, the upper-right is
  // revisions done — so a day that had both shows both at once. Position (which
  // triangle), not colour alone, says which activity; exact counts are in the
  // tooltip and aria-label. Python counts; the JS only renders.
  // ---------------------------------------------------------------------------

  const HEAT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  // Small daily counts, so a compact bucketing: 0, 1, 2, 3-4, 5+.
  function heatLevel(count) {
    if (!count) return 0;
    if (count >= 5) return 4;
    if (count >= 3) return 3;
    return count; // 1 or 2
  }

  function mondayOf(d) {
    const copy = new Date(d);
    const back = (copy.getDay() + 6) % 7; // days since Monday
    copy.setDate(copy.getDate() - back);
    return copy;
  }

  function renderActivityHeatmap() {
    const host = $("#heatmap");
    const legend = $("#heatmap-legend");
    const total = $("#heatmap-total");
    if (!host) return;
    host.replaceChildren();
    if (legend) legend.replaceChildren();

    if (!feedAvailable()) {
      host.removeAttribute("aria-label");
      if (total) {
        total.textContent = "offline";
        total.className = "pill num warn";
      }
      host.append(degradedBanner());
      return;
    }

    const hm = state.feed.activity_heatmap || { days: [] };
    const byDate = new Map((hm.days || []).map((d) => [d.date, d]));
    const solvedTotal = (hm.days || []).reduce((s, d) => s + (d.solves || 0), 0);
    const revisedTotal = (hm.days || []).reduce((s, d) => s + (d.revisions || 0), 0);
    if (total) {
      total.textContent = `${solvedTotal} solved · ${revisedTotal} revised`;
      total.className = "pill num";
    }

    if (!(hm.days || []).length) {
      host.removeAttribute("aria-label");
      host.append(empty("No activity recorded yet — solves and revisions will appear here day by day."));
      return;
    }

    const start = parseDate(hm.start);
    const end = parseDate(hm.end) || todayDate();
    const gridStart = mondayOf(start);

    const CELL = 18;
    const GAP = 5;
    const STEP = CELL + GAP;
    const LEFT = 38; // room for the full weekday name
    const TOP = 22; // month labels
    const PAD = 14; // breathing room inside the panel

    const weeks = Math.floor((mondayOf(end) - gridStart) / (7 * 86400000)) + 1;
    const W = PAD + LEFT + weeks * STEP + PAD;
    const H = TOP + 7 * STEP + PAD;

    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "heatmap-svg", width: W, height: H });

    // One rounded-square clip, reused by every cell (each cell group is
    // translated into place, so a single origin clip rounds all of them).
    const defs = svgEl("defs", {});
    const clip = svgEl("clipPath", { id: "heat-round", clipPathUnits: "userSpaceOnUse" });
    clip.append(svgEl("rect", { x: 0, y: 0, width: CELL, height: CELL, rx: 4 }));
    defs.append(clip);
    svg.append(defs);

    // Every weekday is labelled (not just Mon/Wed/Fri) — there is room and it
    // reads clearer.
    CAL_DOW.forEach((name, row) => {
      svg.append(svgEl("text",
        { x: PAD + LEFT - 8, y: TOP + row * STEP + CELL - 4, "text-anchor": "end", class: "heat-axis" }, name));
    });

    let lastMonth = -1;
    const cursor = new Date(gridStart);
    for (let col = 0; col < weeks; col += 1) {
      // Month label above the first column that starts a new month.
      const weekStart = new Date(gridStart);
      weekStart.setDate(gridStart.getDate() + col * 7);
      if (weekStart.getMonth() !== lastMonth) {
        lastMonth = weekStart.getMonth();
        svg.append(svgEl("text",
          { x: PAD + LEFT + col * STEP, y: TOP - 8, class: "heat-axis" }, HEAT_MONTHS[lastMonth]));
      }
      for (let row = 0; row < 7; row += 1) {
        const iso = isoDate(cursor);
        cursor.setDate(cursor.getDate() + 1);
        if (cursor <= gridStart) continue; // never happens; keeps cursor advancing
        const dayDate = parseDate(iso);
        if (dayDate < start || dayDate > end) continue;

        const x = PAD + LEFT + col * STEP;
        const y = TOP + row * STEP;
        const rec = byDate.get(iso) || { solves: 0, skills: 0, revisions: 0 };
        const sL = heatLevel(rec.solves);
        const rL = heatLevel(rec.revisions);

        // Cell drawn in local 0..CELL coords and translated into place, so the
        // shared rounded clip applies to both triangles; the border rounds too.
        const cell = svgEl("g", { class: "heat-cell", role: "img", transform: `translate(${x},${y})` });
        // lower-left triangle = solves; upper-right triangle = revisions.
        cell.append(svgEl("path", {
          d: `M0,0 L0,${CELL} L${CELL},${CELL} Z`,
          "clip-path": "url(#heat-round)",
          class: `heat-solve l${sL}`,
        }));
        cell.append(svgEl("path", {
          d: `M0,0 L${CELL},0 L${CELL},${CELL} Z`,
          "clip-path": "url(#heat-round)",
          class: `heat-rev l${rL}`,
        }));
        cell.append(svgEl("rect", { x: 0.5, y: 0.5, width: CELL - 1, height: CELL - 1, rx: 4, class: "heat-border" }));

        const parts = [];
        if (rec.solves) parts.push(`${rec.solves} solved${rec.skills ? ` (${rec.skills} skill${rec.skills === 1 ? "" : "s"})` : ""}`);
        if (rec.revisions) parts.push(`${rec.revisions} revised`);
        const label = `${iso}: ${parts.length ? parts.join(", ") : "no activity"}`;
        cell.setAttribute("aria-label", label);
        cell.append(svgEl("title", {}, label));
        svg.append(cell);
      }
    }

    host.append(svg);
    host.setAttribute("aria-label",
      `Activity heatmap from ${hm.start} to ${hm.end}: ${solvedTotal} problems solved and ${revisedTotal} revisions, by day.`);

    if (legend) {
      const swatch = (cls, lvl) => {
        const s = svgEl("svg", { viewBox: "0 0 13 13", class: "heat-swatch", width: 13, height: 13 });
        s.append(svgEl("rect", { x: 0, y: 0, width: 13, height: 13, rx: 3, class: `${cls} l${lvl}` }));
        s.append(svgEl("rect", { x: 0.5, y: 0.5, width: 12, height: 12, rx: 3, class: "heat-border" }));
        return s;
      };

      // A worked split-cell example makes the two-triangle encoding legible.
      const example = document.createElement("div");
      example.className = "heat-legend-example";
      const sample = svgEl("svg", { viewBox: "0 0 26 26", class: "heat-sample", width: 26, height: 26 });
      sample.append(svgEl("path", { d: "M0,0 L0,26 L26,26 Z", class: "heat-solve l3" }));
      sample.append(svgEl("path", { d: "M0,0 L26,0 L26,26 Z", class: "heat-rev l3" }));
      sample.append(svgEl("rect", { x: 0.5, y: 0.5, width: 25, height: 25, rx: 5, class: "heat-border" }));
      const caption = document.createElement("span");
      caption.className = "microlabel";
      caption.innerHTML = "each day splits: <strong>solved</strong> lower-left, <strong>revised</strong> upper-right";
      example.append(sample, caption);

      const ramp = (label, cls) => {
        const row = document.createElement("span");
        row.className = "heat-legend-row";
        const name = document.createElement("span");
        name.className = "microlabel heat-legend-name";
        name.textContent = label;
        const less = document.createElement("span");
        less.className = "microlabel";
        less.textContent = "less";
        const more = document.createElement("span");
        more.className = "microlabel";
        more.textContent = "more";
        row.append(name, less);
        [1, 2, 3, 4].forEach((lvl) => row.append(swatch(cls, lvl)));
        row.append(more);
        return row;
      };
      legend.append(example, ramp("solved", "heat-solve"), ramp("revised", "heat-rev"));
    }
  }

  function renderRevisionCalendar() {
    const grid = $("#calendar-grid");
    const detail = $("#calendar-detail");
    const label = $("#calendar-month");
    if (!grid || !detail) return;
    grid.replaceChildren();
    detail.replaceChildren();

    if (!feedAvailable()) {
      if (label) label.textContent = "offline";
      grid.append(degradedBanner());
      return;
    }

    const byDate = calendarByDate();
    const today = referenceDate();

    // Seed the view month once: earliest scheduled date, else the current month.
    if (calendarView.year == null) {
      const first = [...byDate.keys()].sort()[0] || today;
      const seed = parseDate(first);
      calendarView.year = seed.getFullYear();
      calendarView.month = seed.getMonth();
    }
    const { year, month } = calendarView;
    if (label) label.textContent = `${CAL_MONTHS[month]} ${year}`;

    const table = document.createElement("table");
    table.className = "calendar-table";
    table.setAttribute("role", "grid");
    table.setAttribute("aria-label", `Revision calendar, ${CAL_MONTHS[month]} ${year}`);

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    CAL_DOW.forEach((dow) => {
      const th = document.createElement("th");
      th.scope = "col";
      th.className = "microlabel";
      th.textContent = dow;
      headRow.append(th);
    });
    thead.append(headRow);
    table.append(thead);

    const tbody = document.createElement("tbody");
    // Monday-first offset for the 1st of the month.
    const firstDow = (new Date(year, month, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];
    for (let i = 0; i < firstDow; i += 1) cells.push(null);
    for (let d = 1; d <= daysInMonth; d += 1) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);

    const dayButtons = [];
    for (let row = 0; row < cells.length / 7; row += 1) {
      const tr = document.createElement("tr");
      for (let col = 0; col < 7; col += 1) {
        const td = document.createElement("td");
        td.setAttribute("role", "gridcell");
        const dayNum = cells[row * 7 + col];
        if (dayNum == null) {
          td.className = "calendar-cell empty";
          tr.append(td);
          continue;
        }
        const iso = isoDate(new Date(year, month, dayNum));
        const items = byDate.get(iso) || [];
        const isToday = iso === today;
        const isPast = iso < today;

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "calendar-day";
        if (isToday) btn.classList.add("today");
        if (isPast) btn.classList.add("past");
        if (items.length) btn.classList.add("has-items");
        btn.dataset.date = iso;
        btn.tabIndex = -1;

        const num = document.createElement("span");
        num.className = "calendar-daynum num";
        num.textContent = String(dayNum);
        btn.append(num);

        if (items.length) {
          const count = document.createElement("span");
          count.className = "calendar-count num";
          count.textContent = String(items.length);
          btn.append(count);
        }
        btn.setAttribute(
          "aria-label",
          `${CAL_MONTHS[month]} ${dayNum}${isToday ? ", today" : ""}. ${
            items.length
              ? `${items.length} revision${items.length === 1 ? "" : "s"}: ${items
                  .map((i) => `${i.stage_label} ${i.title || i.problem_id}`)
                  .join(", ")}`
              : "no revisions"
          }`,
        );
        btn.addEventListener("click", () => selectCalendarDay(iso));
        dayButtons.push(btn);
        td.append(btn);
        tr.append(td);
      }
      tbody.append(tr);
    }
    table.append(tbody);
    grid.append(table);

    wireCalendarKeyboard(dayButtons);

    // Roving tabindex: today if in view, else the first day with work, else day 1.
    const initial =
      dayButtons.find((b) => b.dataset.date === today) ||
      dayButtons.find((b) => b.classList.contains("has-items")) ||
      dayButtons[0];
    if (initial) initial.tabIndex = 0;

    // Show detail for the selected day if it is in this month, else the first
    // day this month that has work, else a prompt.
    const inMonth = (iso) => iso && iso.slice(0, 7) === calendarMonthKey(year, month);
    const detailDate =
      (inMonth(calendarView.selected) && calendarView.selected) ||
      dayButtons.find((b) => b.classList.contains("has-items"))?.dataset.date ||
      null;
    renderCalendarDetail(detailDate);
  }

  function wireCalendarKeyboard(dayButtons) {
    const index = (btn) => dayButtons.indexOf(btn);
    const focusAt = (i) => {
      const clamped = Math.max(0, Math.min(dayButtons.length - 1, i));
      dayButtons.forEach((b) => (b.tabIndex = -1));
      dayButtons[clamped].tabIndex = 0;
      dayButtons[clamped].focus();
    };
    dayButtons.forEach((btn) => {
      btn.addEventListener("keydown", (event) => {
        const i = index(btn);
        const rowStart = i - (i % 7);
        const map = {
          ArrowRight: i + 1,
          ArrowLeft: i - 1,
          ArrowDown: i + 7,
          ArrowUp: i - 7,
          Home: rowStart,
          End: rowStart + 6,
        };
        if (event.key in map) {
          event.preventDefault();
          focusAt(map[event.key]);
        } else if (event.key === "PageUp" || event.key === "PageDown") {
          event.preventDefault();
          stepCalendarMonth(event.key === "PageUp" ? -1 : 1);
        }
      });
    });
  }

  function selectCalendarDay(iso) {
    calendarView.selected = iso;
    renderCalendarDetail(iso);
    const grid = $("#calendar-grid");
    if (grid) {
      grid.querySelectorAll(".calendar-day").forEach((b) =>
        b.setAttribute("aria-selected", b.dataset.date === iso ? "true" : "false"),
      );
    }
  }

  function renderCalendarDetail(iso) {
    const detail = $("#calendar-detail");
    if (!detail) return;
    detail.replaceChildren();
    if (!iso) {
      detail.append(empty("Nothing scheduled this month. Pick a day to see its recall load."));
      return;
    }
    const items = calendarByDate().get(iso) || [];
    const head = document.createElement("p");
    head.className = "calendar-detail-date num";
    head.textContent = iso;
    detail.append(head);

    if (!items.length) {
      detail.append(empty("No revisions due on this day."));
      return;
    }
    const list = document.createElement("div");
    list.className = "calendar-detail-list";
    items.forEach((item) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "calendar-detail-row";
      const stage = pill(item.stage_label, item.projected ? "" : "accent");
      stage.classList.add("num");
      const title = document.createElement("span");
      title.className = "calendar-detail-title";
      title.textContent = item.title ? `${item.problem_id} · ${item.title}` : item.problem_id;
      const tag = document.createElement("span");
      tag.className = "calendar-detail-tag microlabel";
      tag.textContent = item.projected ? "projected" : "scheduled";
      row.append(stage, title, tag);
      if (item.problem_id) row.addEventListener("click", () => openProblemModal(item.problem_id));
      list.append(row);
    });
    detail.append(list);
  }

  function stepCalendarMonth(delta) {
    let m = calendarView.month + delta;
    let y = calendarView.year;
    if (m < 0) {
      m = 11;
      y -= 1;
    } else if (m > 11) {
      m = 0;
      y += 1;
    }
    calendarView.month = m;
    calendarView.year = y;
    renderRevisionCalendar();
  }

  function renderConsistency() {
    const host = $("#consistency-chart");
    if (!host) return;
    host.replaceChildren();
    const badge = $("#consistency-days");
    const timeline = cumulativeCompletionTimeline([...state.completedById.values()]);
    const setBadge = (label, tone = "") => {
      if (badge) {
        badge.textContent = label;
        badge.className = `pill num ${tone}`.trim();
      }
    };
    if (!timeline.length) {
      setBadge("0 active days");
      host.append(empty("Complete the first problem to start the consistency graph."));
      return;
    }

    // Rolling last-30-days window (today-29 .. today), not the first 30 days.
    const xMaxDays = 29;
    const endDate = referenceDate();
    const startDate = addDays(endDate, -xMaxDays);
    const windowPoints = timeline.filter((point) => point.date >= startDate && point.date <= endDate);
    if (!windowPoints.length) {
      setBadge("0 active days", "warn");
      host.append(
        empty("No completions in the last 30 days. The cumulative count resumes with the next solve."),
      );
      return;
    }
    setBadge(`${windowPoints.length} active day${windowPoints.length === 1 ? "" : "s"}`, "good");

    const last = windowPoints.at(-1);
    // The y-axis was pinned at a fixed 100 so progress read as a fraction of the
    // quarter goal. With 13 problems logged that left ~87% of the plot empty and
    // flattened the trend into the baseline. Scale the axis to the window and
    // keep the goal as a labelled reference in the note instead of as the domain.
    const GOAL = 100;
    const dataMax = Math.max(last.problems, last.skills, 1);
    const step = dataMax <= 20 ? 5 : dataMax <= 60 ? 10 : 25;
    const yMax = Math.min(GOAL, Math.max(step, Math.ceil((dataMax * 1.35) / step) * step));
    // Close the area at the last plotted day, not at the right edge - otherwise
    // the fill runs on past the final data point as though the data continued.
    const lastElapsed = Math.max(
      0,
      Math.round((parseDate(last.date) - parseDate(startDate)) / (24 * 60 * 60 * 1000)),
    );
    const lastX = clamp((lastElapsed / xMaxDays) * 100, 0, 100).toFixed(2);
    const midDate = addDays(startDate, Math.floor(xMaxDays / 2));
    const wrap = document.createElement("div");
    wrap.className = "line-chart-wrap";
    wrap.innerHTML = `
      <span class="axis-title microlabel y">Cumulative count</span>
      <div class="line-y-axis num">
        ${lineTicks(yMax).map((tick) => `<span>${tick}</span>`).join("")}
      </div>
      <div class="line-chart" role="img" aria-label="Cumulative completed problems and skills over the rolling 30-day window. ${last.problems} problems and ${last.skills} skills so far.">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none">
          <polyline class="line-area problems" points="${linePoints(windowPoints, "problems", yMax, xMaxDays, startDate)} ${lastX},100 0,100" />
          <polyline class="line-stroke problems" points="${linePoints(windowPoints, "problems", yMax, xMaxDays, startDate)}" />
          <polyline class="line-stroke skills" points="${linePoints(windowPoints, "skills", yMax, xMaxDays, startDate)}" />
        </svg>
        <div class="line-axis num">
          <span>${startDate}</span>
          <span>${midDate}</span>
          <span>${endDate}</span>
        </div>
      </div>
      <span class="axis-title microlabel x">Rolling 30-day study window</span>
    `;
    host.append(wrap);
    host.append(
      chartLegend([
        { label: `problems completed · ${last.problems}`, shape: "line", color: "var(--series-1)" },
        { label: `skills touched · ${last.skills}`, shape: "line", color: "var(--series-2)" },
      ]),
    );
    host.append(
      chartNote(
        `${last.problems} of the ${GOAL}-problem goal. The axis scales to this window so the trend stays readable.`,
      ),
    );
  }

  const DIFFICULTY_SERIES = {
    Easy: "var(--series-3)",
    Medium: "var(--series-4)",
    Hard: "var(--series-8)",
    Unknown: "var(--muted)",
  };

  function renderTimeInvested() {
    const tiles = $("#time-tiles");
    const chart = $("#time-chart");
    const legendHost = $("#time-legend");
    const pillNode = $("#time-total-pill");
    if (!tiles || !chart) return;
    tiles.replaceChildren();
    chart.replaceChildren();
    if (legendHost) legendHost.replaceChildren();
    if (pillNode) pillNode.textContent = "-";
    if (!feedAvailable()) {
      chart.append(degradedBanner());
      return;
    }
    const invested = state.feed.time_invested || {};
    const series = invested.series || [];
    if (!series.length) {
      chart.append(empty("No timed solves recorded yet."));
      return;
    }
    const hours = (invested.total_minutes || 0) / 60;
    if (pillNode) pillNode.textContent = `${hours.toFixed(1)} h total`;

    const tileData = [
      { label: "Total time", value: `${hours.toFixed(1)} h`, note: `${invested.sessions} timed solves` },
      { label: "Average / solve", value: `${invested.average_minutes} min`, note: "all difficulties" },
      ...(invested.by_difficulty || []).map((bucket) => ({
        label: `${bucket.difficulty} average`,
        value: `${bucket.average_minutes} min`,
        note: `${bucket.count} solve${bucket.count === 1 ? "" : "s"}`,
      })),
    ];
    tileData.forEach((tile) => {
      const node = document.createElement("div");
      node.className = "pace-tile";
      const label = document.createElement("span");
      label.className = "microlabel";
      label.textContent = tile.label;
      const value = document.createElement("strong");
      value.className = "num";
      value.textContent = tile.value;
      const note = document.createElement("small");
      note.className = "microlabel";
      note.textContent = tile.note;
      node.append(label, value, note);
      tiles.append(node);
    });

    const W = 660;
    const H = 190;
    const PAD_L = 34;
    const PAD_R = 10;
    const PAD_T = 16;
    const PAD_B = 24;
    const maxMinutes = Math.max(...series.map((entry) => entry.minutes), 30);
    const bandW = (W - PAD_L - PAD_R) / series.length;
    const barW = Math.min(bandW - 2, 26);
    const plotH = H - PAD_T - PAD_B;
    const svg = svgEl("svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "time-svg");
    svg.append(svgEl("line", {
      x1: PAD_L, y1: H - PAD_B, x2: W - PAD_R, y2: H - PAD_B, class: "forecast-baseline",
    }));
    svg.append(svgEl("text", { x: 2, y: PAD_T + 4, class: "forecast-axis" }, `${maxMinutes}m`));
    svg.append(svgEl("text", { x: 2, y: H - PAD_B + 4, class: "forecast-axis" }, "0"));
    series.forEach((entry, index) => {
      const x = PAD_L + index * bandW + (bandW - barW) / 2;
      const h = Math.max((plotH * entry.minutes) / maxMinutes, 2);
      const bar = svgEl("rect", {
        x, y: H - PAD_B - h, width: barW, height: h, rx: 3,
        fill: DIFFICULTY_SERIES[entry.difficulty] || DIFFICULTY_SERIES.Unknown,
        class: "time-bar",
      });
      bar.append(svgEl("title", {},
        `${entry.problem_id} · ${entry.date} · ${entry.minutes} min · ${entry.difficulty || "Unknown"}`));
      svg.append(bar);
    });
    chart.append(svg);
    chart.setAttribute("aria-label",
      `Minutes per solve for ${series.length} solves; total ${hours.toFixed(1)} hours; ` +
      `average ${invested.average_minutes} minutes.`);

    if (legendHost) {
      const seen = [...new Set(series.map((entry) => entry.difficulty || "Unknown"))];
      legendHost.append(chartLegend(
        seen.map((difficulty) => ({
          label: difficulty,
          shape: "line",
          color: DIFFICULTY_SERIES[difficulty] || DIFFICULTY_SERIES.Unknown,
        })),
      ));
    }
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

  function empty(message) {
    const div = document.createElement("div");
    div.className = "empty";
    div.textContent = message;
    return div;
  }

  function renderDataWarning() {
    const banner = $("#data-warning");
    if (!state.feed && state.feedStatus && state.feedStatus.status !== "ok") {
      $("#data-warning-text").textContent = state.feedStatus.detail;
      banner.hidden = false;
      return;
    }
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

  function renderAll() {
    $("#last-updated").textContent = `Updated ${state.datasets.progress.last_updated}`;
    $("#reference-date-pill").textContent = `Reference date ${referenceDate()}`;
    RENDERERS.global.forEach((fn) => fn());
    markAllDirty();
    switchWorkspace(state.activeWorkspace); // switchWorkspace calls renderWorkspace
  }

  async function main() {
    try {
      initTheme();
      await loadData();
      buildStageOptions();
      renderAll();
      const themeToggle = $("#theme-toggle");
      if (themeToggle) themeToggle.addEventListener("click", toggleTheme);
      const calPrev = $("#calendar-prev");
      if (calPrev) calPrev.addEventListener("click", () => stepCalendarMonth(-1));
      const calNext = $("#calendar-next");
      if (calNext) calNext.addEventListener("click", () => stepCalendarMonth(1));
      const dataWarningDismiss = $("#data-warning-dismiss");
      if (dataWarningDismiss) {
        dataWarningDismiss.addEventListener("click", () => {
          $("#data-warning").hidden = true;
        });
      }
      // Filters live only on list workspaces; guard so their absence is safe.
      const search = $("#search");
      if (search) search.addEventListener("input", debounce(applyFilters, 150));
      const stageFilter = $("#stage-filter");
      if (stageFilter) stageFilter.addEventListener("change", applyFilters);
      const statusFilter = $("#status-filter");
      if (statusFilter) statusFilter.addEventListener("change", applyFilters);
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
      const browserSort = $("#browser-sort");
      if (browserSort) browserSort.addEventListener("change", () => {
        browserState.sort = browserSort.value;
        renderProblemBrowser();
      });
      document.querySelectorAll("[data-workspace-link]").forEach((link) => {
        link.addEventListener("click", (event) => {
          event.preventDefault();
          switchWorkspace(link.dataset.workspaceLink, link.getAttribute("href"));
        });
      });
      watchActiveSection();
      $("#modal-close").addEventListener("click", () => $("#skill-modal").close());
      $("#skill-modal").addEventListener("click", (event) => {
        if (event.target === $("#skill-modal")) {
          $("#skill-modal").close();
        }
      });
      // Returning to the tab (e.g. after midnight, or once the server is up)
      // refreshes the live feed and re-renders against the current date.
      document.addEventListener("visibilitychange", async () => {
        if (document.visibilityState !== "visible") return;
        state.feed = await fetchFeed();
        renderAll();
      });
    } catch (error) {
      document.body.innerHTML = `<main class="main"><section class="panel"><h2>Dashboard load failed</h2><p>${error.message}</p><p>Run it through <code>make web-dashboard</code> so the JSON files can be fetched.</p></section></main>`;
      if (window.location.protocol === "file:") {
        console.info(`Dashboard degraded: ${error.message}`);
      } else {
        console.error(error);
      }
    }
  }

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
  RENDERERS,
  markAllDirty,
  main,
};
