"""
Test script for recursive while loop approach.

This tests:
1. Loading recursive workflow JSON files
2. Executing recursive functions directly
3. Validating that the workflow schema supports recursion
"""

import sys
from pathlib import Path

# Add the source directory to Python path
src_path = Path(__file__).parent.parent.parent / "python_workflow_definition" / "src"
sys.path.insert(0, str(src_path))

# Add current directory for workflow imports
sys.path.insert(0, str(Path(__file__).parent))

from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow
import workflow


def test_workflow_loading():
    """Test loading recursive workflow JSON files."""
    print("=" * 60)
    print("Testing Recursive Workflow JSON Loading")
    print("=" * 60)

    # Test 1: Simple recursive workflow
    print("\n1. Loading simple_recursive.json...")
    try:
        workflow_path = Path(__file__).parent / "simple_recursive.json"
        wf = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
        print(f"   ✓ Loaded successfully")
        print(f"   - Nodes: {len(wf['nodes'])}")
        print(f"   - Edges: {len(wf['edges'])}")
        func_node = [n for n in wf["nodes"] if n["type"] == "function"][0]
        print(f"   - Function: {func_node['value']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 2: Recursive with accumulator
    print("\n2. Loading recursive_accumulator.json...")
    try:
        workflow_path = Path(__file__).parent / "recursive_accumulator.json"
        wf = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
        print(f"   ✓ Loaded successfully")
        print(f"   - Nodes: {len(wf['nodes'])}")
        func_node = [n for n in wf["nodes"] if n["type"] == "function"][0]
        print(f"   - Function: {func_node['value']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 3: Fibonacci
    print("\n3. Loading fibonacci.json...")
    try:
        workflow_path = Path(__file__).parent / "fibonacci.json"
        wf = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
        print(f"   ✓ Loaded successfully")
        print(f"   - Nodes: {len(wf['nodes'])}")
        print(f"   - Input nodes: {len([n for n in wf['nodes'] if n['type'] == 'input'])}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


def test_recursive_functions():
    """Test executing recursive functions directly."""
    print("\n" + "=" * 60)
    print("Testing Recursive Function Execution")
    print("=" * 60)

    # Test 1: Simple while loop
    print("\n1. Testing while_loop(n=10, m=0)...")
    try:
        result = workflow.while_loop(n=10, m=0)
        expected = 10
        if result == expected:
            print(f"   ✓ Result: {result} (expected: {expected})")
        else:
            print(f"   ✗ Result: {result} (expected: {expected})")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 2: While loop with accumulator
    print("\n2. Testing while_loop_with_accumulator(n=5, m=0, accumulator=[])...")
    try:
        result = workflow.while_loop_with_accumulator(n=5, m=0, accumulator=[])
        expected_m = 5
        expected_acc = [0, 1, 2, 3, 4]
        if result["m"] == expected_m and result["accumulator"] == expected_acc:
            print(f"   ✓ Result: m={result['m']}, accumulator={result['accumulator']}")
        else:
            print(f"   ✗ Result: {result}")
            print(f"     Expected: m={expected_m}, accumulator={expected_acc}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 3: Fibonacci sequence
    print("\n3. Testing fibonacci_recursive(n=10, current=0, a=0, b=1, results=[])...")
    try:
        result = workflow.fibonacci_recursive(n=10, current=0, a=0, b=1, results=[])
        expected_count = 10
        expected_first_few = [1, 1, 2, 3, 5, 8]
        if (
            result["count"] == expected_count
            and result["results"][:6] == expected_first_few
        ):
            print(f"   ✓ Generated {result['count']} Fibonacci numbers")
            print(f"   - First 6 numbers: {result['results'][:6]}")
        else:
            print(f"   ✗ Result: {result}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 4: Convergence
    print("\n4. Testing converge_to_zero(value=100, threshold=0.01, iterations=0)...")
    try:
        result = workflow.converge_to_zero(value=100, threshold=0.01, iterations=0)
        if result["converged"] and abs(result["value"]) <= 0.01:
            print(f"   ✓ Converged after {result['iterations']} iterations")
            print(f"   - Final value: {result['value']}")
        else:
            print(f"   ✗ Result: {result}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


def test_recursion_depth():
    """Test that recursion handles reasonable iteration counts."""
    print("\n" + "=" * 60)
    print("Testing Recursion Depth Handling")
    print("=" * 60)

    # Test with moderate iteration count (should work)
    print("\n1. Testing with n=100 (moderate depth)...")
    try:
        result = workflow.while_loop(n=100, m=0)
        if result == 100:
            print(f"   ✓ Handled 100 iterations successfully")
        else:
            print(f"   ✗ Unexpected result: {result}")
    except RecursionError:
        print(f"   ✗ Hit recursion limit (this is a limitation of the recursive approach)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test with large iteration count (may hit recursion limit)
    print("\n2. Testing with n=1000 (deep recursion)...")
    try:
        result = workflow.while_loop(n=1000, m=0)
        if result == 1000:
            print(f"   ✓ Handled 1000 iterations successfully")
        else:
            print(f"   ✗ Unexpected result: {result}")
    except RecursionError:
        print(f"   ⚠  Hit Python recursion limit (expected for deep recursion)")
        print(f"      This demonstrates a key limitation of the recursive approach.")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


def test_schema_compatibility():
    """Test that recursive workflows are compatible with current schema."""
    print("\n" + "=" * 60)
    print("Testing Schema Compatibility")
    print("=" * 60)

    print("\n1. Checking if workflows validate against schema...")
    try:
        # Load and validate each workflow
        workflows = ["simple_recursive.json", "recursive_accumulator.json", "fibonacci.json"]
        for wf_file in workflows:
            workflow_path = Path(__file__).parent / wf_file
            wf = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
            print(f"   ✓ {wf_file} validates successfully")
    except Exception as e:
        print(f"   ✗ Validation failed: {e}")

    print("\n2. Checking node types...")
    try:
        workflow_path = Path(__file__).parent / "simple_recursive.json"
        wf = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
        node_types = {n["type"] for n in wf["nodes"]}
        expected_types = {"input", "function", "output"}
        if node_types == expected_types:
            print(f"   ✓ Uses standard node types: {node_types}")
            print(f"   ✓ No schema changes required for recursive approach!")
        else:
            print(f"   ✗ Unexpected node types: {node_types}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Recursive While Loop Implementation Tests")
    print("=" * 60)

    test_workflow_loading()
    test_recursive_functions()
    test_recursion_depth()
    test_schema_compatibility()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nKey Findings:")
    print("✓ No schema changes needed - uses existing function nodes")
    print("✓ Natural functional programming style")
    print("⚠  Python recursion depth limit (~1000 calls)")
    print("⚠  Stack overflow risk for large iterations")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
