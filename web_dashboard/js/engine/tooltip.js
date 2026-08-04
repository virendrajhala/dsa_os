let tipEl = null;

function ensureTip() {
  if (!tipEl) {
    tipEl = document.createElement("div");
    tipEl.className = "dt-tooltip";
    document.body.append(tipEl);
  }
  return tipEl;
}

function place(clientX, clientY) {
  const tip = ensureTip();
  const pad = 12;
  const rect = tip.getBoundingClientRect();
  const x = Math.min(clientX + pad, window.innerWidth - rect.width - pad);
  const y = clientY - rect.height - pad < 0 ? clientY + pad : clientY - rect.height - pad;
  tip.style.transform = `translate(${x}px, ${y}px)`;
}

export function showTip(html, clientX, clientY) {
  const tip = ensureTip();
  tip.innerHTML = html;
  tip.classList.add("show");
  place(clientX, clientY);
}

export function hideTip() {
  ensureTip().classList.remove("show");
}

export function initTooltips() {
  document.addEventListener("pointerover", (e) => {
    const host = e.target.closest("[data-tip]");
    if (host) showTip(host.dataset.tip, e.clientX, e.clientY);
  });
  document.addEventListener("pointermove", (e) => {
    const host = e.target.closest("[data-tip]");
    if (host) place(e.clientX, e.clientY);
    // Crosshair-attached SVGs drive the tooltip themselves — leave theirs alone.
    else if (!e.target.closest?.("[data-crosshair]")) hideTip();
  });
  document.addEventListener("pointerout", (e) => {
    if (e.target.closest?.("[data-tip]")) hideTip();
  });
  // Keyboard parity: focus shows the tooltip under the focused element.
  document.addEventListener("focusin", (e) => {
    const host = e.target.closest("[data-tip]");
    if (!host) return hideTip();
    const r = host.getBoundingClientRect();
    showTip(host.dataset.tip, r.left + r.width / 2, r.top);
  });
}

export function attachCrosshair(svg, points, renderTip) {
  if (!points?.length) return;
  svg.dataset.crosshair = "1";
  const ns = "http://www.w3.org/2000/svg";
  const line = document.createElementNS(ns, "line");
  line.setAttribute("class", "dt-crosshair");
  line.setAttribute("y1", "0");
  line.setAttribute("y2", "100%");
  line.style.display = "none";
  svg.append(line);
  svg.addEventListener("pointermove", (e) => {
    const rect = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const sx = ((e.clientX - rect.left) / rect.width) * (vb?.width || rect.width);
    let nearest = points[0];
    for (const p of points) if (Math.abs(p.x - sx) < Math.abs(nearest.x - sx)) nearest = p;
    line.setAttribute("x1", nearest.x);
    line.setAttribute("x2", nearest.x);
    line.setAttribute("y1", vb ? 0 : 0);
    line.setAttribute("y2", vb ? vb.height : rect.height);
    line.style.display = "";
    showTip(renderTip(nearest), e.clientX, e.clientY);
  });
  svg.addEventListener("pointerleave", () => {
    line.style.display = "none";
    hideTip();
  });
}
