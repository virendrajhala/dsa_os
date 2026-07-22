# DSA OS — Skill Map (generated from `knowledge/skills.json`)

This file is generated, not hand-maintained. It replaces the old module/pattern-based skill map after the skill-first migration (curriculum.json v3.0). Regenerate it any time `knowledge/skills.json` or `curriculum/curriculum.json` changes.

**557 problems** across **91 skills** in **13 stages**. Difficulty: 94 Easy / 320 Medium / 143 Hard. Importance: 266 CORE / 250 COMMON / 41 SPECIALIZED / 0 NICHE.

## Observation

Learn to read the prompt exactly, simulate small examples, and state the invariant before reaching for a pattern name. Includes reasoning about what a brute force costs and why.

*6 skills, 21 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-OB-01` Asymptotic Estimation | Brute force O(n^2) vs hash-map O(n) — the canonical first lesson in reading constraints to infer required complexity. | CPX-001 | 1 problems | 1 problems |
| `SK-OB-02` Amortized Analysis | Every operation must be O(1) — introduces amortized/worst-case distinction via auxiliary state. | CPX-004 | 2 problems | 0 problems |
| `SK-OB-03` Running Extremum Scan | Running Extremum Scan — track a running best-so-far value (max, min, or both) in a single pass; when a new element makes the running value worse than starting fresh, reset instead of carrying stale history forward. The basis of Kadane's algorithm for maximum subarray problems. | OBS-001 | 1 problems | 0 problems |
| `SK-OB-04` Single-Pass Greedy Choice | Single-Pass Greedy Choice — scan once, maintain one running invariant (best buy-so-far, farthest reachable index, cumulative deficit, or a two-pass local allocation), and make an irrevocable locally-optimal decision at each step instead of exploring alternatives. Distinct from Running Extremum Scan: the invariant here drives a decision (buy/sell, jump, refuel, allocate), not just a max/min value. | OBS-003 | 4 problems | 1 problems |
| `SK-OB-05` Expand Around Center | Expand Around Center — for every possible palindrome center (each index, and each gap between two indices, for odd- and even-length palindromes), expand outward while the characters on both sides match. O(n^2) time, O(1) space; the standard non-DP approach to palindrome-substring problems. | OBS-019 | 1 problems | 0 problems |
| `SK-OB-06` Pattern Matching / Prefix Function | PDF subsection: Pattern Matching. Shared technique note for this skill group (general, not specific to this problem): KMP / Rabin-Karp / Z-Algorithm — efficient O(n+m) substring search. | OBS-021 | 2 problems | 2 problems |

## State Construction

Build explicit state representations (hash maps, frequency counts, pointer-linked structures) that summarize an input well enough to answer the actual question.

*6 skills, 46 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-SC-01` String Simulation / Frequency Map | PDF subsection: String Manipulation & Hashing. Shared technique note for this skill group (general, not specific to this problem): HashMap / Frequency Count — count character frequencies to compare or find patterns. | HSH-001 | 11 problems | 0 problems |
| `SK-SC-02` Hash Map / Hash Set | HashMap — O(1) lookups to avoid nested loops; track frequency, index, or pairs. Intentional revisit preserved from the PDF. | HSH-005 | 6 problems | 0 problems |
| `SK-SC-03` Cycle Detection or Value-Space Search | Sorting + Binary Search — sort once, then binary-search for O(n log n) solutions. | LNK-001 | 1 problems | 0 problems |
| `SK-SC-04` Fast & Slow Pointers | PDF subsection: Fast & Slow Pointers. Shared technique note for this skill group (general, not specific to this problem): Floyd's Cycle Detection — two pointers at different speeds to detect cycles and midpoints. | LNK-002 | 4 problems | 0 problems |
| `SK-SC-05` Linked-List Reversal / Merge | PDF subsection: Reversal & Merging. Shared technique note for this skill group (general, not specific to this problem): In-place Reversal — reverse sublists or entire lists using pointer manipulation. | LNK-007 | 11 problems | 2 problems |
| `SK-SC-06` Pointer Stitching / List Design | PDF subsection: Advanced Linked List. Shared technique note for this skill group (general, not specific to this problem): In-place Reversal — reverse sublists or entire lists using pointer manipulation. | LNK-026 | 5 problems | 0 problems |

## Constraint Maintenance

