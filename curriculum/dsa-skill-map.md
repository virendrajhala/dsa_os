# DSA OS — Skill Map (generated from `knowledge/skills.json`)

This file is generated, not hand-maintained. It replaces the old module/pattern-based skill map after the skill-first migration (curriculum.json v3.0). Regenerate it any time `knowledge/skills.json` or `curriculum/curriculum.json` changes.

**581 problems** across **93 skills** in **13 stages**. Difficulty: 99 Easy / 336 Medium / 146 Hard. Importance: 292 CORE / 252 COMMON / 37 SPECIALIZED / 0 NICHE.

## Observation

Learn to read the prompt exactly, simulate small examples, and state the invariant before reaching for a pattern name. Includes reasoning about what a brute force costs and why.

*7 skills, 24 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-OB-01` Asymptotic Estimation | Brute force O(n^2) vs hash-map O(n) — the canonical first lesson in reading constraints to infer required complexity. | CPX-001 | 1 problems | 1 problems |
| `SK-OB-02` Amortized Analysis | Every operation must be O(1) — introduces amortized/worst-case distinction via auxiliary state. | CPX-004 | 2 problems | 0 problems |
| `SK-OB-03` Running Extremum Scan | Running Extremum Scan — track a running best-so-far value (max, min, or both) in a single pass; when a new element makes the running value worse than starting fresh, reset instead of carrying stale history forward. The basis of Kadane's algorithm for maximum subarray problems. | OBS-001 | 1 problems | 0 problems |
| `SK-OB-04` Single-Pass Greedy Choice | Single-Pass Greedy Choice — scan once, maintain one running invariant (best buy-so-far, farthest reachable index, cumulative deficit, or a two-pass local allocation), and make an irrevocable locally-optimal decision at each step instead of exploring alternatives. Distinct from Running Extremum Scan: the invariant here drives a decision (buy/sell, jump, refuel, allocate), not just a max/min value. | OBS-003 | 4 problems | 1 problems |
| `SK-OB-05` Expand Around Center | Expand Around Center — for every possible palindrome center (each index, and each gap between two indices, for odd- and even-length palindromes), expand outward while the characters on both sides match. O(n^2) time, O(1) space; the standard non-DP approach to palindrome-substring problems. | OBS-019 | 1 problems | 0 problems |
| `SK-OB-06` Pattern Matching / Prefix Function | Substring search that preprocesses the pattern into a prefix (failure) function so mismatches skip ahead without re-scanning, matching in O(n+m) instead of O(nm). KMP uses the prefix table for shifts, Rabin-Karp uses a rolling hash, and the Z-algorithm computes longest-match lengths at each position. | OBS-021 | 2 problems | 3 problems |
| `SK-OB-07` Boyer-Moore Voting | Boyer-Moore Voting - find majority elements in one pass and O(1) space by maintaining candidate(s) and vote counts that cancel opposing elements, then verifying the survivor(s). | OBS-028 | 1 problems | 0 problems |

## State Construction

Build explicit state representations (hash maps, frequency counts, pointer-linked structures) that summarize an input well enough to answer the actual question.

*7 skills, 52 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-SC-01` String Simulation / Frequency Map | Scan a string while maintaining a frequency map (array or hash) of character or token counts, then compare or update counts to detect anagrams, duplicates, or valid arrangements in O(n). Often paired with a running state that you simulate character by character. | HSH-001 | 12 problems | 0 problems |
| `SK-SC-02` Hash Map / Hash Set | HashMap — O(1) lookups to avoid nested loops; track frequency, index, or pairs. Intentional revisit preserved from the PDF. | HSH-005 | 6 problems | 0 problems |
| `SK-SC-03` Cycle Detection or Value-Space Search | Detect a cycle or search the value space directly rather than over indices: Floyd's tortoise-and-hare on an implicit functional graph, or binary search over the range of possible values, to find a duplicate or target in O(n) / O(n log n). | LNK-001 | 1 problems | 0 problems |
| `SK-SC-04` Fast & Slow Pointers | Advance two pointers through a sequence at different speeds (one step vs two steps); Floyd's tortoise-and-hare uses this to detect a cycle when they meet, find the cycle entry, or locate the list midpoint in O(n) time and O(1) space. | LNK-002 | 4 problems | 0 problems |
| `SK-SC-05` Linked-List Reversal / Merge | Reverse a linked list or a sublist in place by rewiring next pointers one node at a time (prev, curr, next), and merge two sorted lists by splicing nodes; both run in O(n) with O(1) extra space and underlie reorder, palindrome, and k-group problems. | LNK-007 | 11 problems | 2 problems |
| `SK-SC-06` Pointer Stitching / List Design | Build or restructure linked lists by carefully stitching next/prev (and random) pointers, using dummy heads and multi-pass or hash-map cloning; used for problems like copy-list-with-random-pointer, flatten, and complex in-place rewiring. | LNK-026 | 5 problems | 0 problems |
| `SK-SC-07` Matrix Simulation | Matrix Simulation - transform a 2D grid in place (rotate, spiral-traverse, mark-and-sweep, simultaneous update) by carefully managing boundaries, index mapping, and update ordering without allocating a second grid. | MAT-023 | 4 problems | 0 problems |

