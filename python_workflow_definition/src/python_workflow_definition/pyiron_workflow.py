from collections import Counter
from inspect import isfunction
from importlib import import_module
from typing import Any

import numpy as np
from pyiron_workflow import as_function_node, function_node, Workflow
from pyiron_workflow.api import Function

from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow
from python_workflow_definition.shared import (
    update_node_names,
    set_result_node,
    remove_result,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
    VERSION_NUMBER,
    VERSION_LABEL,
)


def get_linked_nodes(graph_dict):
    nodes_dict = {}
    node_mapping_dict = {}
    input_dict = {}
    for i, [k, v] in enumerate(graph_dict["nodes"].items()):
        if "inputs_to_dict_factory" in str(type(v)):
            nodes_dict[i] = get_dict
        else:
            nodes_dict[i] = v.node_function
        node_mapping_dict[k] = i
        input_dict[k] = {
            con.full_label: con.value
            for con in v.inputs.channel_dict.to_list()
            if len(con.connections) == 0
        }
    return nodes_dict, node_mapping_dict, input_dict


def extend_nodes_dict(nodes_dict, input_dict):
    i = len(nodes_dict)
    nodes_links_dict = {}
    nodes_values_str_lst = [str(s) for s in nodes_dict.values()]
    for val_dict in input_dict.values():
        for k, v in val_dict.items():
            if str(v) not in nodes_values_str_lst:
                nodes_dict[i] = v
                nodes_links_dict[k] = i
                i += 1
            else:
                nodes_links_dict[k] = {tv: tk for tk, tv in nodes_dict.items()}[v]
    return nodes_links_dict


def get_edges(graph_dict, node_mapping_dict, nodes_links_dict):
    edges_lst = []
    for link in list(graph_dict["edges"]["data"].keys()):
        source_combo, target_combo = link
        target, target_handle = target_combo.split(".")
        source, source_handle = source_combo.split(".")
        edges_lst.append(
            {
                TARGET_LABEL: node_mapping_dict[target],
                TARGET_PORT_LABEL: target_handle,
                SOURCE_LABEL: node_mapping_dict[source],
                SOURCE_PORT_LABEL: source_handle,
            }
        )

    for k, v in nodes_links_dict.items():
        target, target_handle = k.split(".")
        edges_lst.append(
            {
                TARGET_LABEL: node_mapping_dict[target],
                TARGET_PORT_LABEL: target_handle,
                SOURCE_LABEL: v,
                SOURCE_PORT_LABEL: None,
            }
        )
    return edges_lst


