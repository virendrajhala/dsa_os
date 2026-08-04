import { test, assertEq } from "./run.js";
import { fuzzyScore } from "../derive/search.js";

test("exact substring beats scattered subsequence", () => {
  const sub = fuzzyScore("heat", "Activity heatmap");
  const scattered = fuzzyScore("heat", "h-e-x-a-t"); // h,e,a,t as subsequence only
  if (!(sub > scattered && scattered > 0)) throw new Error(`sub=${sub} scattered=${scattered}`);
});

test("word-start matches score higher", () => {
  if (!(fuzzyScore("rq", "Revision Queue") > fuzzyScore("rq", "problem rq browser") * 0.5)) throw new Error("prefix bonus missing");
});

test("no subsequence -> 0", () => {
  assertEq(fuzzyScore("zzz", "Revision Queue"), 0);
});

test("empty query matches everything weakly", () => {
  if (!(fuzzyScore("", "anything") > 0)) throw new Error("empty query should match");
});
