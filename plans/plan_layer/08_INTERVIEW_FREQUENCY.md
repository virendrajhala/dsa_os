# Feature 08 — Interview-Ask Frequency in the Problem Browser

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Requires Feature 07 (Problem Browser) complete.

**Goal:** Every problem row in the browser shows how often it is asked in real interviews (★★★ very high → · low), with top companies on hover, and the list can be sorted by that frequency.

**Architecture — snapshot, not live scraping.** LeetCode's own frequency data is premium and scraping it violates their ToS; the repo is also stdlib-only and the dashboard offline-first. So: a one-time (re-runnable) script `scripts/fetch_interview_frequency.py` downloads a community-maintained company-wise dataset from GitHub, aggregates it per problem, and writes a committed static file `curriculum/interview_frequency.json` keyed by LeetCode slug. The dashboard reads that file like any other static JSON (works with no server and no internet). Refresh anytime with `make refresh-frequency`.

**Data source:** `github.com/liquidslr/leetcode-company-wise-problems` (community-maintained CSVs, one folder per company, one CSV per time window incl. an "All" window; columns include Title, Frequency, Link). Fallback if the repo disappears: `github.com/krishnadey30/LeetCode-Questions-CompanyWise` (same shape, flat files). The script must not hard-fail on column-name drift — see the tolerant-parse rules in Task 1.

