const results = [];

export function test(name, fn) {
  try {
    fn();
    results.push({ name, ok: true });
  } catch (error) {
    results.push({ name, ok: false, error: String(error) });
  }
}

export function assertEq(actual, expected, msg = "") {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Error(`${msg} expected ${e}, got ${a}`);
}

export function report() {
  const fail = results.filter((r) => !r.ok);
  document.title = fail.length ? `FAIL (${fail.length})` : `PASS (${results.length})`;
  document.body.innerHTML = results
    .map((r) => `<p style="color:${r.ok ? "green" : "red"}">${r.ok ? "✓" : "✗"} ${r.name} ${r.error || ""}</p>`)
    .join("");
}
