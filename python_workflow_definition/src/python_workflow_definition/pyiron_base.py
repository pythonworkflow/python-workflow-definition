from importlib import import_module
from inspect import isfunction
import json
from typing import Optional

import numpy as np
from pyiron_base import job, Project
from pyiron_base.project.delayed import DelayedObject

from python_workflow_definition.shared import (
    get_kwargs,
    get_source_handles,
    convert_nodes_list_to_dict,
    update_node_names,
    remove_result,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
)


def _resort_total_lst(total_lst: list, nodes_dict: dict) -> list:
    nodes_with_dep_lst = list(sorted([v[0] for v in total_lst]))
    nodes_without_dep_lst = [
        k for k in nodes_dict.keys() if k not in nodes_with_dep_lst
    ]
    ordered_lst, total_new_lst = [], []
    while len(total_new_lst) < len(total_lst):
        for ind, connect in total_lst:
            if ind not in ordered_lst:
                source_lst = [sd[SOURCE_LABEL] for sd in connect.values()]
                if all(
                    [s in ordered_lst or s in nodes_without_dep_lst for s in source_lst]
                ):
                    ordered_lst.append(ind)
                    total_new_lst.append([ind, connect])
    return total_new_lst


def _group_edges(edges_lst: list) -> list:
    edges_sorted_lst = sorted(edges_lst, key=lambda x: x[TARGET_LABEL], reverse=True)
    total_lst, tmp_lst = [], []
    target_id = edges_sorted_lst[0][TARGET_LABEL]
    for ed in edges_sorted_lst:
        if target_id == ed[TARGET_LABEL]:
            tmp_lst.append(ed)
        else:
            total_lst.append((target_id, get_kwargs(lst=tmp_lst)))
            target_id = ed[TARGET_LABEL]
            tmp_lst = [ed]
    total_lst.append((target_id, get_kwargs(lst=tmp_lst)))
    return total_lst


def _get_source(
    nodes_dict: dict, delayed_object_dict: dict, source: str, source_handle: str
):
    if source in delayed_object_dict.keys() and source_handle is not None:
        return (
            delayed_object_dict[source].__getattr__("output").__getattr__(source_handle)
        )
    elif source in delayed_object_dict.keys():
        return delayed_object_dict[source]
    else:
        return nodes_dict[source]


def _get_delayed_object_dict(
    total_lst: list, nodes_dict: dict, source_handle_dict: dict, pyiron_project: Project
) -> dict:
    delayed_object_dict = {}
    for item in total_lst:
        key, input_dict = item
        kwargs = {
            k: _get_source(
                nodes_dict=nodes_dict,
                delayed_object_dict=delayed_object_dict,
                source=v[SOURCE_LABEL],
                source_handle=v[SOURCE_PORT_LABEL],
            )
            for k, v in input_dict.items()
        }
        delayed_object_dict[key] = job(
            funct=nodes_dict[key],
            output_key_lst=source_handle_dict.get(key, []),
        )(**kwargs, pyiron_project=pyiron_project)
    return delayed_object_dict


def get_dict(**kwargs) -> dict:
    return {k: v for k, v in kwargs["kwargs"].items()}


def get_list(**kwargs) -> list:
    return list(kwargs["kwargs"].values())


def _remove_server_obj(nodes_dict: dict, edges_lst: list):
    server_lst = [k for k in nodes_dict.keys() if k.startswith("server_obj_")]
    for s in server_lst:
        del nodes_dict[s]
        edges_lst = [ep for ep in edges_lst if s not in ep]
    return nodes_dict, edges_lst


def _get_nodes(connection_dict: dict, delayed_object_updated_dict: dict):
    return {
        connection_dict[k]: v._python_function if isinstance(v, DelayedObject) else v
        for k, v in delayed_object_updated_dict.items()
    }


def _get_unique_objects(nodes_dict: dict):
    delayed_object_dict = {}
    for k, v in nodes_dict.items():
        if isinstance(v, DelayedObject):
            delayed_object_dict[k] = v
        elif isinstance(v, list) and any([isinstance(el, DelayedObject) for el in v]):
            delayed_object_dict[k] = DelayedObject(function=get_list)
            delayed_object_dict[k]._input = {i: el for i, el in enumerate(v)}
            delayed_object_dict[k]._python_function = get_list
        elif isinstance(v, dict) and any(
            [isinstance(el, DelayedObject) for el in v.values()]
        ):
            delayed_object_dict[k] = DelayedObject(
                function=get_dict,
                **v,
            )
            delayed_object_dict[k]._python_function = get_dict
            delayed_object_dict[k]._input = v
    unique_lst = []
    delayed_object_updated_dict, match_dict = {}, {}
    for dobj in delayed_object_dict.keys():
        match = False
        for obj in unique_lst:
            if (
                delayed_object_updated_dict[obj]._python_function
                == delayed_object_dict[dobj]._python_function
                and delayed_object_dict[dobj]._input == delayed_object_dict[obj]._input
            ):
                delayed_object_updated_dict[obj] = delayed_object_dict[obj]
                match_dict[dobj] = obj
                match = True
                break
        if not match:
            unique_lst.append(dobj)
            delayed_object_updated_dict[dobj] = delayed_object_dict[dobj]
    update_dict = {}
    for k, v in nodes_dict.items():
        if not (
            isinstance(v, DelayedObject)
            or (
                isinstance(v, list) and any([isinstance(el, DelayedObject) for el in v])
            )
            or (
                isinstance(v, dict)
                and any([isinstance(el, DelayedObject) for el in v.values()])
            )
        ):
            update_dict[k] = v
    delayed_object_updated_dict.update(update_dict)
    return delayed_object_updated_dict, match_dict


