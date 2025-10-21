# Recursive While Loop Implementation

This directory demonstrates the **recursive approach** to implementing while loops in the Python Workflow Definition syntax.

## Overview

The recursive approach leverages Python's native recursion to implement while loops **without requiring any schema changes**. Instead of adding a new node type, recursive functions call themselves until a termination condition is met.

## Key Concept

```python
def while_(n, m):
    if m >= n:       # Base case: condition met
        return m
    m += 1           # Update state
    return while_(n=n, m=m)  # Recursive call
```

This translates to a workflow with a single `function` node - no special "while" node needed!

## Files

### Workflow Functions
- **workflow.py** - Recursive function implementations:
  - `while_loop()` - Simple counter
  - `while_loop_with_accumulator()` - Collecting results
  - `fibonacci_recursive()` - Fibonacci sequence generator
  - `converge_to_zero()` - Iterative convergence algorithm

### Workflow Definitions
1. **simple_recursive.json** - Basic counter (m → n)
2. **recursive_accumulator.json** - Accumulator pattern example
3. **fibonacci.json** - Generate Fibonacci sequence

### Testing
- **test_recursive.py** - Comprehensive test suite

## Workflow Schema

**No schema changes required!** Uses standard nodes:

```json
{
  "version": "0.1.0",
  "nodes": [
    {"id": 0, "type": "input", "name": "n", "value": 10},
    {"id": 1, "type": "input", "name": "m", "value": 0},
    {"id": 2, "type": "function", "value": "workflow.while_loop"},
    {"id": 3, "type": "output", "name": "result"}
  ],
  "edges": [
    {"source": 0, "target": 2, "targetPort": "n"},
    {"source": 1, "target": 2, "targetPort": "m"},
    {"source": 2, "target": 3}
  ]
}
```

## Examples

### Example 1: Simple Counter

**Goal**: Count from 0 to 10

**Function** (`workflow.py`):
```python
def while_loop(n, m):
    if m >= n:
        return m
    m = m + 1
    return while_loop(n=n, m=m)
```

**Execution**:
```python
while_loop(n=10, m=0)
# Calls: while_loop(10, 0) → while_loop(10, 1) → ... → while_loop(10, 10) → 10
```

**Workflow**: `simple_recursive.json`

### Example 2: Accumulator Pattern

**Goal**: Collect all values from 0 to n-1 in a list

**Function**:
```python
def while_loop_with_accumulator(n, m, accumulator):
    if m >= n:
        return {"m": m, "accumulator": accumulator}

    new_accumulator = accumulator + [m]
    m = m + 1

    return while_loop_with_accumulator(n=n, m=m, accumulator=new_accumulator)
```

**Execution**:
```python
while_loop_with_accumulator(n=5, m=0, accumulator=[])
# Result: {"m": 5, "accumulator": [0, 1, 2, 3, 4]}
```

**Workflow**: `recursive_accumulator.json`

### Example 3: Fibonacci Sequence

**Goal**: Generate first N Fibonacci numbers

**Function**:
```python
def fibonacci_recursive(n, current, a, b, results):
    if current >= n:
        return {"results": results, "count": current}

    next_fib = a + b
    new_results = results + [b]

    return fibonacci_recursive(
        n=n, current=current + 1, a=b, b=next_fib, results=new_results
    )
```

**Execution**:
```python
fibonacci_recursive(n=10, current=0, a=0, b=1, results=[])
# Result: {"results": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55], "count": 10}
```

**Workflow**: `fibonacci.json`

### Example 4: Convergence Algorithm

**Goal**: Reduce value until below threshold

**Function**:
```python
def converge_to_zero(value, threshold, iterations):
    if abs(value) <= threshold:
        return {"value": value, "iterations": iterations, "converged": True}

    if iterations >= 1000:  # Safety limit
        return {"value": value, "iterations": iterations, "converged": False}

    new_value = value * 0.5
    return converge_to_zero(value=new_value, threshold=threshold, iterations=iterations + 1)
```

**Use case**: Simulates iterative scientific algorithms that converge to a solution.

## How It Works

