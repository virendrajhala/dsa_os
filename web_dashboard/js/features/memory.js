import { state, RENDERERS } from "../legacy/app.js";
import { matureRecallStats, maturityBuckets } from "../derive/memory.js";
import { svgEl } from "../svg.js";
import { openProblemList } from "../engine/drilldown.js";

const TARGET = 0.9;

function gaugePoint(cx, cy, r, t) {
  const angle = Math.PI * (1 - t);
  return { x: cx + r * Math.cos(angle), y: cy - r * Math.sin(angle) };
}

function renderRetentionGauge(host, stats) {
  host.replaceChildren();
  const W = 220;
  const H = 132;
  const cx = 110;
  const cy = 108;
  const r = 86;
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "retention-gauge-svg", role: "img" });
  const arc = (radius) => `M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`;
  svg.append(svgEl("path", { d: arc(r), fill: "none", stroke: "currentColor", "stroke-opacity": 0.15, "stroke-width": 12, "stroke-linecap": "round", pathLength: 100 }));
  if (stats.rate !== null) {
    svg.append(svgEl("path", {
      d: arc(r), fill: "none", stroke: "var(--accent, #4ba3a0)", "stroke-width": 12, "stroke-linecap": "round",
      pathLength: 100, "stroke-dasharray": `${(stats.rate * 100).toFixed(1)} 100`,
    }));
  }
  // Target tick at 90%
  const t1 = gaugePoint(cx, cy, r - 10, TARGET);
  const t2 = gaugePoint(cx, cy, r + 10, TARGET);
  svg.append(svgEl("line", { x1: t1.x, y1: t1.y, x2: t2.x, y2: t2.y, stroke: "currentColor", "stroke-opacity": 0.6, "stroke-width": 2 }));
  svg.append(svgEl("text", { x: cx, y: cy - 26, "text-anchor": "middle", class: "gauge-value num", fill: "currentColor", "font-size": 26 },
    stats.rate === null ? "–" : `${Math.round(stats.rate * 100)}%`));
  svg.append(svgEl("text", { x: cx, y: cy - 6, "text-anchor": "middle", fill: "currentColor", "fill-opacity": 0.65, "font-size": 11 },
    `${stats.pass}/${stats.total} mature recalls`));
  host.append(svg);
  const cap = document.createElement("p");
  cap.className = "microlabel";
  cap.style.textAlign = "center";
  cap.textContent = "true retention · target 90% (tick)";
  host.append(cap);
  host.dataset.tip = stats.rate === null
    ? "No graded recalls on mature problems yet (revision stage ≥ 2)."
    : `Pass rate of recalls on mature problems (stage ≥ 2): ${stats.pass}/${stats.total}.`;
}

function renderMaturityDonut(host, buckets, bucketItems) {
  host.replaceChildren();
  const total = buckets.new + buckets.learning + buckets.young + buckets.mature;
  const W = 220;
  const H = 132;
  const cx = 110;
  const cy = 66;
  const r = 52;
  const C = 2 * Math.PI * r;
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "maturity-donut-svg", role: "img" });
  const order = [
    { key: "new", label: "new", color: "color-mix(in srgb, currentColor 18%, transparent)" },
    { key: "learning", label: "learning · R1-R2 ahead", color: "var(--warn, #d9822b)" },
    { key: "young", label: "young · stage 2-3", color: "var(--series-1, #5aa9e6)" },
    { key: "mature", label: "mature · mastered", color: "var(--good, #3f9c6b)" },
  ];
  const center = svgEl("text", { x: cx, y: cy - 2, "text-anchor": "middle", fill: "currentColor", "font-size": 22, class: "num" }, String(total));
  const centerLabel = svgEl("text", { x: cx, y: cy + 16, "text-anchor": "middle", fill: "currentColor", "fill-opacity": 0.65, "font-size": 10 }, "problems");
  let offset = 0;
  for (const seg of order) {
    const count = buckets[seg.key];
    if (!count) continue;
    const frac = count / total;
    const ring = svgEl("circle", {
      cx, cy, r, fill: "none", stroke: seg.color, "stroke-width": 16,
      "stroke-dasharray": `${frac * C} ${C}`, "stroke-dashoffset": String(-offset * C),
      transform: `rotate(-90 ${cx} ${cy})`, class: "donut-seg",
    });
    ring.style.cursor = "pointer";
    ring.addEventListener("pointerover", () => {
      center.textContent = String(count);
      centerLabel.textContent = seg.label;
    });
    ring.addEventListener("pointerout", () => {
      center.textContent = String(total);
      centerLabel.textContent = "problems";
    });
    ring.addEventListener("click", () => openProblemList({
      title: `Maturity: ${seg.label}`,
      subtitle: `${count} problem${count === 1 ? "" : "s"}`,
      items: bucketItems[seg.key],
    }));
    svg.append(ring);
    offset += frac;
  }
  svg.append(center, centerLabel);
  host.append(svg);
  const cap = document.createElement("p");
  cap.className = "microlabel";
  cap.style.textAlign = "center";
  cap.textContent = "maturity · hover a segment, click to list";
  host.append(cap);
}

export function renderMemoryPack() {
  const gaugeHost = document.querySelector("#retention-gauge");
  const donutHost = document.querySelector("#maturity-donut");
  if (!gaugeHost || !donutHost) return;
  const completed = state.datasets.progress.completed || [];
  renderRetentionGauge(gaugeHost, matureRecallStats(completed));

  const totalProblems = state.problemsById.size;
  const buckets = maturityBuckets(totalProblems, completed);
  const completedIds = new Set(completed.map((r) => r.problem_id));
  const bucketItems = {
    new: [...state.problemsById.keys()].filter((id) => !completedIds.has(id)).map((id) => ({ problemId: id })),
    learning: completed.filter((r) => r.revision?.status !== "MASTERED" && (r.revision?.stage ?? 0) < 2).map((r) => ({ problemId: r.problem_id })),
    young: completed.filter((r) => r.revision?.status !== "MASTERED" && (r.revision?.stage ?? 0) >= 2).map((r) => ({ problemId: r.problem_id })),
    mature: completed.filter((r) => r.revision?.status === "MASTERED").map((r) => ({ problemId: r.problem_id })),
  };
  renderMaturityDonut(donutHost, buckets, bucketItems);
}

RENDERERS.byWorkspace.evidence.push(renderMemoryPack);
