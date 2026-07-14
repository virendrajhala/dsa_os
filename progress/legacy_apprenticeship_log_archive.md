# Legacy Apprenticeship Log Archive

Preserved verbatim from the pre-migration `progress/progress.json` (schema_version 3). The structured fields (thinking_process, implementation_review, mentor_review) don't map onto the completion-record schema the scripts require, so rather than lose this narrative detail during the schema migration, it's archived here in full. The condensed, schema-valid version of these same 4 sessions now lives in `progress/progress.json` under `completed`.

## OBS-001

- **Status:** passed
- **Hint level:** 2
- **Summary:** Derived Kadane's algorithm from first principles. Correct Java implementation without algorithm reveal.

---

## OBS-002

- **Status:** passed
- **Hint level:** 2
- **Summary:** Derived Maximum Product Subarray from first principles.

### Thinking Process
**Breakthrough:** Need to preserve both running maximum and running minimum because a future negative can swap their roles.

### Implementation Review
**Mistakes:**
- Initially focused on implementation before identifying the minimal state.

### Mentor Review
**Weaknesses:**
- Started with exhaustive sign-case analysis instead of searching for a higher-level abstraction.
**Lessons:**
- Identify the minimum state that must survive.
- Think using state transitions instead of enumerating cases.
- Preserve previous state before updating dependent variables.

---

## OBS-003

- **Status:** passed
- **Hint level:** 2
- **Summary:** Derived Best Time to Buy and Sell Stock from first principles.

### Thinking Process
**First observation:** Maximum profit at an index can only be obtained by subtracting the minimum value before that index from the current value.
**Breakthrough:** Only the minimum historical value influences every future decision.
**Mental model:** Future transitions depend only on the minimum state that must survive.
**Transfer rule:** Whenever scanning sequential data, determine the minimum historical information required for future transitions and preserve only that state.
**Personal note:** Identify the minimum state that future transitions depend on and preserve only that state.

### Implementation Review
**Initial solution issue:** Introduced an unnecessary runningMaxProfit variable.
**Final solution:** Removed redundant state and retained only minPrice and maxProfit.
**Clean code notes:**
- Each variable should represent exactly one responsibility.
- Remove redundant state after correctness is established.

### Mentor Review
**Strengths:**
- Derived the required state before implementation.
- Challenged mentor assumptions when terminology became inconsistent.
- Refactored independently after identifying redundant state.
**Weaknesses:**
- Initially carried redundant state.
- Allowed variable responsibility to drift before refactoring.
**Lessons:**
- Identify what information from the past can still influence future decisions.
- Store only the minimum state required.
- Separate current state from accumulated optimal state.
- Review working solutions to eliminate unnecessary state.
**Future watch items:**
- Continue searching for minimal state before coding.
- Maintain strict single responsibility for every variable.

---

## OBS-004

- **Status:** passed
- **Hint level:** 2
- **Summary:** Derived Best Time to Buy and Sell Stock II from first principles.

### Thinking Process
**First observation:** Every profitable local price increase can be treated as an independent transaction and accumulated.
**Breakthrough:** Local profitable transitions replace the need for maintaining a historical minimum price.
**Mental model:** When multiple independent transactions are allowed, evaluate each local transition instead of optimizing for one global transaction.
**Transfer rule:** Before reusing a previous solution, verify whether changed constraints require a different state representation.
**Personal note:** For multiple transactions, focus on profitable local transaction opportunities instead of maintaining a single historical minimum price.

### Implementation Review
**Initial solution issue:** Initially attempted to reuse the single-transaction approach before recognizing the changed constraint.
**Final solution:** Accumulated profit from every positive adjacent price difference in a single traversal.
**Clean code notes:**
- Align maintained state with the transaction constraints.
- Accumulate only guaranteed profitable local gains.

### Mentor Review
**Strengths:**
- Adapted reasoning after identifying the changed problem constraint.
- Derived the solution through examples instead of memorizing a pattern.
- Implemented the derived logic cleanly in one pass.
**Weaknesses:**
- Initially exhibited solution bias by applying the previous problem's state model.
- Needed to validate that changed constraints require re-evaluating preserved state.
**Lessons:**
- Constraint changes should trigger a re-evaluation of the required state.
- Multiple independent transactions may eliminate the need for historical optimization state.
- Accumulate independent local gains when they are provably optimal.
**Future watch items:**
- Check whether previous problem assumptions still hold before coding.
- Derive the required state from the current constraints rather than the previous solution.

---
