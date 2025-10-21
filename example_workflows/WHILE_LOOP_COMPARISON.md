# While Loop Implementation Comparison

This document compares two approaches for implementing while loops in Python Workflow Definition.

## Approaches

### 1. **While Node Approach**
**Location**: `example_workflows/while_loop/`
**Branch**: (separate branch with WhileNode implementation)

Adds a new `PythonWorkflowDefinitionWhileNode` to the schema with support for:
- Function-based or expression-based conditions
- Function-based or nested workflow bodies
- Safe expression evaluation
- Explicit iteration limits

### 2. **Recursive Approach**
**Location**: `example_workflows/while_loop_recursive/`
**Branch**: `main` (no schema changes)

Uses native Python recursion within function nodes - no new node types needed.

---

## Quick Comparison

| Feature | While Node | Recursive |
|---------|-----------|-----------|
| **Schema Changes** | ❌ New node type | ✅ None required |
| **Max Iterations** | ✅ 1000+ | ❌ ~1000 (recursion limit) |
| **Memory Efficiency** | ✅ Constant | ❌ Stack grows |
| **Performance** | ✅ Native loop | ❌ Function call overhead |
| **Visualization** | ✅ Loop node visible | ❌ Just function node |
| **Backend Support** | ⚠️ Needs implementation | ✅ Works everywhere |
| **Debugging** | ✅ Iteration tracking | ❌ Deep call stacks |
| **Functional Style** | ⚠️ Hybrid | ✅ Pure functions |

---

## Detailed Comparison

### Schema & Implementation

#### While Node Approach
```json
{
  "id": 2,
  "type": "while",
  "conditionExpression": "m < n",
  "bodyFunction": "workflow.increment_m",
  "maxIterations": 1000
}
```

**Requires**:
- New `PythonWorkflowDefinitionWhileNode` class
- Expression evaluator (`expression_eval.py`)
- Updated discriminated union
- Backend execution support

#### Recursive Approach
```json
{
  "id": 2,
  "type": "function",
  "value": "workflow.while_loop"
}
```

**Requires**:
- Nothing! Standard function node
- Recursive function implementation
- No backend changes

---

### Code Examples

#### Example: Count from 0 to 10

**While Node Approach**:

*Workflow JSON* (`while_loop/simple_counter_expression.json`):
```json
{
  "nodes": [
    {"id": 0, "type": "input", "name": "n", "value": 10},
    {"id": 1, "type": "input", "name": "m", "value": 0},
    {"id": 2, "type": "while",
     "conditionExpression": "m < n",
     "bodyFunction": "workflow.increment_m"},
    {"id": 3, "type": "output", "name": "result"}
  ]
}
```

*Python* (`while_loop/workflow.py`):
```python
def increment_m(n, m):
    return {"n": n, "m": m + 1}
```

**Recursive Approach**:

*Workflow JSON* (`while_loop_recursive/simple_recursive.json`):
```json
{
  "nodes": [
    {"id": 0, "type": "input", "name": "n", "value": 10},
    {"id": 1, "type": "input", "name": "m", "value": 0},
    {"id": 2, "type": "function", "value": "workflow.while_loop"},
    {"id": 3, "type": "output", "name": "result"}
  ]
}
```

*Python* (`while_loop_recursive/workflow.py`):
```python
def while_loop(n, m):
    if m >= n:
        return m
    return while_loop(n=n, m=m+1)
```

---

### Nested Workflows

#### While Node Approach ✅

Supports complex multi-step loop bodies:

```json
{
  "type": "while",
  "conditionFunction": "check_converged",
  "bodyWorkflow": {
    "nodes": [
      {"id": 100, "type": "function", "value": "calculate_energy"},
      {"id": 101, "type": "function", "value": "calculate_forces"},
      {"id": 102, "type": "function", "value": "update_geometry"}
    ],
    "edges": [...]
  }
}
```

#### Recursive Approach ⚠️

Must chain functions manually:

