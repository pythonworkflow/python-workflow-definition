import json
from importlib import import_module
from inspect import isfunction


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


def resort_total_lst(total_lst: list, nodes_dict: dict) -> list:
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


def group_edges(edges_lst: list) -> list:
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


def _get_value(result_dict: dict, nodes_new_dict: dict, link_dict: dict):
    source, source_handle = link_dict[SOURCE_LABEL], link_dict[SOURCE_PORT_LABEL]
    if source in result_dict.keys():
        result = result_dict[source]
    elif source in nodes_new_dict.keys():
        result = nodes_new_dict[source]
    else:
        raise KeyError()
    if source_handle is None:
        return result
    else:
        return result[source_handle]


def load_workflow_json(file_name: str):
    with open(file_name, "r") as f:
        content = json.load(f)

    edges_new_lst = content[EDGES_LABEL]
    nodes_new_dict = {}
    for k, v in convert_nodes_list_to_dict(nodes_list=content[NODES_LABEL]).items():
        if isinstance(v, str) and "." in v:
            p, m = v.rsplit(".", 1)
            mod = import_module(p)
            nodes_new_dict[int(k)] = getattr(mod, m)
        else:
            nodes_new_dict[int(k)] = v

    total_lst = group_edges(edges_new_lst)
    total_new_lst = resort_total_lst(total_lst=total_lst, nodes_dict=nodes_new_dict)

    result_dict = {}
    last_key = None
    for lst in total_new_lst:
        node = nodes_new_dict[lst[0]]
        if isfunction(node):
            kwargs = {
                k: _get_value(
                    result_dict=result_dict, nodes_new_dict=nodes_new_dict, link_dict=v
                )
                for k, v in lst[1].items()
            }
            result_dict[lst[0]] = node(**kwargs)
            last_key = lst[0]

    return result_dict[last_key]
