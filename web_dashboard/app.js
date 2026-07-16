(function () {
  const DATA = {
    progress: "../progress/progress.json",
    scoring: "../progress/scoring.json",
    curriculum: "../curriculum/curriculum.json",
    stages: "../curriculum/stages.json",
    skills: "../knowledge/skills.json",
    mistakes: "../mistake_catalog.json",
    patterns: "../thinking_patterns.md",
  };

  const state = {
    datasets: null,
    problemsById: new Map(),
    completedById: new Map(),
    skillsById: new Map(),
    filteredProblems: [],
  };

  const $ = (selector) => document.querySelector(selector);
  const today = new Date();

  function parseDate(value) {
    if (!value) return null;
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function isoDate(date) {
    return date.toISOString().slice(0, 10);
  }

  function daysBetween(a, b) {
    const day = 24 * 60 * 60 * 1000;
    return Math.round((parseDate(a) - parseDate(b)) / day);
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
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
    if (stage >= 5) return "MASTERED";
    return `R${stage + 1} due`;
  }

  function pill(label, tone = "") {
    const span = document.createElement("span");
    span.className = `pill ${tone}`.trim();
    span.textContent = label;
    return span;
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
    const [progress, scoring, curriculum, stages, skills, mistakes, patterns] = await Promise.all([
      fetchJson(DATA.progress),
      fetchJson(DATA.scoring),
      fetchJson(DATA.curriculum),
      fetchJson(DATA.stages),
      fetchJson(DATA.skills),
      fetchJson(DATA.mistakes),
      fetchText(DATA.patterns),
    ]);

    state.datasets = { progress, scoring, curriculum, stages, skills, mistakes, patterns };
    state.problemsById = new Map(curriculum.problems.map((problem) => [problem.id, problem]));
    state.skillsById = new Map(Object.entries(skills.skills || {}));
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

  function getRevisionEntries() {
    const ref = referenceDate();
    return [...state.completedById.values()]
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

  function renderMetrics() {
    const { progress, curriculum } = state.datasets;
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

    const metrics = [
      {
        label: "Problems completed",
        value: `${completed} / ${total}`,
        note: `${((completed / total) * 100).toFixed(1)}% curriculum coverage`,
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
        label: "Confidence",
        value: latestConfidence.toFixed(1),
        note: `Average after-session confidence ${avgConfidence.toFixed(2)}`,
      },
      {
        label: "Weighted thinking",
        value: (progress.scores?.averages?.thinking_weighted || 0).toFixed(2),
        note: "Weighted average across completed problems",
      },
      {
        label: "Interview score",
        value: (progress.scores?.averages?.interview_average || 0).toFixed(2),
        note: "Average interview readiness score",
      },
      {
        label: "Last updated",
        value: text(progress.last_updated),
        note: `Reference date ${referenceDate()}`,
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
    wrap.append(title, meta, reason, notes);
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
      const card = document.createElement("article");
      card.className = `stage-card ${stageName === progress.current_stage ? "active" : ""}`;
      const skills = details.skills || [];
      const masteredSkillNames = skills
        .filter((skillId) => progress.skill_progress?.[skillId]?.mastered)
        .map((skillId) => skillTitle(skillId));
      const nextSkill = skills.find((skillId) => !progress.skill_progress?.[skillId]?.mastered);
      card.innerHTML = `
        <div class="section-head">
          <div class="stage-title">
            <span class="stage-number">${stageNumber}</span>
            <h4>${stageName}</h4>
          </div>
          <span class="pill ${mastery.status === "mastered" ? "good" : mastery.status === "locked" ? "" : "warn"}">${mastery.status || "unknown"}</span>
        </div>
        <p>${details.goal || "No goal recorded."}</p>
        <div class="bar-row">
          <span class="bar-name">${mastered}/${total} skills</span>
          <div class="track"><div class="fill" style="--width:${percent}%"></div></div>
          <span class="bar-value">${Math.round(percent)}%</span>
        </div>
        <div class="stage-skill-summary">
          <p><strong>Mastered:</strong> ${masteredSkillNames.length ? masteredSkillNames.join(", ") : "None yet"}</p>
          <p><strong>Next skill:</strong> ${nextSkill ? skillLabel(nextSkill) : "Stage complete"}</p>
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
    const modal = $("#skill-modal");
    const body = $("#modal-body");
    $("#modal-title").textContent = `Stage ${stageNumber}: ${stageName}`;
    $("#modal-subtitle").textContent = `${mastery.skills_mastered || 0}/${mastery.skills_total || details.skills?.length || 0} skills mastered · ${mastery.status || "unknown"}`;
    body.replaceChildren();

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

    if (typeof modal.showModal === "function") {
      modal.showModal();
    } else {
      modal.setAttribute("open", "");
    }
  }

  function buildSkillDetailRow(skillId) {
    const progress = state.datasets.progress;
    const skillInfo = skillMeta(skillId);
    const skill = progress.skill_progress?.[skillId] || {};
    const problems = state.datasets.curriculum.problems.filter(
      (problem) => problem.primary_skill === skillId || problem.secondary_skill === skillId,
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
    if (title === "Remaining") details.open = true;
    const summary = document.createElement("summary");
    summary.textContent = `${title} (${problems.length})`;
    if (tone) summary.className = tone;
    const list = document.createElement("div");
    list.className = "problem-chip-list";
    if (!problems.length) {
      list.append(empty(`No ${title.toLowerCase()} problems.`));
    } else {
      problems.forEach((problem) => {
        const item = document.createElement("div");
        item.className = "problem-chip";
        item.innerHTML = `
          <strong>${problem.id}</strong>
          <span>${problem.title}</span>
          <small>${problem.difficulty} · ${problem.problem_role || "role"}${problem.original_number ? ` · LC ${problem.original_number}` : ""}</small>
        `;
        list.append(item);
      });
    }
    details.append(summary, list);
    return details;
  }

  function renderRevisionLanes() {
    const entries = getRevisionEntries();
    const lanes = [
      { key: "due", label: "Due now", entries: entries.filter((entry) => entry.nextDue && entry.daysUntil <= 0) },
      { key: "r1", label: "R1", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage === 0) },
      { key: "r2", label: "R2", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage === 1) },
      { key: "r3", label: "R3", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage === 2) },
      { key: "r4r5", label: "R4/R5", entries: entries.filter((entry) => entry.status !== "MASTERED" && entry.stage >= 3) },
      { key: "mastered", label: "Mastered", entries: entries.filter((entry) => entry.status === "MASTERED") },
    ];

    const wrap = $("#revision-lanes");
    wrap.replaceChildren();
    lanes.forEach((lane) => {
      const node = document.createElement("article");
      node.className = "lane";
      const next = lane.entries[0];
      node.innerHTML = `
        <strong>${lane.label}</strong>
        <span class="lane-count">${lane.entries.length}</span>
        <small class="small-muted">${next ? `${next.problem.id} on ${next.nextDue || "maintenance"}` : "No items"}</small>
      `;
      wrap.append(node);
    });
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
      target.append(item);
    });
  }

  function renderSkills() {
    const target = $("#skill-grid");
    target.replaceChildren();
    const { progress, stages } = state.datasets;
    const { query, stage: selectedStage } = currentFilters();
    const stageSkills = selectedStage
      ? stages.stages[selectedStage]?.skills || []
      : Object.keys(progress.skill_progress || {});

    stageSkills.filter((skillId) => skillMatchesQuery(skillId, query)).forEach((skillId) => {
      const skillInfo = skillMeta(skillId);
      const skill = progress.skill_progress?.[skillId] || {};
      const problems = state.datasets.curriculum.problems.filter(
        (problem) => problem.primary_skill === skillId || problem.secondary_skill === skillId,
      );
      const solved = problems.filter((problem) => state.completedById.has(problem.id)).length;
      const card = document.createElement("article");
      card.className = "skill-card";
      card.innerHTML = `
        <div class="section-head">
          <div>
            <h4>${skillInfo.name || skillId}</h4>
            <span class="small-muted">${skillId}</span>
          </div>
          <span class="pill ${skill.mastered ? "good" : ""}">${skill.mastered ? "mastered" : "learning"}</span>
        </div>
        <p>${skillInfo.description || "No skill description recorded."}</p>
        <p>${solved}/${problems.length} related problems completed</p>
        <div class="meta-row">
          <span class="pill">primary ${skill.primary_solved ? "done" : "open"}</span>
          <span class="pill">reinforcement ${skill.reinforcement_attempted ? "done" : "open"}</span>
          <span class="pill">score ${skill.primary_weighted_score ?? "-"}</span>
        </div>
      `;
      target.append(card);
    });
    if (!target.children.length) {
      target.append(empty("No skills match the current filters."));
    }
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
    const haystack = [
      problem.id,
      problem.title,
      problem.stage,
      problem.primary_skill,
      skillMeta(problem.primary_skill).name,
      skillMeta(problem.primary_skill).description,
      problem.secondary_skill,
      problem.secondary_skill ? skillMeta(problem.secondary_skill).name : null,
      problem.secondary_skill ? skillMeta(problem.secondary_skill).description : null,
      problem.section,
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
    return state.datasets.curriculum.problems
      .filter((problem) => problem.primary_skill === skillId || problem.secondary_skill === skillId)
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
    renderProblemTable();
    renderSkills();
  }

  function renderProblemTable() {
    const body = $("#problem-table");
    body.replaceChildren();
    const rows = state.filteredProblems.slice(0, 120);
    if (!rows.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="8">No matching problems.</td>`;
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
      body.append(tr);
    });
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
    const lessons = state.datasets.progress.lessons_learned || {};
    Object.entries(lessons)
      .slice(-4)
      .forEach(([problemId, lesson]) => {
        const card = document.createElement("article");
        card.className = "note-card";
        card.innerHTML = `
          <h4>${problemId}</h4>
          <p>${lesson.implementation_lesson || lesson.interview_takeaway || lesson.core_mental_model || "No lesson text."}</p>
        `;
        target.append(card);
      });

    const mistakes = state.datasets.mistakes.entries || [];
    mistakes.slice(-4).forEach((mistake) => {
      const card = document.createElement("article");
      card.className = "note-card";
      card.innerHTML = `
        <h4>${mistake.id} · ${mistake.title}</h4>
        <p>${mistake.fix}</p>
      `;
      target.append(card);
    });
  }

  function empty(message) {
    const div = document.createElement("div");
    div.className = "empty";
    div.textContent = message;
    return div;
  }

  function renderAll() {
    $("#last-updated").textContent = `Updated ${state.datasets.progress.last_updated}`;
    renderMetrics();
    renderNextAction();
    renderThinkingBars();
    renderStages();
    renderRevisionLanes();
    renderRevisionCalendar();
    renderSkills();
    renderProblemTable();
    renderThinkingProfile();
    renderLearningNotes();
  }

  async function main() {
    try {
      await loadData();
      buildStageOptions();
      renderAll();
      $("#search").addEventListener("input", applyFilters);
      $("#stage-filter").addEventListener("change", applyFilters);
      $("#status-filter").addEventListener("change", applyFilters);
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
