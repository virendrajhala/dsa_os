#!/usr/bin/env python3
"""Regression tests for the track layer (TrackPaths / load_repository_state(track=)).

Run: python3 scripts/test_track_paths.py
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import _shared
from _shared import (
    DEFAULT_TRACK,
    RepositoryError,
    RepositoryState,
    build_dashboard_feed,
    load_repository_state,
    state_paths,
    track_paths,
)


class TrackPathsResolution(unittest.TestCase):
    def test_main_track_matches_module_constants(self) -> None:
        paths = track_paths()
        self.assertEqual(paths.track, DEFAULT_TRACK)
        self.assertEqual(paths.curriculum, _shared.CURRICULUM_PATH)
        self.assertEqual(paths.graph, _shared.GRAPH_PATH)
        self.assertEqual(paths.stages, _shared.STAGES_PATH)
        self.assertEqual(paths.skills, _shared.SKILLS_PATH)
        self.assertEqual(paths.patterns, _shared.PATTERNS_PATH)
        self.assertEqual(paths.scoring, _shared.SCORING_PATH)
        self.assertEqual(paths.progress, _shared.PROGRESS_PATH)
        self.assertEqual(paths.progress_template, _shared.PROGRESS_TEMPLATE_PATH)
        self.assertEqual(paths.plan, _shared.PLAN_PATH)
        self.assertEqual(paths.solutions_dir, _shared.ROOT / "solutions")

    def test_named_track_resolves_under_tracks_dir(self) -> None:
        # Use a throwaway directory so the test never depends on which tracks
        # actually ship in the repo.
        base = _shared.TRACKS_DIR / "_test_track"
        base.mkdir(parents=True, exist_ok=True)
        try:
            paths = track_paths("_test_track")
            self.assertEqual(paths.curriculum, base / "curriculum.json")
            self.assertEqual(paths.solutions_dir, base / "solutions")
            self.assertEqual(paths.plan, base / "plan.json")
        finally:
            shutil.rmtree(base)

    def test_unknown_track_raises_with_available_list(self) -> None:
        with self.assertRaises(RepositoryError) as ctx:
            track_paths("no_such_track")
        self.assertIn("no_such_track", str(ctx.exception))
        self.assertIn(DEFAULT_TRACK, str(ctx.exception))

    def test_tracks_share_no_files(self) -> None:
        """The separation invariant: no field may resolve to the same path on
        two tracks. A shared path is a data leak between curricula."""

        base = _shared.TRACKS_DIR / "_test_track"
        base.mkdir(parents=True, exist_ok=True)
        try:
            main = track_paths(DEFAULT_TRACK)
            other = track_paths("_test_track")
            fields = [f for f in main.__dataclass_fields__ if f != "track"]
            self.assertTrue(fields)
            for field in fields:
                self.assertNotEqual(
                    getattr(main, field),
                    getattr(other, field),
                    f"{field} is shared between tracks",
                )
            # And every non-main path must live inside that track's directory.
            for field in fields:
                self.assertIn(base, getattr(other, field).parents, field)
        finally:
            shutil.rmtree(base)

    def test_learner_files_are_track_owned(self) -> None:
        main = track_paths(DEFAULT_TRACK)
        self.assertEqual(main.mistake_catalog, _shared.ROOT / "mistake_catalog.json")
        self.assertEqual(main.mentor_memory, _shared.ROOT / "mentor_memory.md")
        self.assertEqual(main.thinking_patterns, _shared.ROOT / "thinking_patterns.md")
        self.assertEqual(main.interview_playbook, _shared.ROOT / "interview_playbook.md")
        self.assertEqual(
            main.interview_frequency,
            _shared.ROOT / "curriculum" / "interview_frequency.json",
        )

    def test_state_paths_defaults_to_main_for_hand_built_state(self) -> None:
        state = RepositoryState(
            curriculum={},
            graph={},
            stages={},
            skills={},
            patterns={},
            scoring={},
            progress={},
            progress_path=Path("unused.json"),
        )
        self.assertEqual(state_paths(state).track, DEFAULT_TRACK)


class LoadRepositoryStateTrack(unittest.TestCase):
    def test_default_load_carries_main_paths(self) -> None:
        state = load_repository_state()
        self.assertIsNotNone(state.paths)
        self.assertEqual(state.paths.track, DEFAULT_TRACK)

    def test_unknown_track_raises(self) -> None:
        with self.assertRaises(RepositoryError):
            load_repository_state(track="no_such_track")

    def test_feed_reports_track_and_repo_relative_solutions(self) -> None:
        state = load_repository_state()
        feed = build_dashboard_feed(state, date(2026, 8, 6))
        self.assertEqual(feed["track"], DEFAULT_TRACK)
        for entry in feed["solution_files"]:
            self.assertTrue(entry["path"].startswith("solutions/"))
        gate = feed["next_action"].get("code_gate")
        if gate is not None:
            self.assertTrue(gate["solution_expected"].startswith("solutions/"))


if __name__ == "__main__":
    unittest.main()
