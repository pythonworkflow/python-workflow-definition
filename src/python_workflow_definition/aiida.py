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


def load_workflow_json_nested(file_name: str) -> WorkGraph:
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
            sub_wg = load_workflow_json_nested(file_name=str(workflow_path))

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


def load_workflow_json(file_name: str) -> WorkGraph:

    data = PythonWorkflowDefinitionWorkflow.load_json_file(file_name=file_name)

    wg = WorkGraph()
    task_name_mapping = {}

    for id, identifier in convert_nodes_list_to_dict(
        nodes_list=data[NODES_LABEL]
    ).items():
        if isinstance(identifier, str) and "." in identifier:
            p, m = identifier.rsplit(".", 1)
            mod = import_module(p)
            func = getattr(mod, m)
            decorated_func = task(outputs=namespace())(func)
            new_task = wg.add_task(decorated_func)
            new_task.spec = replace(new_task.spec, schema_source=SchemaSource.EMBEDDED)
            task_name_mapping[id] = new_task
        else:
            # data task
            data_node = general_serializer(identifier)
            task_name_mapping[id] = data_node

    # add links
    for link in data[EDGES_LABEL]:
        # TODO: continue here
        to_task = task_name_mapping[str(link[TARGET_LABEL])]
        # if the input is not exit, it means we pass the data into to the kwargs
        # in this case, we add the input socket
        if isinstance(to_task, Task):
            if link[TARGET_PORT_LABEL] not in to_task.inputs:
                to_socket = to_task.add_input_spec(
                    "workgraph.any", name=link[TARGET_PORT_LABEL]
                )
            else:
                to_socket = to_task.inputs[link[TARGET_PORT_LABEL]]
        from_task = task_name_mapping[str(link[SOURCE_LABEL])]
        if isinstance(from_task, orm.Data):
            to_socket.value = from_task
        else:
            try:
                if link[SOURCE_PORT_LABEL] is None:
                    link[SOURCE_PORT_LABEL] = "result"
                # because we are not define the outputs explicitly during the pythonjob creation
                # we add it here, and assume the output exit
                if link[SOURCE_PORT_LABEL] not in from_task.outputs:
                    # if str(link["sourcePort"]) not in from_task.outputs:
                    from_socket = from_task.add_output_spec(
                        "workgraph.any",
                        name=link[SOURCE_PORT_LABEL],
                    )
                else:
                    from_socket = from_task.outputs[link[SOURCE_PORT_LABEL]]
                if isinstance(to_task, Task):
                    wg.add_link(from_socket, to_socket)
            except Exception as e:
                traceback.print_exc()
                print("Failed to link", link, "with error:", e)
    return wg


def write_workflow_json(wg: WorkGraph, file_name: str) -> dict:
    data = {NODES_LABEL: [], EDGES_LABEL: []}
    node_name_mapping = {}
    data_node_name_mapping = {}
    i = 0
    GRAPH_LEVEL_NAMES = ["graph_inputs", "graph_outputs", "graph_ctx"]

    for node in wg.tasks:

        if node.name in GRAPH_LEVEL_NAMES:
            continue

        node_name_mapping[node.name] = i

        executor = node.get_executor()
        callable_name = f"{executor.module_path}.{executor.callable_name}"

        data[NODES_LABEL].append({"id": i, "type": "function", "value": callable_name})
        i += 1

    for link in wg.links:
        link_data = link.to_dict()
        # if the from socket is the default result, we set it to None
        if link_data["from_socket"] == "result":
            link_data["from_socket"] = None
        link_data[TARGET_LABEL] = node_name_mapping[link_data.pop("to_node")]
        link_data[TARGET_PORT_LABEL] = link_data.pop("to_socket")
        link_data[SOURCE_LABEL] = node_name_mapping[link_data.pop("from_node")]
        link_data[SOURCE_PORT_LABEL] = link_data.pop("from_socket")
        data[EDGES_LABEL].append(link_data)

    for node in wg.tasks:
        for input in node.inputs:
            # assume namespace is not used as input
            if isinstance(input, TaskSocketNamespace):
                continue
            if isinstance(input.value, orm.Data):
                if input.value.uuid not in data_node_name_mapping:
                    if isinstance(input.value, orm.List):
                        raw_value = input.value.get_list()
                    elif isinstance(input.value, orm.Dict):
                        raw_value = input.value.get_dict()
                        # unknow reason, there is a key "node_type" in the dict
                        raw_value.pop("node_type", None)
                    else:
                        raw_value = input.value.value
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

    data[VERSION_LABEL] = VERSION_NUMBER
    PythonWorkflowDefinitionWorkflow(
        **set_result_node(workflow_dict=update_node_names(workflow_dict=data))
    ).dump_json_file(file_name=file_name, indent=2)
