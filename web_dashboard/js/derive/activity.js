import { addDays, diffDays } from "./dates.js";

export function activeDaySet(completed) {
  const days = new Set();
  for (const rec of completed || []) {
    if (rec.completed_at) days.add(rec.completed_at);
    for (const h of rec.revision?.history || []) if (h.date) days.add(h.date);
  }
  return days;
}

export function streaks(daySet, todayIso) {
  const sorted = [...daySet].sort();
  let max = 0;
  let run = 0;
  let prev = null;
  for (const day of sorted) {
    run = prev !== null && diffDays(prev, day) === 1 ? run + 1 : 1;
    if (run > max) max = run;
    prev = day;
  }
  let current = 0;
  let cursor = daySet.has(todayIso) ? todayIso : addDays(todayIso, -1);
  while (daySet.has(cursor)) {
    current += 1;
    cursor = addDays(cursor, -1);
  }
  return { current, max };
}