## Constraint Maintenance

Maintain a moving invariant (window, pointer pair, or monotonic stack) while scanning, so that repeated work collapses into amortized linear time.

*6 skills, 50 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-CM-01` Two Pointers | Two Pointers — use two indices moving toward/away from each other to reduce O(n²) to O(n). Intentional revisit preserved from the PDF. | TWO-001 | 11 problems | 1 problems |
| `SK-CM-02` Sliding Window | Sliding Window — maintain a window of elements; expand/shrink to satisfy a constraint. | WIN-002 | 7 problems | 2 problems |
| `SK-CM-03` Sliding Window on Strings | Variable-size Sliding Window — track character counts inside a window. | WIN-011 | 2 problems | 1 problems |
| `SK-CM-04` Stack Parsing / Monotonic Stack | Monotonic Stack / Explicit Stack — process characters left-to-right with a stack. | STK-001 | 8 problems | 2 problems |
| `SK-CM-05` Monotonic Stack on Linked List | Apply a monotonic stack while traversing a linked list (often after collecting values or via recursion) to answer next-greater-style queries when random indexed access is unavailable. | STK-011 | 1 problems | 0 problems |
| `SK-CM-06` Monotonic Stack | Monotonic Stack — maintain a stack in increasing/decreasing order for next-greater/smaller | STK-012 | 7 problems | 2 problems |

## Ordered Reasoning

Use sorted order and monotonic feasibility to replace repeated scans with binary search or a single sorted pass.

*5 skills, 36 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-OR-01` Patience Sorting / Bisect | Patience Sorting / Bisect — maintain a `tails` array where tails[k] is the smallest possible tail of an increasing subsequence of length k+1; binary-search for each new element's insertion point. The basis of the O(n log n) Longest Increasing Subsequence algorithm. | OBS-026 | 1 problems | 0 problems |
| `SK-OR-02` Parametric Search | When the answer is monotonic (a feasible value stays feasible as you relax it), binary-search the answer space and test each candidate with a boolean feasibility check, giving O(log(range) * check) time. Used for minimize-the-maximum problems like Koko eating bananas or split-array-largest-sum. | TWO-011 | 8 problems | 6 problems |
| `SK-OR-03` Binary Search on Rotated Array | Binary search on a rotated sorted array by, at each midpoint, deciding which half is sorted and whether the target lies within it, then discarding the other half - locating a value or the pivot in O(log n) despite the rotation. | BSR-001 | 1 problems | 0 problems |
| `SK-OR-04` Binary Search | Binary Search — repeatedly halve the search space on a monotonic function. | BSR-003 | 7 problems | 1 problems |
| `SK-OR-05` Sorting Algorithms & Custom Comparators | Raw sorting mechanics were previously assumed, never taught — implement the algorithm itself. | ORD-008 | 7 problems | 0 problems |