### 1. Recursion Pattern

Every recursive while loop follows this structure:

```python
def recursive_loop(condition_vars, state_vars):
    # Base case: check termination condition
    if <condition_met>:
        return <final_result>

    # Recursive case: update state
    <update_state_vars>

    # Recurse with updated state
    return recursive_loop(condition_vars, updated_state_vars)
```

### 2. State Management

State flows through function parameters and return values:

**Input → Function → Recursive Call → ... → Output**

Each iteration:
1. Receives current state as parameters
2. Checks termination condition
3. Updates state variables
4. Passes updated state to next call (itself)

### 3. Workflow Execution

The workflow engine executes the function node, which:
1. Receives initial inputs from input nodes
2. Executes the recursive function
3. Returns final result to output node

**Key insight**: The recursion happens **inside** the function, not in the workflow graph!

## Advantages ✅

### 1. **No Schema Changes**
- Uses existing `function` nodes
- Works with current workflow definition (v0.1.0)
- No new validation rules needed
- Backward compatible

### 2. **Natural Functional Style**
- Pure functions with immutable data
- Easy to reason about
- Testable without workflow engine
- Follows functional programming paradigms

### 3. **Explicit State**
- All state passed through parameters
- No hidden state or side effects
- Clear data flow
- Easy to debug

### 4. **Backend Compatibility**
- Functions execute in any Python environment
- No special loop constructs needed
- Works with AiiDA, Jobflow, pure Python, etc.
- No backend-specific translation required

### 5. **Type Safety**
- Standard Python type hints work
- IDEs provide autocomplete
- Static analysis tools work out-of-the-box

## Disadvantages ❌

### 1. **Python Recursion Limit**
- Default limit: ~1000 recursive calls
- Can be increased but risky (stack overflow)
- Not suitable for deeply iterative algorithms

**Example**:
```python
# This will hit recursion limit!
while_loop(n=2000, m=0)  # RecursionError
```

**Workaround**:
```python
import sys
sys.setrecursionlimit(10000)  # Dangerous!
```

### 2. **Stack Memory Usage**
- Each call consumes stack space
- Large iteration counts risk stack overflow
- Memory inefficient compared to loops

### 3. **Performance Overhead**
- Function call overhead per iteration
- Slower than native loops
- Not suitable for tight inner loops

### 4. **Visualization Challenges**
- Graph doesn't show the loop structure
- Appears as single function node
- Hard to understand iteration count from graph
- No cycle visualization

### 5. **Limited Error Messages**
- RecursionError doesn't show which iteration failed
- Hard to debug deep recursion issues
- No built-in iteration tracking

### 6. **No Early Termination**
- Can't implement `break` easily
- Must reach base case or hit recursion limit
- Difficult to handle exceptional conditions

## Comparison with While Node Approach

| Aspect | Recursive Approach | While Node Approach |
|--------|-------------------|---------------------|
| Schema changes | ✅ None | ❌ New node type needed |
| Max iterations | ❌ ~1000 (recursion limit) | ✅ Configurable (1000+ fine) |
| Memory usage | ❌ Stack grows with iterations | ✅ Constant memory |
| Performance | ❌ Function call overhead | ✅ Native loop performance |
| Visualization | ❌ No loop structure visible | ✅ Clear loop node in graph |
| Functional style | ✅ Pure functions | ⚠️ Hybrid (functions + graph structure) |
| Backend support | ✅ Works everywhere | ⚠️ Requires backend implementation |
| Debugging | ❌ Deep call stacks | ✅ Iteration tracking possible |
| Type safety | ✅ Standard Python types | ✅ Pydantic validation |
| Safety limits | ❌ Implicit (recursion limit) | ✅ Explicit `maxIterations` |

## When to Use Recursive Approach

### ✅ Good For:
- **Shallow iterations** (< 100 iterations)
- **Algorithms naturally recursive** (tree traversal, divide-and-conquer)
- **Functional workflow style** preferred
- **No schema modifications** allowed
- **Quick prototyping** without backend changes

