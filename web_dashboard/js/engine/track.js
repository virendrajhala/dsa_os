// Curriculum track: which body of problems the whole dashboard is looking at.
//
// The main 582-problem curriculum lives in the classic repo layout; every other
// track lives under tracks/<name>/. Track is orthogonal to workspace (which is
// what the hash router owns), so it is stored in localStorage rather than the
// URL — a track is a mode you stay in, not a place you navigate to.
//
// Flipping reloads the page. state.datasets and its five lookup Maps are built
// exactly once in loadData(); rebuilding them live would mean re-deriving every
// cached view. A reload on a localhost tool is the honest, low-risk answer.
//
// No module-level DOM or storage access: legacy/app.js imports transitively
// into the headless test suite and must stay import-side-effect-free.

const STORAGE_KEY = "track";
export const DEFAULT_TRACK = "main";

export const TRACKS = {
  main: { label: "582 Curriculum", short: "582", dir: null },
  blind75: { label: "Blind 75", short: "B75", dir: "tracks/blind75" },
};

// Tracks share NO files. The main track keeps its classic homes; every other
// track keeps all of them side by side under its own directory. Adding a key
// here means adding it to BOTH maps, or the other track 404s.
const MAIN_PATHS = {
  progress: "../progress/progress.json",
  scoring: "../progress/scoring.json",
  curriculum: "../curriculum/curriculum.json",
  stages: "../curriculum/stages.json",
  skills: "../knowledge/skills.json",
  patterns: "../knowledge/patterns.json",
  dependencyGraph: "../curriculum/dependency_graph.json",
  mistakes: "../mistake_catalog.json",
  frequency: "../curriculum/interview_frequency.json",
};

const TRACK_FILENAMES = {
  progress: "progress.json",
  scoring: "scoring.json",
  curriculum: "curriculum.json",
  stages: "stages.json",
  skills: "skills.json",
  patterns: "patterns.json",
  dependencyGraph: "dependency_graph.json",
  mistakes: "mistake_catalog.json",
  frequency: "interview_frequency.json",
};

export function isTrack(name) {
  return Object.prototype.hasOwnProperty.call(TRACKS, name);
}

export function activeTrack() {
  let stored = null;
  try {
    stored = window.localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    return DEFAULT_TRACK; // private mode / storage disabled
  }
  return isTrack(stored) ? stored : DEFAULT_TRACK;
}

export function trackMeta(name = activeTrack()) {
  return TRACKS[isTrack(name) ? name : DEFAULT_TRACK];
}

export function otherTrack(name = activeTrack()) {
  const names = Object.keys(TRACKS);
  const index = names.indexOf(isTrack(name) ? name : DEFAULT_TRACK);
  return names[(index + 1) % names.length];
}

// Resolve one of TRACK_FILENAMES' keys to a URL for the given track. Paths are
// relative to web_dashboard/, which is how the static server serves the repo.
export function trackFile(key, name = activeTrack()) {
  if (!Object.prototype.hasOwnProperty.call(TRACK_FILENAMES, key)) {
    throw new Error(`Unknown track file: ${key}`);
  }
  const meta = trackMeta(name);
  if (!meta.dir) return MAIN_PATHS[key];
  return `../${meta.dir}/${TRACK_FILENAMES[key]}`;
}

export function feedUrl(name = activeTrack()) {
  return `/api/feed?track=${encodeURIComponent(name)}`;
}

export function setTrack(name) {
  if (!isTrack(name)) return;
  storeTrack(name);
  window.location.reload();
}

// Drop back to the default track WITHOUT reloading. Used when the stored
// track's files cannot be read: reloading would just fail the same way, and the
// failure page has no track switch on it to escape with.
export function resetTrack() {
  storeTrack(DEFAULT_TRACK);
}

function storeTrack(name) {
  try {
    window.localStorage.setItem(STORAGE_KEY, name);
  } catch (error) {
    /* storage disabled: the choice just won't persist */
  }
}
