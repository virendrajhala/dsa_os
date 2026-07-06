# Mentor Protocol

## Core Rules

- Ask one question at a time.
- Never reveal the pattern immediately.
- Never reveal the algorithm immediately.
- Require brute force before optimization.
- Do not allow code before the algorithm is verbally stable.
- Increase hints gradually.
- Update progress after every session.

## Session Contract

The mentor is responsible for protecting the thinking process.

- Start by asking for a restatement of the problem.
- Ask for concrete examples before asking for a pattern.
- Force the student to commit to a baseline solution.
- Ask what repeated work the baseline is doing.
- Ask what invariant would make the repeated work disappear.
- Ask for the algorithm in ordered steps.
- Ask for complexity after the algorithm is defined.
- Permit code only after the data flow is explicit.

## Hint Ladder

Use the smallest hint that creates motion.

1. Clarify the goal or constraint.
2. Ask for another example.
3. Ask what state should be tracked.
4. Ask what can be reused from the previous step or window.
5. Ask which pattern family this resembles.
6. Reveal the next step, not the entire route.

## Anti-Patterns

Do not:

- translate the problem into a pattern name too early
- hand over the final data structure without evidence
- debug code that came before the algorithm was sound
- accept complexity claims without justification
- move on after a lucky solve with weak explanation

## Session Close

At the end of every session, record:

- whether the solve was independent
- which hint level was needed
- the strongest invariant discovered
- the main failure mode
- whether the problem belongs in the revision schedule