Maintain a moving invariant (window, pointer pair, or monotonic stack) while scanning, so that repeated work collapses into amortized linear time.

*6 skills, 46 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-CM-01` Two Pointers | Two Pointers — use two indices moving toward/away from each other to reduce O(n²) to O(n). Intentional revisit preserved from the PDF. | TWO-001 | 8 problems | 1 problems |
| `SK-CM-02` Sliding Window | Sliding Window — maintain a window of elements; expand/shrink to satisfy a constraint. | WIN-002 | 7 problems | 2 problems |
| `SK-CM-03` Sliding Window on Strings | Variable-size Sliding Window — track character counts inside a window. | WIN-011 | 2 problems | 1 problems |
| `SK-CM-04` Stack Parsing / Monotonic Stack | Monotonic Stack / Explicit Stack — process characters left-to-right with a stack. | STK-001 | 8 problems | 1 problems |
| `SK-CM-05` Monotonic Stack on Linked List | In-place Reversal — reverse sublists or entire lists using pointer manipulation. | STK-011 | 1 problems | 0 problems |
| `SK-CM-06` Monotonic Stack | Monotonic Stack — maintain a stack in increasing/decreasing order for next-greater/smaller | STK-012 | 7 problems | 2 problems |

## Ordered Reasoning

Use sorted order and monotonic feasibility to replace repeated scans with binary search or a single sorted pass.

*5 skills, 36 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-OR-01` Patience Sorting / Bisect | Patience Sorting / Bisect — maintain a `tails` array where tails[k] is the smallest possible tail of an increasing subsequence of length k+1; binary-search for each new element's insertion point. The basis of the O(n log n) Longest Increasing Subsequence algorithm. | OBS-026 | 1 problems | 0 problems |
| `SK-OR-02` Parametric Search | PDF subsection: Binary Search on Answer. Shared technique note for this skill group (general, not specific to this problem): Parametric Search — binary search on the answer space, validate with a feasibility function. | TWO-011 | 8 problems | 6 problems |
| `SK-OR-03` Binary Search on Rotated Array | PDF subsection: Sorting & Searching in Arrays. Shared technique note for this skill group (general, not specific to this problem): Sorting + Binary Search — sort once, then binary-search for O(n log n) solutions. | BSR-001 | 1 problems | 0 problems |
| `SK-OR-04` Binary Search | Binary Search — repeatedly halve the search space on a monotonic function. | BSR-003 | 7 problems | 1 problems |
| `SK-OR-05` Sorting Algorithms & Custom Comparators | Raw sorting mechanics were previously assumed, never taught — implement the algorithm itself. | ORD-008 | 7 problems | 0 problems |

## Query Processing

Answer repeated queries efficiently using precomputed prefix structures or order-statistic heaps, instead of rescanning the input per query.

*6 skills, 37 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-QP-01` Prefix Sum / Difference Array | Prefix Sum — precompute cumulative sums for O(1) range queries. | PFX-002 | 9 problems | 0 problems |
| `SK-QP-02` Prefix Sum + Hash Map | HashMap — O(1) lookups to avoid nested loops; track frequency, index, or pairs. Intentional revisit preserved from the PDF. | PFX-011 | 2 problems | 0 problems |
| `SK-QP-03` Weighted Prefix Sampling | Reservoir Sampling / Fisher-Yates — uniform random sampling in O(1) space. Intentional revisit preserved from the PDF. | PFX-014 | 1 problems | 0 problems |
| `SK-QP-04` Heap Selection | Heap Selection — maintain a fixed-size min-heap (size k) of the largest elements seen so far; after processing all elements, the heap's minimum is the kth largest, avoiding a full O(n log n) sort. | HEP-001 | 1 problems | 0 problems |
| `SK-QP-05` Top-K Heap | Min-Heap of size K — maintain the K largest elements efficiently. Intentional revisit preserved from the PDF. | HEP-003 | 8 problems | 1 problems |
| `SK-QP-06` Two Heaps / Priority Queue | Two Heaps — one max-heap and one min-heap to find the median dynamically. | HEP-016 | 3 problems | 6 problems |

## Decision Making

Commit to local, irrevocable choices and defend them with an exchange argument, invariant, or counterexample search, instead of exploring every branch.

*3 skills, 19 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-DM-01` Priority Scheduling | Priority Scheduling — repeatedly pick the highest-priority or most-frequent remaining item using a max-heap (or frequency-bucket count), respecting a cooldown or ordering constraint before that item can be reused. | HEP-002 | 1 problems | 0 problems |
| `SK-DM-02` Sorting / Greedy Choice | Sorting / Greedy Choice — sort the input first, then apply a greedy selection rule (e.g. always take from a fixed relative position within each sorted group) to optimize an aggregate outcome; correctness typically follows from an exchange argument. | GRD-001 | 1 problems | 0 problems |
| `SK-DM-03` String / Array Greedy | Greedy Selection — always pick the locally optimal choice; prove exchange argument. | GRD-014 | 13 problems | 1 problems |

