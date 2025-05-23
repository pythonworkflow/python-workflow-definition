from inspect import isfunction
from importlib import import_module
from typing import Any, Optional

import numpy as np
from pyiron_workflow import function_node, Workflow
from pyiron_workflow.api import Function

from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow
from python_workflow_definition.shared import (
    convert_nodes_list_to_dict,
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


def create_input_nodes(nodes_dict, edges_lst):
    node_conversion_dict = {
        ed[SOURCE_LABEL]: ed[TARGET_PORT_LABEL]
        for ed in edges_lst
        if ed[SOURCE_PORT_LABEL] is None
    }
    nodes_to_create_dict = {v: nodes_dict[k] for k, v in node_conversion_dict.items()}
    return nodes_to_create_dict, node_conversion_dict


def set_input_nodes(workflow, nodes_to_create_dict):
    for k, v in nodes_to_create_dict.items():
        workflow.__setattr__(k, v)
    return workflow


def get_source_handles(edges_lst):
    source_handle_dict = {}
    for ed in edges_lst:
        if ed[SOURCE_LABEL] not in source_handle_dict.keys():
            source_handle_dict[ed[SOURCE_LABEL]] = [ed[SOURCE_PORT_LABEL]]
        else:
            source_handle_dict[ed[SOURCE_LABEL]].append(ed[SOURCE_PORT_LABEL])
    return source_handle_dict


def get_function_nodes(nodes_dict, source_handle_dict):
    function_dict = {}
    for k, v in nodes_dict.items():
        if isfunction(v):
            function_dict[k] = {"node_function": v}
    return function_dict


def get_kwargs(lst):
    return {
        t[TARGET_PORT_LABEL]: {
            SOURCE_LABEL: t[SOURCE_LABEL],
            SOURCE_PORT_LABEL: t[SOURCE_PORT_LABEL],
        }
        for t in lst
    }


def group_edges(edges_lst):
    edges_sorted_lst = sorted(edges_lst, key=lambda x: x[TARGET_LABEL], reverse=True)
    total_dict = {}
    tmp_lst = []
    target_id = edges_sorted_lst[0][TARGET_LABEL]
    for ed in edges_sorted_lst:
        if target_id == ed[TARGET_LABEL]:
            tmp_lst.append(ed)
        else:
            total_dict[target_id] = get_kwargs(lst=tmp_lst)
            target_id = ed[TARGET_LABEL]
            tmp_lst = [ed]
    total_dict[target_id] = get_kwargs(lst=tmp_lst)
    return total_dict


def build_workflow(workflow, function_dict, total_dict, node_conversion_dict):
    for k, v in function_dict.items():
        kwargs_link_dict = total_dict[k]
        kwargs_dict = {}
        for kw, vw in kwargs_link_dict.items():
            if vw[SOURCE_LABEL] in node_conversion_dict.keys():
                kwargs_dict[kw] = workflow.__getattribute__(
                    node_conversion_dict[vw[SOURCE_LABEL]]
                )
            else:
                kwargs_dict[kw] = workflow.__getattr__(
                    "tmp_" + str(vw[SOURCE_LABEL])
                ).__getitem__(vw[SOURCE_PORT_LABEL])
        v.update(kwargs_dict)
        workflow.__setattr__(
            "tmp_" + str(k), function_node(**v, validate_output_labels=False)
        )
    return workflow, "tmp_" + str(k)


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


def load_workflow_json(file_name: str, workflow: Optional[Workflow] = None):
    content = remove_result(
        workflow_dict=PythonWorkflowDefinitionWorkflow.load_json_file(
            file_name=file_name
        )
    )
    edges_lst = content[EDGES_LABEL]

    nodes_new_dict = {}
    for k, v in convert_nodes_list_to_dict(nodes_list=content[NODES_LABEL]).items():
        if isinstance(v, str) and "." in v:
            p, m = v.rsplit(".", 1)
            mod = import_module(p)
            nodes_new_dict[int(k)] = getattr(mod, m)
        else:
            nodes_new_dict[int(k)] = v

    if workflow is None:
        workflow = Workflow(file_name.split(".")[0])

    nodes_to_create_dict, node_conversion_dict = create_input_nodes(
        nodes_dict=nodes_new_dict, edges_lst=edges_lst
    )
    wf = set_input_nodes(workflow=workflow, nodes_to_create_dict=nodes_to_create_dict)

    source_handle_dict = get_source_handles(edges_lst=edges_lst)
    function_dict = get_function_nodes(
        nodes_dict=nodes_new_dict, source_handle_dict=source_handle_dict
    )
    total_dict = group_edges(edges_lst=edges_lst)

    return build_workflow(
        workflow=wf,
        function_dict=function_dict,
        total_dict=total_dict,
        node_conversion_dict=node_conversion_dict,
    )


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


def build_function_dag_workflow(file_name: str) -> Workflow:
    content = remove_result(
        PythonWorkflowDefinitionWorkflow.load_json_file(file_name=file_name)
    )

    input_values: dict[int, object] = (
        {}
    )  # Type is actually more restrictive, must be jsonifyable object
    nodes: dict[int, Function] = {}
    wf = Workflow(file_name.split(".")[0])
    for node_dict in content[NODES_LABEL]:
        if node_dict["type"] == "function":
            fnc = import_from_string(node_dict["value"])
            n = function_node(
                fnc,
                output_labels=fnc.__name__  # Strictly force single-output
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
        setattr(
            downstream.inputs, target_port, upstream
        )  # Exploit input panel magic
        # Warning: edge setup routine is bespoke for an environment where all nodes return
        # a single value or a dictionary

    return wf