## Query Processing

Answer repeated queries efficiently using precomputed prefix structures or order-statistic heaps, instead of rescanning the input per query.

*6 skills, 38 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-QP-01` Prefix Sum / Difference Array | Prefix Sum — precompute cumulative sums for O(1) range queries. | PFX-002 | 10 problems | 0 problems |
| `SK-QP-02` Prefix Sum + Hash Map | HashMap — O(1) lookups to avoid nested loops; track frequency, index, or pairs. Intentional revisit preserved from the PDF. | PFX-011 | 2 problems | 0 problems |
| `SK-QP-03` Weighted Prefix Sampling | Reservoir Sampling / Fisher-Yates — uniform random sampling in O(1) space. Intentional revisit preserved from the PDF. | PFX-014 | 1 problems | 0 problems |
| `SK-QP-04` Heap Selection | Heap Selection — maintain a fixed-size min-heap (size k) of the largest elements seen so far; after processing all elements, the heap's minimum is the kth largest, avoiding a full O(n log n) sort. | HEP-001 | 1 problems | 0 problems |
| `SK-QP-05` Top-K Heap | Min-Heap of size K — maintain the K largest elements efficiently. Intentional revisit preserved from the PDF. | HEP-003 | 8 problems | 1 problems |
| `SK-QP-06` Two Heaps / Priority Queue | Two Heaps — one max-heap and one min-heap to find the median dynamically. | HEP-013 | 4 problems | 5 problems |

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

*6 skills, 50 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-RT-01` Tree Traversal (DFS/BFS) | Traverse a tree via DFS (preorder, inorder, or postorder, recursively or with an explicit stack) or BFS (level-order with a queue); these traversals underpin nearly all tree computations such as searching, aggregating, and building level-based answers. | TRE-001 | 8 problems | 1 problems |
| `SK-RT-02` Tree Recursion | Tree Recursion — solve sub-problems on left/right subtrees and combine results. | TRE-011 | 16 problems | 1 problems |
| `SK-RT-03` Tree Serialization | Tree Serialization — convert a tree into a string (typically via pre-order or level-order traversal, encoding null children as sentinels) and reconstruct it unambiguously from that string alone. | TRE-026 | 1 problems | 0 problems |
| `SK-RT-04` BST Invariant | BST Invariant — for every node, all values in the left subtree are smaller and all values in the right subtree are larger. Exploit this ordering to prune search (go left or right, never both) instead of visiting every node. | BST-003 | 10 problems | 1 problems |
| `SK-RT-05` Trie / Prefix Tree | A trie stores strings as a tree of character-labeled edges with a shared-prefix path, enabling insert and prefix/word lookup in O(L) per key (L = key length) independent of the number of stored words; ideal for autocomplete, prefix counting, and word dictionaries. | TRI-001 | 3 problems | 2 problems |
| `SK-RT-06` Trie with Multiplicity | Trie with Multiplicity — extend a standard trie node with a count (or list) at each node or end-of-word marker to track how many times a word or prefix has been inserted, enabling frequency-aware prefix queries. | TRI-007 | 1 problems | 0 problems |

## State Transition

Define explicit states, transitions, and base cases, then choose an evaluation order that respects dependencies -- the discipline of dynamic programming.