## Recursive Thinking

Decompose hierarchical structures (trees, BSTs, tries) into reusable subproblems and combine subtree results through a stated recursive contract.

*6 skills, 46 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-RT-01` Tree Traversal (DFS/BFS) | PDF subsection: Tree Traversals. Shared technique note for this skill group (general, not specific to this problem): DFS (Pre/In/Post-order) & BFS (Level-order) — foundation of nearly all tree problems. | TRE-001 | 8 problems | 1 problems |
| `SK-RT-02` Tree Recursion | Tree Recursion — solve sub-problems on left/right subtrees and combine results. | TRE-011 | 13 problems | 1 problems |
| `SK-RT-03` Tree Serialization | Tree Serialization — convert a tree into a string (typically via pre-order or level-order traversal, encoding null children as sentinels) and reconstruct it unambiguously from that string alone. | TRE-026 | 1 problems | 0 problems |
| `SK-RT-04` BST Invariant | BST Invariant — for every node, all values in the left subtree are smaller and all values in the right subtree are larger. Exploit this ordering to prune search (go left or right, never both) instead of visiting every node. | BST-003 | 9 problems | 1 problems |
| `SK-RT-05` Trie / Prefix Tree | PDF subsection: Tries. Shared technique note for this skill group (general, not specific to this problem): Trie (Prefix Tree) — efficient prefix search and autocomplete in O(L) per query. | TRI-001 | 3 problems | 2 problems |
| `SK-RT-06` Trie with Multiplicity | Trie with Multiplicity — extend a standard trie node with a count (or list) at each node or end-of-word marker to track how many times a word or prefix has been inserted, enabling frequency-aware prefix queries. | TRI-007 | 1 problems | 0 problems |

## State Transition

Define explicit states, transitions, and base cases, then choose an evaluation order that respects dependencies -- the discipline of dynamic programming.

*17 skills, 103 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-ST-01` 2-D Dynamic Programming | 2-D DP — state is two indices (i, j); fill a table row by row. | DP-029 | 6 problems | 10 problems |
| `SK-ST-02` Word-Break Dynamic Programming | Word-Break Dynamic Programming — dp[i] is true if the prefix of length i can be segmented into dictionary words: dp[i] is true when some dp[j] is true and s[j:i] is in the dictionary. | DP-003 | 1 problems | 0 problems |
| `SK-ST-03` Decode Dynamic Programming | Decode Dynamic Programming — dp[i] is the number of ways to decode the prefix of length i, combining the ways from treating s[i-1] alone and s[i-2:i] as a pair, with '0' and two-digit validity as base-case constraints. | DP-004 | 1 problems | 0 problems |
| `SK-ST-04` LIS Dynamic Programming with Bisect | Parametric Search — binary search on the answer space, validate with a feasibility function. | DP-005 | 1 problems | 0 problems |
| `SK-ST-05` LIS on Ordered Envelopes | LIS on Ordered Envelopes — sort by one dimension (width ascending, height descending on ties) to reduce a 2-D nesting problem to a 1-D Longest Increasing Subsequence on the second dimension, then solve with patience sorting / bisect. | DP-006 | 1 problems | 0 problems |
| `SK-ST-06` Weighted Interval Scheduling | Second weighted-interval-scheduling DP, more approachable than Job Scheduling. | DP-097 | 1 problems | 0 problems |
| `SK-ST-07` Longest Increasing Subsequence Counting | Longest Increasing Subsequence Counting — for each index, track both the length of the longest increasing subsequence ending there and the number of subsequences achieving that length, combining counts from all valid predecessors. | DP-008 | 1 problems | 0 problems |
| `SK-ST-08` Catalan Dynamic Programming | Catalan Dynamic Programming — dp[n] is the number of structurally distinct trees/structures of size n, computed by summing dp[i-1] * dp[n-i] over every possible split point i. Produces the Catalan number sequence. | DP-009 | 1 problems | 0 problems |
| `SK-ST-09` Tree Dynamic Programming | Simpler tree-DP on-ramp that should really be solved before the harder Binary Tree Cameras already in this pattern. | DP-100 | 1 problems | 0 problems |
| `SK-ST-10` LIS Counting with Range Queries | Segment Tree / Fenwick Tree — O(log n) range queries and point updates. Intentional revisit preserved from the PDF. | DP-011 | 1 problems | 0 problems |
| `SK-ST-11` Pointer Dynamic Programming | PDF subsection: Two-Heap Pattern. Shared technique note for this skill group (general, not specific to this problem): Two Heaps — one max-heap and one min-heap to find the median dynamically. | DP-012 | 1 problems | 0 problems |
| `SK-ST-12` 1-D Dynamic Programming | 1-D DP — state is a single index; transition from previous states. | DP-014 | 15 problems | 1 problems |
| `SK-ST-13` Knapsack Dynamic Programming | PDF subsection: Knapsack Variants. Shared technique note for this skill group (general, not specific to this problem): 0/1 Knapsack / Unbounded Knapsack — classic DP on items with weight/value. | DP-044 | 8 problems | 1 problems |
| `SK-ST-14` Interval / Range Dynamic Programming | PDF subsection: Interval / Range DP. Shared technique note for this skill group (general, not specific to this problem): Interval DP — solve subproblems over all intervals [i, j], merge results. | DP-055 | 1 problems | 7 problems |
| `SK-ST-15` State Machine Dynamic Programming | PDF subsection: State-Machine DP (Stocks & Transactions). Shared technique note for this skill group (general, not specific to this problem): State Machine DP — model allowed states (holding/not holding) and transitions. | DP-065 | 3 problems | 6 problems |
| `SK-ST-16` Bitmask Dynamic Programming | PDF subsection: Bitmask DP. Shared technique note for this skill group (general, not specific to this problem): Bitmask DP — represent subsets as bitmasks; ideal for small n (≤20). | DP-074 | 1 problems | 8 problems |
| `SK-ST-17` Tree / Graph Dynamic Programming | Tree / Graph Dynamic Programming — compute a value at each node from its already-computed children (post-order traversal), e.g. height, diameter, or max path sum, combining child results at each parent. | DP-083 | 1 problems | 8 problems |

