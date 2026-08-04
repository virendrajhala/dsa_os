import { toggleTheme } from "../legacy/app.js";

const CHORD_TIMEOUT_MS = 900;
const GO = { t: "today", p: "plan", b: "problems", w: "practice", c: "curriculum", e: "evidence" };
let pendingChord = null;
let chordTimer = 0;
const lists = [];
let listPos = -1;

function typingContext(e) {
  const t = e.target;
  return t.closest?.("input, textarea, select, [contenteditable]") || document.querySelector("dialog[open]");
}

export function registerList(selector, { itemSelector, onEnter }) {
  lists.push({ selector, itemSelector, onEnter });
}

function activeList() {
  return lists.find((l) => {
    const host = document.querySelector(l.selector);
    return host && host.offsetParent !== null;
  });
}

function moveSelection(delta) {
  const list = activeList();
  if (!list) return;
  const items = [...document.querySelectorAll(`${list.selector} ${list.itemSelector}`)];
  if (!items.length) return;
  listPos = Math.max(0, Math.min(items.length - 1, listPos + delta));
  items.forEach((el, i) => el.classList.toggle("kb-selected", i === listPos));
  items[listPos].scrollIntoView({ block: "nearest" });
}

export function initKeyboard({ onFocusMode, onHelp } = {}) {
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (typingContext(e)) return;
    if (pendingChord === "g") {
      pendingChord = null;
      clearTimeout(chordTimer);
      const ws = GO[e.key];
      if (ws) {
        e.preventDefault();
        document.dispatchEvent(new CustomEvent("dash:navigate", { detail: { workspace: ws } }));
        listPos = -1;
      }
      return;
    }
    switch (e.key) {
      case "g":
        pendingChord = "g";
        chordTimer = setTimeout(() => { pendingChord = null; }, CHORD_TIMEOUT_MS);
        break;
      case "j": moveSelection(1); break;
      case "k": moveSelection(-1); break;
      case "Enter": {
        const list = activeList();
        const sel = list && document.querySelector(`${list.selector} .kb-selected`);
        if (sel) { e.preventDefault(); list.onEnter(sel); }
        break;
      }
      case "/": {
        const search = [...document.querySelectorAll('input[type="search"]')].find((i) => i.offsetParent !== null);
        if (search) { e.preventDefault(); search.focus(); }
        break;
      }
      case "t": toggleTheme(); break;
      case "f": onFocusMode?.(); break;
      case "?": onHelp?.(); break;
    }
  });
}
