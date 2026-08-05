import { onRoute } from "./router.js";

const GROUPS_KEY = "sidebar-groups";
const COLLAPSED_KEY = "sidebar-collapsed";

function readGroups() {
  try {
    return JSON.parse(localStorage.getItem(GROUPS_KEY) || "{}");
  } catch {
    return {};
  }
}

export function initSidebar() {
  const saved = readGroups();
  document.querySelectorAll(".rail-group").forEach((group) => {
    if (group.dataset.group in saved) group.open = saved[group.dataset.group];
    group.addEventListener("toggle", () => {
      localStorage.setItem(GROUPS_KEY, JSON.stringify({ ...readGroups(), [group.dataset.group]: group.open }));
    });
    // A summary owns two affordances: its link navigates, the rest of the row
    // toggles. Without this the workspace link would also collapse the group
    // it just opened.
    group.querySelector("summary")?.addEventListener("click", (event) => {
      const link = event.target.closest("a[data-rail-workspace]");
      if (!link) return;
      event.preventDefault();
      location.hash = link.getAttribute("href");
    });
  });

  const collapseBtn = document.querySelector("#rail-collapse");
  const setCollapsed = (on) => {
    document.body.classList.toggle("rail-collapsed", on);
    localStorage.setItem(COLLAPSED_KEY, on ? "1" : "");
    collapseBtn.textContent = on ? "⟩⟩" : "⟨⟨";
    collapseBtn.setAttribute("aria-label", on ? "Expand sidebar" : "Collapse sidebar");
  };
  setCollapsed(Boolean(localStorage.getItem(COLLAPSED_KEY)));
  collapseBtn.addEventListener("click", () => setCollapsed(!document.body.classList.contains("rail-collapsed")));

  onRoute((route) => {
    // Quiet state: the open workspace's group. The loud state is per-section
    // (legacy's scroll spy) and per-tab (route.sub) below.
    document.querySelectorAll(".rail-group").forEach((group) => {
      const isActive = group.dataset.group === route.workspace;
      group.classList.toggle("in-workspace", isActive);
      if (isActive) group.open = true;
    });
    document.querySelectorAll('[data-rail-target^="tab:"]').forEach((link) => {
      link.classList.toggle("active", route.workspace === "evidence" && link.dataset.railTarget === `tab:${route.sub || "performance"}`);
    });
  });
}
