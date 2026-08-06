// The suite, in one place. Both entry points — tests.html (browser) and
// node.js (make test) — import this, so neither can drift from the other.
// Each module calls test() at its top level, so importing is running.
import "./activity.test.js";
import "./memory.test.js";
import "./pace.test.js";
import "./search.test.js";
import "./router.test.js";
import "./filters.test.js";
import "./track.test.js";
