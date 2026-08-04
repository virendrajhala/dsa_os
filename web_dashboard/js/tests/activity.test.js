import { test, assertEq } from "./run.js";
import { activeDaySet, streaks } from "../derive/activity.js";

const completed = [
  { completed_at: "2026-08-01", revision: { history: [{ date: "2026-08-03", result: "PASS", stage: 1 }] } },
  { completed_at: "2026-08-02", revision: {} },
];

test("activeDaySet unions solves and revisions", () => {
  assertEq([...activeDaySet(completed)].sort(), ["2026-08-01", "2026-08-02", "2026-08-03"]);
});

test("streak counts through today", () => {
  assertEq(streaks(new Set(["2026-08-01", "2026-08-02", "2026-08-03"]), "2026-08-03"), { current: 3, max: 3 });
});

test("streak survives if today not yet active (counts from yesterday)", () => {
  assertEq(streaks(new Set(["2026-08-01", "2026-08-02"]), "2026-08-03").current, 2);
});

test("no grace: gap breaks current streak, max remembers", () => {
  assertEq(streaks(new Set(["2026-07-28", "2026-07-29", "2026-08-02"]), "2026-08-02"), { current: 1, max: 2 });
});
