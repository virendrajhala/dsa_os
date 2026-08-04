import { addDays, diffDays } from "./dates.js";

export function paceProjection({ solved, target, startIso, endIso, todayIso, whatIfPerWeek = null }) {
  const elapsedDays = Math.max(1, diffDays(startIso, todayIso));
  const velocityPerWeek = (solved / elapsedDays) * 7;
  const rate = whatIfPerWeek ?? velocityPerWeek;
  const remaining = Math.max(0, target - solved);
  if (rate <= 0) return { velocityPerWeek, finishIso: null, onTrack: false };
  const finishIso = addDays(todayIso, Math.ceil((remaining / rate) * 7));
  return { velocityPerWeek, finishIso, onTrack: finishIso <= endIso };
}

export function fastestByDifficulty(entries) {
  const best = {};
  for (const entry of entries || []) {
    if (!entry.difficulty || !(entry.minutes > 0)) continue;
    if (!best[entry.difficulty] || entry.minutes < best[entry.difficulty].minutes) best[entry.difficulty] = entry;
  }
  return best;
}

export function nearComplete(groups, limit = 4) {
  return (groups || [])
    .filter((g) => g.total > 0 && g.done < g.total && g.done / g.total >= 0.6)
    .map((g) => ({ ...g, remaining: g.total - g.done }))
    .sort((a, b) => a.remaining - b.remaining || b.done / b.total - a.done / a.total)
    .slice(0, limit);
}
