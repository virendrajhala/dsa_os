# Feature 06 — Time-Invested Analytics (Evidence workspace)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Requires Feature 02 complete (feed exposes `time_invested`).

**Goal:** Surface `time_taken_minutes` (recorded on every solve, currently visible only inside the problem modal): total hours, average by difficulty, and a per-solve minutes chart over time.

**Architecture:** Pure view over `feed.time_invested`. One Evidence section: three stat tiles + an SVG bar-per-solve chart (bars colored by difficulty with a legend and direct `<title>` tooltips — difficulty is also encoded in the tooltip text, never color alone).

**Feed contract consumed:**

```json
"time_invested": {
  "total_minutes": 785, "sessions": 13, "average_minutes": 60.4,
  "by_difficulty": [{"difficulty": "Easy", "count": 9, "average_minutes": 54.4}],
  "series": [{"date": "2026-07-09", "problem_id": "OBS-001", "minutes": 45, "difficulty": "Easy"}]
}
```

---

### Task 1: Section + renderer

**Files:**
- Modify: `web_dashboard/index.html` — Evidence nav link + section
- Modify: `web_dashboard/app.js` — `renderTimeInvested`, registered in `renderAll()` after `renderConsistency();`
- Modify: `web_dashboard/styles.css`

- [ ] **Step 1: Nav link.** In the Evidence nav group, after the `#consistency` link (index.html:38):

```html
          <a href="#time-invested" data-workspace-link="evidence"><span class="nav-icon num" aria-hidden="true">TI</span><span class="nav-text">Time Invested</span></a>
```

- [ ] **Step 2: Section.** In `index.html`, after the closing `</section>` of `#consistency` (index.html:330):

```html
        <section id="time-invested" class="section" data-workspace-section="evidence">
          <div class="section-head">
            <div>
              <p class="eyebrow microlabel">Effort</p>
              <h3>Time invested</h3>
            </div>
            <span class="pill num" id="time-total-pill">-</span>
          </div>
          <div id="time-tiles" class="pace-tiles"></div>
          <div id="time-chart" class="insight-chart" role="img"></div>
          <div id="time-legend" class="chart-legend"></div>
          <p class="chart-note microlabel">Minutes per solve, in solve order. Falling bars at constant difficulty = growing fluency; a Medium/Hard mix pushes averages up by design.</p>
        </section>
```

- [ ] **Step 3: Renderer:**

