import { test, assertEq } from "./run.js";
import { matureRecallStats, maturityBuckets, dueForecast } from "../derive/memory.js";

const completed = [
  { problem_id: "A", completed_at: "2026-07-01",
    revision: { status: "ACTIVE", stage: 2, next_due: "2026-08-05",
      history: [{ date: "2026-07-08", result: "PASS", stage: 1 }, { date: "2026-07-22", result: "PASS", stage: 2 }] } },
  { problem_id: "B", completed_at: "2026-07-02",
    revision: { status: "ACTIVE", stage: 1, next_due: "2026-08-02",
      history: [{ date: "2026-07-09", result: "FAIL", stage: 1 }] } },
  { problem_id: "C", completed_at: "2026-06-01", revision: { status: "MASTERED", stage: 4, history: [
      { date: "2026-06-08", result: "PASS", stage: 1 }, { date: "2026-06-22", result: "PASS", stage: 2 },
      { date: "2026-07-15", result: "FAIL", stage: 3 }, { date: "2026-07-16", result: "PASS", stage: 3 },
      { date: "2026-07-31", result: "PASS", stage: 4 } ] } },
];

test("mature recalls = history entries with stage >= 2", () => {
  // A: 1 mature (stage2 PASS). C: stage2 PASS, stage3 FAIL, stage3 PASS, stage4 PASS = 4. B: none.
  assertEq(matureRecallStats(completed), { pass: 4, total: 5, rate: 0.8 });
});

test("maturity buckets", () => {
  // total problems 10; completed 3 → new 7; B stage1 learning; A stage2 young; C mastered mature
  assertEq(maturityBuckets(10, completed), { new: 7, learning: 1, young: 1, mature: 1 });
});

test("dueForecast counts overdue + per-day dues + cumulative backlog", () => {
  const f = dueForecast(completed, "2026-08-04", 3);
  assertEq(f.overdueBefore, 1); // B due 08-02
  assertEq(f.bars[1], { offset: 1, due: 1, backlogIfIdle: 2 }); // A due 08-05
});

test("empty history yields null rate", () => {
  assertEq(matureRecallStats([]).rate, null);
});
