import { state, RENDERERS } from "../legacy/app.js";
import { paceProjection } from "../derive/pace.js";
import { diffDays } from "../derive/dates.js";
import { svgEl } from "../svg.js";

const WHATIF_KEY = "whatif-hours";

// Mirrors the geometry legacy renderQuarterRoadmap uses for #burnup-chart's
// SVG (viewBox 660x220), so the dashed extension lands on the same scale.
const W = 660;
const H = 220;
const PAD_L = 34;
const PAD_R = 12;
const PAD_T = 14;
const PAD_B = 26;

function chartFns(burnup) {
  const start = Date.parse(`${burnup.start}T00:00:00Z`);
  const end = Date.parse(`${burnup.end}T00:00:00Z`);
  const totalDays = Math.max(1, Math.round((end - start) / 86400000));
  const yMax = Math.max(burnup.target_total, burnup.projected_total, 1);
  const xFor = (iso) => {
    const t = Math.min(1, Math.max(0, Math.round((Date.parse(`${iso}T00:00:00Z`) - start) / 86400000) / totalDays));
    return PAD_L + t * (W - PAD_L - PAD_R);
  };
  const yFor = (count) => H - PAD_B - Math.min(1, Math.max(0, count / yMax)) * (H - PAD_T - PAD_B);
  return { xFor, yFor };
}

function drawProjection(burnup, projection, today) {
  const svg = document.querySelector("#burnup-chart svg");
  if (!svg) return;
  svg.querySelectorAll(".pace-velocity-line").forEach((el) => el.remove());
  if (!projection.finishIso) return;
  const { xFor, yFor } = chartFns(burnup);
  const actual = burnup.actual || [];
  const last = actual.length ? actual[actual.length - 1] : { date: today, cumulative: burnup.actual_total };
  // Clamp the landing point to the chart's right edge when the projected
  // finish overshoots the quarter.
  let endIso = projection.finishIso;
  let endCount = burnup.target_total;
  if (endIso > burnup.end) {
    const rate = (burnup.target_total - burnup.actual_total) / Math.max(1, diffDays(today, projection.finishIso));
    endIso = burnup.end;
    endCount = burnup.actual_total + rate * Math.max(0, diffDays(today, burnup.end));
  }
  svg.append(svgEl("line", {
    x1: xFor(last.date), y1: yFor(last.cumulative || 0),
    x2: xFor(endIso), y2: yFor(endCount),
    class: "pace-velocity-line",
    stroke: "var(--accent)",
    "stroke-width": 2,
    "stroke-dasharray": "6 5",
    fill: "none",
    "pointer-events": "none",
  }));
}

export function renderPacePanel() {
  const host = document.querySelector("#pace-projection");
  if (!host) return;
  const burnup = state.feed?.plan?.burnup;
  if (!burnup || !burnup.start) {
    host.hidden = true;
    host.replaceChildren();
    return;
  }
  host.hidden = false;
  const today = state.feed.reference_date;
  const args = { solved: burnup.actual_total, target: burnup.target_total, startIso: burnup.start, endIso: burnup.end, todayIso: today };
  const base = paceProjection(args);
  const storedRaw = Number(localStorage.getItem(WHATIF_KEY));
  const stored = storedRaw >= 1 && storedRaw <= 15 ? storedRaw : Math.max(1, Math.round(base.velocityPerWeek) || 5);

  host.innerHTML = `
    <p class="num" id="pace-line">At current pace (${base.velocityPerWeek.toFixed(1)} solves/wk): ${base.finishIso ? `finish ~${base.finishIso}` : "no finish in sight"}
      <span class="pill num ${base.onTrack ? "good" : "warn"}">${base.onTrack ? "on track" : "behind"}</span></p>
    <label class="microlabel" for="whatif-slider">what if I did <strong class="num" id="whatif-value">${stored}</strong>/wk?</label>
    <input type="range" id="whatif-slider" min="1" max="15" step="1" value="${stored}" />
    <p class="num microlabel" id="whatif-line"></p>`;

  const slider = host.querySelector("#whatif-slider");
  const valueEl = host.querySelector("#whatif-value");
  const lineEl = host.querySelector("#whatif-line");
  const applyWhatIf = (n) => {
    const p = paceProjection({ ...args, whatIfPerWeek: n });
    valueEl.textContent = String(n);
    lineEl.textContent = p.finishIso
      ? `At ${n}/wk: finish ~${p.finishIso} (${p.onTrack ? "on track" : "past the quarter"})`
      : `At ${n}/wk: never finishes`;
    drawProjection(burnup, base, today);
  };
  applyWhatIf(stored);
  slider.addEventListener("input", () => {
    const n = Number(slider.value);
    localStorage.setItem(WHATIF_KEY, String(n));
    applyWhatIf(n);
  });
}

RENDERERS.byWorkspace.plan.push(renderPacePanel);
