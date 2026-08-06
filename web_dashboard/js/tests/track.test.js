import { test, assertEq } from "./run.js";
import {
  DEFAULT_TRACK,
  TRACKS,
  feedUrl,
  isTrack,
  otherTrack,
  trackFile,
  trackMeta,
} from "../engine/track.js";

test("known track names", () => {
  assertEq(isTrack("main"), true);
  assertEq(isTrack("blind75"), true);
  assertEq(isTrack("nope"), false);
  assertEq(isTrack(null), false);
});

test("main track keeps the classic file homes", () => {
  assertEq(trackFile("progress", "main"), "../progress/progress.json");
  assertEq(trackFile("curriculum", "main"), "../curriculum/curriculum.json");
  assertEq(trackFile("skills", "main"), "../knowledge/skills.json");
  assertEq(trackFile("patterns", "main"), "../knowledge/patterns.json");
  assertEq(trackFile("dependencyGraph", "main"), "../curriculum/dependency_graph.json");
  assertEq(trackFile("mistakes", "main"), "../mistake_catalog.json");
  assertEq(trackFile("frequency", "main"), "../curriculum/interview_frequency.json");
});

test("named track keeps every file under its own directory", () => {
  assertEq(trackFile("progress", "blind75"), "../tracks/blind75/progress.json");
  assertEq(trackFile("curriculum", "blind75"), "../tracks/blind75/curriculum.json");
  assertEq(trackFile("skills", "blind75"), "../tracks/blind75/skills.json");
  assertEq(trackFile("scoring", "blind75"), "../tracks/blind75/scoring.json");
  assertEq(trackFile("dependencyGraph", "blind75"), "../tracks/blind75/dependency_graph.json");
  assertEq(trackFile("mistakes", "blind75"), "../tracks/blind75/mistake_catalog.json");
  assertEq(trackFile("frequency", "blind75"), "../tracks/blind75/interview_frequency.json");
});

// The whole point of the separation: no key may resolve to the same URL on two
// tracks. A shared path is a data leak between curricula.
test("no file is shared between tracks", () => {
  const keys = ["progress", "scoring", "curriculum", "stages", "skills",
                "patterns", "dependencyGraph", "mistakes", "frequency"];
  for (const key of keys) {
    const main = trackFile(key, "main");
    const b75 = trackFile(key, "blind75");
    assertEq(main === b75, false);
  }
});

test("unknown track falls back to the default", () => {
  assertEq(trackFile("progress", "nope"), trackFile("progress", DEFAULT_TRACK));
  assertEq(trackMeta("nope"), TRACKS[DEFAULT_TRACK]);
});

test("unknown file key throws", () => {
  let threw = false;
  try {
    trackFile("nope", "main");
  } catch (error) {
    threw = true;
  }
  assertEq(threw, true);
});

test("otherTrack flips between the two tracks", () => {
  assertEq(otherTrack("main"), "blind75");
  assertEq(otherTrack("blind75"), "main");
  assertEq(otherTrack("nope"), "blind75");
});

test("feed url carries the track", () => {
  assertEq(feedUrl("main"), "/api/feed?track=main");
  assertEq(feedUrl("blind75"), "/api/feed?track=blind75");
});
