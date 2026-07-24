"""CPX-004 - Min Stack (LeetCode 155).

Python port of the learner's accepted Java, kept runnable so the repo's F9
code-execution gate can verify the algorithm. The learner's original Java for
both designs is preserved verbatim in solutions/CPX-004.java.

Two O(1) push/pop/top/getMin designs:

  1. MinStack        - two stacks. The min stack frequency-compresses runs of
     equal minima into (value, frequency) nodes instead of pushing duplicates.
     O(n) auxiliary space.

  2. MinStackEncoded - one stack, O(1) auxiliary space. A new minimum is stored
     encoded as `2*newMin - prevMin`, which is always < currentMin, so a value
     below the running minimum is an encoded marker; popping it restores the
     previous minimum via `prevMin = 2*currentMin - encoded`. Java needs `long`
     here because encoded values can exceed int range; Python ints are
     arbitrary precision, so no explicit widening is required.
"""

from __future__ import annotations


class _Element:
    __slots__ = ("value", "frequency")

    def __init__(self, value: int) -> None:
        self.value = value
        self.frequency = 1


class MinStack:
    """Two-stack design with frequency-compressed minima."""

    def __init__(self) -> None:
        self._main: list[int] = []
        self._min: list[_Element] = []

    def push(self, value: int) -> None:
        self._main.append(value)
        if not self._min or value < self._min[-1].value:
            self._min.append(_Element(value))
        elif value == self._min[-1].value:
            self._min[-1].frequency += 1

    def pop(self) -> None:
        popped = self._main.pop()
        if popped == self._min[-1].value:
            if self._min[-1].frequency == 1:
                self._min.pop()
            else:
                self._min[-1].frequency -= 1

    def top(self) -> int:
        return self._main[-1]

    def get_min(self) -> int:
        return self._min[-1].value


class MinStackEncoded:
    """One-stack, O(1) auxiliary space via `2*newMin - prevMin` encoding."""

    def __init__(self) -> None:
        self._stack: list[int] = []
        self._current_min: int | None = None

    def push(self, value: int) -> None:
        if not self._stack:
            self._stack.append(value)
            self._current_min = value
        elif self._current_min is not None and value < self._current_min:
            self._stack.append(2 * value - self._current_min)  # encoded, < current_min
            self._current_min = value
        else:
            self._stack.append(value)

    def pop(self) -> None:
        top = self._stack.pop()
        if self._current_min is not None and top < self._current_min:  # encoded marker
            self._current_min = 2 * self._current_min - top
        if not self._stack:
            self._current_min = None

    def top(self) -> int:
        assert self._current_min is not None
        top = self._stack[-1]
        return self._current_min if top < self._current_min else top

    def get_min(self) -> int:
        assert self._current_min is not None
        return self._current_min


def _exercise(cls) -> None:
    # LeetCode 155 canonical sequence.
    s = cls()
    s.push(-2)
    s.push(0)
    s.push(-3)
    assert s.get_min() == -3
    s.pop()
    assert s.top() == 0
    assert s.get_min() == -2

    # Duplicate minima (edge case for the frequency-compression design).
    dup = cls()
    dup.push(0)
    dup.push(1)
    dup.push(0)
    assert dup.get_min() == 0
    dup.pop()
    assert dup.get_min() == 0
    dup.pop()
    assert dup.get_min() == 0

    # Single element.
    one = cls()
    one.push(5)
    assert one.top() == 5
    assert one.get_min() == 5

    # Nested new minima then unwind (exercises the encoded restore chain).
    nest = cls()
    for v in (5, 3, 4, 1, 2):
        nest.push(v)
    assert nest.get_min() == 1
    nest.pop()  # remove 2
    assert nest.get_min() == 1
    nest.pop()  # remove 1 -> min restored to 3
    assert nest.get_min() == 3


_exercise(MinStack)
_exercise(MinStackEncoded)
