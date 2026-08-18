class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        // Official LeetCode #45 examples (from the problem statement).
        assert s.jump(new int[] {2, 3, 1, 1, 4}) == 2;
        assert s.jump(new int[] {2, 3, 0, 1, 4}) == 2;
        assert s.jump(new int[] {0}) == 0;
        assert s.jump(new int[] {2, 3, 1, 2, 4, 3}) == 3;
    }
}

class Solution {
    public int jump(int[] nums) {
        int currentRegionEnd = 0, maxReachableIdx = 0, jumps = 0;
        for(int i = 0;i < nums.length - 1;i++){
            maxReachableIdx = Math.max(maxReachableIdx,i + nums[i]);
            if(currentRegionEnd == i){
                // region ends here,update next region
                currentRegionEnd = maxReachableIdx;
                jumps++;
            }
        }

        return jumps;
    }
}
