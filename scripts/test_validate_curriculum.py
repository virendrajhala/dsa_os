#!/usr/bin/env python3
"""Regression tests for the optional `mentor_scores` block in
scripts/validate_curriculum.py (F7: mentor-graded scoring pass).

Run: python3 scripts/test_validate_curriculum.py

These tests never touch the live progress/progress.json. They copy it to a
temp file, mutate one completion record, and pass --progress-file explicitly
so the real file is never opened for writing.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _shared
from _shared import load_json_file
from validate_curriculum import validate_curriculum

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "validate_curriculum.py"
LIVE_PROGRESS = ROOT / "progress" / "progress.json"

WELL_FORMED_MENTOR_SCORES = {
    "thinking_score": {
        "understanding": 3,
        "examples": 3,
        "brute_force": 3,
        "pattern_detection": 3,
        "algorithm_design": 3,
        "complexity_analysis": 3,
        "implementation": 3,
        "communication": 3,
    },
    "interview_score": {
        "understanding": 7,
        "communication": 7,
        "algorithm": 7,
        "coding": 7,
        "complexity": 7,
    },
}


class MentorScoresValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="dsa_os_test_")
        self.tmp_progress = Path(self.tmpdir) / "progress.json"
        self.payload = json.loads(LIVE_PROGRESS.read_text())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self) -> subprocess.CompletedProcess:
        self.tmp_progress.write_text(json.dumps(self.payload, indent=2))
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--progress-file",
                str(self.tmp_progress),
                "--skip-template-progress",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )

    def test_record_without_mentor_scores_passes(self) -> None:
        # Live fixture records carry no `mentor_scores` at all: the field is
        # optional, so absence must validate cleanly.
        record = self.payload["completed"][0]
        self.assertNotIn("mentor_scores", record)

        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_well_formed_mentor_scores_passes(self) -> None:
        record = self.payload["completed"][0]
        record["mentor_scores"] = json.loads(json.dumps(WELL_FORMED_MENTOR_SCORES))

        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_mentor_scores_with_bad_dimension_name_fails(self) -> None:
        record = self.payload["completed"][0]
        mentor_scores = json.loads(json.dumps(WELL_FORMED_MENTOR_SCORES))
        # Typo a dimension name instead of a real one from scoring.json.
        mentor_scores["thinking_score"]["undestanding"] = mentor_scores["thinking_score"].pop("understanding")
        record["mentor_scores"] = mentor_scores

        result = self._run()
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("mentor_scores", result.stdout + result.stderr)

    def test_mentor_scores_with_out_of_range_value_fails(self) -> None:
        record = self.payload["completed"][0]
        mentor_scores = json.loads(json.dumps(WELL_FORMED_MENTOR_SCORES))
        # Thinking scale is 0..4 (see progress/scoring.json); 99 is out of range.
        mentor_scores["thinking_score"]["understanding"] = 99
        record["mentor_scores"] = mentor_scores

        result = self._run()
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("mentor thinking score", result.stdout + result.stderr)


class ReadinessScoringValidationTests(unittest.TestCase):
    """F23: `scoring.json` `readiness` block validation (mirrors hint_mastery_discount)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.curriculum = load_json_file(_shared.CURRICULUM_PATH)
        cls.graph = load_json_file(_shared.GRAPH_PATH)
        cls.stages = load_json_file(_shared.STAGES_PATH)
        cls.skills = load_json_file(_shared.SKILLS_PATH)
        cls.scoring = load_json_file(_shared.SCORING_PATH)

    def _errors(self, scoring: dict) -> list[str]:
        errors, _warnings = validate_curriculum(self.curriculum, self.graph, self.stages, self.skills, scoring)
        return errors

    def test_live_scoring_readiness_block_passes(self) -> None:
        errors = self._errors(self.scoring)
        self.assertFalse(
            [e for e in errors if "readiness" in e],
            msg="\n".join(errors),
        )

    def test_missing_readiness_block_fails(self) -> None:
        scoring = copy.deepcopy(self.scoring)
        del scoring["readiness"]
        errors = self._errors(scoring)
        self.assertTrue(any("`readiness` must be a non-empty object" in e for e in errors), msg=errors)

    def test_core_skill_fraction_out_of_range_fails(self) -> None:
        scoring = copy.deepcopy(self.scoring)
        scoring["readiness"]["core_skill_fraction"] = 1.5
        errors = self._errors(scoring)
        self.assertTrue(any("readiness.core_skill_fraction" in e for e in errors), msg=errors)

    def test_stage_scope_count_beyond_stage_order_length_fails(self) -> None:
        scoring = copy.deepcopy(self.scoring)
        scoring["readiness"]["stage_scope_count"] = len(self.stages["stage_order"]) + 1
        errors = self._errors(scoring)
        self.assertTrue(any("readiness.stage_scope_count" in e for e in errors), msg=errors)

    def test_zero_recent_mock_count_fails(self) -> None:
        scoring = copy.deepcopy(self.scoring)
        scoring["readiness"]["recent_mock_count"] = 0
        errors = self._errors(scoring)
        self.assertTrue(any("readiness.recent_mock_count" in e for e in errors), msg=errors)

    def test_invalid_min_mock_verdict_fails(self) -> None:
        scoring = copy.deepcopy(self.scoring)
        scoring["readiness"]["min_mock_verdicts"] = ["hire", "definitely-hire"]
        errors = self._errors(scoring)
        self.assertTrue(any("readiness.min_mock_verdicts" in e for e in errors), msg=errors)


