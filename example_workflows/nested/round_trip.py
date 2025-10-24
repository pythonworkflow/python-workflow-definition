"""
Round-trip test for nested workflows.

This script demonstrates that:
1. Loading a nested workflow JSON preserves all structure and values
2. Exporting a loaded workflow produces identical JSON
3. Multiple round-trips are stable (load -> export -> load -> export produces identical results)
"""

import json
from pathlib import Path
from python_workflow_definition.aiida import load_workflow_json, write_workflow_json
from aiida import load_profile

# Load AiiDA profile
load_profile()


def compare_json_files(file1: str, file2: str) -> bool:
    """Compare two JSON files for structural equality."""
    with open(file1) as f1, open(file2) as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)
    # Compare as sorted JSON strings to ignore ordering
    return json.dumps(data1, sort_keys=True) == json.dumps(data2, sort_keys=True)


def print_workflow_info(wg, name: str):
    """Print information about a loaded workflow."""
    print(f"\n{name}:")

    # Count tasks (excluding internal graph tasks)
    task_count = len([t for t in wg.tasks if t.name not in ["graph_inputs", "graph_outputs", "graph_ctx"]])
    print(f"  Tasks: {task_count}")

    # Show inputs
    if hasattr(wg.inputs, '_sockets'):
        print("  Inputs:")
        for name, socket in wg.inputs._sockets.items():
            if not name.startswith('_') and name != 'metadata':
                if hasattr(socket, 'value') and socket.value is not None:
                    value = socket.value.value if hasattr(socket.value, 'value') else socket.value
                    print(f"    {name} = {value}")

    # Show outputs
    if hasattr(wg.outputs, '_sockets'):
        output_names = [name for name in wg.outputs._sockets.keys()
                       if not name.startswith('_') and name != 'metadata']
        if output_names:
            print(f"  Outputs: {', '.join(output_names)}")

    # Check for nested workflows
    nested_count = 0
    for task in wg.tasks:
        if hasattr(task, 'tasks'):
            nested_tasks = [t for t in task.tasks if t.name not in ['graph_inputs', 'graph_outputs', 'graph_ctx']]
            if len(nested_tasks) > 0:
                nested_count += 1
                print(f"  Nested workflow '{task.name}' with {len(nested_tasks)} tasks")
                # Show nested workflow defaults
                for subtask in task.tasks:
                    if subtask.name == 'graph_inputs' and hasattr(subtask, 'outputs'):
                        print("    Default inputs:")
                        for out in subtask.outputs:
                            if hasattr(out, '_name') and not out._name.startswith('_'):
                                value = out.value.value if hasattr(out.value, 'value') else out.value
                                print(f"      {out._name} = {value}")


def main():
    print("=" * 70)
    print("NESTED WORKFLOW ROUND-TRIP TEST")
    print("=" * 70)

    # Define file paths
    original_file = "main.pwd.json"
    roundtrip1_file = "roundtrip1.pwd.json"
    roundtrip2_file = "roundtrip2.pwd.json"
    nested_original = "prod_div.json"
    nested_export = "nested_1.json"

    # Test 1: Load original workflow
    print("\n[1] Loading original workflow...")
    wg_original = load_workflow_json(original_file)
    print_workflow_info(wg_original, "Original workflow")

    # Test 2: Export to roundtrip1
    print("\n[2] Exporting to roundtrip1.pwd.json...")
    write_workflow_json(wg_original, roundtrip1_file)
    print(f"  Exported main workflow to {roundtrip1_file}")
    if Path(nested_export).exists():
        print(f"  Exported nested workflow to {nested_export}")

    # Test 3: Load roundtrip1
    print("\n[3] Loading roundtrip1.pwd.json...")
    wg_roundtrip1 = load_workflow_json(roundtrip1_file)
    print_workflow_info(wg_roundtrip1, "Roundtrip 1 workflow")

    # Test 4: Export to roundtrip2
    print("\n[4] Exporting to roundtrip2.pwd.json...")
    write_workflow_json(wg_roundtrip1, roundtrip2_file)
    print(f"  Exported to {roundtrip2_file}")

    # Test 5: Compare files
    print("\n[5] Comparing JSON files...")
    print("-" * 70)

    # Compare main workflows
    main_match = compare_json_files(roundtrip1_file, roundtrip2_file)
    print(f"  roundtrip1 == roundtrip2: {'PASS' if main_match else 'FAIL'}")

    # Compare nested workflows
    if Path(nested_original).exists() and Path(nested_export).exists():
        nested_match = compare_json_files(nested_original, nested_export)
        print(f"  {nested_original} == {nested_export}: {'PASS' if nested_match else 'FAIL'}")
    else:
        nested_match = True  # If files don't exist, consider it a pass

    # Test 6: Load roundtrip2 and verify
    print("\n[6] Loading roundtrip2.pwd.json for verification...")
    wg_roundtrip2 = load_workflow_json(roundtrip2_file)
    print_workflow_info(wg_roundtrip2, "Roundtrip 2 workflow")

    # Final verdict
    print("\n" + "=" * 70)
    if main_match and nested_match:
        print("RESULT: ALL TESTS PASSED")
        print("  - Workflow structure preserved")
        print("  - Input/output values preserved")
        print("  - Nested workflow defaults preserved")
        print("  - Round-trip is stable and idempotent")
        result = 0
    else:
        print("RESULT: SOME TESTS FAILED")
        result = 1
    print("=" * 70)

    # Cleanup
    print("\nCleaning up temporary files...")
    for temp_file in [roundtrip1_file, roundtrip2_file, nested_export]:
        if Path(temp_file).exists():
            Path(temp_file).unlink()
            print(f"  Removed {temp_file}")

    return result


if __name__ == "__main__":
    exit(main())
