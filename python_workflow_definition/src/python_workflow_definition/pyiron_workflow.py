from collections import Counter
from inspect import isfunction
from importlib import import_module
from typing import Any

import numpy as np
from pyiron_workflow import function_node, Workflow
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
    for val_dict in input_dict.values():
        for k, v in val_dict.items():
            if v not in nodes_dict.values():
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

    target_dict = {}
    for edge in edges_lst:
        for k in pyiron_workflow_modules.keys():
            if k == edge[TARGET_LABEL]:
                if k not in target_dict:
                    target_dict[k] = []
                target_dict[k].append(edge)

    source_dict = {}
    for edge in edges_lst:
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
        edge_new_lst.append(
            {
                SOURCE_LABEL: source,
                SOURCE_PORT_LABEL: sourcehandle,
                TARGET_LABEL: source_dict[k][-1][TARGET_LABEL],
                TARGET_PORT_LABEL: source_dict[k][-1][TARGET_PORT_LABEL],
            }
        )

    nodes_to_skip = nodes_to_delete + list(pyiron_workflow_modules.keys())
    nodes_new_dict = {k: v for k, v in nodes_dict.items() if k not in nodes_to_skip}

    nodes_store_lst = []
    for k, v in enumerate(nodes_new_dict.values()):
        if isfunction(v):
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

    for edge in edges_lst:
        if (
            edge[TARGET_LABEL] not in nodes_to_skip
            and edge[SOURCE_LABEL] not in nodes_to_skip
        ):
            edge_new_lst.append(edge)

    nodes_updated_dict, mapping_dict = {}, {}
    i = 0
    for k, v in nodes_new_dict.items():
        nodes_updated_dict[i] = v
        mapping_dict[k] = i
        i += 1

    edge_updated_lst = []
    for edge in edge_new_lst:
        source_node = nodes_new_dict[edge[SOURCE_LABEL]]
        if isfunction(source_node) and source_node.__name__ == edge[SOURCE_PORT_LABEL]:
            edge_updated_lst.append(
                {
                    SOURCE_LABEL: mapping_dict[edge[SOURCE_LABEL]],
                    SOURCE_PORT_LABEL: None,
                    TARGET_LABEL: mapping_dict[edge[TARGET_LABEL]],
                    TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                }
            )
        else:
            edge_updated_lst.append(
                {
                    SOURCE_LABEL: mapping_dict[edge[SOURCE_LABEL]],
                    SOURCE_PORT_LABEL: edge[SOURCE_PORT_LABEL],
                    TARGET_LABEL: mapping_dict[edge[TARGET_LABEL]],
                    TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                }
            )

    PythonWorkflowDefinitionWorkflow(
        **set_result_node(
            workflow_dict=update_node_names(
                workflow_dict={
                    VERSION_LABEL: VERSION_NUMBER,
                    NODES_LABEL: nodes_store_lst,
                    EDGES_LABEL: edge_updated_lst,
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


def load_workflow_json(file_name: str) -> Workflow:
    content = remove_result(
        PythonWorkflowDefinitionWorkflow.load_json_file(file_name=file_name)
    )

    input_values: dict[int, object] = (
        {}
    )  # Type is actually more restrictive, must be jsonifyable object
    nodes: dict[int, Function] = {}
    total_counter_dict = Counter([n["value"] for n in content[NODES_LABEL] if n["type"] == "function"])
    counter_dict = {k: -1 for k in total_counter_dict.keys()}
    wf = Workflow(file_name.split(".")[0])
    for node_dict in content[NODES_LABEL]:
        if node_dict["type"] == "function":
            fnc = import_from_string(node_dict["value"])
            if total_counter_dict[node_dict["value"]] > 1:
                counter_dict[node_dict["value"]] += 1
                name = fnc.__name__ + "_" + str(counter_dict[node_dict["value"]])
            else:
                name = fnc.__name__
            n = function_node(
                fnc, output_labels=name  # Strictly force single-output
            )
            nodes[node_dict["id"]] = n
            wf.add_child(n)
        elif node_dict["type"] == "input":
            input_values[node_dict["id"]] = node_dict["value"]

    for edge_dict in content[EDGES_LABEL]:
        target_id = edge_dict["target"]
        target_port = edge_dict["targetPort"]
        source_id = edge_dict["source"]
        source_port = edge_dict["sourcePort"]

        if source_port is None:
            if source_id in input_values.keys():  # Parent input value
                upstream = input_values[source_id]
            else:  # Single-output sibling
                upstream = nodes[source_id]
        else:  # Dictionary-output sibling
            injected_attribute_access = nodes[source_id].__getitem__(source_port)
            upstream = injected_attribute_access
        downstream = nodes[target_id]
        setattr(downstream.inputs, target_port, upstream)  # Exploit input panel magic
        # Warning: edge setup routine is bespoke for an environment where all nodes return
        # a single value or a dictionary

    return wf
