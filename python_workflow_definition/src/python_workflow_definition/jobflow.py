import json
from importlib import import_module
from inspect import isfunction

import numpy as np
from jobflow import job, Flow

from python_workflow_definition.shared import (
    get_dict,
    get_list,
    get_kwargs,
    get_source_handles,
    convert_nodes_list_to_dict,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
)


def _get_function_dict(flow: Flow):
    return {job.uuid: job.function for job in flow.jobs}


def _get_nodes_dict(function_dict: dict):
    nodes_dict, nodes_mapping_dict = {}, {}
    for i, [k, v] in enumerate(function_dict.items()):
        nodes_dict[i] = v
        nodes_mapping_dict[k] = i

    return nodes_dict, nodes_mapping_dict


def _get_edge_from_dict(
    target: str, key: str, value_dict: dict, nodes_mapping_dict: dict
) -> dict:
    if len(value_dict["attributes"]) == 1:
        return {
            TARGET_LABEL: target,
            TARGET_PORT_LABEL: key,
            SOURCE_LABEL: nodes_mapping_dict[value_dict["uuid"]],
            SOURCE_PORT_LABEL: value_dict["attributes"][0][1],
        }
    else:
        return {
            TARGET_LABEL: target,
            TARGET_PORT_LABEL: key,
            SOURCE_LABEL: nodes_mapping_dict[value_dict["uuid"]],
            SOURCE_PORT_LABEL: None,
        }


def _get_edges_and_extend_nodes(
    flow_dict: dict, nodes_mapping_dict: dict, nodes_dict: dict
):
    edges_lst = []
    for job in flow_dict["jobs"]:
        for k, v in job["function_kwargs"].items():
            if (
                isinstance(v, dict)
                and "@module" in v
                and "@class" in v
                and "@version" in v
            ):
                edges_lst.append(
                    _get_edge_from_dict(
                        target=nodes_mapping_dict[job["uuid"]],
                        key=k,
                        value_dict=v,
                        nodes_mapping_dict=nodes_mapping_dict,
                    )
                )
            elif isinstance(v, dict) and any(
                [
                    isinstance(el, dict)
                    and "@module" in el
                    and "@class" in el
                    and "@version" in el
                    for el in v.values()
                ]
            ):
                node_dict_index = len(nodes_dict)
                nodes_dict[node_dict_index] = get_dict
                for kt, vt in v.items():
                    if (
                        isinstance(vt, dict)
                        and "@module" in vt
                        and "@class" in vt
                        and "@version" in vt
                    ):
                        edges_lst.append(
                            _get_edge_from_dict(
                                target=node_dict_index,
                                key=kt,
                                value_dict=vt,
                                nodes_mapping_dict=nodes_mapping_dict,
                            )
                        )
                    else:
                        if vt not in nodes_dict.values():
                            node_index = len(nodes_dict)
                            nodes_dict[node_index] = vt
                        else:
                            node_index = {str(tv): tk for tk, tv in nodes_dict.items()}[
                                str(vt)
                            ]
                        edges_lst.append(
                            {
                                TARGET_LABEL: node_dict_index,
                                TARGET_PORT_LABEL: kt,
                                SOURCE_LABEL: node_index,
                                SOURCE_PORT_LABEL: None,
                            }
                        )
                edges_lst.append(
                    {
                        TARGET_LABEL: nodes_mapping_dict[job["uuid"]],
                        TARGET_PORT_LABEL: k,
                        SOURCE_LABEL: node_dict_index,
                        SOURCE_PORT_LABEL: None,
                    }
                )
            elif isinstance(v, list) and any(
                [
                    isinstance(el, dict)
                    and "@module" in el
                    and "@class" in el
                    and "@version" in el
                    for el in v
                ]
            ):
                node_list_index = len(nodes_dict)
                nodes_dict[node_list_index] = get_list
                for kt, vt in enumerate(v):
                    if (
                        isinstance(vt, dict)
                        and "@module" in vt
                        and "@class" in vt
                        and "@version" in vt
                    ):
                        edges_lst.append(
                            _get_edge_from_dict(
                                target=node_list_index,
                                key=str(kt),
                                value_dict=vt,
                                nodes_mapping_dict=nodes_mapping_dict,
                            )
                        )
                    else:
                        if vt not in nodes_dict.values():
                            node_index = len(nodes_dict)
                            nodes_dict[node_index] = vt
                        else:
                            node_index = {str(tv): tk for tk, tv in nodes_dict.items()}[
                                str(vt)
                            ]
                        edges_lst.append(
                            {
                                TARGET_LABEL: node_list_index,
                                TARGET_PORT_LABEL: kt,
                                SOURCE_LABEL: node_index,
                                SOURCE_PORT_LABEL: None,
                            }
                        )
                edges_lst.append(
                    {
                        TARGET_LABEL: nodes_mapping_dict[job["uuid"]],
                        TARGET_PORT_LABEL: k,
                        SOURCE_LABEL: node_list_index,
                        SOURCE_PORT_LABEL: None,
                    }
                )
            else:
                if v not in nodes_dict.values():
                    node_index = len(nodes_dict)
                    nodes_dict[node_index] = v
                else:
                    node_index = {tv: tk for tk, tv in nodes_dict.items()}[v]
                edges_lst.append(
                    {
                        TARGET_LABEL: nodes_mapping_dict[job["uuid"]],
                        TARGET_PORT_LABEL: k,
                        SOURCE_LABEL: node_index,
                        SOURCE_PORT_LABEL: None,
                    }
                )
    return edges_lst, nodes_dict