```python
def optimization_step(structure, threshold):
    energy = calculate_energy(structure)
    forces = calculate_forces(structure, energy)
    new_structure = update_geometry(structure, forces)

    if converged(energy, threshold):
        return new_structure

    return optimization_step(new_structure, threshold)
```

---

### Condition Specification

#### While Node Approach

**Option 1: Function**
```json
"conditionFunction": "workflow.is_less_than"
```

**Option 2: Expression** (safe eval)
```json
"conditionExpression": "m < n and m % 2 == 0"
```

**Supported in expressions**:
- Comparison: `<`, `<=`, `>`, `>=`, `==`, `!=`
- Boolean: `and`, `or`, `not`
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `**`
- Subscript: `data[0]`, `dict["key"]`

**Blocked**:
- Function calls
- Imports
- Dunder attributes

#### Recursive Approach

Condition is Python code in the function:

```python
def while_loop(n, m):
    if m >= n:  # Any Python expression
        return m
    return while_loop(n, m+1)
```

More flexible but no validation.

---

### Safety & Limits

#### While Node Approach

**Built-in safety**:
```json
"maxIterations": 1000  // Explicit limit
```

- Configurable per workflow
- Prevents infinite loops
- Clear error messages
- Can be set high (10000+) safely

#### Recursive Approach

**Implicit Python limit**:
```python
import sys
sys.getrecursionlimit()  # ~1000
```

- Hard limit around 1000
- RecursionError if exceeded
- Can increase (risky)
- Stack overflow danger

---

### Execution Performance

#### While Node Approach

Backends can optimize to native loops:

```python
# Backend can transform to:
result = initial_state
for _ in range(maxIterations):
    if not condition(result):
        break
    result = body(result)
```

**Performance**: Near-native loop speed

#### Recursive Approach

Every iteration is a function call:

```python
# Each call adds stack frame
while_loop(n, m) → while_loop(n, m+1) → while_loop(n, m+2) → ...
```

**Performance**: ~10-100x slower than loops

---

### Visualization

#### While Node Approach

Graph shows clear loop structure:

```
┌──────────┐
│ Input: n │───┐
└──────────┘   │
               ├──► ┌──────────────┐      ┌────────┐
┌──────────┐   │    │ While Loop   │─────►│ Output │
│ Input: m │───┘    │ (condition)  │      └────────┘
└──────────┘        │ (body)       │
                    │ max: 1000    │
                    └──────────────┘
```

Clear that there's a loop, condition, and body.

#### Recursive Approach

Graph shows single function:

```
┌──────────┐
│ Input: n │───┐
└──────────┘   │
               ├──► ┌──────────────┐      ┌────────┐
┌──────────┐   │    │ Function     │─────►│ Output │
│ Input: m │───┘    │ while_loop   │      └────────┘
└──────────┘        └──────────────┘
```

No indication of looping behavior from graph.

---

### Backend Compatibility

#### While Node Approach

**Requires backend implementation**:

- **Pure Python**: Execute condition + body in loop
- **AiiDA WorkGraph**: Translate to AiiDA while construct (if available)
- **Jobflow**: Map to Jobflow iteration pattern
- **ExecutorLib**: Parallel iteration support

Each backend needs custom handling.

#### Recursive Approach

**Works immediately**:

All backends already execute function nodes. Recursion happens inside Python - backends don't need to know.

---

### Debugging

#### While Node Approach

Can provide rich debugging info:

```python
# Workflow engine can track:
- Current iteration number
- State at each iteration
- Time per iteration
- Convergence history
```

Example error:
```
WhileLoopError: Maximum iterations (1000) exceeded
  Node ID: 2
  Last state: {"m": 1000, "n": 10000}
  Suggestion: Increase maxIterations or check condition
```

#### Recursive Approach

Standard Python stack trace:

```python
RecursionError: maximum recursion depth exceeded
  File "workflow.py", line 8, in while_loop
    return while_loop(n=n, m=m+1)
  File "workflow.py", line 8, in while_loop
    return while_loop(n=n, m=m+1)
  ... (996 more lines)
```

