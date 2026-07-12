# DSA OS — Study Guide v2.1 (Gap-Fixed, 557 Problems)

Built from the corrected `curriculum.json`. The original 507-problem bank is unchanged and unmarked; **50 new supplemental problems** (`"supplemental": true`, marked 🆕 below) were added on top of it to close every gap identified in review. Nothing was removed or reordered — only added.

### What was fixed

| Gap | Fix |
|---|---|
| No complexity-analysis content | New **Foundational** stage: 'Complexity & Asymptotic Reasoning' module, 6 problems |
| Sorting module too thin (6 problems) | +8 problems on raw sorting mechanics (new pattern) |
| 34 single-problem patterns (not 32 — recount was more precise this pass) | +1 problem to every one of them, 34 total |
| Difficulty cliff into Graphs (2 Easy / 56) | +2 problems, incl. 1 Easy (Island Perimeter) |
| Difficulty cliff into DP (5 Easy / 92) | +11 problems, incl. 2 Easy on-ramps |

## Overview

- **557 problems** total (507 original + 50 supplemental) across **22 modules**, grouped into **10 stages**
- Difficulty: 94 Easy / 320 Medium / 143 Hard
- Interview frequency: 266 high / 250 medium / 41 selective
- Total estimated time: **32436 minutes (~541 hours)**

## Stage-by-stage time & difficulty budget

| Stage | Modules | Problems | Est. hours | Easy/Med/Hard |
|---|---|---|---|---|
| **Foundational** | Complexity & Asymptotic Reasoning | 6 | ~4.6h | 2/3/1 |
| **Explorer** | Observation & Simulation | 27 | ~17.9h | 7/16/4 |
| **Observer** | Two-Pointer Reasoning, Sliding Window, Hashing & Frequency Maps | 36 | ~25.0h | 12/20/4 |
| **Searcher** | Sorting & Interval Reasoning, Binary Search, Prefix Sums & Range Reasoning | 55 | ~45.1h | 11/37/7 |
| **State Builder** | Linked Lists, Stacks & Monotonic Structures, Queues, Deques & BFS Simulation, Heaps & Online Order Statistics | 86 | ~76.9h | 15/54/17 |
| **Recursive Thinker** | Tree Traversal & Structural Recursion, Binary Search Trees & Ordered Recursion, Tries & Prefix Indexes | 46 | ~40.2h | 16/23/7 |
| **Navigator** | Graph Traversal & Connectivity | 58 | ~59.9h | 3/39/16 |
| **Optimizer** | Dynamic Programming | 103 | ~124.1h | 7/45/51 |
| **Inventor** | Backtracking & Recursive Search, Greedy Optimization, Math & Bit Manipulation | 82 | ~76.0h | 17/53/12 |
| **Engineer** | Range Structures & Ordered Interval Systems, System & Data Structure Design | 58 | ~70.9h | 4/30/24 |

## Stage: Foundational
*Complexity and asymptotic reasoning — read constraints, estimate required complexity, understand amortized cost. (New stage, added to close a gap.)*

### Complexity & Asymptotic Reasoning (6 problems, ~4.6h)

**Asymptotic Estimation** (3)
- Two Sum — *Easy* 🔥 🆕 (supplemental)
- Contains Duplicate — *Easy* 🔥 🆕 (supplemental)
- First Missing Positive — *Hard* 🆕 (supplemental)

**Amortized Analysis** (3)
- Min Stack — *Medium* 🔥 🆕 (supplemental)
- Flatten Nested List Iterator — *Medium* 🆕 (supplemental)
- Design a HashMap — *Medium* 🆕 (supplemental)


## Stage: Explorer
*Read a sequence once, track running state, and make simulation-level observations.*

### Observation & Simulation (27 problems, ~17.9h)

