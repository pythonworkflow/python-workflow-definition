# While Loop Export Approaches: Design Document

## Problem Statement

### The Challenge

We want to support a workflow that allows users to:
1. **Create** workflows using the aiida-workgraph Python API (natural, Pythonic)
2. **Export** workflows to a JSON interchange format (machine-readable)
3. **Import** workflows into other workflow managers (interoperability)

The fundamental tension is: **How do we represent runtime constructs (like recursive `@task.graph` while loops) in a static JSON format?**

### Specific Issue: While Loops in AiiDA-WorkGraph

In aiida-workgraph, while loops are typically implemented using recursive `@task.graph` functions:

```python
def condition(x, limit):
    return limit > x

@task
def function_body(x):
    return x + 1

@task.graph()
def abstract_while_aiida(x, limit):
    if not condition(x=x, limit=limit):
        return x
    x = function_body(x=x).result
    return abstract_while_aiida(x=x, limit=limit)  # Recursive call

wg = abstract_while_aiida.build(x=0, limit=5)
```

When you call `.build()`, WorkGraph creates a graph structure containing:
- `graph_inputs`: Special node representing the graph's input interface
- `graph_outputs`: Special node representing the graph's output interface
- Task nodes (e.g., `function_body`)
- The recursion is "baked into" the graph structure itself through the recursive call

**Problem**: This graph structure doesn't explicitly contain a "while loop" node - it's a pattern encoded in the recursion. How do we export this to our JSON format which has an explicit `"type": "while"` node?

### The JSON While Loop Format

Our target JSON format has an explicit while loop node type:

```json
{
  "version": "0.1.0",
  "nodes": [
    {
      "id": 0,
      "type": "while",
      "conditionFunction": "module.condition",
      "bodyFunction": "module.function_body",
      "maxIterations": 1000
    }
  ],
  "edges": []
}
```

Or with nested workflows:

```json
{
  "id": 0,
  "type": "while",
  "conditionFunction": "module.condition",
  "bodyWorkflow": {
    "version": "0.1.0",
    "nodes": [
      {"id": 100, "type": "input", "name": "x"},
      {"id": 101, "type": "function", "value": "module.step1"},
      {"id": 102, "type": "output", "name": "result"}
    ],
    "edges": [...]
  },
  "maxIterations": 100
}
```

## Current State

### What Works ✅

1. **Loading from JSON**: The `load_workflow_json` function successfully loads while loop definitions from JSON and creates executable WorkGraphs
   - Supports both simple mode (conditionFunction + bodyFunction)
   - Supports complex mode (conditionFunction/conditionExpression + bodyWorkflow)
   - Attaches metadata (`_while_node_metadata`) to the created functions for later export

2. **Round-trip for JSON-originated workflows**: If you load a workflow from JSON, you can export it back to JSON successfully because the metadata is preserved

### What Doesn't Work ❌

1. **Exporting manually-created `@task.graph` while loops**: When you create a while loop using the recursive pattern directly in Python (not loaded from JSON), there's no metadata to indicate:
   - This is intended to be a while loop
   - What the condition function is
   - What the body function/workflow is
   - Max iterations limit

2. **Pattern detection**: Currently, we don't attempt to analyze the WorkGraph structure to detect while loop patterns automatically

### Why graph_inputs and graph_outputs Exist

The `graph_inputs` and `graph_outputs` nodes are WorkGraph's internal mechanism for representing the interface of a sub-graph:

- `graph_inputs`: Collects all inputs to the graph and distributes them to tasks
- `graph_outputs`: Collects outputs from tasks and returns them from the graph

In our JSON format, we represent this differently:
- Input nodes with `"type": "input"`
- Output nodes with `"type": "output"`
- Edges that connect them to the workflow tasks

**Current handling**: We skip these internal nodes during export because they don't map directly to our JSON node types. However, for nested workflows (bodyWorkflow), we need to think about how to represent the interface properly.

## Approach 1: Explicit Constructor Pattern