## Graph Thinking

Model problems as graphs, choose the right traversal or connectivity tool, and separate reachability/traversal correctness from path optimality.

*9 skills, 71 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-GT-01` Queue / Deque / BFS | Monotonic Deque — maintain a deque for sliding window max/min in O(n). | QUE-003 | 8 problems | 4 problems |
| `SK-GT-02` Grid BFS | Grid BFS — treat each grid cell as a graph node connected to its (usually 4-directional) neighbors, and run multi-source BFS from every initially 'active' cell simultaneously to compute the minimum steps for a state to propagate across the grid. | GRF-001 | 1 problems | 0 problems |
| `SK-GT-03` Graph BFS | PDF subsection: BFS (Shortest Path / Level-order). Shared technique note for this skill group (general, not specific to this problem): BFS — explore nodes level by level; guarantees shortest path in unweighted graphs. | GRF-004 | 10 problems | 4 problems |
| `SK-GT-04` Graph DFS / Union-Find | PDF subsection: DFS / Backtracking on Graphs. Shared technique note for this skill group (general, not specific to this problem): DFS with Visited Set — explore all paths; detect cycles and connected components. | GRF-017 | 9 problems | 0 problems |
| `SK-GT-05` Topological Sort | PDF subsection: Topological Sort. Shared technique note for this skill group (general, not specific to this problem): Kahn's Algorithm / DFS Post-order — linear ordering of nodes in a DAG. | GRF-028 | 3 problems | 2 problems |
| `SK-GT-06` Disjoint Set Union | PDF subsection: Union-Find (Disjoint Set Union). Shared technique note for this skill group (general, not specific to this problem): DSU with Path Compression + Union by Rank — near-O(1) amortised operations. | GRF-033 | 3 problems | 4 problems |
| `SK-GT-07` Shortest Path Algorithms | PDF subsection: Shortest Path Algorithms. Shared technique note for this skill group (general, not specific to this problem): Dijkstra / Bellman-Ford / Floyd-Warshall — weighted shortest paths. | GRF-041 | 6 problems | 3 problems |
| `SK-GT-08` Minimum Spanning Tree | PDF subsection: Minimum Spanning Tree. Shared technique note for this skill group (general, not specific to this problem): Kruskal's / Prim's — greedily build a spanning tree with minimum total edge weight. | GRF-051 | 1 problems | 3 problems |
| `SK-GT-09` Grid DFS / Flood Fill | An Easy grid-DFS problem — softens the module's steep 2-Easy-out-of-56 difficulty cliff. | GRF-058 | 1 problems | 0 problems |

## Interval Reasoning

Reason about overlapping ranges, sweeps, and ordered range-query structures (Fenwick/segment trees) that summarize or update intervals efficiently.

*11 skills, 40 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-IR-01` Interval / Scheduling Greedy | PDF subsection: Interval & Scheduling Greedy. Shared technique note for this skill group (general, not specific to this problem): Greedy Selection — always pick the locally optimal choice; prove exchange argument. | GRD-005 | 11 problems | 0 problems |
| `SK-IR-02` Sorting / Interval Sweep | PDF subsection: Sorting & Searching in Arrays. Shared technique note for this skill group (general, not specific to this problem): Sorting + Binary Search — sort once, then binary-search for O(n log n) solutions. | ORD-001 | 4 problems | 0 problems |
| `SK-IR-03` Two-Pointer Interval Sweep | Second example of sweeping sorted values into ranges — gives 'Interval List Intersections' a companion instead of standing alone. | ORD-007 | 1 problems | 0 problems |
| `SK-IR-04` Fenwick Tree / Ordered Merge | Fenwick Tree / Ordered Merge — coordinate-compress the values, then use a Fenwick (Binary Indexed) tree to count, in O(log n) per element, how many previously-inserted values are smaller; a merge-sort-based inversion count is the ordered-merge alternative. | RNG-001 | 1 problems | 0 problems |
| `SK-IR-05` Range Count / Ordered Prefix | Range Count / Ordered Prefix — compute prefix sums, then count index pairs (i, j) whose prefix-sum difference falls in a target range, using a Fenwick tree, merge sort, or balanced BST over the prefix-sum sequence for O(n log n). | RNG-002 | 1 problems | 0 problems |
| `SK-IR-06` Fenwick Tree / Ordered Statistics | Second ordered-statistics counting problem, more approachable difficulty than the existing Hard-only pair. | RNG-017 | 1 problems | 0 problems |
| `SK-IR-07` Fenwick Tree / Segment Tree | Segment Tree / Fenwick Tree — O(log n) range queries and point updates. | RNG-004 | 1 problems | 5 problems |
| `SK-IR-08` Interval Booking Structure | Interval Booking Structure — maintain a dynamic set of booked intervals (sorted structure, balanced BST, or segment tree) supporting fast overlap queries and insertions as new bookings arrive online. | RNG-008 | 1 problems | 0 problems |
| `SK-IR-09` Persistent Array Snapshot Design | Persistent Array Snapshot Design — instead of copying the whole array on every snapshot, store each index's value history as a list of (snapshot_id, value) pairs and binary-search that history on read, giving O(1) snapshot and O(log n) get. | RNG-012 | 1 problems | 0 problems |
| `SK-IR-10` Segment Tree / Ordered Range Design | Segment Tree / Ordered Range Design — maintain a dynamic set of non-overlapping ranges (a sorted map of interval boundaries, or a segment tree with lazy propagation) supporting add/remove/query of arbitrary ranges. | RNG-013 | 1 problems | 0 problems |
| `SK-IR-11` Segment Tree Ticket Allocation | A simpler Fenwick/segment-tree prerequisite that should precede the harder Booking Concert Tickets problem already in this pattern. | RNG-021 | 1 problems | 0 problems |

