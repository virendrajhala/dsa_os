export function fuzzyScore(query, text) {
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (!q) return 0.1;
  let score = 0;
  let ti = 0;
  let streak = 0;
  for (const ch of q) {
    const found = t.indexOf(ch, ti);
    if (found === -1) return 0;
    const wordStart = found === 0 || t[found - 1] === " " || t[found - 1] === "-";
    streak = found === ti ? streak + 1 : 1;
    score += 1 + streak * 2 + (wordStart ? 3 : 0);
    ti = found + 1;
  }
  return score / (1 + t.length / 50); // mild length normalization
}
