import { test, assertEq } from "./run.js";
import { mapStatus } from "../engine/filterbar.js";

test("browser consumer passes unified values through", () => {
  assertEq(mapStatus("solved", "browser"), "solved");
  assertEq(mapStatus("not_started", "browser"), "not_started");
});

test("catalog consumer maps solved->active", () => {
  assertEq(mapStatus("solved", "catalog"), "active");
  assertEq(mapStatus("failed", "catalog"), "failed");
  assertEq(mapStatus("mastered", "catalog"), "mastered");
  assertEq(mapStatus("", "catalog"), "");
});
