import java.util.Arrays;

// CPX-006 - Design HashMap (LeetCode 706).
// Accepted direct-addressing solution for LeetCode's bounded key range.
class MyHashMap {

    private final int[] map;

    public MyHashMap() {
        map = new int[1000001];
        Arrays.fill(map, -1);
    }

    public void put(int key, int value) {
        map[key] = value;
    }

    public int get(int key) {
        return map[key];
    }

    public void remove(int key) {
        map[key] = -1;
    }
}

class CPX006Checks {

    public static void main(String[] args) {
        MyHashMap hashMap = new MyHashMap();
        assert hashMap.get(1) == -1;

        hashMap.put(1, 1);
        hashMap.put(2, 2);
        assert hashMap.get(1) == 1;
        assert hashMap.get(3) == -1;

        hashMap.put(2, 1);
        assert hashMap.get(2) == 1;

        hashMap.put(0, 0);
        assert hashMap.get(0) == 0;

        hashMap.remove(2);
        assert hashMap.get(2) == -1;

        hashMap.put(1000000, 42);
        assert hashMap.get(1000000) == 42;
    }
}
