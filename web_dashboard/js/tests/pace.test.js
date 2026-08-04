import { test, assertEq } from "./run.js";
import { paceProjection, fastestByDifficulty, nearComplete } from "../derive/pace.js";

test("paceProjection projects finish from velocity", () => {
  // 14 days elapsed, 10 solved → 5/week; 30 remaining → 6 weeks → finish +42d
  const p = paceProjection({ solved: 10, target: 40, startIso: "2026-07-21", endIso: "2026-10-25", todayIso: "2026-08-04" });
  assertEq(p.velocityPerWeek, 5);
  assertEq(p.finishIso, "2026-09-15");
  assertEq(p.onTrack, true);
});

test("what-if overrides velocity", () => {
  const p = paceProjection({ solved: 10, target: 40, startIso: "2026-07-21", endIso: "2026-08-10", todayIso: "2026-08-04", whatIfPerWeek: 2 });
  assertEq(p.onTrack, false);
});

test("zero velocity yields null finish", () => {
  assertEq(paceProjection({ solved: 0, target: 10, startIso: "2026-08-01", endIso: "2026-10-01", todayIso: "2026-08-04" }).finishIso, null);
});

test("fastestByDifficulty picks min minutes per difficulty", () => {
  assertEq(
    fastestByDifficulty([
      { difficulty: "Easy", minutes: 30, problemId: "A" },
      { difficulty: "Easy", minutes: 20, problemId: "B" },
      { difficulty: "Hard", minutes: 90, problemId: "C" },
    ]),
    { Easy: { difficulty: "Easy", minutes: 20, problemId: "B" }, Hard: { difficulty: "Hard", minutes: 90, problemId: "C" } }
  );
});

test("nearComplete ranks by fewest remaining, >=60% done, excludes complete", () => {
  const groups = [
    { id: "a", name: "A", done: 9, total: 10 },
    { id: "b", name: "B", done: 6, total: 10 },
    { id: "c", name: "C", done: 10, total: 10 },
    { id: "d", name: "D", done: 1, total: 10 },
  ];
  assertEq(nearComplete(groups).map((g) => g.id), ["a", "b"]);
});
