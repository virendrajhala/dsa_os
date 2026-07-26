import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Stack;

// CPX-005 - Flatten Nested List Iterator (LeetCode 341).
// Learner's lazy DFS implementation, adapted with a runnable assertion harness
// for the repository's solved-means-it-ran check.
class NestedIterator implements Iterator<Integer> {

    private List<NestedInteger> nestedList;
    private Integer nextElement;
    private boolean isNextElementPrepared;
    private int currentIndex;
    private Stack<ParentContext> contextStore;

    public NestedIterator(List<NestedInteger> nestedList) {
        this.nestedList = nestedList;
        this.currentIndex = 0;
        this.contextStore = new Stack<>();
    }

    @Override
    public Integer next() {
        if (!isNextElementPrepared && !hasNext()) {
            throw new NoSuchElementException();
        }
        isNextElementPrepared = false;
        return nextElement;
    }

    @Override
    public boolean hasNext() {
        if (isNextElementPrepared) {
            return true;
        }
        return prepareNextElement();
    }

    private boolean prepareNextElement() {
        while (true) {
            if (currentIndex == nestedList.size()) {
                if (contextStore.isEmpty()) {
                    return false;
                }
                ParentContext context = contextStore.pop();
                nestedList = context.getReference();
                currentIndex = context.getNextResumableIndex();
                continue;
            }

            NestedInteger element = nestedList.get(currentIndex);
            if (element.isInteger()) {
                nextElement = element.getInteger();
                isNextElementPrepared = true;
                currentIndex++;
                return true;
            }

            contextStore.push(new ParentContext(nestedList, currentIndex + 1));
            nestedList = element.getList();
            currentIndex = 0;
        }
    }
}

class ParentContext {
    private final List<NestedInteger> reference;
    private final int nextResumableIndex;

    ParentContext(List<NestedInteger> reference, int nextResumableIndex) {
        this.reference = reference;
        this.nextResumableIndex = nextResumableIndex;
    }

    public List<NestedInteger> getReference() {
        return reference;
    }

    public int getNextResumableIndex() {
        return nextResumableIndex;
    }
}

interface NestedInteger {
    boolean isInteger();
    Integer getInteger();
    List<NestedInteger> getList();
}

class TestNestedInteger implements NestedInteger {
    private final Integer value;
    private final List<NestedInteger> list;

    TestNestedInteger(int value) {
        this.value = value;
        this.list = null;
    }

    TestNestedInteger(NestedInteger... items) {
        this.value = null;
        this.list = Arrays.asList(items);
    }

    public boolean isInteger() { return value != null; }
    public Integer getInteger() { return value; }
    public List<NestedInteger> getList() { return list; }
}

class CPX005Checks {
    private static List<Integer> flatten(NestedIterator iterator) {
        List<Integer> values = new ArrayList<>();
        while (iterator.hasNext()) {
            assert iterator.hasNext();
            values.add(iterator.next());
        }
        return values;
    }

    public static void main(String[] args) {
        List<NestedInteger> input = Arrays.asList(
            new TestNestedInteger(1),
            new TestNestedInteger(new TestNestedInteger(4), new TestNestedInteger(new TestNestedInteger(6)))
        );
        assert flatten(new NestedIterator(input)).equals(Arrays.asList(1, 4, 6));
        assert flatten(new NestedIterator(new ArrayList<>())).isEmpty();
        assert flatten(new NestedIterator(Arrays.asList(new TestNestedInteger(), new TestNestedInteger(7))))
            .equals(Arrays.asList(7));
    }
}
