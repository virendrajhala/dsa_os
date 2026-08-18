class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        assert s.canJump(new int[] {2, 3, 1, 1, 4});
        assert !s.canJump(new int[] {3, 2, 1, 0, 4});
        assert s.canJump(new int[] {0});
        assert !s.canJump(new int[] {1, 0, 1});
    }
}

class Solution {
    public boolean canJump(int[] nums) {
        int leftMostGoodIndex = nums.length - 1;
        for(int i = nums.length - 2;i >= 0;i--){
            if(i + nums[i] >= leftMostGoodIndex){
                leftMostGoodIndex = i;
            }
        }

        return leftMostGoodIndex == 0;
    }
}