class RevisitOfValidationTests(unittest.TestCase):
    """F15: `revisit_of` markers + exact-title duplicate gating."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.curriculum = load_json_file(_shared.CURRICULUM_PATH)
        cls.graph = load_json_file(_shared.GRAPH_PATH)
        cls.stages = load_json_file(_shared.STAGES_PATH)
        cls.skills = load_json_file(_shared.SKILLS_PATH)
        cls.scoring = load_json_file(_shared.SCORING_PATH)

    def _errors(self, curriculum: dict) -> list[str]:
        errors, _warnings = validate_curriculum(
            curriculum, self.graph, self.stages, self.skills, self.scoring
        )
        return errors

    def _by_id(self, curriculum: dict) -> dict:
        return {p["id"]: p for p in curriculum["problems"]}

    def test_live_curriculum_revisit_markers_pass(self) -> None:
        errors = self._errors(self.curriculum)
        self.assertFalse(
            [e for e in errors if "revisit_of" in e or "duplicate title" in e],
            msg="\n".join(errors),
        )

    def test_revisit_of_unknown_target_fails(self) -> None:
        curriculum = copy.deepcopy(self.curriculum)
        self._by_id(curriculum)["OBS-025"]["revisit_of"] = "ZZZ-999"
        errors = self._errors(curriculum)
        self.assertTrue(any("references unknown problem `ZZZ-999`" in e for e in errors), msg=errors)

    def test_revisit_of_forward_reference_fails(self) -> None:
        curriculum = copy.deepcopy(self.curriculum)
        # Point an early problem at a much later slot: must be rejected.
        self._by_id(curriculum)["OBS-021"]["revisit_of"] = "DES-036"
        errors = self._errors(curriculum)
        self.assertTrue(any("must appear earlier" in e for e in errors), msg=errors)

    def test_exact_title_dup_without_revisit_of_fails(self) -> None:
        curriculum = copy.deepcopy(self.curriculum)
        # DP-025 is the later "Decode Ways" slot; stripping its marker must error.
        self._by_id(curriculum)["DP-025"].pop("revisit_of", None)
        errors = self._errors(curriculum)
        self.assertTrue(
            any("duplicate title `Decode Ways`" in e for e in errors), msg=errors
        )


class F18DependencyDagTests(unittest.TestCase):
    """F18: real skill DAG, difficulty_gates, meta skill, Easy-depth guard."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.curriculum = load_json_file(_shared.CURRICULUM_PATH)
        cls.graph = load_json_file(_shared.GRAPH_PATH)
        cls.stages = load_json_file(_shared.STAGES_PATH)
        cls.skills = load_json_file(_shared.SKILLS_PATH)
        cls.scoring = load_json_file(_shared.SCORING_PATH)

    def _errors(self, graph=None, skills=None, curriculum=None) -> list[str]:
        errors, _ = validate_curriculum(
            curriculum or self.curriculum,
            graph or self.graph,
            self.stages,
            skills or self.skills,
            self.scoring,
        )
        return errors

    def test_live_dag_passes(self) -> None:
        errors = self._errors()
        self.assertFalse(
            [e for e in errors if "prereq" in e.lower() or "later-stage" in e or "difficulty_gates" in e or "transitively" in e],
            msg="\n".join(errors),
        )

    def test_multi_prereq_allowed(self) -> None:
        # A skill with several prereqs must NOT error (old one-prereq rule is gone).
        multi = [s for s, d in self.graph["skill_dependencies"].items() if len(d) > 1]
        self.assertTrue(multi, "expected some skills to have >1 prereq")
        errors = self._errors()
        self.assertFalse(any("at most one" in e or "prerequisites; the frozen" in e for e in errors), msg=errors)

    def test_forward_stage_dependency_fails(self) -> None:
        graph = copy.deepcopy(self.graph)
        # SK-OB-01 (Observation) depending on SK-IN-01 (Integration) is a forward dep.
        graph["skill_dependencies"]["SK-OB-01"] = ["SK-IN-01"]
        errors = self._errors(graph=graph)
        self.assertTrue(any("later-stage" in e for e in errors), msg=errors)

    def test_difficulty_gates_wrong_fails(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["difficulty_gates"]["Medium"] = []
        errors = self._errors(graph=graph)
        self.assertTrue(any("difficulty_gates" in e for e in errors), msg=errors)

    def test_meta_skill_registered_in_integration(self) -> None:
        self.assertEqual(self.skills["skills"]["SK-IE-00"]["scope"], "meta")
        self.assertEqual(self.skills["skills"]["SK-IE-00"]["stage"], "Integration")
        self.assertIn("SK-IE-00", self.stages["stages"]["Integration"]["skills"])
        # meta skill has no owned problems yet must not raise problem errors
        errors = self._errors()
        self.assertFalse(any("SK-IE-00" in e for e in errors), msg=errors)

    def test_easy_problem_over_depth_limit_fails(self) -> None:
        graph = copy.deepcopy(self.graph)
        easy_id = next(p["id"] for p in self.curriculum["problems"] if p["difficulty"] == "Easy")
        others = [p["id"] for p in self.curriculum["problems"] if p["id"] != easy_id][:31]
        graph["problem_dependencies"][easy_id] = others
        errors = self._errors(graph=graph)
        self.assertTrue(any("transitively requires" in e for e in errors), msg=errors)


if __name__ == "__main__":
    unittest.main()
