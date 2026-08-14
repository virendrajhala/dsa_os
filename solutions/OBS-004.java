class Main {
    public static void main(String[] args) {
        assert maxProfit(new int[] {7, 1, 5, 3, 6, 4}) == 7;
        assert maxProfit(new int[] {}) == 0;
        assert maxProfit(new int[] {5}) == 0;
        assert maxProfit(new int[] {7, 6, 4, 3, 1}) == 0;
        assert maxProfit(new int[] {1, 2, 3, 4, 5}) == 4;
    }

    static int maxProfit(int[] prices) {
        int profit = 0;

        for (int i = 0; i < prices.length - 1; i++) {
            if (prices[i + 1] > prices[i]) {
                profit += prices[i + 1] - prices[i];
            }
        }

        return profit;
    }
}