### Concept

Provide explicit functions to create while loops with the right metadata attached, rather than relying on `@task.graph` recursion.

### API Design

```python
from aiida_workgraph import WorkGraph
from python_workflow_definition.aiida import create_while_loop_task

# Simple mode: condition + body as function references
wg = WorkGraph("my_workflow")
while_task = create_while_loop_task(
    condition_function="examples.while_loop.condition",
    body_function="examples.while_loop.function_body",
    max_iterations=1000
)
wg.add_task(while_task)

# Add inputs
wg.add_task(orm.Int(0), name="initial_x")
wg.add_task(orm.Int(5), name="limit")

# Connect inputs to while loop
wg.add_link(wg.tasks["initial_x"].outputs.result, while_task.inputs.x)
wg.add_link(wg.tasks["limit"].outputs.result, while_task.inputs.limit)
```

For complex mode with nested workflow:

```python
# Build the body workflow separately
body_wg = WorkGraph("body")
body_wg.add_task(some_function, name="step1")
body_wg.add_task(another_function, name="step2")
# ... connect tasks ...

# Create while loop with body workflow
wg = WorkGraph("main")
while_task = create_while_loop_task(
    condition_function="examples.while_loop.condition",
    body_workflow=body_wg,
    max_iterations=100
)
wg.add_task(while_task)
```

### Implementation Strategy

1. `create_while_loop_task()` creates a `@task.graph` function internally
2. Attaches `_while_node_metadata` to store all the while loop configuration
3. Returns a task that can be added to a WorkGraph
4. During export, `write_workflow_json` detects the metadata and exports as a while node

### Pros ✅

- **Explicit and clear**: Users explicitly declare "this is a while loop"
- **Easy to implement**: We control the construction, so we can attach metadata properly
- **Exportable by design**: Metadata is always present for export
- **No pattern matching needed**: We know it's a while loop because the user said so

### Cons ❌

- **Different from natural Python**: Doesn't look like a normal while loop or recursion
- **More verbose**: Requires separate function definitions and explicit wiring
- **Less discoverable**: Users need to learn a new API rather than using familiar `@task.graph`
- **Doesn't work for existing code**: Can't export existing `@task.graph` while loops

### Code Example: Full Workflow

```python
from aiida_workgraph import WorkGraph, task
from aiida import orm
from python_workflow_definition.aiida import create_while_loop_task, write_workflow_json

# Define condition and body as regular Python functions
def condition(x, limit):
    """Check if we should continue iterating."""
    return x < limit

@task
def increment(x):
    """Body function that increments x."""
    return x + 1

# Create the main workflow
wg = WorkGraph("while_loop_example")

# Add input data nodes
x_input = orm.Int(0)
limit_input = orm.Int(5)

# Create the while loop task
while_task = create_while_loop_task(
    condition_function="__main__.condition",
    body_function="__main__.increment",
    max_iterations=1000
)

wg.add_task(while_task, name="while_loop")

# Wire up inputs
wg.add_link(x_input, while_task.inputs.x)
wg.add_link(limit_input, while_task.inputs.limit)

# Export to JSON
write_workflow_json(wg, "while_example.json")
```

## Approach 2: Decorator-Based Annotation

### Concept

Extend the `@task.graph` decorator to accept while loop metadata, allowing users to keep the natural recursive pattern while adding export capability.

### API Design

```python
from aiida_workgraph import task

def condition(x, limit):
    return x < limit

@task
def increment(x):
    return x + 1

# Annotate the recursive function with while loop metadata
@task.graph.while_loop(
    condition="__main__.condition",
    body="__main__.increment",
    max_iterations=1000
)
def while_loop(x, limit):
    """Natural recursive implementation with export metadata."""
    if not condition(x, limit):
        return x
    x = increment(x).result
    return while_loop(x, limit)

# Use it naturally
wg = while_loop.build(x=0, limit=5)
```

For complex mode with nested workflow:

```python
@task.graph()
def body_workflow(x):
    """The body as a separate graph."""
    step1 = calculate_something(x)
    step2 = calculate_more(step1.result)
    return step2.result

@task.graph.while_loop(
    condition="__main__.condition",
    body_workflow=body_workflow,  # Reference to another @task.graph
    max_iterations=100
)
def while_loop_nested(x, limit):
    if not condition(x, limit):
        return x
    x = body_workflow(x).result
    return while_loop_nested(x, limit)
```

### Implementation Strategy

1. Extend `@task.graph` decorator to accept an optional `.while_loop()` method
2. When `.while_loop()` is called, it returns a modified decorator that:
   - Still creates the normal recursive `@task.graph` function
   - Attaches `_while_node_metadata` with the provided configuration
3. The runtime behavior is unchanged (still executes as recursion)
4. During export, the metadata is used to create a while node

### Pros ✅

- **Natural syntax**: Looks like normal Python recursion
- **Keeps recursive pattern**: Users write the loop logic as they would naturally
- **Explicit export intent**: Metadata makes it clear this should be exported as a while loop
- **Minimal API surface**: Small extension to existing `@task.graph` decorator
- **Self-documenting**: The decorator parameters document the loop structure

### Cons ❌

- **Metadata duplication**: The condition and body are specified both in the decorator and in the code
- **Potential inconsistency**: Runtime behavior might not match the metadata if they diverge
- **Limited validation**: Hard to verify that the metadata matches the actual recursive structure
- **Complexity in decorator**: Makes the `@task.graph` decorator more complex
- **Body workflow handling**: For bodyWorkflow, need to handle nested @task.graph references

### Code Example: Full Workflow

```python
from aiida_workgraph import task

def condition(x, limit):
    return x < limit

@task
def increment(x):
    return x + 1

# Simple mode: annotated recursive function
@task.graph.while_loop(
    condition="__main__.condition",
    body="__main__.increment",
    max_iterations=1000
)
def simple_while(x, limit):
    if not condition(x, limit):
        return {"x": x}
    result = increment(x)
    return simple_while(result.result, limit)

# Build and export
wg = simple_while.build(x=0, limit=5)
write_workflow_json(wg, "annotated_while.json")

# Complex mode: with nested workflow
@task
def step1(x):
    return x * 2

@task
def step2(x):
    return x + 1

@task.graph()
def body_tasks(x):
    """Multi-step body as a workflow."""
    result1 = step1(x)
    result2 = step2(result1.result)
    return {"x": result2.result}

@task.graph.while_loop(
    condition="__main__.condition",
    body_workflow="__main__.body_tasks",  # Reference as string
    max_iterations=100
)
def complex_while(x, limit):
    if not condition(x, limit):
        return {"x": x}
    result = body_tasks(x)
    return complex_while(result["x"], limit)
```

## Approach 3: Pattern Detection and Analysis

### Concept

Automatically analyze the built WorkGraph structure to detect while loop patterns, extract the components, and reconstruct as a while loop in JSON.

### Detection Strategy

When exporting a WorkGraph, for each `@task.graph` node:

1. **Detect recursion**: Check if the graph calls itself (name matches)
2. **Identify condition**: Look for conditional branching (if statements that return early)
3. **Extract body**: Find tasks executed between condition check and recursive call
4. **Determine inputs/outputs**: Analyze graph_inputs and graph_outputs to understand the interface
5. **Build while node**: Reconstruct as a while loop with detected components

### Example Pattern

```python
@task.graph()
def abstract_while_aiida(x, limit):
    if not condition(x=x, limit=limit):  # <-- Condition (exit case)
        return x                          # <-- Early return
    x = function_body(x=x).result         # <-- Body
    return abstract_while_aiida(x=x, limit=limit)  # <-- Recursive call
```

Pattern analysis would detect:
- Recursive call to `abstract_while_aiida`
- Conditional branch with early return
- Condition function: `condition`
- Body function: `function_body`
- Loop variable: `x` (passed to both condition and body)