Harder to debug which iteration failed.

---

## Use Case Recommendations

### Use While Node When:

✅ **Deep iterations** (> 100)
- Geometry optimization (100s of steps)
- Convergence algorithms
- Long-running simulations

✅ **Visualization matters**
- Workflow needs to be human-readable
- Graph structure should show logic
- Documentation requires clear diagrams

✅ **Production workflows**
- Unknown iteration counts
- Safety limits critical
- Performance matters

✅ **Complex loop bodies**
- Multi-step iterations
- Nested workflows needed
- Parallel operations in body

✅ **Expression conditions**
- Simple conditions like `error < threshold`
- Don't want separate function for condition
- Inline expressions clearer

### Use Recursive Approach When:

✅ **Shallow iterations** (< 50)
- Small search spaces
- Quick iterations
- Known small bounds

✅ **No schema changes allowed**
- Working with existing infrastructure
- Can't modify workflow definition
- Backward compatibility required

✅ **Functional style preferred**
- Pure functional programming
- Immutable data patterns
- No side effects

✅ **Quick prototyping**
- Experimental workflows
- Rapid iteration
- Minimal setup

✅ **Naturally recursive algorithms**
- Tree traversal
- Divide-and-conquer
- Algorithms already recursive

---

## Migration Path

### From Recursive → While Node

Easy migration when you hit recursion limits:

**Before** (recursive):
```python
def while_loop(n, m):
    if m >= n:
        return m
    return while_loop(n=n, m=m+1)
```

**After** (while node):

*Workflow*:
```json
{
  "type": "while",
  "conditionExpression": "m < n",
  "bodyFunction": "workflow.increment_m"
}
```

*Function*:
```python
def increment_m(n, m):
    return {"n": n, "m": m + 1}
```

### From While Node → Recursive

For simpler workflows:

**Before** (while node + separate condition/body):
```json
{"type": "while", "conditionFunction": "...", "bodyFunction": "..."}
```

**After** (single recursive function):
```python
def combined_loop(...):
    if <condition>:
        return result
    return combined_loop(<updated_state>)
```

---

## Recommendation

**For this project**: Implement **both approaches** on separate branches:

1. **While Node branch**: Full-featured, production-ready
   - Use for: complex workflows, deep iterations, visualization
   - Requires: backend implementation work

2. **Recursive branch** (main): Zero-overhead, immediate use
   - Use for: simple workflows, prototyping, backward compatibility
   - Requires: nothing!

**Users can choose** based on their needs:
- Start with recursive (works now)
- Migrate to while node when needed (better performance, deep iterations)

---

## Examples Summary

### While Node Examples (`while_loop/`)
1. **simple_counter.json** - Function condition + function body
2. **simple_counter_expression.json** - Expression condition + function body
3. **nested_optimization.json** - Nested workflow body (geometry optimization)

### Recursive Examples (`while_loop_recursive/`)
1. **simple_recursive.json** - Basic counter
2. **recursive_accumulator.json** - Accumulator pattern
3. **fibonacci.json** - Fibonacci sequence

---

## Testing

### While Node
```bash
cd example_workflows/while_loop
python test_while_node.py
```

Tests:
- Schema validation
- JSON loading
- Expression evaluation safety

### Recursive
```bash
cd example_workflows/while_loop_recursive
python test_recursive.py
```

Tests:
- Workflow loading
- Function execution
- Recursion limits
- Schema compatibility

---

## Conclusion

Both approaches are valid:

| Priority | Recommended Approach |
|----------|---------------------|
| **Quick start** | Recursive (no changes) |
| **Production** | While Node (robust) |
| **Performance** | While Node (faster) |
| **Simplicity** | Recursive (less code) |
| **Flexibility** | While Node (nested workflows) |
| **Compatibility** | Recursive (works everywhere) |

**Ideal solution**: Support both, let users choose based on use case.