def write_workflow_json(graph_as_dict: dict, file_name: str = "workflow.json"):
    nodes_dict, node_mapping_dict, input_dict = get_linked_nodes(
        graph_dict=graph_as_dict
    )
    nodes_links_dict = extend_nodes_dict(nodes_dict=nodes_dict, input_dict=input_dict)
    edges_lst = get_edges(
        graph_dict=graph_as_dict,
        node_mapping_dict=node_mapping_dict,
        nodes_links_dict=nodes_links_dict,
    )

    pyiron_workflow_modules = {}
    for k, v in nodes_dict.items():
        if isfunction(v) and "pyiron_workflow" in v.__module__:
            pyiron_workflow_modules[k] = v

    cache_mapping_dict, remap_dict = {}, {}
    for k, v in nodes_dict.items():
        if not isfunction(v) and str(v) not in cache_mapping_dict:
            cache_mapping_dict[str(v)] = k
        elif not isfunction(v):
            remap_dict[k] = cache_mapping_dict[str(v)]

    item_node_lst = [
        e[SOURCE_LABEL]
        for e in edges_lst
        if e[TARGET_LABEL] in pyiron_workflow_modules.keys()
        and e[TARGET_PORT_LABEL] == "item"
    ]

    values_from_dict_lst = [
        k
        for k, v in nodes_dict.items()
        if isfunction(v) and v.__name__ == "get_values_from_dict"
    ]

    remap_get_list_dict = {}
    for e in edges_lst:
        if e[TARGET_LABEL] in values_from_dict_lst:
            remap_get_list_dict[e[SOURCE_LABEL]] = e[TARGET_LABEL]

    nodes_remaining_dict = {
        k: v
        for k, v in nodes_dict.items()
        if k not in pyiron_workflow_modules.keys()
        and k not in remap_dict.keys()
        and k not in item_node_lst
        and k not in remap_get_list_dict.values()
    }

    nodes_store_lst = []
    nodes_final_order_dict = {}
    for k, [i, v] in enumerate(nodes_remaining_dict.items()):
        if i in remap_get_list_dict:
            nodes_store_lst.append(
                {
                    "id": k,
                    "type": "function",
                    "value": "python_workflow_definition.shared.get_list",
                }
            )
        elif isfunction(v):
            mod = v.__module__
            if mod == "python_workflow_definition.pyiron_workflow":
                mod = "python_workflow_definition.shared"
            nodes_store_lst.append(
                {"id": k, "type": "function", "value": mod + "." + v.__name__}
            )
        elif isinstance(v, np.ndarray):
            nodes_store_lst.append({"id": k, "type": "input", "value": v.tolist()})
        else:
            nodes_store_lst.append({"id": k, "type": "input", "value": v})
        nodes_final_order_dict[i] = k

    remap_get_list_remove_edges = [
        edge for edge in edges_lst if edge[TARGET_LABEL] in remap_get_list_dict.values()
    ]

    edge_get_list_updated_lst = []
    for edge in edges_lst:
        if edge[SOURCE_LABEL] in remap_get_list_dict.values():
            connected_edge = [
                edge_con
                for edge_con in remap_get_list_remove_edges
                if edge_con[TARGET_LABEL] == edge[SOURCE_LABEL]
            ][-1]
            edge_updated = {
                TARGET_LABEL: edge[TARGET_LABEL],
                TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                SOURCE_LABEL: connected_edge[SOURCE_LABEL],
                SOURCE_PORT_LABEL: connected_edge[SOURCE_PORT_LABEL],
            }
            edge_get_list_updated_lst.append(edge_updated)
        elif edge[SOURCE_LABEL] in remap_dict.keys():
            edge_updated = {
                TARGET_LABEL: edge[TARGET_LABEL],
                TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                SOURCE_LABEL: remap_dict[edge[SOURCE_LABEL]],
                SOURCE_PORT_LABEL: edge[SOURCE_PORT_LABEL],
            }
            edge_get_list_updated_lst.append(edge_updated)
        elif edge[TARGET_LABEL] not in remap_get_list_dict.values():
            edge_get_list_updated_lst.append(edge)

    target_dict = {}
    for edge in edge_get_list_updated_lst:
        for k in pyiron_workflow_modules.keys():
            if k == edge[TARGET_LABEL]:
                if k not in target_dict:
                    target_dict[k] = []
                target_dict[k].append(edge)

    source_dict = {}
    for edge in edge_get_list_updated_lst:
        for k in pyiron_workflow_modules.keys():
            if k == edge[SOURCE_LABEL]:
                if k not in source_dict:
                    source_dict[k] = []
                source_dict[k].append(edge)

    edge_new_lst, nodes_to_delete = [], []
    for k in target_dict.keys():
        source, sourcehandle = None, None
        for edge in target_dict[k]:
            if edge[SOURCE_PORT_LABEL] is None:
                sourcehandle = nodes_dict[edge[SOURCE_LABEL]]
                nodes_to_delete.append(edge[SOURCE_LABEL])
            else:
                source = edge[SOURCE_LABEL]
        if "s_" == source_dict[k][-1][TARGET_PORT_LABEL][:2]:
            edge_new_lst.append(
                {
                    SOURCE_LABEL: nodes_final_order_dict[source],
                    SOURCE_PORT_LABEL: sourcehandle,
                    TARGET_LABEL: nodes_final_order_dict[
                        source_dict[k][-1][TARGET_LABEL]
                    ],
                    TARGET_PORT_LABEL: source_dict[k][-1][TARGET_PORT_LABEL][2:],
                }
            )
        else:
            edge_new_lst.append(
                {
                    SOURCE_LABEL: nodes_final_order_dict[source],
                    SOURCE_PORT_LABEL: sourcehandle,
                    TARGET_LABEL: nodes_final_order_dict[
                        source_dict[k][-1][TARGET_LABEL]
                    ],
                    TARGET_PORT_LABEL: source_dict[k][-1][TARGET_PORT_LABEL],
                }
            )

    nodes_to_skip = nodes_to_delete + list(pyiron_workflow_modules.keys())
    for edge in edge_get_list_updated_lst:
        if (
            edge[TARGET_LABEL] not in nodes_to_skip
            and edge[SOURCE_LABEL] not in nodes_to_skip
        ):
            source_node = nodes_remaining_dict[edge[SOURCE_LABEL]]
            if (
                isfunction(source_node)
                and source_node.__name__ == edge[SOURCE_PORT_LABEL]
            ):
                edge_new_lst.append(
                    {
                        TARGET_LABEL: nodes_final_order_dict[edge[TARGET_LABEL]],
                        TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                        SOURCE_LABEL: nodes_final_order_dict[edge[SOURCE_LABEL]],
                        SOURCE_PORT_LABEL: None,
                    }
                )
            elif (
                isfunction(source_node)
                and source_node.__name__ == "get_dict"
                and edge[SOURCE_PORT_LABEL] == "dict"
            ):
                edge_new_lst.append(
                    {
                        TARGET_LABEL: nodes_final_order_dict[edge[TARGET_LABEL]],
                        TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                        SOURCE_LABEL: nodes_final_order_dict[edge[SOURCE_LABEL]],
                        SOURCE_PORT_LABEL: None,
                    }
                )
            else:
                edge_new_lst.append(
                    {
                        TARGET_LABEL: nodes_final_order_dict[edge[TARGET_LABEL]],
                        TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                        SOURCE_LABEL: nodes_final_order_dict[edge[SOURCE_LABEL]],
                        SOURCE_PORT_LABEL: edge[SOURCE_PORT_LABEL],
                    }
                )

    PythonWorkflowDefinitionWorkflow(
        **set_result_node(
            workflow_dict=update_node_names(
                workflow_dict={
                    VERSION_LABEL: VERSION_NUMBER,
                    NODES_LABEL: nodes_store_lst,
                    EDGES_LABEL: edge_new_lst,
                }
            )
        )
    ).dump_json_file(file_name=file_name, indent=2)