### ❌ Avoid For:
- **Deep iterations** (> 1000 iterations)
- **Performance-critical** tight loops
- **Large state** carried through iterations
- **Production workflows** with unknown iteration counts
- **Workflows needing visualization** of loop structure

## Running the Examples

### Direct Function Execution

```bash
cd example_workflows/while_loop_recursive
python3
```

```python
>>> import workflow
>>> workflow.while_loop(n=10, m=0)
10

>>> workflow.while_loop_with_accumulator(n=5, m=0, accumulator=[])
{'m': 5, 'accumulator': [0, 1, 2, 3, 4]}

>>> workflow.fibonacci_recursive(n=10, current=0, a=0, b=1, results=[])
{'results': [1, 1, 2, 3, 5, 8, 13, 21, 34, 55], 'count': 10}
```

### Running Tests

```bash
cd example_workflows/while_loop_recursive
python test_recursive.py
```

**Expected Output**:
- ✅ All workflow JSON files load successfully
- ✅ All recursive functions execute correctly
- ⚠️ Recursion depth test shows limitation at ~1000 iterations
- ✅ Schema validation passes (no changes needed)

### Loading Workflows

```python
from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow

wf = PythonWorkflowDefinitionWorkflow.load_json_file("simple_recursive.json")
print(wf)
```

## Implementation Notes

### State Passing Pattern

Always return updated state as dict to support multi-value state:

```python
# ✅ Good: Return dict for multiple state vars
def loop_func(a, b, c):
    if <condition>:
        return {"a": a, "b": b, "c": c}
    return loop_func(a=a+1, b=b*2, c=c-1)

# ❌ Bad: Can't return multiple values easily
def loop_func(a, b):
    if <condition>:
        return a, b  # How to route in workflow?
    return loop_func(a+1, b*2)
```

### Safety Limits

Always include maximum iteration guards:

```python
def safe_loop(n, m, max_iter=1000):
    if m >= n or m >= max_iter:  # Safety check
        return m
    return safe_loop(n, m+1, max_iter)
```

### Immutable Updates

Use immutable data structures to avoid state bugs:

```python
# ✅ Good: Create new list
new_list = old_list + [item]

# ❌ Bad: Mutate list (breaks functional purity)
old_list.append(item)
```

## Future Enhancements

### Tail Call Optimization

Python doesn't optimize tail calls, but workflow backends could:

```python
# This is tail-recursive (could be optimized to loop)
def while_loop(n, m):
    if m >= n:
        return m
    return while_loop(n, m+1)  # Tail call
```

**Backend could transform to**:
```python
def while_loop_optimized(n, m):
    while m < n:
        m += 1
    return m
```

### Trampoline Pattern

Implement explicit trampoline to avoid recursion limits:

```python
def while_loop_trampoline(n, m):
    while callable(result := _while_loop_step(n, m)):
        result = result()
    return result

def _while_loop_step(n, m):
    if m >= n:
        return m
    return lambda: _while_loop_step(n, m+1)
```

### Graph Cycle Detection

Future workflow validators could:
1. Detect potential recursion (function calls itself)
2. Warn about deep recursion risks
3. Suggest while node approach for deep iterations

## Conclusion

The recursive approach offers a **zero-schema-change** solution for while loops, leveraging Python's native recursion. It's ideal for:
- Shallow iterations (< 100)
- Functional programming style
- Quick prototyping
- Naturally recursive algorithms

However, for production workflows with deep iterations or performance requirements, the **while node approach** (see `example_workflows/while_loop/`) is recommended.

## Related Examples

- **While Node Approach**: `example_workflows/while_loop/` - Explicit while node with nested workflows
- **Arithmetic Examples**: `example_workflows/arithmetic/` - Basic function chaining
- **Quantum Espresso**: `example_workflows/quantum_espresso/` - Complex workflows with parallelism

## Testing

Run the test suite to validate:

```bash
cd example_workflows/while_loop_recursive
python test_recursive.py
```

Tests cover:
- Workflow JSON validation
- Recursive function execution
- Recursion depth limits
- Schema compatibility

All tests should pass except recursion depth test (demonstrates limitation).