**Join key:** LeetCode slug parsed from each URL (`https://leetcode.com/problems/<slug>/`). 572/582 curriculum problems carry a `url`; the rest simply show "–" (unknown). `lc_id` is NOT the join key (community CSVs don't reliably carry ids).

**Honesty rule for the UI copy:** this is a community snapshot, approximate by nature — the section note must say the source and snapshot date, never present it as live LeetCode data.

## Global constraints

- Python stdlib only: `urllib.request`, `zipfile`, `io`, `csv`, `json`, `argparse`, `datetime`. Network I/O happens ONLY inside `fetch_interview_frequency.py` when explicitly run — never at feed/serve time, never in tests.
- Tests (in `scripts/test_plan_feed.py`) exercise the pure functions with an in-memory synthetic zip — zero network.
- Tier assignment is rank-based (no dataset-scale assumptions): sort matched slugs by `(companies, score)` descending → top 10% `very_high`, next 20% `high`, next 30% `medium`, rest `low` (each bucket at least 1 when non-empty).
- Commit style `feat/frequency: ...`; no Co-Authored-By.

## Data contract — `curriculum/interview_frequency.json`

```json
{
  "schema_version": 1,
  "source": "github.com/liquidslr/leetcode-company-wise-problems",
  "retrieved_at": "2026-08-03",
  "problems": {
    "two-sum": {
      "companies": 312,
      "score": 1543.2,
      "tier": "very_high",
      "top_companies": ["Google", "Amazon", "Meta", "Microsoft", "Bloomberg"]
    }
  }
}
```

---

### Task 1: `scripts/fetch_interview_frequency.py`

**Files:**
- Create: `scripts/fetch_interview_frequency.py`
- Modify: `scripts/test_plan_feed.py` (append test class)
- Modify: `Makefile` (add `refresh-frequency` target)

**Interfaces:**
- Produces (importable pure functions, tested directly):
  - `slug_from_url(url: str) -> str | None` — `"https://leetcode.com/problems/two-sum/"` → `"two-sum"`; None for non-problem URLs.
  - `parse_dataset_zip(zip_bytes: bytes) -> dict[str, dict[str, float]]` — `{slug: {company: max_frequency}}`.
  - `aggregate(per_company: dict[str, dict[str, float]]) -> dict[str, dict]` — `{slug: {companies, score, top_companies}}`.
  - `assign_tiers(aggregated: dict[str, dict]) -> None` — adds `tier` in place, rank-based buckets above.
- CLI: `python3 scripts/fetch_interview_frequency.py [--url ZIP_URL] [--source-zip LOCAL.zip] [--out PATH]` — default url `https://codeload.github.com/liquidslr/leetcode-company-wise-problems/zip/refs/heads/main`, default out `curriculum/interview_frequency.json`.

**Tolerant-parse rules (dataset drift protection):**
- A CSV row's slug comes from the first column whose lowercase header contains `link` or `url`; frequency from the first header containing `freq` (else `1.0` per row); rows without a parsable slug are skipped.
- Company name = first path segment under the zip root (folder-per-company layout) else the CSV filename stem (flat layout).
- When a company folder has several time-window CSVs and any filename contains `all` (case-insensitive), parse only those; otherwise parse every CSV and keep the per-(company, slug) max frequency.
- Exit non-zero with a clear message if fewer than 500 distinct slugs parse (dataset shape changed — do not silently write garbage).

- [ ] **Step 1: Failing tests** (append to `scripts/test_plan_feed.py`):

```python
class InterviewFrequencyTests(unittest.TestCase):
    @staticmethod
    def _zip(files):
        import io
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for path, content in files.items():
                archive.writestr(path, content)
        return buffer.getvalue()

    def test_slug_from_url(self):
        from fetch_interview_frequency import slug_from_url
        self.assertEqual(
            slug_from_url("https://leetcode.com/problems/two-sum/"), "two-sum")
        self.assertEqual(
            slug_from_url("https://leetcode.com/problems/two-sum/description/"), "two-sum")
        self.assertIsNone(slug_from_url("https://leetcode.com/explore/"))
        self.assertIsNone(slug_from_url(None))

    def test_parse_prefers_all_window_and_takes_max(self):
        from fetch_interview_frequency import parse_dataset_zip
        header = "Difficulty,Title,Frequency,Link\n"
        payload = self._zip({
            "repo-main/Google/1. Thirty Days.csv":
                header + "Easy,Two Sum,99.0,https://leetcode.com/problems/two-sum/\n",
            "repo-main/Google/5. All.csv":
                header + "Easy,Two Sum,61.5,https://leetcode.com/problems/two-sum/\n"
                + "Hard,Word Ladder,10.0,https://leetcode.com/problems/word-ladder/\n",
            "repo-main/Amazon/5. All.csv":
                header + "Easy,Two Sum,80.0,https://leetcode.com/problems/two-sum/\n",
        })
        parsed = parse_dataset_zip(payload)
        # "All" window wins over "Thirty Days" for Google.
        self.assertEqual(parsed["two-sum"]["Google"], 61.5)
        self.assertEqual(parsed["two-sum"]["Amazon"], 80.0)
        self.assertEqual(parsed["word-ladder"], {"Google": 10.0})

    def test_aggregate_and_tiers(self):
        from fetch_interview_frequency import aggregate, assign_tiers
        per_company = {
            f"slug-{index}": {f"c{c}": 1.0 for c in range(count)}
            for index, count in enumerate([50, 40, 30, 20, 10, 8, 6, 4, 2, 1])
        }
        aggregated = aggregate(per_company)
        self.assertEqual(aggregated["slug-0"]["companies"], 50)
        assign_tiers(aggregated)
        tiers = [aggregated[f"slug-{index}"]["tier"] for index in range(10)]
        # rank-based: 10% very_high, 20% high, 30% medium, rest low
        self.assertEqual(tiers, ["very_high", "high", "high",
                                 "medium", "medium", "medium",
                                 "low", "low", "low", "low"])

    def test_top_companies_sorted_by_frequency(self):
        from fetch_interview_frequency import aggregate
        aggregated = aggregate({"two-sum": {"A": 1.0, "B": 9.0, "C": 5.0}})
        self.assertEqual(aggregated["two-sum"]["top_companies"][:2], ["B", "C"])
```

- [ ] **Step 2: Run to verify failure** (`ModuleNotFoundError: fetch_interview_frequency`).

- [ ] **Step 3: Implement** `scripts/fetch_interview_frequency.py`:

```python
#!/usr/bin/env python3
"""Build curriculum/interview_frequency.json from a community company-wise
dataset (one-shot snapshot; the dashboard never fetches the internet)."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = (
    "https://codeload.github.com/liquidslr/"
    "leetcode-company-wise-problems/zip/refs/heads/main"
)
DEFAULT_OUT = ROOT / "curriculum" / "interview_frequency.json"
DEFAULT_SOURCE_LABEL = "github.com/liquidslr/leetcode-company-wise-problems"
MIN_EXPECTED_SLUGS = 500
TIER_FRACTIONS = (("very_high", 0.10), ("high", 0.20), ("medium", 0.30))


def slug_from_url(url) -> str | None:
    if not isinstance(url, str) or "/problems/" not in url:
        return None
    tail = url.split("/problems/", 1)[1]
    slug = tail.split("/", 1)[0].split("?", 1)[0].strip()
    return slug or None


def _pick_column(headers: list[str], *needles: str) -> str | None:
    for header in headers:
        lowered = header.lower()
        if any(needle in lowered for needle in needles):
            return header
    return None


def _company_of(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    # zip root dir ("repo-main") / company / file.csv — else flat: use stem.
    if len(parts) >= 3:
        return parts[1]
    return Path(parts[-1]).stem


def parse_dataset_zip(zip_bytes: bytes) -> dict[str, dict[str, float]]:
    """Return {slug: {company: max_frequency}} from a dataset archive."""

    archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    csv_paths = [name for name in archive.namelist() if name.lower().endswith(".csv")]
    by_company: dict[str, list[str]] = {}
    for path in csv_paths:
        by_company.setdefault(_company_of(path), []).append(path)

    result: dict[str, dict[str, float]] = {}
    for company, paths in by_company.items():
        all_window = [path for path in paths if "all" in Path(path).name.lower()]
        for path in all_window or paths:
            text = archive.read(path).decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                continue
            link_col = _pick_column(reader.fieldnames, "link", "url")
            freq_col = _pick_column(reader.fieldnames, "freq")
            if link_col is None:
                continue
            for row in reader:
                slug = slug_from_url(row.get(link_col))
                if slug is None:
                    continue
                try:
                    frequency = float(row.get(freq_col, 1.0)) if freq_col else 1.0
                except (TypeError, ValueError):
                    frequency = 1.0
                companies = result.setdefault(slug, {})
                companies[company] = max(companies.get(company, 0.0), frequency)
    return result


def aggregate(per_company: dict[str, dict[str, float]]) -> dict[str, dict]:
    aggregated: dict[str, dict] = {}
    for slug, companies in per_company.items():
        ranked = sorted(companies.items(), key=lambda item: -item[1])
        aggregated[slug] = {
            "companies": len(companies),
            "score": round(sum(companies.values()), 1),
            "top_companies": [name for name, _ in ranked[:5]],
        }
    return aggregated


def assign_tiers(aggregated: dict[str, dict]) -> None:
    """Rank-based tiers: 10% very_high, 20% high, 30% medium, rest low."""

    ranked = sorted(
        aggregated,
        key=lambda slug: (-aggregated[slug]["companies"], -aggregated[slug]["score"]),
    )
    total = len(ranked)
    cursor = 0
    for tier, fraction in TIER_FRACTIONS:
        count = max(1, round(total * fraction)) if total else 0
        for slug in ranked[cursor:cursor + count]:
            aggregated[slug]["tier"] = tier
        cursor += count
    for slug in ranked[cursor:]:
        aggregated[slug]["tier"] = "low"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--source-zip", help="Local dataset zip (skips download).")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    if args.source_zip:
        zip_bytes = Path(args.source_zip).read_bytes()
    else:
        print(f"Downloading {args.url} ...")
        with urllib.request.urlopen(args.url, timeout=120) as response:
            zip_bytes = response.read()

    per_company = parse_dataset_zip(zip_bytes)
    if len(per_company) < MIN_EXPECTED_SLUGS:
        print(
            f"Only {len(per_company)} slugs parsed (expected >= {MIN_EXPECTED_SLUGS}). "
            "Dataset layout likely changed — refusing to write.",
            file=sys.stderr,
        )
        return 1
    aggregated = aggregate(per_company)
    assign_tiers(aggregated)

    curriculum = json.loads((ROOT / "curriculum" / "curriculum.json").read_text())
    slugs_in_curriculum = {
        slug
        for problem in curriculum.get("problems", [])
        if (slug := slug_from_url(problem.get("url"))) is not None
    }
    matched = sum(1 for slug in slugs_in_curriculum if slug in aggregated)

    payload = {
        "schema_version": 1,
        "source": DEFAULT_SOURCE_LABEL if not args.source_zip else f"local:{args.source_zip}",
        "retrieved_at": date.today().isoformat(),
        "problems": {slug: aggregated[slug] for slug in sorted(aggregated)},
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
    print(
        f"Wrote {out_path} — {len(aggregated)} problems, "
        f"{matched}/{len(slugs_in_curriculum)} curriculum problems matched."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests** — `python3 scripts/test_plan_feed.py` → PASS.

- [ ] **Step 5: Makefile target** (below `check-solution:`):

```make
refresh-frequency:
	$(PYTHON) scripts/fetch_interview_frequency.py
```

- [ ] **Step 6: Generate the real snapshot (network — needs owner ok if offline)**

Run: `make refresh-frequency`
Expected: `Wrote curriculum/interview_frequency.json — N problems, M/572 curriculum problems matched.` with M comfortably above 400. If the download 404s, retry with the fallback source: `python3 scripts/fetch_interview_frequency.py --url https://codeload.github.com/krishnadey30/LeetCode-Questions-CompanyWise/zip/refs/heads/master`.

- [ ] **Step 7: Commit**

```bash
git add scripts/fetch_interview_frequency.py scripts/test_plan_feed.py Makefile curriculum/interview_frequency.json
git commit -m "feat/frequency: snapshot interview-ask frequency per problem"
```

---

### Task 2: Frequency column + sort in the Problem Browser

**Files:**
- Modify: `web_dashboard/app.js`
- Modify: `web_dashboard/index.html`
- Modify: `web_dashboard/styles.css`

**Interfaces:**
- Consumes: Feature 07's `renderProblemBrowser`/`browserState`/`browserProblemsForSelection`, `slug` derivable from `problem.url` in JS.
- Produces: `state.frequency` (nullable dataset), `frequencyFor(problem)`, an "Asked" column, and a sort selector (`curriculum` | `frequency`).

- [ ] **Step 1: Optional load (must NOT break the dashboard when the file is absent).** In `loadData()` (app.js:215), after `state.feed = await fetchFeed();` add:

```js
    // Interview-frequency snapshot is optional: generated by
    // scripts/fetch_interview_frequency.py; absence degrades to "–".
    state.frequency = await fetchJson("../curriculum/interview_frequency.json").catch(() => null);
```

And add `frequency: null,` to the `state` object literal (app.js:12).

- [ ] **Step 2: Helper + glyph map** (next to `problemStatus` from Feature 07):

```js
  const FREQUENCY_TIERS = {
    very_high: { glyph: "★★★", label: "very high" },
    high: { glyph: "★★", label: "high" },
    medium: { glyph: "★", label: "medium" },
    low: { glyph: "·", label: "low" },
  };

  function frequencyFor(problem) {
    if (!state.frequency || !problem.url || !problem.url.includes("/problems/")) return null;
    const slug = problem.url.split("/problems/")[1].split("/")[0];
    return state.frequency.problems?.[slug] || null;
  }
```

- [ ] **Step 3: Column.** In the browser table `<thead>` (Feature 07 Task 2 markup) insert `<th>Asked</th>` between `Importance` and `Status`. In the row builder insert between `importance` and `statusCell`:

```js
      const asked = document.createElement("td");
      asked.className = "num freq-cell";
      const freq = frequencyFor(problem);
      if (!freq) {
        asked.textContent = "–";
      } else {
        const spec = FREQUENCY_TIERS[freq.tier] || FREQUENCY_TIERS.low;
        asked.textContent = spec.glyph;
        asked.title =
          `${spec.label} · listed by ${freq.companies} companies` +
          (freq.top_companies?.length ? ` · top: ${freq.top_companies.join(", ")}` : "");
        asked.setAttribute("aria-label", `asked frequency ${spec.label}`);
      }
```

…and update `row.append(...)` to include `asked` in position, plus the empty-state `colSpan` from 7 → 8.

- [ ] **Step 4: Sort control.** In the browser toolbar markup add:

```html
            <select id="browser-sort" aria-label="Sort problems">
              <option value="curriculum">Curriculum order</option>
              <option value="frequency">Interview frequency</option>
            </select>
```

Add `sort: "curriculum"` to `browserState`; listener next to the other browser listeners:

```js
      const browserSort = $("#browser-sort");
      if (browserSort) browserSort.addEventListener("change", () => {
        browserState.sort = browserSort.value;
        renderProblemBrowser();
      });
```

In `renderProblemBrowser()` after the filters:

```js
    if (browserState.sort === "frequency") {
      const rank = { very_high: 0, high: 1, medium: 2, low: 3 };
      rows = [...rows].sort((a, b) => {
        const fa = frequencyFor(a);
        const fb = frequencyFor(b);
        if (!fa && !fb) return 0;
        if (!fa) return 1;
        if (!fb) return -1;
        return (rank[fa.tier] ?? 9) - (rank[fb.tier] ?? 9) || fb.companies - fa.companies;
      });
    }
```

- [ ] **Step 5: Source note.** Under the browser table add:

```html
              <p class="chart-note microlabel" id="frequency-note"></p>
```

and at the end of `renderProblemBrowser()`:

```js
    const note = $("#frequency-note");
    if (note) {
      note.textContent = state.frequency
        ? `"Asked" = community snapshot from ${state.frequency.source} (${state.frequency.retrieved_at}); approximate, not live LeetCode data.`
        : `"Asked" column unavailable — run make refresh-frequency to generate curriculum/interview_frequency.json.`;
    }
```

- [ ] **Step 6: Style:**

```css
.freq-cell { letter-spacing: 0.1em; white-space: nowrap; }
```

- [ ] **Step 7: Verify (falsifying checks)**
1. `node --check` clean.
2. Two Sum shows `★★★` with a tooltip listing companies; a niche problem shows `·` or `–`.
3. Sort by frequency puts `★★★` rows first and all `–` rows last; switching back restores curriculum order.
4. Delete/rename `curriculum/interview_frequency.json` → dashboard still loads, column shows `–`, note explains how to regenerate; restore.
5. Works without the server (static file fetch, not the feed).

- [ ] **Step 8: Commit**

```bash
git add web_dashboard/index.html web_dashboard/app.js web_dashboard/styles.css
git commit -m "feat/dashboard: interview-ask frequency column and sort in browser"
```

## Maintenance

Re-run `make refresh-frequency` every few months (dataset drifts slowly). The 500-slug floor in the script refuses to overwrite good data with a broken download. If both source repos vanish, any CSV dataset with Link+Frequency columns zipped in the same shape works via `--source-zip`.