```js
  const DIFFICULTY_SERIES = {
    Easy: "var(--series-3)",
    Medium: "var(--series-4)",
    Hard: "var(--series-8)",
    Unknown: "var(--muted)",
  };

  function renderTimeInvested() {
    const tiles = $("#time-tiles");
    const chart = $("#time-chart");
    const legendHost = $("#time-legend");
    const pillNode = $("#time-total-pill");
    if (!tiles || !chart) return;
    tiles.replaceChildren();
    chart.replaceChildren();
    if (legendHost) legendHost.replaceChildren();
    if (pillNode) pillNode.textContent = "-";
    if (!feedAvailable()) {
      chart.append(degradedBanner());
      return;
    }
    const invested = state.feed.time_invested || {};
    const series = invested.series || [];
    if (!series.length) {
      chart.append(empty("No timed solves recorded yet."));
      return;
    }
    const hours = (invested.total_minutes || 0) / 60;
    if (pillNode) pillNode.textContent = `${hours.toFixed(1)} h total`;

    const tileData = [
      { label: "Total time", value: `${hours.toFixed(1)} h`, note: `${invested.sessions} timed solves` },
      { label: "Average / solve", value: `${invested.average_minutes} min`, note: "all difficulties" },
      ...(invested.by_difficulty || []).map((bucket) => ({
        label: `${bucket.difficulty} average`,
        value: `${bucket.average_minutes} min`,
        note: `${bucket.count} solve${bucket.count === 1 ? "" : "s"}`,
      })),
    ];
    tileData.forEach((tile) => {
      const node = document.createElement("div");
      node.className = "pace-tile";
      const label = document.createElement("span");
      label.className = "microlabel";
      label.textContent = tile.label;
      const value = document.createElement("strong");
      value.className = "num";
      value.textContent = tile.value;
      const note = document.createElement("small");
      note.className = "microlabel";
      note.textContent = tile.note;
      node.append(label, value, note);
      tiles.append(node);
    });

    const svgNS = "http://www.w3.org/2000/svg";
    const W = 660;
    const H = 190;
    const PAD_L = 34;
    const PAD_R = 10;
    const PAD_T = 16;
    const PAD_B = 24;
    const maxMinutes = Math.max(...series.map((entry) => entry.minutes), 30);
    const bandW = (W - PAD_L - PAD_R) / series.length;
    const barW = Math.min(bandW - 2, 26);
    const plotH = H - PAD_T - PAD_B;
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "time-svg");
    const make = (name, attrs, textContent) => {
      const el = document.createElementNS(svgNS, name);
      Object.entries(attrs).forEach(([key, val]) => el.setAttribute(key, String(val)));
      if (textContent != null) el.textContent = textContent;
      return el;
    };
    svg.append(make("line", {
      x1: PAD_L, y1: H - PAD_B, x2: W - PAD_R, y2: H - PAD_B, class: "forecast-baseline",
    }));
    svg.append(make("text", { x: 2, y: PAD_T + 4, class: "forecast-axis" }, `${maxMinutes}m`));
    svg.append(make("text", { x: 2, y: H - PAD_B + 4, class: "forecast-axis" }, "0"));
    series.forEach((entry, index) => {
      const x = PAD_L + index * bandW + (bandW - barW) / 2;
      const h = Math.max((plotH * entry.minutes) / maxMinutes, 2);
      const bar = make("rect", {
        x, y: H - PAD_B - h, width: barW, height: h, rx: 3,
        fill: DIFFICULTY_SERIES[entry.difficulty] || DIFFICULTY_SERIES.Unknown,
        class: "time-bar",
      });
      bar.append(make("title", {},
        `${entry.problem_id} · ${entry.date} · ${entry.minutes} min · ${entry.difficulty || "Unknown"}`));
      svg.append(bar);
    });
    chart.append(svg);
    chart.setAttribute("aria-label",
      `Minutes per solve for ${series.length} solves; total ${hours.toFixed(1)} hours; ` +
      `average ${invested.average_minutes} minutes.`);

    if (legendHost) {
      const seen = [...new Set(series.map((entry) => entry.difficulty || "Unknown"))];
      legendHost.append(chartLegend(
        seen.map((difficulty) => ({
          label: difficulty,
          shape: "line",
          color: DIFFICULTY_SERIES[difficulty] || DIFFICULTY_SERIES.Unknown,
        })),
      ));
    }
  }
```

(Same `chartLegend` note as Feature 04: match the existing call-site signature at app.js:4241; never modify the helper.)

- [ ] **Step 4: Styles:**

```css
.time-svg { width: 100%; height: auto; }
.time-bar:hover { opacity: 0.85; }
```

- [ ] **Step 5: Verify (falsifying checks)**
1. `node --check web_dashboard/app.js` clean.
2. Tile numbers equal `curl -s http://127.0.0.1:8765/api/feed | python3 -c "import json,sys; t=json.load(sys.stdin)['time_invested']; print(t['total_minutes'], t['average_minutes'], t['by_difficulty'])"`.
3. Bar count equals `sessions`; hover tooltip carries problem id, date, minutes AND difficulty (text, not color-only).
4. The 150-minute CPX-005 bar is the tallest; the 20-minute bars are visibly short but present (min height 2px).
5. Without server: degraded banner; both themes readable.

- [ ] **Step 6: Final full verification (whole plan layer)**

```bash
make test
node --check web_dashboard/app.js
```
Then one full manual pass: all four prior features visible, zero console errors with and without the server.

- [ ] **Step 7: Commit**

```bash
git add web_dashboard/index.html web_dashboard/app.js web_dashboard/styles.css
git commit -m "feat/dashboard: time-invested analytics"
```
