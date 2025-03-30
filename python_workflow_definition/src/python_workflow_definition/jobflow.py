import json
from importlib import import_module
from inspect import isfunction

import numpy as np
from jobflow import job, Flow

from python_workflow_definition.shared import get_dict, get_list, get_kwargs, get_source_handles


def _get_function_dict(flow):
    return {
        job.uuid: job.function
        for job in flow.jobs
    }


def _get_nodes_dict(function_dict):
    nodes_dict, nodes_mapping_dict = {}, {}
    for i, [k, v] in enumerate(function_dict.items()):
        nodes_dict[i] = v
        nodes_mapping_dict[k] = i

    return nodes_dict, nodes_mapping_dict


def _get_edge_from_dict(target, key, value_dict, nodes_mapping_dict):
    if len(value_dict['attributes']) == 1:
        return {'tn': target, 'th': key, "sn": nodes_mapping_dict[value_dict['uuid']], 'sh': value_dict['attributes'][0][1]}
    else:
        return {'tn': target, 'th': key, "sn": nodes_mapping_dict[value_dict['uuid']], 'sh': None}


def _get_edges_and_extend_nodes(flow_dict, nodes_mapping_dict, nodes_dict):
    edges_lst = []
    for job in flow_dict['jobs']:
        for k, v in job['function_kwargs'].items():
            if isinstance(v, dict) and '@module' in v and '@class' in v and '@version' in v:
                edges_lst.append(_get_edge_from_dict(
                    target=nodes_mapping_dict[job["uuid"]],
                    key=k,
                    value_dict=v,
                    nodes_mapping_dict=nodes_mapping_dict,
                ))
            elif isinstance(v, dict) and any([isinstance(el, dict) and '@module' in el and '@class' in el and '@version' in el for el in v.values()]):
                node_dict_index = len(nodes_dict)
                nodes_dict[node_dict_index] = get_dict
                for kt, vt in v.items():
                    if isinstance(vt, dict) and '@module' in vt and '@class' in vt and '@version' in vt:
                        edges_lst.append(_get_edge_from_dict(
                            target=node_dict_index,
                            key=kt,
                            value_dict=vt,
                            nodes_mapping_dict=nodes_mapping_dict,
                        ))
                    else:
                        if vt not in nodes_dict.values():
                            node_index = len(nodes_dict)
                            nodes_dict[node_index] = vt
                        else:
                            node_index = {str(tv): tk for tk, tv in nodes_dict.items()}[str(vt)]
                        edges_lst.append({'tn': node_dict_index, 'th': kt, "sn": node_index, 'sh': None})
                edges_lst.append({'tn': nodes_mapping_dict[job["uuid"]], 'th': k, "sn": node_dict_index, 'sh': None})
            elif isinstance(v, list) and any([isinstance(el, dict) and '@module' in el and '@class' in el and '@version' in el for el in v]):
                node_list_index = len(nodes_dict)
                nodes_dict[node_list_index] = get_list
                for kt, vt in enumerate(v):
                    if isinstance(vt, dict) and '@module' in vt and '@class' in vt and '@version' in vt:
                        edges_lst.append(_get_edge_from_dict(
                            target=node_list_index,
                            key=str(kt),
                            value_dict=vt,
                            nodes_mapping_dict=nodes_mapping_dict,
                        ))
                    else:
                        if vt not in nodes_dict.values():
                            node_index = len(nodes_dict)
                            nodes_dict[node_index] = vt
                        else:
                            node_index = {str(tv): tk for tk, tv in nodes_dict.items()}[str(vt)]
                        edges_lst.append({'tn': node_list_index, 'th': kt, "sn": node_index, 'sh': None})
                edges_lst.append({'tn': nodes_mapping_dict[job["uuid"]], 'th': k, "sn": node_list_index, 'sh': None})
            else:
                if v not in nodes_dict.values():
                    node_index = len(nodes_dict)
                    nodes_dict[node_index] = v
                else:
                    node_index = {tv: tk for tk, tv in nodes_dict.items()}[v]
                edges_lst.append({'tn': nodes_mapping_dict[job["uuid"]], 'th': k, "sn": node_index, 'sh': None})
    return edges_lst, nodes_dict


def _resort_total_lst(total_dict, nodes_dict):
    nodes_with_dep_lst = list(sorted(total_dict.keys()))
    nodes_without_dep_lst = [k for k in nodes_dict.keys() if k not in nodes_with_dep_lst]
    ordered_lst = []
    total_new_dict = {}
    while len(total_new_dict) < len(total_dict):
        for ind in sorted(total_dict.keys()):
            connect = total_dict[ind]
            if ind not in ordered_lst:
                source_lst = [sd["sn"] for sd in connect.values()]
                if all([s in ordered_lst or s in nodes_without_dep_lst for s in source_lst]):
                    ordered_lst.append(ind)
                    total_new_dict[ind] = connect
    return total_new_dict


def _group_edges(edges_lst):
    total_dict = {}
    for ed_major in edges_lst:
        target_id = ed_major["tn"]
        tmp_lst = []
        if target_id not in total_dict.keys():
            for ed in edges_lst:
                if target_id == ed["tn"]:
                    tmp_lst.append(ed)
            total_dict[target_id] = get_kwargs(lst=tmp_lst)
    return total_dict


def _get_input_dict(nodes_dict):
    return {k:v for k, v in nodes_dict.items() if not isfunction(v)}


def _get_workflow(nodes_dict, input_dict, total_dict, source_handles_dict):
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
                fn = job(method=v, data=[el for el in source_handles_dict[k] if el is not None])
            else:
                fn = job(method=v)
            kwargs = {
                kw: input_dict[vw['sn']] if vw['sn'] in input_dict else get_attr_helper(
                    obj=memory_dict[vw['sn']], source_handle=vw['sh'])
                for kw, vw in total_dict[k].items()
            }
            memory_dict[k] = fn(**kwargs)
    return list(memory_dict.values())


def _get_item_from_tuple(input_obj, index, index_lst):
    if isinstance(input_obj, dict):
        return input_obj[index]
    else:
        return list(input_obj)[index_lst.index(index)]


def load_workflow_json(file_name):
    with open(file_name, "r") as f:
        content = json.load(f)

    edges_new_lst = []
    for edge in content["edges"]:
        if edge['sh'] is None:
            edges_new_lst.append(edge)
        else:
            edges_new_lst.append(
                {
                    'tn': edge['tn'],
                    'th': edge['th'],
                    'sn': edge['sn'],
                    'sh': str(edge['sh']),
                }
            )

    nodes_new_dict = {}
    for k, v in content["nodes"].items():
        if isinstance(v, str) and "." in v:
            p, m = v.rsplit('.', 1)
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


def write_workflow_json(flow, file_name="workflow.json"):
    flow_dict = flow.as_dict()
    function_dict = _get_function_dict(flow=flow)
    nodes_dict, nodes_mapping_dict = _get_nodes_dict(function_dict=function_dict)
    edges_lst, nodes_dict = _get_edges_and_extend_nodes(
        flow_dict=flow_dict,
        nodes_mapping_dict=nodes_mapping_dict,
        nodes_dict=nodes_dict,
    )

    nodes_store_dict = {}
    for k, v in nodes_dict.items():
        if isfunction(v):
            nodes_store_dict[k] = v.__module__ + "." + v.__name__
        elif isinstance(v, np.ndarray):
            nodes_store_dict[k] = v.tolist()
        else:
            nodes_store_dict[k] = v

    with open(file_name, "w") as f:
        json.dump({"nodes": nodes_store_dict, "edges": edges_lst}, f)
