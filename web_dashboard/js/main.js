import { main, toggleTheme } from "./legacy/app.js";
import { initTooltips } from "./engine/tooltip.js";
import { initKeyboard, registerList } from "./engine/keyboard.js";
import { initPalette } from "./engine/palette.js";
import "./features/motivation.js";
import "./features/memory.js";

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
initKeyboard({ onHelp: () => help.togglePopover(), onFocusMode: () => {} }); // focus mode wired in Task 14

registerList("#due-queue", { itemSelector: ".due-row", onEnter: (el) => el.click() });
registerList("#browser-rows", { itemSelector: "tr", onEnter: (el) => el.querySelector("a, button")?.click() || el.click() });

initPalette({ actions: [
  { id: "act:theme", label: "Toggle theme", hint: "t", run: toggleTheme },
  { id: "act:help", label: "Keyboard help", hint: "?", run: () => help.togglePopover() },
  { id: "act:focus", label: "Focus mode", hint: "f", run: () => {} }, // wired in Task 14
] });

main();