def import_from_string(library_path: str) -> Any:
    # Copied from bagofholding
    split_path = library_path.split(".", 1)
    if len(split_path) == 1:
        module_name, path = split_path[0], ""
    else:
        module_name, path = split_path
    obj = import_module(module_name)
    for k in path.split("."):
        obj = getattr(obj, k)
    return obj


def generate_get_dict_function(args_of_lst):
    lines = "def get_dict(" + ", ".join(args_of_lst) + "):\n"
    lines += "    return {\n"
    for parameter in args_of_lst:
        lines += '        "' + parameter + '": ' + parameter + ",\n"
    lines += "    }"
    return lines


def generate_get_list_function(args_of_lst):
    lines = "def get_list(" + ", ".join(args_of_lst) + "):\n"
    lines += "    return [\n"
    for parameter in args_of_lst:
        lines += "        " + parameter + ",\n"
    lines += "    ]"
    return lines


def load_workflow_json(file_name: str) -> Workflow:
    content = remove_result(
        PythonWorkflowDefinitionWorkflow.load_json_file(file_name=file_name)
    )

    input_values: dict[int, object] = (
        {}
    )  # Type is actually more restrictive, must be jsonifyable object
    nodes: dict[int, Function] = {}
    total_counter_dict = Counter(
        [n["value"] for n in content[NODES_LABEL] if n["type"] == "function"]
    )
    counter_dict = {k: -1 for k in total_counter_dict.keys()}
    wf = Workflow(file_name.split(".")[0])
    nodes_look_up_dict = {node["id"]: node["value"] for node in content[NODES_LABEL]}
    for node_dict in content[NODES_LABEL]:
        if node_dict["type"] == "function":
            if node_dict["value"] == "python_workflow_definition.shared.get_dict":
                exec(
                    generate_get_dict_function(
                        args_of_lst=[
                            edge[TARGET_PORT_LABEL]
                            for edge in content[EDGES_LABEL]
                            if edge[TARGET_LABEL] == node_dict["id"]
                        ]
                    )
                )
                fnc = eval("get_dict")
            elif node_dict["value"] == "python_workflow_definition.shared.get_list":
                exec(
                    generate_get_list_function(
                        args_of_lst=[
                            "s_" + edge[TARGET_PORT_LABEL]
                            for edge in content[EDGES_LABEL]
                            if edge[TARGET_LABEL] == node_dict["id"]
                        ]
                    )
                )
                fnc = eval("get_list")
            else:
                fnc = import_from_string(node_dict["value"])
            if total_counter_dict[node_dict["value"]] > 1:
                counter_dict[node_dict["value"]] += 1
                name = fnc.__name__ + "_" + str(counter_dict[node_dict["value"]])
            else:
                name = fnc.__name__
            n = function_node(
                fnc, output_labels=name, validate_output_labels=False
            )  # Strictly force single-output
            nodes[node_dict["id"]] = n
            wf.add_child(child=n, label=name)
        elif node_dict["type"] == "input":
            input_values[node_dict["id"]] = node_dict["value"]

    for edge_dict in content[EDGES_LABEL]:
        target_id = edge_dict[TARGET_LABEL]
        target_port = edge_dict[TARGET_PORT_LABEL]
        source_id = edge_dict[SOURCE_LABEL]
        source_port = edge_dict[SOURCE_PORT_LABEL]

        if source_port is None:
            if source_id in input_values.keys():  # Parent input value
                upstream = input_values[source_id]
            else:  # Single-output sibling
                upstream = nodes[source_id]
        else:  # Dictionary-output sibling
            injected_attribute_access = nodes[source_id].__getitem__(source_port)
            upstream = injected_attribute_access
        downstream = nodes[target_id]
        if (
            nodes_look_up_dict[target_id]
            == "python_workflow_definition.shared.get_list"
        ):
            setattr(downstream.inputs, "s_" + target_port, upstream)
        else:
            setattr(
                downstream.inputs, target_port, upstream
            )  # Exploit input panel magic
            # Warning: edge setup routine is bespoke for an environment where all nodes return
            # a single value or a dictionary

    return wf
