// OBS-003 - Best Time to Buy and Sell Stock (LeetCode 121).
// Learner's one-pass minimum-prefix solution with a runnable assertion harness.
class Solution {
    public int maxProfit(int[] prices) {
        int minPrice = prices[0];
        int maxProfit = 0;

        for (int i = 1; i < prices.length; i++) {
            maxProfit = Math.max(maxProfit, prices[i] - minPrice);
            if (prices[i] < minPrice) {
                minPrice = prices[i];
            }
        }

        return maxProfit;
    }
}

class OBS003Checks {
    public static void main(String[] args) {
        Solution solution = new Solution();

        assert solution.maxProfit(new int[] {7, 1, 5, 3, 6, 4}) == 5;
        assert solution.maxProfit(new int[] {7, 6, 4, 3, 1}) == 0;
        assert solution.maxProfit(new int[] {1, 1, 2, 2, 3, 3, 4, 4}) == 3;
        assert solution.maxProfit(new int[] {5}) == 0;
        assert solution.maxProfit(new int[] {2, 4, 1}) == 2;
    }
}
