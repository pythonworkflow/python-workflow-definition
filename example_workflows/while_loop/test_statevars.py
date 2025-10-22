"""Test case for while loop with stateVars"""

# Define the workflow functions
def is_less_than(n, m):
    """Condition: check if m < n"""
    return m < n


def increment_m(n, m):
    """Body: increment m, keep n unchanged"""
    return {"n": n, "m": m + 1}


if __name__ == "__main__":
    from aiida import load_profile
    load_profile()

    from python_workflow_definition.aiida import load_workflow_json

    # Load and run the workflow
    wg = load_workflow_json("/home/geiger_j/aiida_projects/adis/git-repos/python-workflow-definition/example_workflows/while_loop/test_statevars.json")

    print("WorkGraph loaded successfully!")
    print(f"Tasks: {[task.name for task in wg.tasks]}")

    # Check the while loop task
    while_task = None
    for task in wg.tasks:
        if hasattr(task, 'get_executor'):
            executor = task.get_executor()
            if executor and hasattr(executor, 'callable'):
                # This might be the while loop
                try:
                    from node_graph.executor import RuntimeExecutor
                    runtime_exec = RuntimeExecutor(**executor.to_dict())
                    if hasattr(runtime_exec.callable, '_while_node_metadata'):
                        while_task = task
                        break
                except:
                    pass

    if while_task:
        print(f"\nWhile loop task found: {while_task.name}")
        print(f"Inputs: {list(while_task.inputs.keys())}")
        print(f"Outputs: {list(while_task.outputs.keys())}")

    # Run the workflow
    print("\nRunning workflow...")
    wg.run()

    print(f"Workflow completed!")
    print(f"Result: {wg.tasks[-1].outputs}")
