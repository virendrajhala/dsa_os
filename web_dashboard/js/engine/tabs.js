import { onRoute, navigate } from "./router.js";

export const EVIDENCE_TABS = {
  performance: ["mock-trend", "hint-independence", "thinking", "thinking-dimensions"],
  memory: ["retention", "revision-calendar", "forecast-panel"],
  consistency: ["activity-heatmap", "consistency", "time-invested"],
  log: ["history", "deferred"],
};

function applyTab(tab) {
  const active = EVIDENCE_TABS[tab] ? tab : "performance";
  document.querySelectorAll("#evidence-tabs [data-tab]").forEach((btn) => {
    const on = btn.dataset.tab === active;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-current", on ? "true" : "false");
  });
  document.querySelectorAll('[data-workspace-section="evidence"][data-evidence-tab]').forEach((section) => {
    // Two independent gates: the workspace gate belongs to legacy's
    // switchWorkspace, the tab gate is ours. `hidden` is the AND of both.
    section.dataset.tabHidden = section.dataset.evidenceTab === active ? "" : "true";
    section.hidden = section.dataset.tabHidden === "true";
  });
}

export function initEvidenceTabs() {
  const bar = document.querySelector("#evidence-tabs");
  bar.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-tab]");
    if (btn) navigate({ workspace: "evidence", sub: btn.dataset.tab });
  });
  onRoute((route) => {
    bar.hidden = route.workspace !== "evidence";
    if (route.workspace === "evidence") applyTab(route.sub || "performance");
  });
}
