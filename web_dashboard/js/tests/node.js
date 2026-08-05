// Headless entry point for `make test`. Mirrors tests.html — same suite, same
// reporter — but exits non-zero on failure so CI and make can see red.
// No DOM shim is needed: every tested module keeps its document/window access
// inside functions, so importing the graph is side-effect free.
import "./all.js";
import { report } from "./run.js";

report();