## Pattern Discovery

Generate the space of possibilities deliberately, prune aggressively using the problem's constraints, and recognize when a decision tree is the right model.

*5 skills, 33 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-PD-01` Memoized DFS / Enumeration | Simpler enumeration-with-pruning on-ramp before the harder Word Break II already in this pattern. | REC-032 | 1 problems | 0 problems |
| `SK-PD-02` Recursive Tree Construction | Recursive Tree Construction — for each possible root value, recursively generate every valid left-subtree and right-subtree shape, then combine each left/right pair under that root to enumerate all distinct trees. | REC-002 | 1 problems | 0 problems |
| `SK-PD-03` Combination Backtracking | PDF subsection: Subsets & Combinations. Shared technique note for this skill group (general, not specific to this problem): Backtracking — explore all choices recursively; prune branches that violate constraints. | REC-003 | 9 problems | 0 problems |
| `SK-PD-04` Permutation Backtracking | PDF subsection: Permutations. Shared technique note for this skill group (general, not specific to this problem): Permutation Backtracking — swap elements or use a visited array. | REC-013 | 4 problems | 5 problems |
| `SK-PD-05` Constraint Backtracking | PDF subsection: Advanced Backtracking. Shared technique note for this skill group (general, not specific to this problem): Permutation Backtracking — swap elements or use a visited array. | REC-024 | 5 problems | 3 problems |

## Mathematical Thinking

Replace simulation with direct reasoning using number-theoretic or bitwise properties, and prove correctness algebraically rather than by example.

*3 skills, 22 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-MT-01` Cycle Detection on State Space | Floyd's Cycle Detection — two pointers at different speeds to detect cycles and midpoints. Intentional revisit preserved from the PDF. | MAT-001 | 1 problems | 0 problems |
| `SK-MT-02` Number Theory / Arithmetic | Number Theory — prime sieves, GCD/LCM, modular arithmetic, combinatorics. | MAT-003 | 9 problems | 0 problems |
| `SK-MT-03` Bit Manipulation | PDF subsection: Bit Manipulation. Shared technique note for this skill group (general, not specific to this problem): Bit Tricks — XOR, AND/OR masks, Brian Kernighan's algorithm for O(1) bit operations. | MAT-012 | 9 problems | 0 problems |

