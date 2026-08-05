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
  const summary = fail.length ? `FAIL (${fail.length})` : `PASS (${results.length})`;

  // Headless (make test): print and set a non-zero exit code so a red suite
  // actually breaks the build. Browser (tests.html): paint the page and put the
  // verdict in the title, which is what the Playwright walk reads.
  if (typeof document === "undefined") {
    for (const r of results) {
      if (!r.ok) console.log(`✗ ${r.name} — ${r.error}`);
    }
    console.log(`${summary} — ${results.length} tests`);
    if (fail.length) process.exitCode = 1;
    return;
  }

  document.title = summary;
  document.body.innerHTML = results
    .map((r) => `<p style="color:${r.ok ? "green" : "red"}">${r.ok ? "✓" : "✗"} ${r.name} ${r.error || ""}</p>`)
    .join("");
}