*17 skills, 105 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-ST-01` 2-D Dynamic Programming | 2-D DP — state is two indices (i, j); fill a table row by row. | DP-029 | 7 problems | 10 problems |
| `SK-ST-02` Word-Break Dynamic Programming | Word-Break Dynamic Programming — dp[i] is true if the prefix of length i can be segmented into dictionary words: dp[i] is true when some dp[j] is true and s[j:i] is in the dictionary. | DP-003 | 1 problems | 0 problems |
| `SK-ST-03` Decode Dynamic Programming | Decode Dynamic Programming — dp[i] is the number of ways to decode the prefix of length i, combining the ways from treating s[i-1] alone and s[i-2:i] as a pair, with '0' and two-digit validity as base-case constraints. | DP-004 | 1 problems | 0 problems |
| `SK-ST-04` LIS Dynamic Programming with Bisect | Longest Increasing Subsequence in O(n log n): maintain a tails array where tails[k] is the smallest possible tail of an increasing subsequence of length k+1, and binary-search (bisect) each element's insertion point. | DP-005 | 1 problems | 0 problems |
| `SK-ST-05` LIS on Ordered Envelopes | LIS on Ordered Envelopes — sort by one dimension (width ascending, height descending on ties) to reduce a 2-D nesting problem to a 1-D Longest Increasing Subsequence on the second dimension, then solve with patience sorting / bisect. | DP-006 | 1 problems | 0 problems |
| `SK-ST-06` Weighted Interval Scheduling | Second weighted-interval-scheduling DP, more approachable than Job Scheduling. | DP-097 | 1 problems | 0 problems |
| `SK-ST-07` Longest Increasing Subsequence Counting | Longest Increasing Subsequence Counting — for each index, track both the length of the longest increasing subsequence ending there and the number of subsequences achieving that length, combining counts from all valid predecessors. | DP-008 | 1 problems | 0 problems |
| `SK-ST-08` Catalan Dynamic Programming | Catalan Dynamic Programming — dp[n] is the number of structurally distinct trees/structures of size n, computed by summing dp[i-1] * dp[n-i] over every possible split point i. Produces the Catalan number sequence. | DP-009 | 1 problems | 0 problems |
| `SK-ST-09` Tree Dynamic Programming | Simpler tree-DP on-ramp that should really be solved before the harder Binary Tree Cameras already in this pattern. | DP-100 | 1 problems | 0 problems |
| `SK-ST-10` LIS Counting with Range Queries | Segment Tree / Fenwick Tree — O(log n) range queries and point updates. Intentional revisit preserved from the PDF. | DP-011 | 1 problems | 0 problems |
| `SK-ST-11` Pointer Dynamic Programming | Pointer DP that generates an ordered sequence by maintaining one index per generator (e.g. one pointer per prime factor) into the sequence built so far; the next term is the minimum of the candidate products, advancing whichever pointer(s) produced it. Basis of the Ugly Number family. | DP-012 | 1 problems | 0 problems |
| `SK-ST-12` 1-D Dynamic Programming | 1-D DP — state is a single index; transition from previous states. | DP-014 | 15 problems | 1 problems |
| `SK-ST-13` Knapsack Dynamic Programming | DP over items with weights and values: 0/1 knapsack allows each item once (iterate capacity descending), unbounded allows repeats (iterate ascending), maximizing value under a capacity constraint; the same recurrence covers subset-sum, coin-change, and partition problems. | DP-044 | 8 problems | 1 problems |
| `SK-ST-14` Interval / Range Dynamic Programming | DP where each state is a contiguous interval [i, j] and the answer is built by choosing a split or merge point k inside it, combining subinterval results; solves matrix-chain multiplication, burst-balloons, and optimal-BST in O(n^3). | DP-055 | 2 problems | 7 problems |
| `SK-ST-15` State Machine Dynamic Programming | Model the problem as a finite set of states (e.g. holding vs not holding a stock, cooldown) with allowed transitions, and carry the best value per state across each step; used for stock-trading with k transactions, cooldowns, and fees. | DP-065 | 3 problems | 6 problems |
| `SK-ST-16` Bitmask Dynamic Programming | Encode a subset of up to ~20 elements as the bits of an integer mask and run DP over masks, transitioning by flipping bits; runs in O(2^n * n) and solves traveling-salesman, assignment, and set-cover style problems. | DP-074 | 1 problems | 8 problems |
| `SK-ST-17` Tree / Graph Dynamic Programming | Tree / Graph Dynamic Programming — compute a value at each node from its already-computed children (post-order traversal), e.g. height, diameter, or max path sum, combining child results at each parent. | DP-083 | 1 problems | 8 problems |

## Graph Thinking

Model problems as graphs, choose the right traversal or connectivity tool, and separate reachability/traversal correctness from path optimality.

*9 skills, 73 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-GT-01` Queue / Deque / BFS | Use a FIFO queue (or double-ended deque) to process elements in arrival order; the backbone of breadth-first traversal, level-order processing, and sliding-window extremes. | QUE-003 | 8 problems | 4 problems |
| `SK-GT-02` Grid BFS | Grid BFS — treat each grid cell as a graph node connected to its (usually 4-directional) neighbors, and run multi-source BFS from every initially 'active' cell simultaneously to compute the minimum steps for a state to propagate across the grid. | GRF-001 | 1 problems | 0 problems |
| `SK-GT-03` Graph BFS | Breadth-first search explores a graph level by level using a queue and a visited set, guaranteeing the shortest path (fewest edges) in unweighted graphs; used for level-order, multi-source spread, and shortest-hop problems. | GRF-004 | 10 problems | 4 problems |
| `SK-GT-04` Graph DFS / Union-Find | Depth-first search recurses (or uses a stack) along each path with a visited set to enumerate reachable nodes, find connected components, and detect cycles; disjoint-set union is an alternative for incrementally merging components and testing connectivity. | GRF-017 | 10 problems | 1 problems |
| `SK-GT-05` Topological Sort | Produce a linear ordering of a DAG's nodes so every edge points forward, via Kahn's algorithm (repeatedly remove zero-indegree nodes) or DFS post-order reversal; used for dependency resolution, build/course scheduling, and cycle detection in directed graphs. | GRF-028 | 3 problems | 2 problems |
| `SK-GT-06` Disjoint Set Union | Disjoint Set Union maintains a partition of elements supporting find (which set) and union (merge sets); with path compression plus union by rank/size, operations are near-O(1) amortized, powering connectivity queries, Kruskal's MST, and cycle detection. | GRF-033 | 3 problems | 4 problems |
| `SK-GT-07` Shortest Path Algorithms | Compute shortest paths on weighted graphs: Dijkstra (non-negative weights, O(E log V) with a heap), Bellman-Ford (handles negative edges and detects negative cycles, O(VE)), and Floyd-Warshall (all-pairs, O(V^3)). | GRF-041 | 6 problems | 3 problems |
| `SK-GT-08` Minimum Spanning Tree | Find a minimum-total-weight tree connecting all vertices: Kruskal's sorts edges and adds them if they join different DSU components, while Prim's grows the tree from a start vertex using a min-heap of frontier edges. | GRF-051 | 1 problems | 3 problems |
| `SK-GT-09` Grid DFS / Flood Fill | An Easy grid-DFS problem — softens the module's steep 2-Easy-out-of-56 difficulty cliff. | GRF-058 | 1 problems | 0 problems |

