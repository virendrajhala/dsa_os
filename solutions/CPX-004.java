// CPX-004 - Min Stack (LeetCode 155). Learner's accepted Java, both designs.
// The repo's F9 gate runs the Python port in solutions/CPX-004.py; these are
// the original accepted implementations, kept for reference.

// 1. Two-stack solution (frequency-compressed min stack). O(n) auxiliary space.
class MinStack {

    Stack<Element> minStack;
    Stack<Integer> mainStack;

    public MinStack() {
        minStack = new Stack<>();
        mainStack = new Stack<>();
    }

    public void push(int value) {
        mainStack.push(value);
        if (minStack.isEmpty() || value < minStack.peek().value) {
            minStack.push(new Element(value));
        } else if (value == minStack.peek().value) {
            Element element = minStack.peek();
            element.frequency += 1;
        }
    }

    public void pop() {
        int poppedValue = mainStack.pop();
        if (poppedValue == minStack.peek().value) {
            if (minStack.peek().frequency == 1) {
                minStack.pop();
            } else {
                Element element = minStack.peek();
                element.frequency -= 1;
            }
        }
    }

    public int top() {
        return mainStack.peek();
    }

    public int getMin() {
        return minStack.peek().value;
    }
}

class Element {
    int value;
    int frequency;

    public Element(int value) {
        this.value = value;
        this.frequency = 1;
    }
}

// 2. O(1) auxiliary-space encoded solution. `encoded = 2*newMin - prevMin` is
// always < currentMin; long arithmetic avoids int overflow in the encoding.
class MinStackEncoded {

    private Stack<Long> stack;
    private long currentMin;

    public MinStackEncoded() {
        stack = new Stack<>();
        currentMin = Long.MAX_VALUE;
    }

    public void push(int value) {
        if (stack.isEmpty()) {
            stack.push((long) value);
            currentMin = value;
        } else {
            if (value < currentMin) {
                long encodedValue = 2L * value - currentMin;
                stack.push(encodedValue);
                currentMin = value;
            } else {
                stack.push((long) value);
            }
        }
    }

    public void pop() {
        long topElement = stack.pop();

        if (topElement < currentMin) {
            currentMin = 2 * currentMin - topElement;
        }

        if (stack.isEmpty()) {
            currentMin = Long.MAX_VALUE;
        }
    }

    public int top() {
        long topElement = stack.peek();

        if (topElement < currentMin) {
            return (int) currentMin;
        }

        return (int) topElement;
    }

    public int getMin() {
        return (int) currentMin;
    }
}
