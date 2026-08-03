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
FALLBACK_URL = (
    "https://codeload.github.com/krishnadey30/"
    "LeetCode-Questions-CompanyWise/zip/refs/heads/master"
)
DEFAULT_OUT = ROOT / "curriculum" / "interview_frequency.json"
DEFAULT_SOURCE_LABEL = "github.com/liquidslr/leetcode-company-wise-problems"
FALLBACK_SOURCE_LABEL = "github.com/krishnadey30/LeetCode-Questions-CompanyWise"
MIN_EXPECTED_SLUGS = 500
TIER_FRACTIONS = (("very_high", 0.10), ("high", 0.20), ("medium", 0.30))


def slug_from_url(url: str) -> str | None:
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
    if len(parts) >= 3:
        return parts[1]
    return Path(parts[-1]).stem


def parse_dataset_zip(zip_bytes: bytes) -> dict[str, dict[str, float]]:
    """Return {slug: {company: max_frequency}} from a dataset archive."""

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_paths = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]
        by_company: dict[str, list[str]] = {}
        for path in csv_paths:
            by_company.setdefault(_company_of(path), []).append(path)

        result: dict[str, dict[str, float]] = {}
        for company, paths in by_company.items():
            all_window = [
                path for path in paths
                if "all" in Path(path).name.lower()
            ]
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
        ranked = sorted(companies.items(), key=lambda item: (-item[1], item[0]))
        aggregated[slug] = {
            "companies": len(companies),
            "score": round(sum(companies.values()), 1),
            "top_companies": [name for name, _ in ranked[:5]],
        }
    return aggregated


def assign_tiers(aggregated: dict[str, dict]) -> None:
    ranked = sorted(
        aggregated,
        key=lambda slug: (
            -aggregated[slug]["companies"],
            -aggregated[slug]["score"],
            slug,
        ),
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


def _download_zip(url: str) -> tuple[bytes, str]:
    print(f"Downloading {url} ...")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read(), url
    except Exception as exc:
        if url != DEFAULT_URL:
            raise
        print(
            f"Default download failed: {exc}. Trying fallback {FALLBACK_URL} ...",
            file=sys.stderr,
        )
    with urllib.request.urlopen(FALLBACK_URL, timeout=120) as response:
        return response.read(), FALLBACK_URL


def _source_label(url: str, source_zip: str | None) -> str:
    if source_zip:
        return f"local:{source_zip}"
    if url == DEFAULT_URL:
        return DEFAULT_SOURCE_LABEL
    if url == FALLBACK_URL:
        return FALLBACK_SOURCE_LABEL
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--source-zip", help="Local dataset zip (skips download).")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    try:
        if args.source_zip:
            zip_bytes = Path(args.source_zip).read_bytes()
            source_url = args.url
        else:
            zip_bytes, source_url = _download_zip(args.url)
    except Exception as exc:
        print(f"Failed to read dataset zip: {exc}", file=sys.stderr)
        return 1

    per_company = parse_dataset_zip(zip_bytes)
    if len(per_company) < MIN_EXPECTED_SLUGS:
        print(
            f"Only {len(per_company)} slugs parsed (expected >= {MIN_EXPECTED_SLUGS}). "
            "Dataset layout likely changed - refusing to write.",
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
        "source": _source_label(source_url, args.source_zip),
        "retrieved_at": date.today().isoformat(),
        "problems": {slug: aggregated[slug] for slug in sorted(aggregated)},
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
    print(
        f"Wrote {out_path} \u2014 {len(aggregated)} problems, "
        f"{matched}/{len(slugs_in_curriculum)} curriculum problems matched."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