## Interval Reasoning

Reason about overlapping ranges, sweeps, and ordered range-query structures (Fenwick/segment trees) that summarize or update intervals efficiently.

*11 skills, 41 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-IR-01` Interval / Scheduling Greedy | Sort intervals or jobs by a key (usually end time or deadline) and greedily pick each locally optimal choice, skipping any that conflict, to maximize non-overlapping selections or minimize resources; correctness is argued with an exchange argument. | GRD-005 | 11 problems | 0 problems |
| `SK-IR-02` Sorting / Interval Sweep | Sort intervals by start (or end) and sweep through them, merging overlaps, counting concurrent intervals, or processing sorted event endpoints, to solve merge-intervals, meeting-rooms, and range-coverage problems in O(n log n). | ORD-001 | 5 problems | 0 problems |
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
| `SK-PD-03` Combination Backtracking | Backtracking that recursively builds subsets or fixed-size combinations, advancing a start index so each element is only considered forward (avoiding duplicate orderings) and pruning branches that break constraints; generates the combinatorial search space in O(2^n) style. | REC-003 | 9 problems | 0 problems |
| `SK-PD-04` Permutation Backtracking | Backtracking that generates all orderings by, at each depth, choosing an unused element (via swap or a used[] array), recursing, then undoing the choice; produces n! permutations and handles duplicate-skipping when the input has repeats. | REC-013 | 4 problems | 5 problems |
| `SK-PD-05` Constraint Backtracking | Backtracking under explicit constraints where each partial placement is validated before recursing and invalid branches are pruned early; solves N-Queens, Sudoku, and word-search by trying a candidate, checking feasibility, and backtracking on failure. | REC-024 | 5 problems | 3 problems |

## Mathematical Thinking

Replace simulation with direct reasoning using number-theoretic or bitwise properties, and prove correctness algebraically rather than by example.

*3 skills, 23 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-MT-01` Cycle Detection on State Space | Floyd's Cycle Detection — two pointers at different speeds to detect cycles and midpoints. Intentional revisit preserved from the PDF. | MAT-001 | 1 problems | 0 problems |
| `SK-MT-02` Number Theory / Arithmetic | Number Theory — prime sieves, GCD/LCM, modular arithmetic, combinatorics. | MAT-003 | 10 problems | 0 problems |
| `SK-MT-03` Bit Manipulation | Manipulate numbers at the bit level using XOR (find the unique element, swap without temp), AND/OR masks (set/clear/test bits), shifts, and Brian Kernighan's n & (n-1) trick to strip the lowest set bit for fast bit counting. | MAT-012 | 9 problems | 0 problems |

