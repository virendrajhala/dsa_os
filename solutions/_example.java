// Example Java solution file shape for solutions/<PROBLEM-ID>.java.
//
// See solutions/README.md. Same contract as the Python files: write your
// solution, then embed 3-5 asserts (including at least one edge case) that
// exercise it. The gate compiles the file and runs it with assertions on
// (`javac` then `java -ea`), so it must exit 0.
//
// Two Java rules to keep the gate happy:
//   1. No `public` top-level class (the file is named after the problem id,
//      e.g. CPX-004.java, and a hyphen is not a legal Java class name). Use
//      package-private classes.
//   2. Exactly one class must declare `public static void main(String[])` —
//      that is where your asserts run. This file is NOT a real problem id.

class Main {
    public static void main(String[] args) {
        assert twoSum(new int[] {2, 7, 11, 15}, 9)[0] == 0;
        assert twoSum(new int[] {3, 2, 4}, 6)[1] == 2;
        assert twoSum(new int[] {3, 3}, 6)[0] == 0;              // duplicates
        assert twoSum(new int[] {-3, 4, 1}, -2)[1] == 2;         // negatives (edge case)
    }

    static int[] twoSum(int[] nums, int target) {
        java.util.Map<Integer, Integer> seen = new java.util.HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            if (seen.containsKey(complement)) {
                return new int[] {seen.get(complement), i};
            }
            seen.put(nums[i], i);
        }
        throw new IllegalArgumentException("No two-sum solution exists.");
    }
}
