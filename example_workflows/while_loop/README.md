# While Loop Control Flow Examples

This directory contains examples demonstrating the `while` loop control flow node added to the Python Workflow Definition syntax.

## Overview

The `PythonWorkflowDefinitionWhileNode` enables iterative execution in workflows, supporting two main modes:

1. **Simple mode**: Condition and body as Python functions
2. **Complex mode**: Nested workflow as loop body

## Files

### Core Implementation

- `models.py`: Contains the `PythonWorkflowDefinitionWhileNode` class (in main source tree)
- `expression_eval.py`: Safe expression evaluator for condition expressions

### Examples

1. **simple_counter.json** - Basic while loop with function-based condition
2. **simple_counter_expression.json** - While loop with expression-based condition
3. **nested_optimization.json** - Complex nested workflow example

### Supporting Files

- `workflow.py`: Simple workflow functions for basic examples
- `nested_workflow.py`: Functions for the geometry optimization example
- `test_while_node.py`: Test suite validating the implementation

## WhileNode Schema

```json
{
  "id": <int>,
  "type": "while",

  // Condition (exactly one required)
  "conditionFunction": "<module.function>",  // OR
  "conditionExpression": "<expression>",     // Safe Python expression

  // Body (exactly one required)
  "bodyFunction": "<module.function>",       // OR
  "bodyWorkflow": { ... },                   // Nested workflow definition

  // Configuration
  "maxIterations": 1000,                     // Safety limit (default: 1000)
  "stateVars": ["var1", "var2"]             // Optional: tracked variables
}
```

## Example 1: Simple Counter (Function-based)

**File**: `simple_counter.json`

Counts from `m=0` to `n=10` using function-based condition and body.

**Workflow Functions** (`workflow.py`):

```python
def is_less_than(n, m):
    """Condition: continue while m < n"""
    return m < n

def increment_m(n, m):
    """Body: increment m by 1"""
    return {"n": n, "m": m + 1}
```

**Workflow Graph**:

```
Input(n=10) ──┐
              ├──> While(condition=is_less_than, body=increment_m) ──> Output(result)
Input(m=0) ──┘
```

## Example 2: Simple Counter (Expression-based)

**File**: `simple_counter_expression.json`

Same as Example 1, but uses a condition expression instead of a function:

```json
{
  "type": "while",
  "conditionExpression": "m < n",
  "bodyFunction": "workflow.increment_m"
}
```

**Supported Expression Operators**:
- Comparison: `<`, `<=`, `>`, `>=`, `==`, `!=`, `in`, `not in`, `is`, `is not`
- Boolean: `and`, `or`, `not`
- Arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Subscript: `data[0]`, `dict["key"]`

**Safety Features**:
- No function calls allowed
- No imports allowed
- No access to `__builtins__`
- No dunder attribute access (e.g., `__import__`)

## Example 3: Nested Workflow (Geometry Optimization)

**File**: `nested_optimization.json`

Demonstrates a complex iterative algorithm with a nested workflow as the loop body.

**Use Case**: Geometry optimization of a molecular structure

**Outer Loop** (While node):
- **Condition**: `not_converged(threshold, energy_change)`
- **Body**: Nested workflow (see below)
- **Max iterations**: 100

**Inner Workflow** (Loop body):
1. `calculate_energy(structure)` → energy
2. `calculate_forces(structure, energy)` → forces
3. `update_geometry(structure, forces)` → new_structure
4. `check_convergence(old_energy, new_structure)` → energy_change

**State Flow**:

```
Iteration N:
  structure_N, energy_N → [nested workflow] → structure_{N+1}, energy_{N+1}, energy_change

Check condition:
  not_converged(threshold, energy_change) → continue or stop
```

**Workflow Functions** (`nested_workflow.py`):

```python
def not_converged(threshold, energy_change):
    return abs(energy_change) > threshold

def calculate_energy(structure):
    # Compute energy from atomic positions
    ...

def calculate_forces(structure, energy):
    # Compute forces on atoms
    ...

def update_geometry(structure, forces):
    # Update positions using steepest descent
    ...

def check_convergence(old_energy, new_structure):
    # Calculate energy change
    new_energy = calculate_energy(new_structure)
    return {"energy": new_energy, "energy_change": new_energy - old_energy}
```

## State Management

The while loop follows the current workflow edge model for state management:

### Input Ports
- Initial values flow into the while node via edges targeting specific ports
- Example: `{"source": 0, "target": 2, "targetPort": "n"}`

### Output Ports
- Loop body functions return dictionaries with updated state
- Output ports extract specific values from the result
- Example: `{"source": 2, "sourcePort": "m", "target": 3}`

### Iteration State Flow

For each iteration:
1. Input state flows into the condition function
2. If condition returns `True`, state flows into body
3. Body returns updated state (dict)
4. Updated state becomes input for next iteration
5. Loop terminates when condition returns `False` or `maxIterations` reached

## Running the Tests

```bash
cd example_workflows/while_loop
python test_while_node.py
```

**Test Coverage**:
- ✓ Schema validation (valid/invalid node configurations)
- ✓ JSON workflow loading (all three examples)
- ✓ Safe expression evaluation (valid expressions and security tests)

## Design Rationale

### Hybrid Approach (Option 3 + 4)

The implementation combines:
1. **Simple function-based** loops (easy to author, backend-compatible)
2. **Nested workflow** loops (powerful for complex multi-step iterations)

### Condition Evaluation Options

**Option A**: `conditionFunction` only
- ✅ Safe, backend-compatible
- ❌ Requires writing functions for simple checks

**Option B**: `conditionExpression` only
- ✅ Natural syntax for simple conditions
- ❌ Requires safe eval mechanism

**Option C**: **Hybrid (Implemented)** ⭐
- ✅ Flexibility: use functions OR expressions
- ✅ Safety: restricted AST validation
- ✅ Convenience: no function needed for `m < n`

### Port-based State Management

Following the existing edge model:
- ✅ Consistent with current architecture
- ✅ Explicit data flow
- ✅ Backend translation is straightforward
- ✅ Visualizable in graph UIs

## Implementation Details

### Files Modified/Created

**Core Schema** (`models.py`):
- Added `PythonWorkflowDefinitionWhileNode` class
- Updated discriminated union to include while nodes
- Added validators for condition/body requirements

**Expression Evaluator** (`expression_eval.py`):
- `evaluate_expression()`: Safe eval with AST validation
- `evaluate_condition()`: Wrapper ensuring boolean results
- `SAFE_NODES`: Whitelist of allowed AST node types

**Examples** (this directory):
- Three JSON workflow examples
- Two Python function modules
- Test suite

### Future Extensions

The while node design can be extended to support:

1. **Other control flow**:
   - `if/else` conditional nodes
   - `for` loop nodes with iterables
   - `break`/`continue` conditions

2. **Advanced features**:
   - Loop carry state (accumulator pattern)
   - Parallel iteration (map-reduce style)
   - Dynamic max iterations based on state

3. **Debugging support**:
   - Iteration count tracking
   - State snapshots per iteration
   - Convergence history logging

## Notes

- **DAG Preservation**: While nodes do not create cycles in the graph. The while node itself is atomic and maintains the DAG structure.
- **Safety**: `maxIterations` prevents infinite loops. Default is 1000.
- **Backend Compatibility**: Backends can choose to:
  - Unroll loops (for static execution)
  - Use native loop constructs (for dynamic execution)
  - Implement custom while loop handling

## Questions?

See the test file (`test_while_node.py`) for detailed usage examples and validation.