### Implementation Challenges

1. **Condition extraction**:
   - Condition might be inline (`if x < limit`) or a function call (`if condition(x, limit)`)
   - Need to serialize inline conditions to conditionExpression
   - Need to resolve function references for conditionFunction

2. **Body extraction**:
   - Body might be a single task or multiple tasks
   - Need to determine if it should be bodyFunction or bodyWorkflow
   - Must extract the subgraph between condition and recursion

3. **State variable tracking**:
   - Determine which variables are loop state (passed to recursion)
   - Which are constant (like `limit`)
   - Map to input/output nodes correctly

4. **Graph structure analysis**:
   - Parse the AST or analyze the built graph structure
   - Handle different code patterns (multiple if-statements, complex bodies, etc.)
   - Deal with graph_inputs and graph_outputs mappings

### Pros ✅

- **No API changes**: Works with existing `@task.graph` code
- **Automatic**: Users don't need to think about export metadata
- **Backward compatible**: Can export existing while loop patterns
- **Natural workflow**: Users write code as they normally would

### Cons ❌

- **Very complex**: Requires sophisticated pattern matching and graph analysis
- **Fragile**: May not work for all valid while loop patterns
- **False positives/negatives**: Might misidentify patterns or miss valid loops
- **Hard to debug**: When it fails, users won't know why or how to fix it
- **Maintenance burden**: Need to update pattern matching as code patterns evolve
- **Performance**: Graph analysis could be expensive for large workflows
- **Limited patterns**: Might only work for simple, canonical while loop forms

### Pseudo-code Implementation

```python
def detect_while_loop_pattern(task_graph_node):
    """Attempt to detect if a @task.graph is a while loop pattern."""

    # 1. Check for recursive call
    if not has_recursive_call(task_graph_node):
        return None

    # 2. Analyze the graph structure
    graph_structure = analyze_graph(task_graph_node)

    # 3. Look for conditional branching with early return
    condition_info = find_condition_branch(graph_structure)
    if not condition_info:
        return None

    # 4. Extract body tasks (between condition and recursion)
    body_tasks = extract_body_tasks(graph_structure, condition_info)

    # 5. Determine if body is simple (single task) or complex (subgraph)
    if len(body_tasks) == 1:
        body_type = "bodyFunction"
        body_value = get_function_reference(body_tasks[0])
    else:
        body_type = "bodyWorkflow"
        body_value = extract_subworkflow(body_tasks, graph_structure)

    # 6. Extract condition function reference
    condition_ref = extract_condition_reference(condition_info)

    # 7. Build while loop metadata
    return {
        "conditionFunction": condition_ref,
        body_type: body_value,
        "maxIterations": 1000,  # Default, can't be determined from code
    }
```

## Nested Workflow Body Options

For the complex mode (`bodyWorkflow`), we need to decide how users specify the nested workflow structure.

### Option A: Separate WorkGraph Instance

Users create a WorkGraph for the body separately and pass it in.

```python
# Build the body workflow
body = WorkGraph("body")
body.add_task(step1, name="s1")
body.add_task(step2, name="s2")
body.add_link(body.tasks.s1.outputs.result, body.tasks.s2.inputs.x)

# Create while loop with body
while_task = create_while_loop_task(
    condition_function="module.condition",
    body_workflow=body,
    max_iterations=100
)
```

**Pros**:
- Explicit and clear
- Full control over body structure
- Can reuse body in multiple places
- Easy to test body independently

**Cons**:
- Verbose
- Need to manage multiple WorkGraph instances
- Have to wire up inputs/outputs carefully

### Option B: Builder Pattern with Context Manager

Use a context manager to build the body inline.

```python
while_task = create_while_loop_task(
    condition_function="module.condition",
    max_iterations=100
)

with while_task.body() as body:
    s1 = body.add_task(step1, name="s1")
    s2 = body.add_task(step2, name="s2")
    body.add_link(s1.outputs.result, s2.inputs.x)
```

