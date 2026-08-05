import { browserState, renderProblemBrowser, setCatalogFilters, stageOptions } from "../legacy/app.js";
import { onRoute, navigate, currentRoute } from "./router.js";

const SHOW = {
  problems: ["fb-search", "fb-difficulty", "fb-status", "fb-sort"],
  curriculum: ["fb-search", "fb-stage", "fb-status"],
  evidence: ["fb-search", "fb-stage", "fb-status"],
};

export function mapStatus(unified, consumer) {
  if (consumer === "catalog") return unified === "solved" ? "active" : unified;
  return unified;
}

function readControls() {
  return {
    q: document.querySelector("#fb-search").value.trim(),
    stage: document.querySelector("#fb-stage").value,
    status: document.querySelector("#fb-status").value,
    difficulty: document.querySelector("#fb-difficulty").value,
    sort: document.querySelector("#fb-sort").value,
  };
}

function clearFilterParams() {
  return { q: "", stage: "", status: "", difficulty: "", sort: "" };
}

function push(workspace, values) {
  // Filters live in the URL (replace, not push — no history spam while typing).
  const params = {};
  if (values.q) params.q = values.q;
  if (values.stage) params.stage = values.stage;
  if (values.status) params.status = values.status;
  if (workspace === "problems") {
    if (values.difficulty) params.difficulty = values.difficulty;
    if (values.sort !== "curriculum") params.sort = values.sort;
  }
  navigate({ params: { ...currentRoute().params, ...clearFilterParams(), ...params } }, { replace: true });
}

// Every route apply reaches the consumers, so skip the work when nothing that
// the consumers care about actually changed (a section jump, a tab switch).
let lastApplied = "";

function applyToConsumers(workspace, params) {
  const key = JSON.stringify([
    workspace,
    params.q || "",
    params.stage || "",
    params.status || "",
    params.difficulty || "",
    params.sort || "curriculum",
  ]);
  if (key === lastApplied) return;
  lastApplied = key;
  if (workspace === "problems") {
    browserState.search = params.q || "";
    browserState.difficulty = params.difficulty || "";
    browserState.status = mapStatus(params.status || "", "browser");
    browserState.sort = params.sort || "curriculum";
    renderProblemBrowser();
  } else {
    setCatalogFilters({ query: params.q || "", stage: params.stage || "", status: mapStatus(params.status || "", "catalog") });
  }
}

function syncControls(params) {
  document.querySelector("#fb-search").value = params.q || "";
  document.querySelector("#fb-stage").value = params.stage || "";
  document.querySelector("#fb-status").value = params.status || "";
  document.querySelector("#fb-difficulty").value = params.difficulty || "";
  document.querySelector("#fb-sort").value = params.sort || "curriculum";
}

export function initFilterBar() {
  const bar = document.querySelector("#filter-bar");
  const stageSelect = document.querySelector("#fb-stage");
  for (const stage of stageOptions()) {
    const option = document.createElement("option");
    option.value = stage;
    option.textContent = stage;
    stageSelect.append(option);
  }
  let debounceId = 0;
  bar.addEventListener("input", () => {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => push(currentRoute().workspace, readControls()), 150);
  });
  onRoute((route) => {
    const visible = SHOW[route.workspace] || null;
    bar.hidden = !visible;
    if (!visible) {
      // A workspace with no filter bar must not keep filtering its content by
      // a query the user can no longer see.
      applyToConsumers(route.workspace, {});
      return;
    }
    for (const el of bar.querySelectorAll("input, select")) el.hidden = !visible.includes(el.id);
    syncControls(route.params);
    applyToConsumers(route.workspace, route.params);
  });
}
