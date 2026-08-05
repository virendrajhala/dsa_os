import { main, toggleTheme, switchWorkspace } from "./legacy/app.js";
import { initTooltips } from "./engine/tooltip.js";
import { initKeyboard, registerList } from "./engine/keyboard.js";
import { initPalette } from "./engine/palette.js";
import { startRouter, onRoute, navigate } from "./engine/router.js";
import { initEvidenceTabs } from "./engine/tabs.js";
import { initSidebar } from "./engine/sidebar.js";
import { initFilterBar } from "./engine/filterbar.js";
import { viewSwitch } from "./engine/motion.js";
import "./features/motivation.js";
import "./features/memory.js";
import "./features/pace.js";
import { toggleFocusMode } from "./features/focus.js";

initTooltips();

const help = document.createElement("div");
help.className = "kb-help";
help.popover = "auto";
help.innerHTML = `<h3>Keyboard</h3><dl>
  <dt>g then t/p/b/w/c/e</dt><dd>Go to workspace</dd>
  <dt>j / k / Enter</dt><dd>Move through visible list, open</dd>
  <dt>/</dt><dd>Search</dd><dt>t</dt><dd>Theme</dd>
  <dt>f</dt><dd>Focus mode</dd><dt>Ctrl+K</dt><dd>Command palette</dd>
  <dt>?</dt><dd>This help</dd></dl>`;
document.body.append(help);
initKeyboard({ onHelp: () => help.togglePopover(), onFocusMode: toggleFocusMode });

registerList("#due-queue", { itemSelector: ".due-row", onEnter: (el) => el.click() });
registerList("#browser-rows", { itemSelector: "tr", onEnter: (el) => el.querySelector("a, button")?.click() || el.click() });

initPalette({ actions: [
  { id: "act:theme", label: "Toggle theme", hint: "t", run: toggleTheme },
  { id: "act:help", label: "Keyboard help", hint: "?", run: () => help.togglePopover() },
  { id: "act:focus", label: "Focus mode", hint: "f", run: toggleFocusMode },
] });

// Everything below needs loaded data: the first route apply renders a workspace.
await main();

document.addEventListener("dash:navigate", (e) => {
  navigate({ workspace: e.detail.workspace, params: e.detail.section ? { s: e.detail.section } : {} });
});

let lastWorkspace = null;
let lastTarget = "";
let firstApply = true;
onRoute((route) => {
  const target = route.params.s ? `#${route.params.s}` : "";
  if (route.workspace !== lastWorkspace) {
    lastWorkspace = route.workspace;
    lastTarget = target;
    const run = () => switchWorkspace(route.workspace, target);
    // The initial paint never animates (Phase-1 motion rule).
    if (firstApply) run();
    else viewSwitch(run);
  } else if (target && target !== lastTarget) {
    // Same workspace, new section: scroll only when the target actually
    // changed, so filter edits (which re-apply the route) never re-scroll.
    lastTarget = target;
    switchWorkspace(route.workspace, target);
  }
  firstApply = false;
});

initEvidenceTabs();
initSidebar();
initFilterBar();

startRouter();
