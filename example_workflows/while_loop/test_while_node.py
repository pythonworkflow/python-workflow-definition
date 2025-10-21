"""
Test script to validate the WhileNode implementation.

This script tests:
1. Schema validation for WhileNode
2. Loading JSON workflows with while loops
3. Safe expression evaluation
"""

import sys
from pathlib import Path

# Add the source directory to Python path
src_path = Path(__file__).parent.parent.parent / "python_workflow_definition" / "src"
sys.path.insert(0, str(src_path))

from python_workflow_definition.models import (
    PythonWorkflowDefinitionWorkflow,
    PythonWorkflowDefinitionWhileNode,
)
from python_workflow_definition.expression_eval import (
    evaluate_expression,
    evaluate_condition,
    UnsafeExpressionError,
)


def test_schema_validation():
    """Test WhileNode schema validation."""
    print("=" * 60)
    print("Testing WhileNode schema validation...")
    print("=" * 60)

    # Test 1: Valid function-based while node
    print("\n1. Testing valid function-based while node...")
    try:
        node = PythonWorkflowDefinitionWhileNode(
            id=1,
            type="while",
            conditionFunction="workflow.check",
            bodyFunction="workflow.body",
            maxIterations=100,
        )
        print("   ✓ Valid function-based node created successfully")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 2: Valid expression-based while node
    print("\n2. Testing valid expression-based while node...")
    try:
        node = PythonWorkflowDefinitionWhileNode(
            id=2,
            type="while",
            conditionExpression="m < n",
            bodyFunction="workflow.body",
        )
        print("   ✓ Valid expression-based node created successfully")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 3: Invalid - no condition specified
    print("\n3. Testing invalid node (no condition)...")
    try:
        node = PythonWorkflowDefinitionWhileNode(
            id=3,
            type="while",
            bodyFunction="workflow.body",
        )
        print("   ✗ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ Correctly rejected: {e}")

    # Test 4: Invalid - both condition methods specified
    print("\n4. Testing invalid node (both condition methods)...")
    try:
        node = PythonWorkflowDefinitionWhileNode(
            id=4,
            type="while",
            conditionFunction="workflow.check",
            conditionExpression="m < n",
            bodyFunction="workflow.body",
        )
        print("   ✗ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ Correctly rejected: {e}")

    # Test 5: Invalid - no body specified
    print("\n5. Testing invalid node (no body)...")
    try:
        node = PythonWorkflowDefinitionWhileNode(
            id=5,
            type="while",
            conditionFunction="workflow.check",
        )
        print("   ✗ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ Correctly rejected: {e}")


def test_workflow_loading():
    """Test loading JSON workflows with while loops."""
    print("\n" + "=" * 60)
    print("Testing workflow JSON loading...")
    print("=" * 60)

    # Test loading simple counter workflow
    print("\n1. Loading simple_counter.json...")
    try:
        workflow_path = Path(__file__).parent / "simple_counter.json"
        workflow = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
        print(f"   ✓ Loaded successfully")
        print(f"   - Nodes: {len(workflow['nodes'])}")
        print(f"   - Edges: {len(workflow['edges'])}")
        while_node = [n for n in workflow["nodes"] if n["type"] == "while"][0]
        print(f"   - While node ID: {while_node['id']}")
        print(f"   - Condition: {while_node.get('conditionFunction')}")
        print(f"   - Body: {while_node.get('bodyFunction')}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test loading expression-based workflow
    print("\n2. Loading simple_counter_expression.json...")
    try:
        workflow_path = Path(__file__).parent / "simple_counter_expression.json"
        workflow = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
        print(f"   ✓ Loaded successfully")
        while_node = [n for n in workflow["nodes"] if n["type"] == "while"][0]
        print(f"   - Condition expression: {while_node.get('conditionExpression')}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test loading nested workflow
    print("\n3. Loading nested_optimization.json...")
    try:
        workflow_path = Path(__file__).parent / "nested_optimization.json"
        workflow = PythonWorkflowDefinitionWorkflow.load_json_file(workflow_path)
        print(f"   ✓ Loaded successfully")
        while_node = [n for n in workflow["nodes"] if n["type"] == "while"][0]
        print(f"   - Has nested workflow: {while_node.get('bodyWorkflow') is not None}")
        if while_node.get("bodyWorkflow"):
            nested = while_node["bodyWorkflow"]
            print(f"   - Nested nodes: {len(nested['nodes'])}")
            print(f"   - Nested edges: {len(nested['edges'])}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


def test_expression_evaluation():
    """Test safe expression evaluation."""
    print("\n" + "=" * 60)
    print("Testing safe expression evaluation...")
    print("=" * 60)

    # Test 1: Simple comparison
    print("\n1. Testing simple comparison: 'm < n'")
    try:
        result = evaluate_condition("m < n", {"m": 5, "n": 10})
        print(f"   ✓ Result: {result} (expected: True)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 2: Complex boolean expression
    print("\n2. Testing complex boolean: 'a > 5 and b < 10'")
    try:
        result = evaluate_condition("a > 5 and b < 10", {"a": 7, "b": 8})
        print(f"   ✓ Result: {result} (expected: True)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 3: Arithmetic in expression
    print("\n3. Testing arithmetic: 'x + y > 10'")
    try:
        result = evaluate_condition("x + y > 10", {"x": 7, "y": 5})
        print(f"   ✓ Result: {result} (expected: True)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 4: Unsafe expression (should fail)
    print("\n4. Testing unsafe expression: '__import__(\"os\")'")
    try:
        result = evaluate_expression("__import__('os')", {})
        print(f"   ✗ Should have raised UnsafeExpressionError")
    except UnsafeExpressionError as e:
        print(f"   ✓ Correctly rejected: {e}")

    # Test 5: Function call (should fail)
    print("\n5. Testing function call: 'print(\"hello\")'")
    try:
        result = evaluate_expression("print('hello')", {})
        print(f"   ✗ Should have raised UnsafeExpressionError")
    except UnsafeExpressionError as e:
        print(f"   ✓ Correctly rejected: {e}")

    # Test 6: List/dict access
    print("\n6. Testing subscript access: 'data[0] > 5'")
    try:
        result = evaluate_condition("data[0] > 5", {"data": [10, 20, 30]})
        print(f"   ✓ Result: {result} (expected: True)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("WhileNode Implementation Tests")
    print("=" * 60)

    test_schema_validation()
    test_workflow_loading()
    test_expression_evaluation()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
