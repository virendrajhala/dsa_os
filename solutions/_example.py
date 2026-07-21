"""Example solution file shape for solutions/<PROBLEM-ID>.py.

See solutions/README.md for the convention:
- One file per problem: solutions/<PROBLEM-ID>.py (e.g. solutions/OBS-001.py).
- Write your solution, then embed 3-5 asserts that exercise it, including at
  least one edge case. Writing the asserts is itself edge-case practice.
- Running the file (`python3 solutions/<PROBLEM-ID>.py`) must execute the
  asserts and exit 0. That is the whole contract - "solved means it ran".

This file is NOT a real problem id; it only demonstrates the shape.
"""

from __future__ import annotations


def two_sum(nums: list[int], target: int) -> list[int]:
    """Return indices of the two numbers in nums that add up to target."""

    seen: dict[int, int] = {}
    for index, value in enumerate(nums):
        complement = target - value
        if complement in seen:
            return [seen[complement], index]
        seen[value] = index
    raise ValueError("No two-sum solution exists.")


assert two_sum([2, 7, 11, 15], 9) == [0, 1]
assert two_sum([3, 2, 4], 6) == [1, 2]
assert two_sum([3, 3], 6) == [0, 1]
assert two_sum([-1, -2, -3, -4, -5], -8) == [2, 4]  # negative numbers (edge case)

try:
    two_sum([1, 2, 3], 100)
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError when no two-sum solution exists.")


if __name__ == "__main__":
    print("solutions/_example.py: all asserts passed.")