def _get_connection_dict(delayed_object_updated_dict: dict, match_dict: dict):
    new_obj_dict = {}
    connection_dict = {}
    lookup_dict = {}
    for i, [k, v] in enumerate(delayed_object_updated_dict.items()):
        new_obj_dict[i] = v
        connection_dict[k] = i
        lookup_dict[i] = k

    for k, v in match_dict.items():
        if v in connection_dict.keys():
            connection_dict[k] = connection_dict[v]

    return connection_dict, lookup_dict


def _get_edges_dict(
    edges_lst: list, nodes_dict: dict, connection_dict: dict, lookup_dict: dict
):
    edges_dict_lst = []
    existing_connection_lst = []
    for ep in edges_lst:
        input_name, output_name = ep
        target = connection_dict[input_name]
        target_handle = "_".join(output_name.split("_")[:-1])
        connection_name = lookup_dict[target] + "_" + target_handle
        if connection_name not in existing_connection_lst:
            output = nodes_dict[output_name]
            if isinstance(output, DelayedObject):
                if output._list_index is not None:
                    edges_dict_lst.append(
                        {
                            TARGET_LABEL: target,
                            TARGET_PORT_LABEL: target_handle,
                            SOURCE_LABEL: connection_dict[output_name],
                            SOURCE_PORT_LABEL: f"s_{output._list_index}",  # check for list index
                        }
                    )
                else:
                    edges_dict_lst.append(
                        {
                            TARGET_LABEL: target,
                            TARGET_PORT_LABEL: target_handle,
                            SOURCE_LABEL: connection_dict[output_name],
                            SOURCE_PORT_LABEL: output._output_key,  # check for list index
                        }
                    )
            else:
                edges_dict_lst.append(
                    {
                        TARGET_LABEL: target,
                        TARGET_PORT_LABEL: target_handle,
                        SOURCE_LABEL: connection_dict[output_name],
                        SOURCE_PORT_LABEL: None,
                    }
                )
            existing_connection_lst.append(connection_name)
    return edges_dict_lst


def load_workflow_json(file_name: str, project: Optional[Project] = None):
    if project is None:
        project = Project(".")

    with open(file_name, "r") as f:
        content = remove_result(workflow_dict=json.load(f))

    edges_new_lst = content[EDGES_LABEL]
    nodes_new_dict = {}
    for k, v in convert_nodes_list_to_dict(nodes_list=content[NODES_LABEL]).items():
        if isinstance(v, str) and "." in v:
            p, m = v.rsplit(".", 1)
            if p == "python_workflow_definition.shared":
                p = "python_workflow_definition.pyiron_base"
            mod = import_module(p)
            nodes_new_dict[int(k)] = getattr(mod, m)
        else:
            nodes_new_dict[int(k)] = v

    total_lst = _group_edges(edges_new_lst)
    total_new_lst = _resort_total_lst(total_lst=total_lst, nodes_dict=nodes_new_dict)
    source_handle_dict = get_source_handles(edges_new_lst)
    delayed_object_dict = _get_delayed_object_dict(
        total_lst=total_new_lst,
        nodes_dict=nodes_new_dict,
        source_handle_dict=source_handle_dict,
        pyiron_project=project,
    )
    return list(delayed_object_dict.values())


def write_workflow_json(
    delayed_object: DelayedObject, file_name: str = "workflow.json"
):
    nodes_dict, edges_lst = delayed_object.get_graph()
    nodes_dict, edges_lst = _remove_server_obj(
        nodes_dict=nodes_dict, edges_lst=edges_lst
    )
    delayed_object_updated_dict, match_dict = _get_unique_objects(nodes_dict=nodes_dict)
    connection_dict, lookup_dict = _get_connection_dict(
        delayed_object_updated_dict=delayed_object_updated_dict, match_dict=match_dict
    )
    nodes_new_dict = _get_nodes(
        connection_dict=connection_dict,
        delayed_object_updated_dict=delayed_object_updated_dict,
    )
    edges_new_lst = _get_edges_dict(
        edges_lst=edges_lst,
        nodes_dict=nodes_dict,
        connection_dict=connection_dict,
        lookup_dict=lookup_dict,
    )

    nodes_store_lst = []
    for k, v in nodes_new_dict.items():
        if isfunction(v):
            mod = v.__module__
            if mod == "python_workflow_definition.pyiron_base":
                mod = "python_workflow_definition.shared"
            nodes_store_lst.append(
                {"id": k, "type": "function", "value": mod + "." + v.__name__}
            )
        elif isinstance(v, np.ndarray):
            nodes_store_lst.append({"id": k, "type": "input", "value": v.tolist()})
        else:
            nodes_store_lst.append({"id": k, "type": "input", "value": v})

    with open(file_name, "w") as f:
        json.dump(
            update_node_names(
                content={NODES_LABEL: nodes_store_lst, EDGES_LABEL: edges_new_lst}
            ),
            f,
            indent=2,
        )
