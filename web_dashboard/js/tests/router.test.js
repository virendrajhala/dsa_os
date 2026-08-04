import { test, assertEq } from "./run.js";
import { parseRoute, formatRoute } from "../engine/router.js";

test("parse full route", () => {
  assertEq(parseRoute("#/evidence/memory?q=two%20sum&status=mastered"),
    { workspace: "evidence", sub: "memory", params: { q: "two sum", status: "mastered" } });
});

test("parse bare workspace", () => {
  assertEq(parseRoute("#/plan"), { workspace: "plan", sub: "", params: {} });
});

test("garbage falls back to today", () => {
  assertEq(parseRoute("#overview"), { workspace: "today", sub: "", params: {} });
  assertEq(parseRoute(""), { workspace: "today", sub: "", params: {} });
  assertEq(parseRoute("#/nope"), { workspace: "today", sub: "", params: {} });
});

test("format round-trips", () => {
  const route = { workspace: "problems", sub: "", params: { q: "kadane", sort: "frequency" } };
  assertEq(parseRoute(formatRoute(route)), route);
});

test("format omits empties", () => {
  assertEq(formatRoute({ workspace: "today", sub: "", params: {} }), "#/today");
});
