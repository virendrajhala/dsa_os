import { WORKSPACE_META } from "../legacy/app.js";

const listeners = [];
let current = { workspace: "today", sub: "", params: {} };
let writing = false;

export function parseRoute(hash) {
  const fallback = { workspace: "today", sub: "", params: {} };
  if (!hash || !hash.startsWith("#/")) return fallback;
  const [path, query = ""] = hash.slice(2).split("?");
  const [workspace, sub = ""] = path.split("/");
  if (!WORKSPACE_META[workspace]) return fallback;
  const params = {};
  for (const [k, v] of new URLSearchParams(query)) if (v) params[k] = v;
  return { workspace, sub, params };
}

export function formatRoute({ workspace, sub = "", params = {} }) {
  let out = `#/${workspace}`;
  if (sub) out += `/${sub}`;
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  if (qs) out += `?${qs}`;
  return out;
}

export function currentRoute() {
  return { ...current, params: { ...current.params } };
}

export function onRoute(fn) {
  listeners.push(fn);
}

function apply(route) {
  current = route;
  for (const fn of listeners) fn(currentRoute());
}

export function navigate(partial, { replace = false } = {}) {
  const next = {
    workspace: partial.workspace ?? current.workspace,
    // A workspace change resets sub + params unless the caller provides them.
    sub: partial.sub ?? (partial.workspace && partial.workspace !== current.workspace ? "" : current.sub),
    params: partial.params ?? (partial.workspace && partial.workspace !== current.workspace ? {} : current.params),
  };
  const hash = formatRoute(next);
  writing = true;
  if (replace) history.replaceState(null, "", hash);
  else if (hash !== location.hash) location.hash = hash;
  writing = false;
  apply(next);
}

export function startRouter() {
  // `location.hash = …` fires hashchange asynchronously, so the synchronous
  // `writing` flag alone cannot suppress our own writes: compare the state we
  // already applied against the URL and skip when they agree.
  window.addEventListener("hashchange", () => {
    if (writing) return;
    if (formatRoute(currentRoute()) === location.hash) return;
    apply(parseRoute(location.hash));
  });
  apply(parseRoute(location.hash));
}
