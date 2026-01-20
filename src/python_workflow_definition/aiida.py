from importlib import import_module
import traceback
from pathlib import Path
from typing import Any

from aiida import orm
from aiida_pythonjob.data.serializer import general_serializer
from aiida_workgraph import WorkGraph, task, Task, namespace
from aiida_workgraph.socket import TaskSocketNamespace
from dataclasses import replace
from node_graph.node_spec import SchemaSource
from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow
from python_workflow_definition.shared import (
    convert_nodes_list_to_dict,
    update_node_names,
    set_result_node,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
    VERSION_NUMBER,
    VERSION_LABEL,
)


def load_workflow_json(file_name: str) -> WorkGraph:
    """Load a workflow from JSON with support for nested workflows.

    This function recursively loads workflows, properly exposing inputs/outputs
    of nested workflows so they can be connected in the parent workflow.
    """
    data = PythonWorkflowDefinitionWorkflow.load_json_file(file_name=file_name)
    parent_dir = Path(file_name).parent

    # Check if this workflow has workflow-type nodes (nested workflows)
    has_nested = any(n["type"] == "workflow" for n in data[NODES_LABEL])

    # Extract input/output nodes for this workflow
    input_nodes = [n for n in data[NODES_LABEL] if n["type"] == "input"]
    output_nodes = [n for n in data[NODES_LABEL] if n["type"] == "output"]

    # Create WorkGraph with proper inputs/outputs if this will be used as a sub-workflow
    if has_nested or input_nodes or output_nodes:
        # Build namespace for inputs
        inputs_ns = {}
        for inp_node in input_nodes:
            inputs_ns[inp_node["name"]] = namespace

        # Build namespace for outputs
        outputs_ns = {}
        for out_node in output_nodes:
            outputs_ns[out_node["name"]] = namespace

        wg = WorkGraph(
            inputs=namespace(**inputs_ns) if inputs_ns else None,
            outputs=namespace(**outputs_ns) if outputs_ns else None,
        )
    else:
        wg = WorkGraph()

    task_name_mapping = {}
    input_node_mapping = {}  # Map input node IDs to their names

    # Process nodes
    for node in data[NODES_LABEL]:
        node_id = str(node["id"])
        node_type = node["type"]

        if node_type == "function":
            # Handle function nodes
            func_path = node["value"]
            p, m = func_path.rsplit(".", 1)
            mod = import_module(p)
            func = getattr(mod, m)
            decorated_func = task(outputs=namespace())(func)
            new_task = wg.add_task(decorated_func)
            new_task.spec = replace(new_task.spec, schema_source=SchemaSource.EMBEDDED)
            task_name_mapping[node_id] = new_task

        elif node_type == "workflow":
            # Handle nested workflow nodes
            workflow_file = node["value"]
            # Resolve path relative to parent workflow file
            workflow_path = parent_dir / workflow_file

            # Recursively load the sub-workflow with proper input/output exposure
            sub_wg = load_workflow_json(file_name=str(workflow_path))

            # Add the sub-workflow as a task - it will automatically have the right inputs/outputs
            workflow_task = wg.add_task(sub_wg)
            task_name_mapping[node_id] = workflow_task

        elif node_type == "input":
            # Store input node info for later connection to wg.inputs
            input_node_mapping[node_id] = node["name"]
            # Set default value on the workflow's exposed input if provided
            if "value" in node and node["value"] is not None:
                value = node["value"]
                data_node = general_serializer(value)
                # Set the default on the workflow's exposed input
                if hasattr(wg.inputs, node["name"]):
                    setattr(wg.inputs, node["name"], data_node)
                # Also store in mapping for direct connections in non-nested contexts
                task_name_mapping[node_id] = data_node

        elif node_type == "output":
            # Output nodes will be handled when setting wg.outputs
            pass

    # Add links
    for link in data[EDGES_LABEL]:
        source_id = str(link[SOURCE_LABEL])
        target_id = str(link[TARGET_LABEL])
        source_port = link[SOURCE_PORT_LABEL]
        target_port = link[TARGET_PORT_LABEL]

        # Handle output node connections
        target_node = next(
            (n for n in data[NODES_LABEL] if str(n["id"]) == target_id), None
        )
        if target_node and target_node["type"] == "output":
            # This connects a task output to a workflow output
            from_task = task_name_mapping.get(source_id)
            if from_task and isinstance(from_task, Task):
                if source_port is None:
                    source_port = "result"
                if source_port not in from_task.outputs:
                    from_socket = from_task.add_output_spec(
                        "workgraph.any", name=source_port
                    )
                else:
                    from_socket = from_task.outputs[source_port]

                # Set the workflow output
                output_name = target_node["name"]
                if hasattr(wg.outputs, output_name):
                    setattr(wg.outputs, output_name, from_socket)
            continue

        # Handle input node connections
        source_node = next(
            (n for n in data[NODES_LABEL] if str(n["id"]) == source_id), None
        )
        if source_node and source_node["type"] == "input":
            to_task = task_name_mapping.get(target_id)
            if to_task and isinstance(to_task, Task):
                # Add target socket if it doesn't exist
                if target_port not in to_task.inputs:
                    to_socket = to_task.add_input_spec(
                        "workgraph.any", name=target_port
                    )
                else:
                    to_socket = to_task.inputs[target_port]

                # Connect from workflow input or from data node
                if hasattr(wg.inputs, source_node["name"]):
                    # Connect from workflow input
                    from_socket = getattr(wg.inputs, source_node["name"])
                    wg.add_link(from_socket, to_socket)
                elif source_id in task_name_mapping:
                    # Connect from data node (has a value)
                    data_node = task_name_mapping[source_id]
                    if isinstance(data_node, orm.Data):
                        to_socket.value = data_node
            continue

        # Handle regular task-to-task connections
        to_task = task_name_mapping.get(target_id)
        from_task = task_name_mapping.get(source_id)

        if to_task is None or from_task is None:
            continue

        if isinstance(to_task, Task):
            # Add target socket if needed
            if target_port not in to_task.inputs:
                to_socket = to_task.add_input_spec("workgraph.any", name=target_port)
            else:
                to_socket = to_task.inputs[target_port]

            if isinstance(from_task, orm.Data):
                to_socket.value = from_task
            elif isinstance(from_task, Task):
                try:
                    if source_port is None:
                        source_port = "result"

                    # Add source socket if needed
                    if source_port not in from_task.outputs:
                        from_socket = from_task.add_output_spec(
                            "workgraph.any", name=source_port
                        )
                    else:
                        from_socket = from_task.outputs[source_port]

                    wg.add_link(from_socket, to_socket)
                except Exception as e:
                    traceback.print_exc()
                    print("Failed to link", link, "with error:", e)

    return wg


