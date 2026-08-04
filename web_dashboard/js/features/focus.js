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
  const problemId = action?.problem_id || null; // verified: feed.next_action = {mode, problem_id, title, url, reason, stage_label}
  const problem = problemId ? state.problemsById.get(problemId) : null;
  overlay = document.createElement("div");
  overlay.className = "focus-overlay";
  overlay.innerHTML = problem
    ? `<p class="microlabel">${(action.mode || "solve").toUpperCase()}${action.stage_label ? ` · ${action.stage_label}` : ""}</p>
       <h1>${problemId} — ${problem.title || ""}</h1>
       <p class="focus-timer num" id="focus-timer">00:00</p>
       <p class="microlabel" id="focus-typical"></p>
       <details><summary>Edge-case checklist</summary><div id="focus-edges"></div></details>
       <p class="microlabel">Esc to exit — record via the mentor CLI</p>`
    : `<h1>No next action</h1><p class="microlabel">${state.feed ? "Queue is empty." : "Live feed required — run \`make web-dashboard\`."} Esc to exit.</p>`;
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
