#!/usr/bin/env python3
"""Regression tests for scripts/generate_blind75_track.py and the shipped track.

Run: python3 scripts/test_generate_blind75_track.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import _shared
import generate_blind75_track as gen
from _shared import (
    build_dashboard_feed,
    load_json_file,
    load_repository_state,
    select_next_problem,
)

TRACK_DIR = _shared.ROOT / "tracks" / gen.TRACK


class GeneratorOutput(unittest.TestCase):
    """Generate into a temp dir and check the shape of what comes out."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        out = Path(cls._tmp.name) / "blind75"
        result = subprocess.run(
            [
                sys.executable,
                str(_shared.ROOT / "scripts" / "generate_blind75_track.py"),
                "--out-dir",
                str(out),
                "--skip-validate",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        cls.out = out
        cls.curriculum = load_json_file(out / "curriculum.json")
        cls.skills = load_json_file(out / "skills.json")
        cls.stages = load_json_file(out / "stages.json")
        cls.graph = load_json_file(out / "dependency_graph.json")
        cls.patterns = load_json_file(out / "patterns.json")
        cls.scoring = load_json_file(out / "scoring.json")
        cls.plan = load_json_file(out / "plan.json")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_seventy_five_problems_with_minted_ids(self) -> None:
        problems = self.curriculum["problems"]
        self.assertEqual(len(problems), 75)
        self.assertEqual(
            [p["id"] for p in problems], [f"B75-{i:03d}" for i in range(1, 76)]
        )
        self.assertTrue(self.curriculum["source"]["track_derived"])
        self.assertEqual(self.curriculum["source"]["total_problem_count"], 75)

    def test_every_blind75_lc_id_present_exactly_once(self) -> None:
        lc_ids = [p["lc_id"] for p in self.curriculum["problems"]]
        self.assertEqual(len(lc_ids), len(set(lc_ids)))
        self.assertEqual(set(lc_ids), set(gen.category_by_lc_id()))

    def test_ids_are_independent_of_the_main_track(self) -> None:
        main_ids = {p["id"] for p in load_json_file(_shared.CURRICULUM_PATH)["problems"]}
        track_ids = {p["id"] for p in self.curriculum["problems"]}
        self.assertEqual(track_ids & main_ids, set())
        # ...but each keeps a pointer back to the slot it was derived from.
        for problem in self.curriculum["problems"]:
            self.assertIn(problem["derived_from_id"], main_ids)

    def test_problems_are_stage_major(self) -> None:
        order = {name: i for i, name in enumerate(self.stages["stage_order"])}
        indexes = [order[p["stage"]] for p in self.curriculum["problems"]]
        self.assertEqual(indexes, sorted(indexes))

    def test_each_skill_has_exactly_one_primary(self) -> None:
        by_skill: dict[str, list[str]] = {}
        for problem in self.curriculum["problems"]:
            by_skill.setdefault(problem["primary_skill"], []).append(problem["problem_role"])
        for skill_id, roles in by_skill.items():
            self.assertEqual(roles.count("PRIMARY"), 1, skill_id)
            self.assertNotIn("CHALLENGE", roles, skill_id)

    def test_skills_cover_every_problem_and_keep_the_meta_skill(self) -> None:
        referenced = {p["primary_skill"] for p in self.curriculum["problems"]}
        kept = set(self.skills["skill_order"])
        self.assertTrue(referenced <= kept)
        self.assertIn(gen.META_SKILL_ID, kept)
        self.assertEqual(kept - referenced, {gen.META_SKILL_ID})

    def test_stages_drop_the_empty_ones_but_keep_the_meta_host(self) -> None:
        stage_order = self.stages["stage_order"]
        self.assertNotIn("Decision Making", stage_order)
        self.assertIn("Integration", stage_order)  # hosts SK-IE-00
        for stage_name in stage_order:
            self.assertTrue(self.stages["stages"][stage_name]["skills"])

    def test_graph_is_reidentified_and_matches_skill_order(self) -> None:
        self.assertEqual(self.graph["skill_order"], self.skills["skill_order"])
        track_ids = {p["id"] for p in self.curriculum["problems"]}
        self.assertEqual(set(self.graph["problem_dependencies"]), track_ids)
        for deps in self.graph["problem_dependencies"].values():
            for dep in deps:
                self.assertIn(dep, track_ids)

    def test_patterns_only_reference_track_contents(self) -> None:
        track_ids = {p["id"] for p in self.curriculum["problems"]}
        kept_skills = set(self.skills["skill_order"])
        survivors = set(self.patterns["pattern_order"])
        for pattern_id in survivors:
            pattern = self.patterns["patterns"][pattern_id]
            self.assertTrue(pattern["appears_in"])
            self.assertTrue(set(pattern["appears_in"]) <= track_ids)
            self.assertTrue(set(pattern["skills"]) <= kept_skills)
            self.assertTrue(set(pattern["related_patterns"]) <= survivors)
            self.assertTrue(set(pattern["contrast_with"]) <= survivors)

    def test_scoring_recalibrates_only_the_volume_coupled_blocks(self) -> None:
        main_scoring = load_json_file(_shared.SCORING_PATH)
        # The revision policy MUST stay identical: interval scheduling still
        # runs off module-level config read from the main scoring.json.
        self.assertEqual(self.scoring["revision_policy"], main_scoring["revision_policy"])
        self.assertEqual(self.scoring["weights"], main_scoring["weights"])
        self.assertEqual(
            set(self.scoring["promotion_thresholds"]), set(self.stages["stage_order"])
        )
        cumulative = [
            self.scoring["promotion_thresholds"][name]["minimum_completed_problems"]
            for name in self.stages["stage_order"]
        ]
        self.assertEqual(cumulative, sorted(cumulative))
        self.assertEqual(cumulative[-1], 75)
        self.assertLessEqual(
            self.scoring["readiness"]["stage_scope_count"], len(self.stages["stage_order"])
        )

    def test_plan_covers_every_problem(self) -> None:
        self.assertEqual(self.plan["quarter"]["target_new_solves"], 75)
        self.assertEqual(sum(w["target_solves"] for w in self.plan["weeks"]), 75)
        self.assertFalse(any(w["deload"] for w in self.plan["weeks"]))

    def test_generated_track_validates(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(_shared.ROOT / "scripts" / "validate_curriculum.py"),
                "--track",
                gen.TRACK,
            ],
            capture_output=True,
            text=True,
            cwd=_shared.ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class RegenerationSafety(unittest.TestCase):
    """Re-running the generator must never destroy recorded learner history."""

    def _generate(self, out: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(_shared.ROOT / "scripts" / "generate_blind75_track.py"),
                "--out-dir",
                str(out),
                "--skip-validate",
            ],
            capture_output=True,
            text=True,
        )

    def test_progress_with_completions_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "blind75"
            self.assertEqual(self._generate(out).returncode, 0)

            progress_path = out / "progress.json"
            payload = json.loads(progress_path.read_text())
            payload["completed"] = [
                {"problem_id": "B75-001", "completed_at": "2026-08-06", "sentinel": True}
            ]
            progress_path.write_text(json.dumps(payload, indent=2))

            result = self._generate(out)
            self.assertEqual(result.returncode, 0)
            self.assertIn("KEPT existing progress.json", result.stdout)
            kept = json.loads(progress_path.read_text())
            self.assertEqual(kept["completed"][0]["problem_id"], "B75-001")

            # Everything else is derived and still regenerates.
            self.assertEqual(len(json.loads((out / "curriculum.json").read_text())["problems"]), 75)

    def test_learner_files_are_seeded_once_then_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "blind75"
            self.assertEqual(self._generate(out).returncode, 0)

            # Write into each learner-owned file, then regenerate.
            (out / "mentor_memory.md").write_text("# my notes\nSENTINEL\n")
            (out / "thinking_patterns.md").write_text("SENTINEL patterns\n")
            (out / "interview_playbook.md").write_text("SENTINEL playbook\n")
            catalog = json.loads((out / "mistake_catalog.json").read_text())
            catalog["entries"] = [{"id": "M001", "source_problem": "B75-001"}]
            (out / "mistake_catalog.json").write_text(json.dumps(catalog))

            result = self._generate(out)
            self.assertEqual(result.returncode, 0)
            self.assertIn("SENTINEL", (out / "mentor_memory.md").read_text())
            self.assertIn("SENTINEL", (out / "thinking_patterns.md").read_text())
            self.assertIn("SENTINEL", (out / "interview_playbook.md").read_text())
            kept = json.loads((out / "mistake_catalog.json").read_text())
            self.assertEqual(kept["entries"][0]["id"], "M001")

    def test_empty_progress_is_regenerated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "blind75"
            self.assertEqual(self._generate(out).returncode, 0)
            (out / "progress.json").write_text(json.dumps({"schema_version": 8, "completed": []}))
            result = self._generate(out)
            self.assertEqual(result.returncode, 0)
            # The seeded markdown/frequency files are always kept; progress is not.
            self.assertNotIn("KEPT existing progress.json", result.stdout)
            self.assertIn("current_stage", json.loads((out / "progress.json").read_text()))


@unittest.skipUnless(TRACK_DIR.is_dir(), "tracks/blind75 is not present")
class ShippedTrack(unittest.TestCase):
    """The committed track must load and schedule through the real engine."""

    def test_loads_and_schedules(self) -> None:
        state = load_repository_state(track=gen.TRACK)
        self.assertEqual(state.paths.track, gen.TRACK)
        self.assertEqual(len(state.curriculum["problems"]), 75)
        selection = select_next_problem(state, on_date=date(2026, 8, 6))
        self.assertIsNotNone(selection.problem)
        self.assertTrue(selection.problem["id"].startswith("B75-"))

    def test_feed_is_track_scoped(self) -> None:
        state = load_repository_state(track=gen.TRACK)
        feed = build_dashboard_feed(state, date(2026, 8, 6))
        self.assertEqual(feed["track"], gen.TRACK)
        self.assertIsNotNone(feed["plan"])
        self.assertNotIn("error", feed["plan"])
        gate = feed["next_action"].get("code_gate")
        if gate is not None:
            self.assertTrue(
                gate["solution_expected"].startswith(f"tracks/{gen.TRACK}/solutions/")
            )

    def test_progress_starts_empty(self) -> None:
        progress = load_json_file(TRACK_DIR / "progress.json")
        self.assertEqual(progress["completed"], [])
        self.assertIsNone(progress["current_problem"])
        self.assertEqual(progress["mastered_skills"], [])

    def test_track_owns_every_learner_file(self) -> None:
        """Tracks share nothing: the track directory must be self-contained."""

        for name in (
            "mistake_catalog.json",
            "mentor_memory.md",
            "thinking_patterns.md",
            "interview_playbook.md",
            "interview_frequency.json",
        ):
            self.assertTrue((TRACK_DIR / name).exists(), f"{name} missing from the track")

        paths = _shared.track_paths(gen.TRACK)
        self.assertEqual(paths.mistake_catalog, TRACK_DIR / "mistake_catalog.json")
        self.assertEqual(paths.mentor_memory, TRACK_DIR / "mentor_memory.md")
        self.assertEqual(paths.thinking_patterns, TRACK_DIR / "thinking_patterns.md")
        self.assertEqual(paths.interview_playbook, TRACK_DIR / "interview_playbook.md")
        self.assertEqual(paths.interview_frequency, TRACK_DIR / "interview_frequency.json")

    def test_track_mistake_catalog_is_independent(self) -> None:
        """The track's catalog is its own: it must not carry the main track's
        entries, which reference main-track problem ids."""

        track_catalog = load_json_file(TRACK_DIR / "mistake_catalog.json")
        main_catalog = load_json_file(_shared.ROOT / "mistake_catalog.json")
        self.assertEqual(track_catalog.get("track"), gen.TRACK)
        track_ids = {e.get("source_problem") for e in track_catalog.get("entries", [])}
        main_ids = {e.get("source_problem") for e in main_catalog.get("entries", [])}
        self.assertEqual(track_ids & main_ids, set())


if __name__ == "__main__":
    unittest.main()
