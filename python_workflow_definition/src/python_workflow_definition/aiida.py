from importlib import import_module
import json


from python_workflow_definition.shared import (
    convert_nodes_list_to_dict,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
)


# -> WorkGraph
def load_workflow_json(file_name: str):
    """
    Load a workflow JSON file and convert it to a WorkGraph.

    Args:
        file_name: Path to the JSON workflow file

    Returns:
        A populated WorkGraph object
    """
    with open(file_name) as f:
        data = json.load(f)

    from aiida_workgraph import WorkGraph
    wg = WorkGraph()
    task_name_mapping = {}

    # Create all tasks first
    for task_id, identifier in convert_nodes_list_to_dict(data[NODES_LABEL]).items():
        if isinstance(identifier, str) and "." in identifier:
            # Import the function dynamically
            package_path, function_name = identifier.rsplit(".", 1)
            module = import_module(package_path)
            func = getattr(module, function_name)

            # Add task and prepare for linking
            wg.add_task(func)
            current_task = wg.tasks[-1]

            # Remove default output as we'll add custom outputs later
            del current_task.outputs["result"]
            task_name_mapping[task_id] = current_task

    # Add all connections between tasks
    for link in data[EDGES_LABEL]:
        source_id = link[SOURCE_LABEL]
        target_id = link[TARGET_LABEL]
        source_port = link[SOURCE_PORT_LABEL]
        target_port = link[TARGET_PORT_LABEL]

        # Handle task-to-task connections
        if source_id is not None and target_id is not None:
            from_task = task_name_mapping[str(source_id)]
            to_task = task_name_mapping[str(target_id)]

            # Create output socket on source task
            from_socket = from_task.add_output("workgraph.any", name=source_port, metadata={"is_function_output": True})

            # Create or get input socket on target task
            if target_port not in to_task.inputs:
                to_socket = to_task.add_input("workgraph.any", name=target_port)
            else:
                to_socket = to_task.inputs[target_port]

            # Connect the tasks
            wg.add_link(from_socket, to_socket)

        # Handle dangling outputs (no target)
        elif source_id is not None and target_id is None:
            from_task = task_name_mapping[str(source_id)]
            from_task.add_output("workgraph.any", name=source_port, metadata={"is_function_output": True})

    return wg


def write_workflow_json(wg: "WorkGraph", file_name: str) -> dict:
    """
    Write a WorkGraph to a JSON file.

    Args:
        wg: WorkGraph object to serialize
        file_name: Path where the JSON file will be written

    Returns:
        Dictionary representation of the serialized workflow
    """
    data = {NODES_LABEL: [], EDGES_LABEL: []}
    node_name_mapping = {}

    # Add all process nodes first
    for i, node in enumerate(wg.tasks):
        # Store node index for later reference
        node_name_mapping[node.name] = i

        # Get executor info and build full callable name
        executor = node.get_executor()
        callable_name = f"{executor['module_path']}.{executor['callable_name']}"

        # Add node to data structure
        data[NODES_LABEL].append({"id": i, "function": callable_name})

    # Create edges from WorkGraph links
    for link in wg.links:
        link_data = link.to_dict()

        # Handle default result case
        from_socket = link_data.pop("from_socket")
        if from_socket == "result":
            from_socket = None

        # Convert to expected format
        edge = {
            SOURCE_LABEL: node_name_mapping[link_data.pop("from_node")],
            SOURCE_PORT_LABEL: from_socket,
            TARGET_LABEL: node_name_mapping[link_data.pop("to_node")],
            TARGET_PORT_LABEL: link_data.pop("to_socket"),
        }

        data[EDGES_LABEL].append(edge)

    # Define sockets to ignore when adding workflow I/O connections
    wg_input_sockets = {
        "_wait",
        "metadata",
        "function_data",
        "process_label",
        "function_inputs",
        "deserializers",
        "serializers",
    }
    wg_output_sockets = {"_wait", "_outputs", "exit_code"}

    # Handle first node's inputs (external inputs to workflow)
    first_node = wg.tasks[0]
    first_node_id = node_name_mapping[first_node.name]

    for input_name in first_node.inputs._sockets:
        if input_name not in wg_input_sockets:
            data[EDGES_LABEL].append(
                {
                    SOURCE_LABEL: None,
                    SOURCE_PORT_LABEL: None,
                    TARGET_LABEL: first_node_id,
                    TARGET_PORT_LABEL: input_name,
                }
            )

    # Handle last node's outputs (workflow outputs)
    last_node = wg.tasks[-1]
    last_node_id = node_name_mapping[last_node.name]

    for output_name in last_node.outputs._sockets:
        if output_name not in wg_output_sockets:
            data[EDGES_LABEL].append(
                {
                    SOURCE_LABEL: last_node_id,
                    SOURCE_PORT_LABEL: output_name,
                    TARGET_LABEL: None,
                    TARGET_PORT_LABEL: None,
                }
            )

    # Write the data to file
    import ipdb; ipdb.set_trace()

    with open(file_name, "w") as f:
        json.dump(data, f, indent=2)

    return data