def write_workflow_json(
    wg: WorkGraph, file_name: str, _nested_counter: dict = None
) -> dict:
    """Write a WorkGraph to JSON file(s), with support for nested workflows.

    Args:
        wg: The WorkGraph to write
        file_name: Output JSON file path
        _nested_counter: Internal counter for generating nested workflow filenames
    """
    if _nested_counter is None:
        _nested_counter = {"count": 0}

    data = {NODES_LABEL: [], EDGES_LABEL: []}
    node_name_mapping = {}
    data_node_name_mapping = {}
    i = 0
    GRAPH_LEVEL_NAMES = ["graph_inputs", "graph_outputs", "graph_ctx"]
    parent_dir = Path(file_name).parent

    for node in wg.tasks:

        if node.name in GRAPH_LEVEL_NAMES:
            continue

        node_name_mapping[node.name] = i

        # Try to determine if this is a nested WorkGraph or a regular function task
        executor = node.get_executor()

        # Check if this is a SubGraph-type task (truly nested workflow)
        # Note: GraphTask (from @task.graph) is flattened and can't be exported as nested
        is_graph = False
        nested_wg = None

        # Method 1: Check if this is a SubGraphTask (has spec.node_type == 'SubGraph')
        if hasattr(node, "spec") and hasattr(node.spec, "node_type"):
            if node.spec.node_type == "SubGraph" and hasattr(node, "tasks"):
                is_graph = True
                nested_wg = node

        # Method 2: Check if the node itself has tasks attribute (indicating it's a subgraph)
        if not is_graph and hasattr(node, "tasks"):
            # Make sure it has actual tasks (not just an empty list)
            tasks_list = [t for t in node.tasks if t.name not in GRAPH_LEVEL_NAMES]
            if len(tasks_list) > 0:
                is_graph = True
                nested_wg = node

        # Method 3: Check if executor is a WorkGraph instance
        if not is_graph and isinstance(executor, WorkGraph):
            is_graph = True
            nested_wg = executor

        if is_graph and nested_wg is not None:
            # This is a nested workflow - write it to a separate file
            _nested_counter["count"] += 1
            nested_filename = f"nested_{_nested_counter['count']}.json"
            nested_path = parent_dir / nested_filename

            # Recursively write the nested workflow
            write_workflow_json(nested_wg, str(nested_path), _nested_counter)

            data[NODES_LABEL].append(
                {"id": i, "type": "workflow", "value": nested_filename}
            )
        else:
            # This is a regular function task
            # Try to get the module path from different sources
            module_path = executor.module_path

            # If module_path is None, try to extract from pickled_callable
            if module_path is None and hasattr(executor, "pickled_callable"):
                # For pickled callables, try to get the original function
                try:
                    import cloudpickle

                    func = cloudpickle.loads(executor.pickled_callable)
                    if hasattr(func, "__module__"):
                        module_path = func.__module__
                except Exception:
                    pass  # Keep module_path as None

            callable_name = f"{module_path}.{executor.callable_name}"
            data[NODES_LABEL].append(
                {"id": i, "type": "function", "value": callable_name}
            )

        i += 1

    # Handle workflow-level inputs (create input nodes)
    input_name_mapping = {}
    INTERNAL_SOCKETS = [
        "metadata",
        "_wait",
        "_outputs",
        "function_data",
        "function_inputs",
    ]

    # First, try to get default values from graph_inputs task (for SubGraphTasks)
    graph_inputs_defaults = {}
    for task in wg.tasks:
        if task.name == "graph_inputs" and hasattr(task, "outputs"):
            for output in task.outputs:
                if hasattr(output, "_name") and hasattr(output, "value"):
                    output_name = output._name
                    if output.value is not None and isinstance(output.value, orm.Data):
                        if isinstance(output.value, orm.List):
                            graph_inputs_defaults[output_name] = output.value.get_list()
                        elif isinstance(output.value, orm.Dict):
                            val = output.value.get_dict()
                            val.pop("node_type", None)
                            graph_inputs_defaults[output_name] = val
                        else:
                            val = output.value.value
                            # Convert float to int if it's a whole number
                            if isinstance(val, float) and val.is_integer():
                                val = int(val)
                            graph_inputs_defaults[output_name] = val

    if (
        hasattr(wg, "inputs")
        and wg.inputs is not None
        and hasattr(wg.inputs, "_sockets")
    ):
        for input_name, input_socket in wg.inputs._sockets.items():
            # Skip metadata and other special namespaces/internal sockets
            if isinstance(input_socket, TaskSocketNamespace):
                continue
            if input_name in INTERNAL_SOCKETS or input_name.startswith("_"):
                continue

            # Check if this input has a default value
            # First try graph_inputs defaults, then the socket value
            input_value = None
            if input_name in graph_inputs_defaults:
                input_value = graph_inputs_defaults[input_name]
            elif hasattr(input_socket, "value") and input_socket.value is not None:
                if isinstance(input_socket.value, orm.Data):
                    if isinstance(input_socket.value, orm.List):
                        input_value = input_socket.value.get_list()
                    elif isinstance(input_socket.value, orm.Dict):
                        input_value = input_socket.value.get_dict()
                        input_value.pop("node_type", None)
                    else:
                        input_value = input_socket.value.value
                        # Convert float to int if it's a whole number
                        if isinstance(input_value, float) and input_value.is_integer():
                            input_value = int(input_value)

            # Create input node
            node_data = {"id": i, "type": "input", "name": input_name}
            if input_value is not None:
                node_data["value"] = input_value
            data[NODES_LABEL].append(node_data)
            input_name_mapping[input_name] = i
            i += 1

    # Handle workflow-level outputs (create output nodes)
    output_name_mapping = {}
    if (
        hasattr(wg, "outputs")
        and wg.outputs is not None
        and hasattr(wg.outputs, "_sockets")
    ):
        for output_name, output_socket in wg.outputs._sockets.items():
            # Skip metadata and other special namespaces/internal sockets
            if isinstance(output_socket, TaskSocketNamespace):
                continue
            if output_name in INTERNAL_SOCKETS or output_name.startswith("_"):
                continue

            data[NODES_LABEL].append({"id": i, "type": "output", "name": output_name})
            output_name_mapping[output_name] = i
            i += 1

    for link in wg.links:
        link_data = link.to_dict()
        from_node_name = link_data.pop("from_node")
        to_node_name = link_data.pop("to_node")
        from_socket = link_data.pop("from_socket")
        to_socket = link_data.pop("to_socket")

        # Handle links from graph_inputs
        if from_node_name == "graph_inputs":
            if from_socket in input_name_mapping:
                link_data[SOURCE_LABEL] = input_name_mapping[from_socket]
                link_data[SOURCE_PORT_LABEL] = None
            else:
                continue
        else:
            link_data[SOURCE_LABEL] = node_name_mapping.get(from_node_name)
            # if the from socket is the default result, we set it to None
            link_data[SOURCE_PORT_LABEL] = (
                None if from_socket == "result" else from_socket
            )

        # Handle links to graph_outputs
        if to_node_name == "graph_outputs":
            if to_socket in output_name_mapping:
                link_data[TARGET_LABEL] = output_name_mapping[to_socket]
                link_data[TARGET_PORT_LABEL] = None
            else:
                continue
        else:
            link_data[TARGET_LABEL] = node_name_mapping.get(to_node_name)
            link_data[TARGET_PORT_LABEL] = to_socket

        # Only add link if both source and target are valid
        if link_data[SOURCE_LABEL] is not None and link_data[TARGET_LABEL] is not None:
            data[EDGES_LABEL].append(link_data)

    # Build set of links that are already handled (to avoid duplicates)
    existing_links = {
        (link[SOURCE_LABEL], link[TARGET_LABEL], link[TARGET_PORT_LABEL])
        for link in data[EDGES_LABEL]
    }

    for node in wg.tasks:
        if node.name in GRAPH_LEVEL_NAMES:
            continue

        for input in node.inputs:
            # assume namespace is not used as input
            if isinstance(input, TaskSocketNamespace):
                continue
            if isinstance(input.value, orm.Data):
                # Check if this input is already connected (e.g., from workflow inputs)
                node_id = node_name_mapping[node.name]
                if any(
                    link[1] == node_id and link[2] == input._name
                    for link in existing_links
                ):
                    continue

                if input.value.uuid not in data_node_name_mapping:
                    if isinstance(input.value, orm.List):
                        raw_value = input.value.get_list()
                    elif isinstance(input.value, orm.Dict):
                        raw_value = input.value.get_dict()
                        # unknow reason, there is a key "node_type" in the dict
                        raw_value.pop("node_type", None)
                    else:
                        raw_value = input.value.value
                        # Convert float to int if it's a whole number
                        if isinstance(raw_value, float) and raw_value.is_integer():
                            raw_value = int(raw_value)
                    data[NODES_LABEL].append(
                        {"id": i, "type": "input", "value": raw_value}
                    )
                    input_node_name = i
                    data_node_name_mapping[input.value.uuid] = input_node_name
                    i += 1
                else:
                    input_node_name = data_node_name_mapping[input.value.uuid]
                data[EDGES_LABEL].append(
                    {
                        TARGET_LABEL: node_name_mapping[node.name],
                        TARGET_PORT_LABEL: input._name,
                        SOURCE_LABEL: input_node_name,
                        SOURCE_PORT_LABEL: None,
                    }
                )
                existing_links.add(
                    (input_node_name, node_name_mapping[node.name], input._name)
                )

    data[VERSION_LABEL] = VERSION_NUMBER

    # Check if we have named input nodes (from workflow-level inputs)
    has_named_inputs = any(
        node.get("type") == "input" and "name" in node for node in data[NODES_LABEL]
    )
    has_output_nodes = any(node.get("type") == "output" for node in data[NODES_LABEL])

    if has_named_inputs or has_output_nodes:
        # New-style workflow with exposed inputs/outputs - names are already set, don't rename
        workflow_data = data
    else:
        # Old-style workflow - need to update names and add result node
        workflow_data = set_result_node(
            workflow_dict=update_node_names(workflow_dict=data)
        )

    PythonWorkflowDefinitionWorkflow(**workflow_data).dump_json_file(
        file_name=file_name, indent=2
    )