**Pros**:
- Cleaner syntax
- Clear scope for body tasks
- Context manager handles setup/teardown

**Cons**:
- More complex API
- Harder to reuse body
- Limited flexibility

### Option C: Inline task.graph Function

Allow passing a `@task.graph` function as the body, which gets converted.

```python
@task.graph()
def body_workflow(x):
    s1 = step1(x)
    s2 = step2(s1.result)
    return s2.result

while_task = create_while_loop_task(
    condition_function="module.condition",
    body_workflow=body_workflow,  # Pass the task.graph function
    max_iterations=100
)
```

**Pros**:
- Natural Python function syntax
- Reusable body definition
- Can test body independently
- Consistent with @task.graph patterns

**Cons**:
- Need to "unpack" the task.graph to extract the workflow
- Might be confusing (is it executed or converted?)
- Need to handle inputs/outputs mapping

## Handling graph_inputs and graph_outputs

### The Role of These Nodes

In WorkGraph:
- `graph_inputs`: Entry point for data coming into a sub-graph
- `graph_outputs`: Exit point for data leaving a sub-graph

For a while loop body workflow:
```
graph_inputs (x=5) → body_task (x+1) → graph_outputs (result=6)
```

### Mapping to JSON Format

In our JSON format, we use explicit input and output nodes:

```json
{
  "bodyWorkflow": {
    "nodes": [
      {"id": 100, "type": "input", "name": "x"},
      {"id": 101, "type": "function", "value": "module.body_task"},
      {"id": 102, "type": "output", "name": "result"}
    ],
    "edges": [
      {"source": 100, "target": 101, "targetPort": "x"},
      {"source": 101, "target": 102, "sourcePort": "result"}
    ]
  }
}
```

### Current Handling: Why We Skip Them

Currently, `write_workflow_json` skips `graph_inputs` and `graph_outputs` because:

1. **Top-level workflows**: For the main workflow, inputs are represented as data nodes with `"type": "input"` and explicit values
2. **Not directly mappable**: graph_inputs/outputs are WorkGraph internals, not user-defined nodes
3. **Implicit interface**: The workflow interface is defined by the edges, not explicit nodes

### When They Should Be Converted

For **nested workflows** (bodyWorkflow in while loops):

1. **graph_inputs should become input nodes**: Each input to the body becomes an explicit input node
2. **graph_outputs should become output nodes**: Each output from the body becomes an explicit output node
3. **Edges need updating**: Connect input nodes to tasks, tasks to output nodes

### Export Strategy for Nested Workflows

When exporting a while loop with bodyWorkflow:

```python
# For each socket in graph_inputs:
#   Create an input node: {"id": N, "type": "input", "name": socket_name}
#   Create edges from input node to tasks that use it

# For each socket in graph_outputs:
#   Create an output node: {"id": M, "type": "output", "name": socket_name}
#   Create edges from tasks to output node

# Regular tasks in between are exported normally
```

Example transformation:

```python
# WorkGraph structure:
graph_inputs → [step1, step2] → graph_outputs

# Becomes JSON:
{
  "nodes": [
    {"id": 100, "type": "input", "name": "x"},
    {"id": 101, "type": "function", "value": "module.step1"},
    {"id": 102, "type": "function", "value": "module.step2"},
    {"id": 103, "type": "output", "name": "result"}
  ],
  "edges": [
    {"source": 100, "target": 101},
    {"source": 101, "target": 102},
    {"source": 102, "target": 103}
  ]
}
```

## Recommendations

### Short-term: Explicit Constructor (Approach 1)

**Recommendation**: Implement Approach 1 (Explicit Constructor) first.

**Rationale**:
- Simplest to implement correctly
- Provides immediate value for users who want to export while loops
- Serves as a foundation for more sophisticated approaches later
- Clear and explicit, reducing confusion

