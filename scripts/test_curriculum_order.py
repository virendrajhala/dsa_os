#!/usr/bin/env python3
"""Curriculum ORDERING invariants (cognitive-load progression).

These pin the properties an interview-prep curriculum must have:
reachability, stage monotonicity, a gentle entry ramp, and canon ladders.
They read the repo's curriculum files; they never touch progress.json.
"""
from __future__ import annotations

import unittest

import _shared
from _shared import load_json_file

DW = {"Easy": 1, "Medium": 2, "Hard": 3}


def _load():
    curriculum = load_json_file(_shared.CURRICULUM_PATH)
    skills = load_json_file(_shared.SKILLS_PATH)
    stages = load_json_file(_shared.STAGES_PATH)
    graph = load_json_file(_shared.GRAPH_PATH)
    return curriculum, skills, stages, graph


def simulate_journey():
    """Reproduce select_next_problem's served order for a fresh learner:
    only dependency-complete problems are servable; prefer the current
    skill, then the current stage, then earliest curriculum order."""
    curriculum, skills, stages, graph = _load()
    problems = curriculum["problems"]
    by_id = {p["id"]: p for p in problems}
    file_index = {p["id"]: i for i, p in enumerate(problems)}
    stage_index = {s: i for i, s in enumerate(stages["stage_order"])}
    deps = graph["problem_dependencies"]
    role_gate = _shared.challenge_stage_gate(curriculum)

    completed: set[str] = set()
    served: list[str] = []
    skill = None
    stage = stages["stage_order"][0]
    ids = [p["id"] for p in problems]
    while len(served) < len(problems):
        ready = [
            i for i in ids
            if i not in completed
            and all(d in completed for d in (deps.get(i) or []))
            and role_gate(by_id[i], completed)
        ]
        if not ready:
            break
        def key(i):
            p = by_id[i]
            return (
                0 if p["primary_skill"] == skill else 1,
                0 if p["stage"] == stage else 1,
                stage_index[p["stage"]],
                file_index[i],
            )
        chosen = min(ready, key=key)
        served.append(chosen)
        completed.add(chosen)
        skill = by_id[chosen]["primary_skill"]
        stage = by_id[chosen]["stage"]
    return served, by_id, stage_index


class JourneyInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.served, cls.by_id, cls.stage_index = simulate_journey()
        cls.pos = {pid: n for n, pid in enumerate(cls.served, 1)}

    def test_every_problem_is_reachable(self):
        total = len(load_json_file(_shared.CURRICULUM_PATH)["problems"])
        self.assertEqual(len(self.served), total)

    def test_stages_are_contiguous_in_served_order(self):
        spans = {}
        for n, pid in enumerate(self.served, 1):
            spans.setdefault(self.by_id[pid]["stage"], []).append(n)
        for stage, positions in spans.items():
            expected = max(positions) - min(positions) + 1
            self.assertEqual(expected, len(positions), f"{stage} is interleaved")

    # Fails today (D3): a CHALLENGE unlocks after one reinforcement, so
    # CPX-003 and OBS-008 (both Hard) land in the first fifteen solves.
    # Marker removed by Task 2 (challenge stage-fundamentals gate).
    @unittest.expectedFailure
    def test_entry_ramp_has_no_hard_in_first_fifteen(self):
        early = [p for p in self.served[:15] if self.by_id[p]["difficulty"] == "Hard"]
        self.assertEqual(early, [], f"Hard problems too early: {early}")

    def test_no_forward_stage_dependencies(self):
        graph = load_json_file(_shared.GRAPH_PATH)
        bad = [
            (pid, dep)
            for pid, dep_list in graph["problem_dependencies"].items()
            for dep in (dep_list or [])
            if self.stage_index[self.by_id[dep]["stage"]]
            > self.stage_index[self.by_id[pid]["stage"]]
        ]
        self.assertEqual(bad, [])

    def _pos_of_lc(self, lc_id):
        hits = [p for p in self.by_id.values() if p.get("lc_id") == lc_id]
        self.assertTrue(hits, f"LC{lc_id} missing from curriculum")
        return min(self.pos[p["id"]] for p in hits)

    def test_backtracking_ladder_order(self):
        subsets = self._pos_of_lc(78)
        permutations = self._pos_of_lc(46)
        n_queens = self._pos_of_lc(51)
        self.assertLess(subsets, permutations)
        self.assertLess(permutations, n_queens)

    def test_graph_ladder_order(self):
        islands = self._pos_of_lc(200)
        course_schedule = self._pos_of_lc(207)
        dijkstra = self._pos_of_lc(743)
        self.assertLess(islands, course_schedule)
        self.assertLess(course_schedule, dijkstra)

    def test_dp_ladder_order(self):
        stairs = self._pos_of_lc(70)
        coin_change = self._pos_of_lc(322)
        burst_balloons = self._pos_of_lc(312)
        self.assertLess(stairs, coin_change)
        self.assertLess(coin_change, burst_balloons)

    def test_tree_ladder_builds_before_serialize(self):
        self.assertLess(self._pos_of_lc(105), self._pos_of_lc(297))

    # Fails today (D1): Pattern Discovery is stage 11 and the readiness
    # scope covers 9 stages, so backtracking sits outside the core.
    # Marker removed by Task 1 (stage reorder + wider scope).
    @unittest.expectedFailure
    def test_backtracking_is_inside_the_readiness_scope(self):
        stages = load_json_file(_shared.STAGES_PATH)
        scoring = load_json_file(_shared.SCORING_PATH)
        scope_count = scoring["readiness"]["stage_scope_count"]
        scope = set(stages["stage_order"][:scope_count])
        subsets = [p for p in self.by_id.values() if p.get("lc_id") == 78][0]
        self.assertIn(subsets["stage"], scope)


if __name__ == "__main__":
    unittest.main()