## Integration

Compose multiple data structures into a durable system, support online updates, and reason about API guarantees under sustained use -- the terminal stage of the apprenticeship.

*8 skills, 37 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-IN-01` O(1) Cache Design | O(1) Cache Design — combine a hash map (O(1) key lookup) with a doubly linked list (O(1) reordering/eviction) so both get and put run in O(1); the list tracks recency or frequency order for eviction. | DES-001 | 1 problems | 0 problems |
| `SK-IN-02` Frequency-Aware Cache Design | Second recency/frequency-aware design problem, complementing LFU Cache. | DES-036 | 1 problems | 0 problems |
| `SK-IN-03` Ordered Probabilistic Structure | Ordered Probabilistic Structure — build a multi-level linked structure where each node is randomly promoted to higher levels with fixed probability, giving expected O(log n) search/insert/delete without balanced-tree rebalancing logic. | DES-003 | 1 problems | 0 problems |
| `SK-IN-04` Core Data-Structure Design | PDF subsection: Classic Design Problems. Shared technique note for this skill group (general, not specific to this problem): OOP + Right Data Structures — combine hash maps, heaps, doubly linked lists for O(1) ops. | DES-004 | 5 problems | 3 problems |
| `SK-IN-05` Randomized Data Structure | PDF subsection: Randomized & Probabilistic Structures. Shared technique note for this skill group (general, not specific to this problem): Reservoir Sampling / Fisher-Yates — uniform random sampling in O(1) space. | DES-013 | 3 problems | 1 problems |
| `SK-IN-06` Online / Streaming Design | Online Algorithms — process data one element at a time without looking back. | DES-018 | 7 problems | 1 problems |
| `SK-IN-07` Data-Structure Design | Data-Structure Design — maintain a dynamic ordered set of occupied positions (a sorted structure or a heap of gaps) supporting online insert/remove operations while always answering the optimal-placement query efficiently. | DES-028 | 4 problems | 3 problems |
| `SK-IE-00` Implementation Engineering | The ability to correctly translate an understood algorithm into bug-free code by determining initialization, loop boundaries, state ownership, update ordering, previous-state preservation, and return value without relying on memorized implementations. | — | 0 problems | 0 problems |