def _resort_total_lst(total_dict: dict, nodes_dict: dict) -> dict:
    nodes_with_dep_lst = list(sorted(total_dict.keys()))
    nodes_without_dep_lst = [
        k for k in nodes_dict.keys() if k not in nodes_with_dep_lst
    ]
    ordered_lst = []
    total_new_dict = {}
    while len(total_new_dict) < len(total_dict):
        for ind in sorted(total_dict.keys()):
            connect = total_dict[ind]
            if ind not in ordered_lst:
                source_lst = [sd[SOURCE_LABEL] for sd in connect.values()]
                if all(
                    [s in ordered_lst or s in nodes_without_dep_lst for s in source_lst]
                ):
                    ordered_lst.append(ind)
                    total_new_dict[ind] = connect
    return total_new_dict


def _group_edges(edges_lst: list) -> dict:
    total_dict = {}
    for ed_major in edges_lst:
        target_id = ed_major[TARGET_LABEL]
        tmp_lst = []
        if target_id not in total_dict.keys():
            for ed in edges_lst:
                if target_id == ed[TARGET_LABEL]:
                    tmp_lst.append(ed)
            total_dict[target_id] = get_kwargs(lst=tmp_lst)
    return total_dict


def _get_input_dict(nodes_dict: dict) -> dict:
    return {k: v for k, v in nodes_dict.items() if not isfunction(v)}


def _get_workflow(
    nodes_dict: dict, input_dict: dict, total_dict: dict, source_handles_dict: dict
) -> list:
    def get_attr_helper(obj, source_handle):
        if source_handle is None:
            return getattr(obj, "output")
        else:
            return getattr(getattr(obj, "output"), source_handle)

    memory_dict = {}
    for k in total_dict.keys():
        v = nodes_dict[k]
        if isfunction(v):
            if k in source_handles_dict.keys():
                fn = job(
                    method=v,
                    data=[el for el in source_handles_dict[k] if el is not None],
                )
            else:
                fn = job(method=v)
            kwargs = {
                kw: (
                    input_dict[vw[SOURCE_LABEL]]
                    if vw[SOURCE_LABEL] in input_dict
                    else get_attr_helper(
                        obj=memory_dict[vw[SOURCE_LABEL]],
                        source_handle=vw[SOURCE_PORT_LABEL],
                    )
                )
                for kw, vw in total_dict[k].items()
            }
            memory_dict[k] = fn(**kwargs)
    return list(memory_dict.values())


def _get_item_from_tuple(input_obj, index, index_lst):
    if isinstance(input_obj, dict):
        return input_obj[index]
    else:
        return list(input_obj)[index_lst.index(index)]


def load_workflow_json(file_name: str) -> Flow:
    with open(file_name, "r") as f:
        content = json.load(f)

    edges_new_lst = []
    for edge in content[EDGES_LABEL]:
        if edge[SOURCE_PORT_LABEL] is None:
            edges_new_lst.append(edge)
        else:
            edges_new_lst.append(
                {
                    TARGET_LABEL: edge[TARGET_LABEL],
                    TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
                    SOURCE_LABEL: edge[SOURCE_LABEL],
                    SOURCE_PORT_LABEL: str(edge[SOURCE_PORT_LABEL]),
                }
            )

    nodes_new_dict = {}
    for k, v in convert_nodes_list_to_dict(nodes_list=content[NODES_LABEL]).items():
        if isinstance(v, str) and "." in v:
            p, m = v.rsplit(".", 1)
            mod = import_module(p)
            nodes_new_dict[int(k)] = getattr(mod, m)
        else:
            nodes_new_dict[int(k)] = v

    source_handles_dict = get_source_handles(edges_lst=edges_new_lst)
    total_dict = _group_edges(edges_lst=edges_new_lst)
    input_dict = _get_input_dict(nodes_dict=nodes_new_dict)
    new_total_dict = _resort_total_lst(total_dict=total_dict, nodes_dict=nodes_new_dict)
    task_lst = _get_workflow(
        nodes_dict=nodes_new_dict,
        input_dict=input_dict,
        total_dict=new_total_dict,
        source_handles_dict=source_handles_dict,
    )
    return Flow(task_lst)


def write_workflow_json(flow: Flow, file_name: str = "workflow.json"):
    flow_dict = flow.as_dict()
    function_dict = _get_function_dict(flow=flow)
    nodes_dict, nodes_mapping_dict = _get_nodes_dict(function_dict=function_dict)
    edges_lst, nodes_dict = _get_edges_and_extend_nodes(
        flow_dict=flow_dict,
        nodes_mapping_dict=nodes_mapping_dict,
        nodes_dict=nodes_dict,
    )

    nodes_store_lst = []
    for k, v in nodes_dict.items():
        if isfunction(v):
            nodes_store_lst.append(
                {"id": k, "type": "function", "value": v.__module__ + "." + v.__name__}
            )
        elif isinstance(v, np.ndarray):
            nodes_store_lst.append({"id": k, "type": "input", "value": v.tolist()})
        else:
            nodes_store_lst.append({"id": k, "type": "input", "value": v})

    with open(file_name, "w") as f:
        json.dump({NODES_LABEL: nodes_store_lst, EDGES_LABEL: edges_lst}, f)