## Integration

Compose multiple data structures into a durable system, support online updates, and reason about API guarantees under sustained use -- the terminal stage of the apprenticeship.

*8 skills, 37 problems.*

| Skill | Description | Primary | Reinforcement | Challenge |
|---|---|---|---|---|
| `SK-IN-01` O(1) Cache Design | O(1) Cache Design — combine a hash map (O(1) key lookup) with a doubly linked list (O(1) reordering/eviction) so both get and put run in O(1); the list tracks recency or frequency order for eviction. | DES-001 | 1 problems | 0 problems |
| `SK-IN-02` Frequency-Aware Cache Design | Second recency/frequency-aware design problem, complementing LFU Cache. | DES-036 | 1 problems | 0 problems |
| `SK-IN-03` Ordered Probabilistic Structure | Ordered Probabilistic Structure — build a multi-level linked structure where each node is randomly promoted to higher levels with fixed probability, giving expected O(log n) search/insert/delete without balanced-tree rebalancing logic. | DES-003 | 1 problems | 0 problems |
| `SK-IN-04` Core Data-Structure Design | Design a custom data structure by composing primitives - hash maps for O(1) lookup, heaps for ordered extremes, doubly linked lists for O(1) removal - to meet the required operation complexities, as in LRU cache, LFU cache, or an O(1) insert/delete/getRandom set. | DES-004 | 5 problems | 3 problems |
| `SK-IN-05` Randomized Data Structure | Randomized structures for streaming or sampling: reservoir sampling picks k uniform items from an unknown-length stream in O(1) space, and the Fisher-Yates shuffle produces a uniformly random permutation in place in O(n). | DES-013 | 3 problems | 1 problems |
| `SK-IN-06` Online / Streaming Design | Online Algorithms — process data one element at a time without looking back. | DES-018 | 7 problems | 1 problems |
| `SK-IN-07` Data-Structure Design | Data-Structure Design — maintain a dynamic ordered set of occupied positions (a sorted structure or a heap of gaps) supporting online insert/remove operations while always answering the optimal-placement query efficiently. | DES-028 | 4 problems | 3 problems |
| `SK-IE-00` Implementation Engineering | The ability to correctly translate an understood algorithm into bug-free code by determining initialization, loop boundaries, state ownership, update ordering, previous-state preservation, and return value without relying on memorized implementations. | — | 0 problems | 0 problems |

