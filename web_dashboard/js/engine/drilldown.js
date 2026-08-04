import { state, setModal, problemStatus, openProblemModal } from "../legacy/app.js";

export function openProblemList({ title, subtitle = "", items }) {
  const body = setModal(title, subtitle, "Drill-down");
  const list = document.createElement("div");
  list.className = "stack";
  if (!items.length) list.innerHTML = `<p class="small-muted">Nothing here.</p>`;
  for (const item of items) {
    const problem = state.problemsById.get(item.problemId);
    const row = document.createElement("button");
    row.type = "button";
    row.className = "drill-row";
    const status = problemStatus(item.problemId);
    row.textContent = `${status.glyph} ${item.problemId} ${problem?.title || ""} ${item.note || ""}`;
    row.addEventListener("click", () => openProblemModal(item.problemId));
    list.append(row);
  }
  body.append(list);
  const modal = document.querySelector("#skill-modal");
  if (modal && !modal.open) modal.showModal();
}