**Invariant Scan / Greedy on Arrays** (10)
- Maximum Subarray (Kadane's) — *Medium* (#31)
- Maximum Product Subarray — *Medium* (#32)
- Best Time to Buy and Sell Stock — *Easy* (#33)
- Best Time to Buy and Sell Stock II — *Medium* (#34)
- Jump Game — *Medium* (#35)
- Jump Game II (minimum jumps) — *Medium* (#36)
- Gas Station — *Medium* (#37)
- Candy Distribution — *Hard* (#38)
- Partition Labels — *Medium* (#39)
- Minimum Number of Arrows to Burst Balloons — *Medium* (#40)

**String Simulation / Frequency Map** (8)
- Longest Common Prefix — *Easy* (#53)
- Reverse Words in a String — *Medium* (#54)
- String to Integer (atoi) — *Medium* (#55)
- Roman to Integer — *Easy* (#56)
- Integer to Roman — *Medium* (#57)
- Count and Say — *Medium* (#58)
- ZigZag Conversion — *Medium* (#59)
- Multiply Strings — *Medium* (#60)

**Expand Around Center** (2)
- Longest Palindromic Substring — *Medium* (#67)
- Palindromic Substrings (count all) — *Medium* (#68)

**Pattern Matching / Prefix Function** (5)
- Implement strStr() / Needle in Haystack — *Easy* (#69)
- Repeated Substring Pattern — *Easy* (#70)
- Shortest Palindrome (KMP) — *Hard* (#71)
- Longest Happy Prefix (KMP failure function) — *Hard* (#72)
- Find the Index of the First Occurrence in a String — *Easy* (#73)

**Patience Sorting / Bisect** (2)
- Minimum Operations to Make Array Increasing — *Easy* (#172)
- Minimum Number of Removals to Make Mountain Array — *Hard* 🆕 (supplemental)


## Stage: Observer
*Two pointers and windows — exploit structure by moving indices with a rule.*

### Two-Pointer Reasoning (11 problems, ~7.1h)

**Two Pointers** (10)
- Two Sum (sorted array) — *Easy* 🔥 (#1)
- Three Sum — *Medium* 🔥 (#2)
- Four Sum — *Medium* 🔥 (#3)
- Container With Most Water — *Medium* 🔥 (#4)
- Trapping Rain Water — *Hard* (#5)
- Remove Duplicates from Sorted Array — *Easy* 🔥 (#6)
- Move Zeroes to End — *Easy* 🔥 (#7)
- Sort Colors (Dutch National Flag) — *Medium* 🔥 (#8)
- Minimum Size Subarray Sum — *Medium* 🔥 (#9)
- Squares of a Sorted Array — *Easy* 🔥 (#10)

**Parametric Search** (1)
- Count of Pairs with Sum Less Than Target — *Easy* 🔥 (#167)

### Sliding Window (14 problems, ~11.7h)

**Sliding Window** (10)
- Longest Substring Without Repeating Characters — *Medium* 🔥 (#11)
- Maximum Sum Subarray of Size K — *Easy* 🔥 (#12)
- Fruit Into Baskets (at most 2 distinct) — *Medium* 🔥 (#13)
- Minimum Window Substring — *Hard* 🔥 (#14)
- Longest Subarray with Ones after Replacement — *Medium* 🔥 (#15)
- Permutation in String — *Medium* 🔥 (#16)
- Find All Anagrams in a String — *Medium* 🔥 (#17)
- Substring with Concatenation of All Words — *Hard* (#18)
- Max Consecutive Ones III — *Medium* 🔥 (#19)
- Number of Subarrays with Product Less Than K — *Medium* 🔥 (#20)

**Sliding Window on Strings** (4)
- Longest Repeating Character Replacement — *Medium* 🔥 (#63)
- Minimum Window Substring (revisited with string focus) — *Hard* 🔥 (#64)
- Longest Substring with At Most K Distinct Characters — *Medium* 🔥 (#65)
- Longest Substring with At Most Two Distinct Characters — *Medium* 🔥 (#66)

### Hashing & Frequency Maps (11 problems, ~6.2h)

**String Simulation / Frequency Map** (4)
- Valid Anagram — *Easy* 🔥 (#51)
- Group Anagrams — *Medium* 🔥 (#52)
- Longest Palindrome (by rearrangement) — *Easy* 🔥 (#61)
- First Unique Character in a String — *Easy* 🔥 (#62)

**Hash Map / Hash Set** (7)
- Two Sum (HashMap) — *Easy* 🔥 (#442)
- Longest Consecutive Sequence — *Medium* 🔥 (#443)
- 4Sum II (count tuples) — *Medium* 🔥 (#444)
- Isomorphic Strings — *Easy* 🔥 (#445)
- Word Pattern — *Easy* 🔥 (#446)
- Bulls and Cows — *Medium* 🔥 (#447)
- Brick Wall (maximum bricks not cut) — *Medium* 🔥 (#448)


## Stage: Searcher
*Sorting, binary search, prefix sums — reduce a problem via ordering or precomputation.*

### Sorting & Interval Reasoning (15 problems, ~10.3h)

**Sorting / Interval Sweep** (5)
- Merge Intervals — *Medium* 🔥 (#41)
- Insert Interval — *Medium* 🔥 (#42)
- Meeting Rooms II (min conference rooms) — *Medium* 🔥 (#43)
- Non-overlapping Intervals — *Medium* 🔥 (#44)
- Largest Number (custom sort) — *Medium* 🔥 (#45)

**Two-Pointer Interval Sweep** (2)
- Interval List Intersections — *Medium* 🔥 (#223)
- Summary Ranges — *Easy* 🆕 (supplemental)

**Sorting Algorithms & Custom Comparators** (8)
- Merge Sort (Implement) — *Easy* 🔥 🆕 (supplemental)
- Quick Sort (Implement) — *Medium* 🔥 🆕 (supplemental)
- Sort Array By Parity II — *Easy* 🆕 (supplemental)
- Sort Array By Parity — *Easy* 🆕 (supplemental)
- Relative Sort Array — *Easy* 🆕 (supplemental)
- H-Index — *Medium* 🆕 (supplemental)
- Wiggle Sort II — *Medium* 🆕 (supplemental)
- Sort List (Merge Sort on Linked List) — *Medium* 🔥 🆕 (supplemental)

### Binary Search (25 problems, ~23.3h)

**Binary Search on Rotated Array** (2)
- Find Minimum in Rotated Sorted Array — *Medium* 🔥 (#47)
- Search in Rotated Sorted Array — *Medium* 🔥 (#48)

**Binary Search** (9)
- Binary Search (basic) — *Easy* 🔥 (#144)
- First Bad Version — *Easy* 🔥 (#145)
- Search Insert Position — *Easy* 🔥 (#146)
- Find Peak Element — *Medium* 🔥 (#148)
- Find Minimum in Rotated Sorted Array II (duplicates) — *Hard* (#149)
- Search a 2D Matrix — *Medium* 🔥 (#150)
- Search a 2D Matrix II — *Medium* 🔥 (#151)
- Kth Smallest Element in Sorted Matrix — *Medium* 🔥 (#152)
- Find K Closest Elements — *Medium* 🔥 (#153)

**Parametric Search** (14)
- Capacity to Ship Packages Within D Days — *Medium* 🔥 (#154)
- Split Array Largest Sum — *Hard* (#155)
- Koko Eating Bananas — *Medium* 🔥 (#156)
- Minimum Number of Days to Make m Bouquets — *Medium* 🔥 (#157)
- Magnetic Force Between Two Balls — *Medium* 🔥 (#158)
- Find the Smallest Divisor Given a Threshold — *Medium* 🔥 (#159)
- Allocate Minimum Number of Pages — *Medium* 🔥 (#160)
- Aggressive Cows (SPOJ classic) — *Medium* 🔥 (#161)
- Painters Partition Problem — *Hard* (#162)
- EKO — Cutting Trees (binary search on height) — *Medium* 🔥 (#163)
- Median of Two Sorted Arrays — *Hard* (#164)
- K-th Smallest Prime Fraction — *Hard* (#165)
- Find K-th Smallest Pair Distance — *Hard* (#166)
- Maximum Running Time of N Computers — *Hard* (#168)

### Prefix Sums & Range Reasoning (15 problems, ~11.5h)

**Prefix Sum / Difference Array** (10)
- Subarray Sum Equals K — *Medium* 🔥 (#21)
- Range Sum Query — Immutable — *Easy* 🔥 (#22)
- Continuous Subarray Sum (multiple of k) — *Medium* 🔥 (#23)
- Product of Array Except Self — *Medium* 🔥 (#24)
- Find Pivot Index — *Easy* 🔥 (#25)
- Count Subarrays with Equal 0s and 1s — *Medium* 🔥 (#26)
- Subarray Sums Divisible by K — *Medium* 🔥 (#27)
- Minimum Operations to Reduce X to Zero — *Medium* 🔥 (#28)
- Running Sum of 1D Array — *Easy* 🔥 (#29)
- Random Pick with Weight — *Medium* 🔥 (#30)

**Prefix Sum + Hash Map** (3)
- Subarray Sum Equals K (revisited with HashMap) — *Medium* 🔥 (#449)
- Contiguous Array (equal 0s and 1s) — *Medium* 🔥 (#450)
- Maximum Size Subarray Sum Equals k — *Medium* 🔥 (#451)

**Weighted Prefix Sampling** (2)
- Random Pick with Weight — *Medium* 🔥 (#485)
- Random Point in Non-overlapping Rectangles — *Medium* 🆕 (supplemental)


## Stage: State Builder
*Linked lists, stacks, queues, heaps — build and maintain non-trivial live state.*

### Linked Lists (27 problems, ~20.8h)

**Cycle Detection or Value-Space Search** (2)
- Find the Duplicate Number — *Medium* 🔥 (#50)
- Linked List Cycle II — *Medium* 🔥 🆕 (supplemental)

**Fast & Slow Pointers** (5)
- Linked List Cycle Detection — *Easy* 🔥 (#89)
- Linked List Cycle II (entry point) — *Medium* 🔥 (#90)
- Find the Middle of Linked List — *Easy* 🔥 (#91)
- Palindrome Linked List — *Easy* 🔥 (#93)
- Reorder List (L0→Ln→L1→Ln-1) — *Medium* 🔥 (#94)

**Linked-List Reversal / Merge** (14)
- Reverse a Linked List — *Easy* 🔥 (#95)
- Reverse Linked List II (sub-list) — *Medium* 🔥 (#96)
- Reverse Nodes in k-Group — *Hard* (#97)
- Rotate List by k — *Medium* 🔥 (#98)
- Merge Two Sorted Lists — *Easy* 🔥 (#99)
- Merge K Sorted Lists — *Hard* (#100)
- Sort List (merge sort on LL) — *Medium* 🔥 (#101)
- Partition List around value x — *Medium* 🔥 (#102)
- Remove Nth Node from End — *Medium* 🔥 (#103)
- Delete Node in a Linked List (no head) — *Easy* 🔥 (#104)
- Odd Even Linked List — *Medium* 🔥 (#105)
- Intersection of Two Linked Lists — *Easy* 🔥 (#106)
- Flatten a Multilevel Doubly Linked List — *Medium* 🔥 (#107)
- Copy List with Random Pointer — *Medium* 🔥 (#108)

**Pointer Stitching / List Design** (6)
- Add Two Numbers (LL representation) — *Medium* 🔥 (#112)
- Add Two Numbers II (no reversal) — *Medium* 🔥 (#113)
- Swap Nodes in Pairs — *Medium* 🔥 (#114)
- Remove Duplicates from Sorted List II — *Medium* 🔥 (#115)
- Insert into a Sorted Circular Linked List — *Medium* 🔥 (#117)
- Convert Binary Number in LL to Integer — *Easy* 🔥 (#118)

### Stacks & Monotonic Structures (23 problems, ~20.1h)

**Stack Parsing / Monotonic Stack** (10)
- Valid Parentheses — *Easy* 🔥 (#79)
- Minimum Remove to Make Valid Parentheses — *Medium* 🔥 (#80)
- Score of Parentheses — *Medium* 🔥 (#81)
- Decode String (k[encoded_string]) — *Medium* 🔥 (#82)
- Remove All Adjacent Duplicates in String — *Easy* 🔥 (#83)
- Remove K Digits — *Medium* 🔥 (#84)
- Basic Calculator II — *Medium* 🔥 (#85)
- Evaluate Reverse Polish Notation — *Medium* 🔥 (#86)
- Remove Duplicate Letters (lexicographically smallest) — *Medium* 🔥 (#87)
- Largest Rectangle in Histogram (string of bars) — *Hard* 🔥 (#88)

**Monotonic Stack on Linked List** (2)
- Next Greater Node in Linked List — *Medium* 🔥 (#116)
- Remove Nodes From Linked List — *Medium* 🆕 (supplemental)

**Monotonic Stack** (10)
- Next Greater Element I — *Easy* 🔥 (#119)
- Next Greater Element II (circular) — *Medium* 🔥 (#120)
- Daily Temperatures — *Medium* 🔥 (#121)
- Largest Rectangle in Histogram — *Hard* 🔥 (#122)
- Maximal Rectangle in Binary Matrix — *Hard* (#123)
- Sum of Subarray Minimums — *Medium* 🔥 (#124)
- Maximum Width Ramp — *Medium* 🔥 (#125)
- Online Stock Span — *Medium* 🔥 (#126)
- 132 Pattern — *Medium* 🔥 (#127)
- Asteroid Collision — *Medium* 🔥 (#128)

**Queue / Deque / BFS** (1)
- Max of Min for Every Window Size — *Hard* (#135)

### Queues, Deques & BFS Simulation (12 problems, ~10.5h)

**Queue / Deque / BFS** (12)
- Sliding Window Maximum — *Hard* (#129)
- First Negative in Every Window of Size K — *Medium* (#130)
- Implement Stack using Queues — *Easy* (#131)
- Implement Queue using Stacks — *Easy* (#132)
- Design Circular Queue — *Medium* (#133)
- Design Circular Deque — *Medium* (#134)
- Shortest Subarray with Sum at Least K — *Hard* (#136)
- Jump Game VI (DP + deque) — *Medium* (#137)
- Constrained Subsequence Sum — *Hard* (#138)
- Number of Recent Calls — *Easy* (#140)
- Dota2 Senate — *Medium* 🔥 (#141)
- Reveal Cards in Increasing Order — *Medium* (#142)

### Heaps & Online Order Statistics (24 problems, ~25.5h)

**Heap Selection** (2)
- Kth Largest Element in an Array — *Medium* (#46)
- Kth Smallest Element in a Sorted Matrix — *Medium* 🔥 🆕 (supplemental)

**Priority Scheduling** (2)
- Task Scheduler — *Medium* 🔥 (#139)
- Rearrange String k Distance Apart — *Hard* 🆕 (supplemental)

**Top-K Heap** (10)
- Kth Largest Element in a Stream — *Easy* 🔥 (#231)
- Top K Frequent Elements — *Medium* (#232)
- Top K Frequent Words — *Medium* (#233)
- K Closest Points to Origin — *Medium* (#234)
- Find K Pairs with Smallest Sums — *Medium* (#235)
- Kth Smallest Element in Sorted Matrix (Heap) — *Medium* 🔥 (#236)
- Sort Characters By Frequency — *Medium* (#237)
- Reorganize String — *Medium* (#238)
- Task Scheduler (Heap approach) — *Medium* 🔥 (#239)
- Maximum Frequency Stack — *Hard* (#240)

**Two Heaps / Priority Queue** (10)
- Find Median from Data Stream — *Hard* 🔥 (#241)
- Sliding Window Median — *Hard* (#242)
- IPO (Maximize Capital) — *Hard* (#243)
- Minimum Cost to Connect Sticks — *Medium* (#244)
- Smallest Range Covering Elements from K Lists — *Hard* (#245)
- Meeting Rooms III (heap-based room assignment) — *Hard* (#248)
- Employee Free Time — *Hard* (#249)
- Process Tasks Using Servers — *Medium* (#250)
- Single-Threaded CPU — *Medium* (#251)
- Furthest Building You Can Reach — *Medium* (#252)


## Stage: Recursive Thinker
*Trees, BSTs, tries — recursive structure and recursive traversal.*

### Tree Traversal & Structural Recursion (27 problems, ~22.4h)

**Tree Traversal (DFS/BFS)** (10)
- Binary Tree Inorder Traversal (iterative) — *Easy* 🔥 (#175)
- Binary Tree Preorder Traversal (iterative) — *Easy* 🔥 (#176)
- Binary Tree Postorder Traversal (iterative) — *Easy* 🔥 (#177)
- Binary Tree Level Order Traversal — *Medium* 🔥 (#178)
- Binary Tree Zigzag Level Order — *Medium* 🔥 (#179)
- Binary Tree Right Side View — *Medium* 🔥 (#180)
- Average of Levels in Binary Tree — *Easy* 🔥 (#181)
- N-ary Tree Level Order Traversal — *Medium* 🔥 (#182)
- Vertical Order Traversal — *Hard* (#183)
- Boundary Traversal of Binary Tree — *Medium* 🔥 (#184)

**Tree Recursion** (15)
- Maximum Depth of Binary Tree — *Easy* 🔥 (#185)
- Minimum Depth of Binary Tree — *Easy* 🔥 (#186)
- Diameter of Binary Tree — *Easy* 🔥 (#187)
- Balanced Binary Tree — *Easy* 🔥 (#188)
- Same Tree — *Easy* 🔥 (#189)
- Symmetric Tree — *Easy* 🔥 (#190)
- Invert Binary Tree — *Easy* 🔥 (#191)
- Count Complete Tree Nodes — *Medium* 🔥 (#192)
- Sum of Left Leaves — *Easy* 🔥 (#193)
- Path Sum — *Easy* 🔥 (#194)
- Path Sum II (all paths) — *Medium* 🔥 (#195)
- Binary Tree Maximum Path Sum — *Hard* 🔥 (#196)
- Sum Root to Leaf Numbers — *Medium* 🔥 (#197)
- Flatten Binary Tree to Linked List — *Medium* 🔥 (#198)
- Populating Next Right Pointers — *Medium* 🔥 (#199)

**Tree Serialization** (2)
- Serialize and Deserialize Binary Tree — *Hard* (#211)
- Serialize and Deserialize N-ary Tree — *Hard* 🆕 (supplemental)

### Binary Search Trees & Ordered Recursion (11 problems, ~9.6h)

**BST Invariant** (11)
- Validate Binary Search Tree — *Medium* (#200)
- Kth Smallest Element in a BST — *Medium* (#201)
- Lowest Common Ancestor of BST — *Easy* (#202)
- Lowest Common Ancestor of Binary Tree — *Medium* (#203)
- Convert Sorted Array to BST — *Easy* (#204)
- Convert BST to Greater Tree — *Medium* (#205)
- Insert into a BST — *Medium* (#206)
- Delete Node in a BST — *Medium* (#207)
- Recover Binary Search Tree (two nodes swapped) — *Hard* (#208)
- Construct BST from Preorder Traversal — *Medium* (#213)
- Two Sum IV in BST — *Easy* (#214)

### Tries & Prefix Indexes (8 problems, ~8.2h)

**Trie / Prefix Tree** (6)
- Implement Trie (Prefix Tree) — *Medium* (#225)
- Word Search II (Trie + DFS) — *Hard* (#226)
- Design Add and Search Words Data Structure — *Medium* (#227)
- Replace Words with Root (Trie) — *Medium* (#228)
- Maximum XOR of Two Numbers (Trie) — *Medium* (#229)
- Palindrome Pairs (Trie) — *Hard* (#230)

**Trie with Multiplicity** (2)
- Implement Trie with Count — *Medium* (#480)
- Replace Words — *Medium* 🆕 (supplemental)


## Stage: Navigator
*Graphs — traversal, connectivity, shortest paths, MST.*

### Graph Traversal & Connectivity (58 problems, ~59.9h)

**Grid BFS** (2)
- Rotten Oranges (BFS) — *Medium* 🔥 (#143)
- Nearest Exit from Entrance in Maze — *Medium* 🔥 🆕 (supplemental)

**Graph BFS** (15)
- Number of Islands — *Medium* 🔥 (#253)
- Max Area of Island — *Medium* 🔥 (#254)
- Flood Fill — *Easy* 🔥 (#255)
- Pacific Atlantic Water Flow — *Medium* 🔥 (#256)
- 01 Matrix (multi-source BFS) — *Medium* 🔥 (#257)
- Rotting Oranges — *Medium* 🔥 (#258)
- Walls and Gates (multi-source BFS) — *Medium* 🔥 (#259)
- Shortest Path in Binary Matrix — *Medium* 🔥 (#260)
- Snakes and Ladders — *Medium* 🔥 (#261)
- Open the Lock — *Medium* 🔥 (#262)
- Word Ladder — *Hard* (#263)
- Word Ladder II (all shortest paths) — *Hard* (#264)
- Minimum Knight Moves — *Medium* 🔥 (#265)
- Bus Routes (BFS on routes) — *Hard* (#266)
- Cut Off Trees for Golf Event — *Hard* (#267)

**Graph DFS / Union-Find** (10)
- Clone Graph — *Medium* 🔥 (#268)
- Course Schedule (cycle detection) — *Medium* 🔥 (#269)
- Course Schedule II (topological sort) — *Medium* 🔥 (#270)
- Number of Connected Components in Undirected Graph — *Medium* 🔥 (#271)
- Graph Valid Tree — *Medium* 🔥 (#272)
- Redundant Connection (Union-Find) — *Medium* 🔥 (#273)
- Accounts Merge (Union-Find / DFS) — *Medium* 🔥 (#274)
- All Paths from Source to Target — *Medium* 🔥 (#275)
- Is Graph Bipartite? — *Medium* 🔥 (#276)
- Possible Bipartition — *Medium* 🔥 (#277)

**Topological Sort** (6)
- Alien Dictionary — *Hard* (#278)
- Sequence Reconstruction — *Medium* 🔥 (#279)
- Minimum Height Trees — *Medium* 🔥 (#280)
- Find Eventual Safe States — *Medium* 🔥 (#281)
- Parallel Courses (min semesters) — *Medium* 🔥 (#282)
- Sort Items by Groups Respecting Dependencies — *Hard* (#283)

**Disjoint Set Union** (8)
- Find if Path Exists in Graph — *Easy* 🔥 (#284)
- Number of Provinces — *Medium* 🔥 (#285)
- Redundant Connection II (directed) — *Hard* (#286)
- Making a Large Island — *Hard* (#287)
- Swim in Rising Water — *Hard* (#288)
- Earliest Moment When Everyone Become Friends — *Medium* 🔥 (#289)
- Satisfiability of Equality Equations — *Medium* 🔥 (#290)
- Remove Max Number of Edges to Keep Graph Fully Traversable — *Hard* (#291)

**Shortest Path Algorithms** (10)
- Network Delay Time (Dijkstra) — *Medium* 🔥 (#292)
- Path with Maximum Probability — *Medium* 🔥 (#293)
- Cheapest Flights Within K Stops (Bellman-Ford) — *Medium* 🔥 (#294)
- Find the City with Smallest Number of Neighbors (Floyd-Warshall) — *Medium* 🔥 (#295)
- Path with Minimum Effort (Dijkstra / Binary Search) — *Medium* 🔥 (#296)
- Number of Ways to Arrive at Destination — *Medium* 🔥 (#297)
- Minimum Weighted Subgraph with Required Paths — *Hard* (#298)
- Minimum Score of a Path Between Two Cities — *Medium* 🔥 (#299)
- Reachable Nodes in Subdivided Graph — *Hard* (#300)
- K-th Shortest Path (Yen's Algorithm concept) — *Hard* (#301)

**Minimum Spanning Tree** (5)
- Min Cost to Connect All Points (Prim's) — *Medium* 🔥 (#302)
- Optimize Water Distribution in a Village — *Hard* (#303)
- Critical Connections in a Network (Bridges) — *Hard* (#304)
- Minimum Cost to Reach City with Tolls — *Medium* 🔥 (#305)
- Find Critical and Pseudo-Critical Edges in MST — *Hard* (#306)

**Grid DFS / Flood Fill** (2)
- Coloring a Border — *Medium* 🔥 (#414)
- Island Perimeter — *Easy* 🔥 🆕 (supplemental)


## Stage: Optimizer
*Dynamic programming — the largest and hardest stage by far.*

### Dynamic Programming (103 problems, ~124.1h)

**2-D Dynamic Programming** (17)
- Wildcard Matching — *Hard* 🔥 (#74)
- Regular Expression Matching — *Hard* 🔥 (#75)
- Unique Paths — *Medium* 🔥 (#322)
- Unique Paths II (with obstacles) — *Medium* 🔥 (#323)
- Minimum Path Sum in Grid — *Medium* 🔥 (#324)
- Dungeon Game (reverse DP) — *Hard* (#325)
- Maximal Square — *Medium* 🔥 (#326)
- Count Square Submatrices with All Ones — *Medium* 🔥 (#327)
- Longest Common Subsequence — *Medium* 🔥 (#328)
- Shortest Common Supersequence — *Hard* (#329)
- Edit Distance — *Hard* (#330)
- Distinct Subsequences — *Hard* (#331)
- Interleaving String — *Medium* 🔥 (#332)
- Regular Expression Matching (DP) — *Hard* 🔥 (#333)
- Wildcard Matching (DP) — *Hard* 🔥 (#334)
- Scramble String — *Hard* (#335)
- Burst Balloons (interval DP) — *Hard* (#336)

**Word-Break Dynamic Programming** (2)
- Word Break — *Medium* 🔥 (#76)
- Concatenated Words — *Hard* 🆕 (supplemental)

**Decode Dynamic Programming** (2)
- Decode Ways — *Medium* 🔥 (#78)
- Palindrome Partitioning II — *Hard* 🔥 🆕 (supplemental)

**LIS Dynamic Programming with Bisect** (2)
- Longest Increasing Subsequence (O(n log n)) — *Medium* 🔥 (#169)
- Longest String Chain — *Medium* 🆕 (supplemental)

**LIS on Ordered Envelopes** (2)
- Russian Doll Envelopes — *Hard* (#170)
- Box Stacking Problem — *Hard* 🆕 (supplemental)

**Weighted Interval Scheduling** (2)
- Maximum Profit in Job Scheduling — *Hard* (#173)
- Maximum Earnings From Taxi — *Medium* 🔥 🆕 (supplemental)

**Longest Increasing Subsequence Counting** (2)
- Number of Longest Increasing Subsequences — *Medium* 🔥 (#174)
- Longest Arithmetic Subsequence — *Medium* 🆕 (supplemental)

**Catalan Dynamic Programming** (2)
- Unique Binary Search Trees (count) — *Medium* 🔥 (#209)
- Different Ways to Add Parentheses — *Medium* 🆕 (supplemental)

**Tree Dynamic Programming** (2)
- Binary Tree Cameras — *Hard* (#212)
- House Robber III — *Medium* 🔥 🆕 (supplemental)

**LIS Counting with Range Queries** (2)
- Number of Longest Increasing Subsequences (Segment Tree) — *Medium* 🔥 (#218)
- Create Sorted Array through Instructions — *Hard* 🆕 (supplemental)

**Pointer Dynamic Programming** (2)
- Ugly Number II — *Medium* 🔥 (#246)
- Super Ugly Number — *Medium* 🔥 (#247)

**1-D Dynamic Programming** (17)
- Climbing Stairs — *Easy* 🔥 (#307)
- House Robber — *Medium* 🔥 (#308)
- House Robber II (circular) — *Medium* 🔥 (#309)
- House Robber III (tree DP) — *Medium* 🔥 (#310)
- Min Cost Climbing Stairs — *Easy* 🔥 (#311)
- Fibonacci Number — *Easy* 🔥 (#312)
- Tribonacci Number — *Easy* 🔥 (#313)
- Coin Change (minimum coins) — *Medium* 🔥 (#314)
- Coin Change II (number of ways) — *Medium* 🔥 (#315)
- Perfect Squares — *Medium* 🔥 (#316)
- Integer Break — *Medium* 🔥 (#317)
- Decode Ways — *Medium* 🔥 (#318)
- Decode Ways II — *Hard* (#319)
- Ugly Number III — *Medium* 🔥 (#320)
- N-th Tribonacci Number — *Easy* 🔥 (#321)
- Pascal's Triangle II — *Easy* 🆕 (supplemental)
- Divisor Game — *Easy* 🆕 (supplemental)

**Knapsack Dynamic Programming** (10)
- 0/1 Knapsack Problem — *Medium* 🔥 (#337)
- Unbounded Knapsack — *Medium* 🔥 (#338)
- Partition Equal Subset Sum — *Medium* 🔥 (#339)
- Target Sum (assign +/- to reach target) — *Medium* 🔥 (#340)
- Last Stone Weight II (knapsack) — *Medium* 🔥 (#341)
- Ones and Zeroes (2D knapsack) — *Medium* 🔥 (#342)
- Profitable Schemes — *Hard* (#343)
- Number of Dice Rolls with Target Sum — *Medium* 🔥 (#344)
- Combination Sum IV — *Medium* 🔥 (#345)
- Count Ways to Build Good Strings — *Medium* 🔥 (#346)

**Interval / Range Dynamic Programming** (9)
- Matrix Chain Multiplication — *Hard* (#347)
- Minimum Cost Tree from Leaf Values — *Medium* 🔥 (#348)
- Strange Printer — *Hard* (#349)
- Remove Boxes — *Hard* (#350)
- Zuma Game — *Hard* (#351)
- Minimum Cost to Merge Stones — *Hard* (#352)
- Optimal Strategy for a Game — *Medium* 🔥 (#353)
- Palindrome Partitioning II (min cuts) — *Hard* (#354)
- Palindrome Partitioning IV (3 parts) — *Hard* (#355)

**State Machine Dynamic Programming** (10)
- Best Time to Buy and Sell Stock III (at most 2 transactions) — *Hard* (#357)
- Best Time to Buy and Sell Stock IV (at most k transactions) — *Hard* (#358)
- Best Time to Buy and Sell Stock with Cooldown — *Medium* 🔥 (#359)
- Best Time to Buy and Sell Stock with Transaction Fee — *Medium* 🔥 (#360)
- Paint House — *Medium* 🔥 (#361)
- Paint House II (k colors) — *Hard* (#362)
- Paint Fence — *Medium* 🔥 (#363)
- Student Attendance Record II — *Hard* (#364)
- Coin Path (min cost with k steps) — *Hard* (#365)
- Number of Ways to Stay in the Same Place After Some Steps — *Hard* (#366)

**Bitmask Dynamic Programming** (10)
- Traveling Salesman Problem (bitmask DP) — *Hard* (#367)
- Partition to K Equal Sum Subsets — *Medium* 🔥 (#368)
- Minimum XOR Sum of Two Arrays (assignment) — *Hard* (#369)
- Maximum Students Taking Exam — *Hard* (#370)
- Stickers to Spell Word — *Hard* (#371)
- Shortest Path Visiting All Nodes (BFS + bitmask) — *Hard* (#372)
- Number of Ways to Wear Different Hats to Each Other — *Hard* (#373)
- Count Ways to Distribute Candies — *Hard* (#374)
- Maximize Score After N Operations — *Hard* (#375)
- Find the Shortest Superstring (bitmask DP) — *Hard* (#376)

**Tree / Graph Dynamic Programming** (10)
- Diameter of N-ary Tree — *Hard* (#377)
- Binary Tree Maximum Path Sum (revisited) — *Hard* 🔥 (#378)
- Maximum Sum of 3 Non-Overlapping Subarrays — *Hard* (#379)
- Cherry Pickup — *Hard* (#380)
- Cherry Pickup II (two robots) — *Hard* (#381)
- Minimum Difficulty of a Job Schedule — *Hard* (#382)
- Build Array Where You Can Find the Maximum Exactly K Comparisons — *Hard* (#383)
- Number of Music Playlists — *Hard* (#384)
- Count Vowels Permutation — *Hard* (#385)
- Minimum Cost to Cut a Stick — *Hard* (#386)


## Stage: Inventor
*Backtracking, greedy, math/bits — construct search spaces and prove correctness.*

### Backtracking & Recursive Search (33 problems, ~37.1h)

**Memoized DFS / Enumeration** (2)
- Word Break II — *Hard* (#77)
- Combination Sum III — *Medium* 🔥 🆕 (supplemental)

**Recursive Tree Construction** (2)
- Unique Binary Search Trees II (generate all) — *Medium* (#210)
- All Possible Full Binary Trees — *Medium* 🆕 (supplemental)

**Combination Backtracking** (10)
- Subsets — *Medium* (#387)
- Subsets II (with duplicates) — *Medium* (#388)
- Combinations — *Medium* (#389)
- Combination Sum — *Medium* (#390)
- Combination Sum II (each number once) — *Medium* (#391)
- Combination Sum III (exactly k numbers) — *Medium* (#392)
- Letter Combinations of a Phone Number — *Medium* (#393)
- Generate Parentheses — *Medium* (#394)
- Count Numbers with Unique Digits — *Medium* (#395)
- Beautiful Arrangement — *Medium* (#396)

**Permutation Backtracking** (10)
- Permutations — *Medium* (#397)
- Permutations II (with duplicates) — *Medium* (#398)
- Next Permutation — *Medium* (#399)
- Permutation Sequence (kth permutation) — *Hard* (#400)
- Palindrome Partitioning — *Medium* (#401)
- Word Search — *Medium* (#402)
- N-Queens — *Hard* (#403)
- N-Queens II (count solutions) — *Hard* (#404)
- Sudoku Solver — *Hard* (#405)
- Remove Invalid Parentheses — *Hard* (#406)

**Constraint Backtracking** (9)
- Expression Add Operators — *Hard* (#407)
- Restore IP Addresses — *Medium* (#408)
- Letter Tile Possibilities — *Medium* (#409)
- Splitting a String Into Descending Consecutive Values — *Medium* (#410)
- Number of Squareful Arrays — *Hard* (#411)
- Maximum Length of a Concatenated String with Unique Characters — *Medium* (#412)
- Tiling a Rectangle with the Fewest Squares — *Hard* (#413)
- Factor Combinations — *Medium* (#415)
- Construct the Lexicographically Largest Valid Sequence — *Medium* (#416)

### Greedy Optimization (27 problems, ~23.7h)

**Sorting / Greedy Choice** (2)
- Maximum Coins You Can Get — *Medium* (#356)
- Minimum Number of Taps to Open to Water a Garden — *Hard* 🆕 (supplemental)

**Interval / Scheduling Greedy** (10)
- Activity Selection / Non-overlapping Intervals — *Medium* (#417)
- Minimum Number of Platforms Required — *Medium* (#418)
- Job Sequencing Problem — *Medium* (#419)
- Fractional Knapsack — *Easy* (#420)
- N meetings in one room — *Easy* (#421)
- Assign Cookies — *Easy* (#422)
- Lemonade Change — *Easy* (#423)
- Queue Reconstruction by Height — *Medium* (#424)
- Two City Scheduling — *Medium* (#425)
- Minimum Cost to Move Chips to Same Position — *Easy* (#426)

**String / Array Greedy** (15)
- Remove K Digits (smallest number) — *Medium* 🔥 (#427)
- Largest Number After Removing k Digits (largest) — *Medium* (#428)
- Maximum Units on a Truck — *Easy* (#429)
- Minimum Deletions to Make Character Frequencies Unique — *Medium* (#430)
- Minimum Number of Flips to Make Binary String Alternating — *Medium* (#431)
- Minimum Swaps to Balance Parentheses — *Medium* (#432)
- Maximum Score from Removing Substrings — *Medium* (#433)
- Wiggle Subsequence — *Medium* (#434)
- Dota2 Senate (greedy queue) — *Medium* 🔥 (#435)
- Minimum Time to Make Rope Colorful — *Medium* (#436)
- Boats to Save People — *Medium* (#437)
- Advantage Shuffle — *Medium* (#438)
- Maximum Performance of a Team — *Hard* (#439)
- Minimize Maximum Pair Sum in Array — *Medium* (#440)
- Earliest Deadline First Scheduling — *Medium* (#441)

### Math & Bit Manipulation (22 problems, ~15.2h)

**Cycle Detection on State Space** (2)
- Happy Number (cycle in sequence) — *Easy* 🔥 (#92)
- Longest Cycle in a Graph — *Hard* 🆕 (supplemental)

**Number Theory / Arithmetic** (10)
- Count Primes (Sieve of Eratosthenes) — *Medium* (#452)
- Power of Two / Three / Four — *Easy* (#453)
- Excel Sheet Column Number — *Easy* (#454)
- Happy Number (Floyd's cycle) — *Easy* 🔥 (#455)
- Ugly Number — *Easy* (#456)
- Reverse Integer — *Medium* (#457)
- Palindrome Number — *Easy* (#458)
- Factorial Trailing Zeroes — *Medium* (#459)
- Nth Digit — *Medium* (#460)
- Super Power (modular exponentiation) — *Medium* (#461)

**Bit Manipulation** (10)
- Single Number — *Easy* (#462)
- Single Number II (bit counting) — *Medium* (#463)
- Single Number III (two unique) — *Medium* (#464)
- Number of 1 Bits (Hamming Weight) — *Easy* (#465)
- Counting Bits (0 to n) — *Easy* (#466)
- Reverse Bits — *Easy* (#467)
- Missing Number — *Easy* (#468)
- Sum of Two Integers (without + operator) — *Medium* (#469)
- Maximum XOR of Two Numbers in Array — *Medium* (#470)
- UTF-8 Validation — *Medium* (#471)


## Stage: Engineer
*Range/segment structures and system design — combine everything into designed systems.*

### Range Structures & Ordered Interval Systems (21 problems, ~27.5h)

**Fenwick Tree / Ordered Merge** (2)
- Count of Smaller Numbers After Self — *Hard* 🔥 (#49)
- Reverse Pairs — *Hard* 🔥 🆕 (supplemental)

**Range Count / Ordered Prefix** (2)
- Count of Range Sum (advanced) — *Hard* 🔥 (#147)
- Number of Pairs Satisfying Inequality — *Hard* 🆕 (supplemental)

**Fenwick Tree / Ordered Statistics** (2)
- Count of Smaller Numbers After Self (BIT/BST) — *Hard* 🔥 (#171)
- Count Number of Teams — *Medium* 🆕 (supplemental)

**Fenwick Tree / Segment Tree** (7)
- Range Sum Query — Mutable (Segment Tree / BIT) — *Medium* (#215)
- Range Minimum Query — *Medium* (#216)
- Count of Range Sum (Merge Sort / BIT) — *Hard* 🔥 (#217)
- The Skyline Problem — *Hard* (#219)
- Rectangle Area II (coordinate compression) — *Hard* (#221)
- Falling Squares — *Hard* (#222)
- Data Stream as Disjoint Intervals — *Hard* (#224)

**Interval Booking Structure** (2)
- My Calendar I, II, III — *Medium* 🔥 (#220)
- Car Pooling — *Medium* 🔥 🆕 (supplemental)

**Persistent Array Snapshot Design** (2)
- Snapshot Array — *Medium* (#495)
- Design a Stack With Increment Operation — *Medium* 🆕 (supplemental)

**Segment Tree / Ordered Range Design** (2)
- Range Module (add/remove/query ranges) — *Hard* (#501)
- Rectangle Area II — *Hard* 🆕 (supplemental)

**Segment Tree Ticket Allocation** (2)
- Booking Concert Tickets in Groups — *Hard* (#506)
- Range Sum Query - Mutable — *Medium* 🔥 🆕 (supplemental)

### System & Data Structure Design (37 problems, ~43.5h)

**O(1) Cache Design** (2)
- LRU Cache (design problem) — *Medium* (#109)
- Design Underground System — *Medium* 🆕 (supplemental)

**Frequency-Aware Cache Design** (2)
- LFU Cache — *Hard* (#110)
- Design Twitter — *Medium* 🔥 🆕 (supplemental)

**Ordered Probabilistic Structure** (2)
- Design Skiplist — *Hard* (#111)
- Random Pick with Blacklist — *Hard* 🆕 (supplemental)

**Core Data-Structure Design** (9)
- Design LRU Cache — *Medium* (#472)
- Design LFU Cache — *Hard* (#473)
- Design Twitter (top 10 tweets feed) — *Medium* (#474)
- Design a Hit Counter — *Medium* (#475)
- Design a Rate Limiter (token bucket) — *Medium* (#476)
- Design In-Memory File System — *Hard* (#477)
- Design Search Autocomplete System (Trie + heap) — *Hard* (#478)
- Design a Phone Directory — *Medium* (#479)
- Design Underground System (check-in/check-out) — *Medium* (#481)

**Randomized Data Structure** (5)
- Shuffle an Array — *Medium* (#482)
- Random Pick Index (reservoir sampling) — *Medium* (#483)
- Linked List Random Node — *Medium* (#484)
- Insert Delete GetRandom O(1) — *Medium* (#486)
- Insert Delete GetRandom O(1) — Duplicates Allowed — *Hard* (#487)

**Online / Streaming Design** (9)
- Moving Average from Data Stream — *Easy* (#488)
- Find Median from Data Stream (revisited) — *Hard* 🔥 (#489)
- Kth Largest Element in a Stream (revisited) — *Easy* 🔥 (#490)
- Design a Stack with Increment Operation — *Medium* (#491)
- Design a Stack with getMin() / getMax() — *Easy* (#492)
- Time-Based Key-Value Store — *Medium* (#493)
- Design an Ordered Stream — *Easy* (#494)
- Design a Log Aggregation System — *Medium* (#496)
- First Unique Number in Stream — *Medium* (#497)

**Advanced System Design** (8)
- Word Filter (prefix + suffix search, Trie) — *Hard* (#498)
- Exam Room (seat assignment) — *Medium* (#499)
- My Calendar I / II / III — *Medium* 🔥 (#500)
- All O'one Data Structure (O(1) min/max string freq) — *Hard* (#502)
- Design a Food Rating System — *Medium* (#503)
- Stock Price Fluctuation (max/min with updates) — *Medium* (#504)
- Find Servers That Handled Most Requests — *Hard* (#505)
- Subrectangle Queries — *Medium* (#507)

---

## How to use this guide

Work stage by stage, top to bottom, starting with the new **Foundational** stage — it's short (6 problems, ~4 hours) and everything after it assumes you can read a constraint and estimate required complexity. Within a module, problems are listed in sequence order; new 🆕 supplemental problems are appended after the original block for that pattern, so solve the original entries first, then the supplement as reinforcement. 🔥 marks `interview_frequency: high`. Supplemental problems have `original_number: null` and `"supplemental": true` in the JSON — filter on that field if you ever want to isolate just the original 507 or just the additions.

## Verification

- 557 total problems in the fixed file (507 original + 50 supplemental), all present in this doc — checked programmatically, zero missing.
- Zero duplicate IDs. Two duplicate *titles* exist ("Random Pick with Weight", "Decode Ways") — both pre-existing in the original 507, not introduced by the fix.
- Every one of the 34 single-problem patterns identified in the gap analysis now has 2 problems. The Sorting module went from 6 → 14 problems. A new Foundational stage now precedes Explorer. Graph module Easy count: 2 → 3. DP module Easy count: 5 → 7.
