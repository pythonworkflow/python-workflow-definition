from importlib import import_module
import json
import traceback

from aiida import orm
from aiida_pythonjob.data.serializer import general_serializer
from aiida_workgraph import WorkGraph, task
from aiida_workgraph.socket import TaskSocketNamespace

from python_workflow_definition.shared import (
    convert_nodes_list_to_dict,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
)


def load_workflow_json(file_name: str) -> WorkGraph:
    with open(file_name) as f:
        data = json.load(f)

    wg = WorkGraph()
    task_name_mapping = {}

    for id, identifier in convert_nodes_list_to_dict(
        nodes_list=data[NODES_LABEL]
    ).items():
        if isinstance(identifier, str) and "." in identifier:
            p, m = identifier.rsplit(".", 1)
            mod = import_module(p)
            func = getattr(mod, m)
            wg.add_task(func)
            # Remove the default result output, because we will add the outputs later from the data in the link
            del wg.tasks[-1].outputs["result"]
            task_name_mapping[id] = wg.tasks[-1]
        else:
            # data task
            data_node = general_serializer(identifier)
            task_name_mapping[id] = data_node

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
                        metadata={"is_function_output": True},
                    )
                else:
                    from_socket = from_task.outputs[link[SOURCE_PORT_LABEL]]

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
    for node in wg.tasks:
        executor = node.get_executor()
        node_name_mapping[node.name] = i

        callable_name = executor["callable_name"]
        callable_name = f"{executor['module_path']}.{callable_name}"
        data[NODES_LABEL].append({"id": i, "function": callable_name})
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
                    data[NODES_LABEL].append({"id": i, "value": raw_value})
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
    with open(file_name, "w") as f:
        # json.dump({"nodes": data[], "edges": edges_new_lst}, f)
        json.dump(data, f, indent=2)

    return data