**Implementation plan**:
1. Create `create_while_loop_task()` function
2. Support both simple mode (conditionFunction + bodyFunction) and complex mode (conditionFunction + bodyWorkflow)
3. For bodyWorkflow, use Option C (inline task.graph function) or Option A (separate WorkGraph)
4. Update `write_workflow_json` to properly export nested bodyWorkflow with input/output nodes

### Medium-term: Decorator Enhancement (Approach 2)

**After** Approach 1 is working, consider adding Approach 2 as syntactic sugar.

**Rationale**:
- Provides a more natural API for users familiar with @task.graph
- Can internally delegate to the explicit constructor
- Offers better developer experience while keeping implementation simple

### Long-term: Pattern Detection (Approach 3)

**Only if needed**: Consider Approach 3 for backward compatibility with existing code.

**Rationale**:
- Complex and fragile
- Only valuable for exporting existing @task.graph while loops
- Most use cases can be served by Approaches 1 and 2
- Could be implemented as a separate "migration tool" rather than core functionality

### Hybrid Approach

Combine approaches for maximum flexibility:

1. **Explicit constructor** (Approach 1): For programmatic creation
2. **Decorator annotations** (Approach 2): For natural syntax
3. **Both internally use the same metadata mechanism**
4. **Pattern detection** (Approach 3): Optional tool for migration only

### Testing Strategy

To validate any implementation:

1. **Round-trip tests**: Load JSON → Build WorkGraph → Export JSON → Compare
2. **Execution tests**: Verify that exported/imported workflows execute correctly
3. **Edge cases**: Empty bodies, complex conditions, nested loops, error handling
4. **Cross-platform**: Test with different workflow managers (jobflow, pyiron, etc.)

## Example: Complete Flow with Approach 1

```python
# 1. Define reusable condition and body functions
def check_convergence(energy, threshold):
    """Condition: stop when converged."""
    return abs(energy - prev_energy) > threshold

@task
def calculate_energy(structure):
    """Body: compute energy and update structure."""
    # ... DFT calculation ...
    return {"structure": new_structure, "energy": energy}

# 2. Create workflow with explicit while loop
from python_workflow_definition.aiida import create_while_loop_task

wg = WorkGraph("optimization")

# Add inputs
wg.add_task(orm.StructureData(...), name="initial_structure")
wg.add_task(orm.Float(0.001), name="threshold")

# Create while loop
optimization_loop = create_while_loop_task(
    condition_function="module.check_convergence",
    body_function="module.calculate_energy",
    max_iterations=100
)
wg.add_task(optimization_loop, name="optimize")

# Wire inputs
wg.add_link(wg.tasks.initial_structure.outputs.result, optimization_loop.inputs.structure)
wg.add_link(wg.tasks.threshold.outputs.result, optimization_loop.inputs.threshold)

# 3. Export to JSON for other workflow managers
write_workflow_json(wg, "optimization.json")

# 4. Later: Load in another workflow manager
# (jobflow, pyiron, etc. can read optimization.json)
```

## Open Questions

1. **State management**: How do we handle loop state variables that need to persist across iterations?
2. **Error handling**: What happens if the condition function fails? Body function fails?
3. **Nested loops**: Should we support while loops inside while loop bodies?
4. **Break/continue**: Can we support early exit or skip semantics?
5. **Performance**: For large graphs, how do we efficiently detect patterns and export?
6. **Versioning**: How do we handle evolution of the JSON format over time?

## Conclusion

The while loop export problem is fundamentally about bridging the gap between:
- **Runtime**: Dynamic, recursive, Python-native
- **Static representation**: Fixed structure, declarative, JSON-based

Each approach offers different trade-offs between naturalness, explicitness, and complexity. The recommended path is to start with explicit constructors (Approach 1) for clarity and correctness, then enhance with decorator syntax (Approach 2) for better developer experience, and only consider pattern detection (Approach 3) if backward compatibility requires it.

The key insight is that **metadata preservation** is essential - whether attached via constructor, decorator, or detection, we need to know the while loop's structure to export it correctly. The approach that makes this metadata most explicit and maintainable will be the most successful long-term solution.
