import { diffDays } from "./dates.js";

export function matureRecallStats(completed) {
  let pass = 0;
  let total = 0;
  for (const rec of completed || []) {
    for (const h of rec.revision?.history || []) {
      if ((h.stage ?? 0) < 2) continue;
      total += 1;
      if (h.result === "PASS") pass += 1;
    }
  }
  return { pass, total, rate: total ? pass / total : null };
}

export function maturityBuckets(totalProblems, completed) {
  const buckets = { new: 0, learning: 0, young: 0, mature: 0 };
  for (const rec of completed || []) {
    const r = rec.revision || {};
    if (r.status === "MASTERED") buckets.mature += 1;
    else if ((r.stage ?? 0) >= 2) buckets.young += 1;
    else buckets.learning += 1;
  }
  buckets.new = Math.max(0, totalProblems - (completed || []).length);
  return buckets;
}

export function dueForecast(completed, startIso, daysAhead = 30) {
  const perDay = new Map();
  let overdueBefore = 0;
  for (const rec of completed || []) {
    const r = rec.revision || {};
    if (!r.next_due || r.status === "MASTERED") continue;
    const offset = diffDays(startIso, r.next_due);
    if (offset < 0) overdueBefore += 1;
    else if (offset < daysAhead) perDay.set(offset, (perDay.get(offset) || 0) + 1);
  }
  const bars = [];
  let backlog = overdueBefore;
  for (let offset = 0; offset < daysAhead; offset += 1) {
    const due = perDay.get(offset) || 0;
    backlog += due;
    bars.push({ offset, due, backlogIfIdle: backlog });
  }
  return { overdueBefore, bars };
}
