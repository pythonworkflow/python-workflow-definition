from importlib import import_module
import traceback

from aiida import orm
from aiida_pythonjob.data.serializer import general_serializer
from aiida_workgraph import WorkGraph, task
from aiida_workgraph.socket import TaskSocketNamespace

from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow
from python_workflow_definition.expression_eval import evaluate_condition
from python_workflow_definition.shared import (
    convert_nodes_list_to_dict,
    update_node_names,
    remove_result,
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


def _create_while_loop_task(while_node_data: dict):
    """Create a recursive task.graph from while node definition.

    Stores the original while_node_data in the task's properties for later export.
    """
    # Extract while node components
    condition_func = while_node_data.get("conditionFunction")
    condition_expr = while_node_data.get("conditionExpression")
    body_func = while_node_data.get("bodyFunction")
    body_workflow = while_node_data.get("bodyWorkflow")
    max_iterations = while_node_data.get("maxIterations", 1000)
    state_vars = while_node_data.get("stateVars", [])

    # Import condition function if needed
    if condition_func:
        p, m = condition_func.rsplit(".", 1)
        mod = import_module(p)
        check_condition = getattr(mod, m)
    else:
        # Create condition function from expression
        def check_condition(**kwargs):
            return evaluate_condition(condition_expr, kwargs)

    # Import body function if using function-based body
    if body_func:
        p, m = body_func.rsplit(".", 1)
        mod = import_module(p)
        body = getattr(mod, m)
        body_task = task(body)

        # Create recursive task.graph
        @task.graph
        def while_loop(**kwargs):
            iteration = kwargs.pop("_iteration", 0)

            # Extract state based on stateVars
            if state_vars:
                state = {var: kwargs[var] for var in state_vars if var in kwargs}
            else:
                # Backward compatibility: if no stateVars, use all kwargs
                state = kwargs

            # Check termination conditions
            if iteration >= max_iterations:
                return state
            if not check_condition(**state):
                return state

            # Call body as a task to get outputs properly
            result = body_task(**state)

            # Extract the actual result
            if hasattr(result, 'result'):
                result_value = result.result
            else:
                result_value = result

            # Map result back to state variables
            if state_vars:
                if isinstance(result_value, dict):
                    # Body returned a dict - update state with returned values
                    result_data = {**state, **result_value}
                elif len(state_vars) == 1:
                    # Single state var - wrap the result
                    result_data = {state_vars[0]: result_value}
                else:
                    # Multiple state vars but got single value - try to use as-is
                    # This handles cases where result might be a dict-like object
                    result_data = result_value if isinstance(result_value, dict) else state
            else:
                # No stateVars specified - assume result is a dict
                result_data = result_value if isinstance(result_value, dict) else {"result": result_value}

            result_data["_iteration"] = iteration + 1
            return while_loop(**result_data)

        # Store metadata for export
        while_loop._while_node_metadata = while_node_data
        return while_loop
    elif body_workflow:
        # Handle nested workflow body
        # First, recursively load the body workflow
        nested_wg = load_workflow_json_from_dict(body_workflow)

        # Create recursive task.graph with nested workflow
        @task.graph
        def while_loop(**kwargs):
            iteration = kwargs.pop("_iteration", 0)

            # Extract state based on stateVars
            if state_vars:
                state = {var: kwargs[var] for var in state_vars if var in kwargs}
            else:
                # Backward compatibility: if no stateVars, use all kwargs
                state = kwargs

            # Check termination conditions
            if iteration >= max_iterations:
                return state
            if not check_condition(**state):
                return state

            # Execute the nested workflow with the current state
            result = nested_wg(**state)

            # Extract the actual result
            if hasattr(result, 'result'):
                result_value = result.result
            else:
                result_value = result

            # Map result back to state variables
            if state_vars:
                if isinstance(result_value, dict):
                    # Workflow returned a dict - update state with returned values
                    result_data = {**state, **result_value}
                elif len(state_vars) == 1:
                    # Single state var - wrap the result
                    result_data = {state_vars[0]: result_value}
                else:
                    # Multiple state vars but got single value
                    result_data = result_value if isinstance(result_value, dict) else state
            else:
                # No stateVars specified - assume result is a dict
                result_data = result_value if isinstance(result_value, dict) else {"result": result_value}

            result_data["_iteration"] = iteration + 1
            return while_loop(**result_data)

        # Store metadata for export
        while_loop._while_node_metadata = while_node_data
        return while_loop
    else:
        raise ValueError("While node must have either bodyFunction or bodyWorkflow")


def load_workflow_json_from_dict(workflow_dict: dict) -> WorkGraph:
    """Load a WorkGraph from a workflow dictionary (used for nested workflows)."""
    data = remove_result(workflow_dict=workflow_dict)

    wg = WorkGraph()
    task_name_mapping = {}

    for node in data[NODES_LABEL]:
        id = str(node["id"])
        node_type = node["type"]

        if node_type == "function":
            identifier = node["value"]
            p, m = identifier.rsplit(".", 1)
            mod = import_module(p)
            func = getattr(mod, m)
            wg.add_task(func)
            # Remove the default result output, because we will add the outputs later from the data in the link
            del wg.tasks[-1].outputs["result"]
            task_name_mapping[id] = wg.tasks[-1]
        elif node_type == "while":
            # Create while loop task
            while_task_func = _create_while_loop_task(node)
            wg.add_task(while_task_func)
            task_obj = wg.tasks[-1]

            # Remove default result output
            if "result" in task_obj.outputs:
                del task_obj.outputs["result"]

            # Create explicit input/output sockets based on stateVars
            state_vars = node.get("stateVars", [])
            if state_vars:
                # Add input sockets for each state variable
                for var in state_vars:
                    if var not in task_obj.inputs:
                        task_obj.add_input("workgraph.any", name=var)

                # Add output sockets for each state variable
                for var in state_vars:
                    if var not in task_obj.outputs:
                        task_obj.add_output("workgraph.any", name=var)

            task_name_mapping[id] = task_obj
        elif node_type == "input":
            # data task
            data_node = general_serializer(node["value"])
            task_name_mapping[id] = data_node
        elif node_type == "output":
            # output nodes are handled via edges
            pass

    # add links
    for link in data[EDGES_LABEL]:
        to_task = task_name_mapping[str(link[TARGET_LABEL])]
        # if the input is not exit, it means we pass the data into to the kwargs
        # in this case, we add the input socket
        if link[TARGET_PORT_LABEL] not in to_task.inputs:
            to_socket = to_task.add_input("workgraph.any", name=link[TARGET_PORT_LABEL])
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
                    from_socket = from_task.add_output(
                        "workgraph.any",
                        name=link[SOURCE_PORT_LABEL],
                        # name=str(link["sourcePort"]),
                    )
                else:
                    from_socket = from_task.outputs[link[SOURCE_PORT_LABEL]]

                wg.add_link(from_socket, to_socket)
            except Exception as e:
                traceback.print_exc()
                print("Failed to link", link, "with error:", e)
    return wg


def load_workflow_json(file_name: str) -> WorkGraph:
    """Load a WorkGraph from a JSON file."""
    data = remove_result(
        workflow_dict=PythonWorkflowDefinitionWorkflow.load_json_file(
            file_name=file_name
        )
    )
    return load_workflow_json_from_dict(data)


def write_workflow_json(wg: WorkGraph, file_name: str) -> dict:
    from node_graph.executor import RuntimeExecutor

    data = {NODES_LABEL: [], EDGES_LABEL: []}
    node_name_mapping = {}
    data_node_name_mapping = {}
    i = 0

    # Special WorkGraph internal nodes that should be converted to input/output nodes
    INTERNAL_NODES = ['graph_inputs', 'graph_outputs', 'graph_ctx']

    for node in wg.tasks:
        # Handle internal WorkGraph meta-tasks
        if node.name in INTERNAL_NODES:
            # For now, we skip these as they're handled differently
            # In nested workflows, these become explicit input/output nodes
            # TODO: Convert graph_inputs to input nodes and graph_outputs to output nodes
            continue

        node_name_mapping[node.name] = i

        # Get the executor
        executor_spec = node.get_executor()

        # Try to get the actual callable to check for while loop metadata
        is_while_loop = False
        while_metadata = None

        if executor_spec:
            try:
                # Get the actual callable from the executor
                runtime_exec = RuntimeExecutor(**executor_spec.to_dict())
                callable_obj = runtime_exec.callable

                # Check if this callable has while loop metadata attached
                if hasattr(callable_obj, '_while_node_metadata'):
                    is_while_loop = True
                    while_metadata = callable_obj._while_node_metadata
            except Exception:
                # If we can't get the callable, it's not a while loop
                pass

        if is_while_loop and while_metadata:
            # This is a while loop - use the stored metadata
            node_dict = {"id": i, "type": "while"}

            # Copy all the while loop configuration from metadata
            if 'conditionFunction' in while_metadata:
                node_dict['conditionFunction'] = while_metadata['conditionFunction']
            if 'conditionExpression' in while_metadata:
                node_dict['conditionExpression'] = while_metadata['conditionExpression']
            if 'bodyFunction' in while_metadata:
                node_dict['bodyFunction'] = while_metadata['bodyFunction']
            if 'bodyWorkflow' in while_metadata:
                node_dict['bodyWorkflow'] = while_metadata['bodyWorkflow']
            if 'maxIterations' in while_metadata:
                node_dict['maxIterations'] = while_metadata['maxIterations']

            data[NODES_LABEL].append(node_dict)
        elif executor_spec is None:
            # This is a graph task (task.graph) without while loop metadata
            # This typically happens when trying to export a manually-created @task.graph function
            raise NotImplementedError(
                f"Cannot export task '{node.name}' - it appears to be a @task.graph function "
                f"created manually, not loaded from JSON.\n\n"
                f"The write_workflow_json function currently only supports exporting:\n"
                f"1. Regular function tasks (decorated with @task)\n"
                f"2. While loops that were originally loaded from JSON using load_workflow_json\n\n"
                f"To export this workflow, you need to first create it using the JSON format "
                f"and load it with load_workflow_json, or manually construct a while loop node "
                f"definition in the JSON format."
            )
        else:
            # Regular function node
            callable_name = executor_spec["callable_name"]
            callable_name = f"{executor_spec['module_path']}.{callable_name}"
            data[NODES_LABEL].append({"id": i, "type": "function", "value": callable_name})
        i += 1

    for link in wg.links:
        link_data = link.to_dict()

        # Skip links involving internal nodes
        if link_data["from_node"] in INTERNAL_NODES or link_data["to_node"] in INTERNAL_NODES:
            continue

        # if the from socket is the default result, we set it to None
        if link_data["from_socket"] == "result":
            link_data["from_socket"] = None
        link_data[TARGET_LABEL] = node_name_mapping[link_data.pop("to_node")]
        link_data[TARGET_PORT_LABEL] = link_data.pop("to_socket")
        link_data[SOURCE_LABEL] = node_name_mapping[link_data.pop("from_node")]
        link_data[SOURCE_PORT_LABEL] = link_data.pop("from_socket")
        data[EDGES_LABEL].append(link_data)

    for node in wg.tasks:
        # Skip internal nodes when processing inputs
        if node.name in INTERNAL_NODES:
            continue

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
