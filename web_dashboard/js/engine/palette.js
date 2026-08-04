import { fuzzyScore } from "../derive/search.js";
import { state, WORKSPACE_META, openProblemModal } from "../legacy/app.js";
import { navigate } from "./router.js";

const goTo = (workspace) =>
  document.dispatchEvent(new CustomEvent("dash:navigate", { detail: { workspace } }));

const FRECENCY_KEY = "palette-frecency";
const frecency = JSON.parse(localStorage.getItem(FRECENCY_KEY) || "{}");

function bump(id) {
  frecency[id] = (frecency[id] || 0) * 0.9 + 1;
  localStorage.setItem(FRECENCY_KEY, JSON.stringify(frecency));
}

function buildIndex(actions) {
  const items = [];
  for (const [ws, meta] of Object.entries(WORKSPACE_META)) {
    items.push({ id: `go:${ws}`, group: "Go to", label: meta.title, hint: `g ${ws === "problems" ? "b" : ws === "practice" ? "w" : ws[0]}`, run: () => goTo(ws) });
  }
  for (const tab of ["performance", "memory", "consistency", "log"]) {
    items.push({ id: `tab:${tab}`, group: "Go to", label: `Evidence · ${tab[0].toUpperCase()}${tab.slice(1)}`, hint: "", run: () => navigate({ workspace: "evidence", sub: tab }) });
  }
  for (const a of actions) items.push({ ...a, group: "Actions" });
  for (const [id, problem] of state.problemsById) {
    items.push({ id: `p:${id}`, group: "Problems", label: `${id} ${problem.title || ""}`, hint: "", run: () => openProblemModal(id) });
  }
  for (const [id, skill] of state.skillsById) {
    items.push({ id: `s:${id}`, group: "Skills", label: skill.name || id, hint: "", run: () => goTo("curriculum") });
  }
  return items;
}

function rank(items, query) {
  const scored = items
    .map((item) => ({ item, score: fuzzyScore(query, item.label) * (1 + Math.log1p(frecency[item.id] || 0)) }))
    .filter((r) => r.score > 0);
  scored.sort((a, b) => b.score - a.score);
  if (!query) {
    // Empty query: recents (by frecency) then Go-to + Actions, never problems dump.
    return scored.filter((r) => r.item.group !== "Problems" && r.item.group !== "Skills").slice(0, 12);
  }
  return scored.slice(0, 12);
}

export function initPalette({ actions = [] } = {}) {
  const dialog = document.createElement("dialog");
  dialog.className = "palette";
  dialog.innerHTML = `<input type="search" placeholder="Type a command or search…" autofocus />
    <ul role="listbox"></ul>`;
  document.body.append(dialog);
  const input = dialog.querySelector("input");
  const listEl = dialog.querySelector("ul");
  let rows = [];
  let cursor = 0;

  const paint = () => {
    const groups = new Map();
    rows.forEach((r, i) => {
      if (!groups.has(r.item.group)) groups.set(r.item.group, []);
      groups.get(r.item.group).push({ ...r, i });
    });
    listEl.innerHTML = "";
    for (const [group, members] of groups) {
      const head = document.createElement("li");
      head.className = "palette-group";
      head.textContent = group;
      listEl.append(head);
      for (const m of members) {
        const li = document.createElement("li");
        li.className = m.i === cursor ? "sel" : "";
        li.setAttribute("role", "option");
        const label = document.createElement("span");
        label.textContent = m.item.label;
        const hint = document.createElement("kbd");
        hint.textContent = m.item.hint || "";
        li.append(label, hint);
        li.addEventListener("click", () => execute(m.i));
        listEl.append(li);
      }
    }
  };

  const refresh = () => {
    rows = rank(buildIndex(actions), input.value.trim());
    cursor = 0;
    paint();
  };

  const execute = (i) => {
    const row = rows[i];
    if (!row) return;
    dialog.close();
    bump(row.item.id);
    row.item.run();
  };

  input.addEventListener("input", refresh);
  dialog.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || (e.key === "Tab" && !e.shiftKey)) { e.preventDefault(); cursor = Math.min(rows.length - 1, cursor + 1); paint(); }
    else if (e.key === "ArrowUp" || (e.key === "Tab" && e.shiftKey)) { e.preventDefault(); cursor = Math.max(0, cursor - 1); paint(); }
    else if (e.key === "Enter") { e.preventDefault(); execute(cursor); }
    else if (e.key === "Escape" && input.value) { e.preventDefault(); input.value = ""; refresh(); }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      input.value = "";
      refresh();
      dialog.showModal();
      input.focus();
    }
  });
}
