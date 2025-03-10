import json
from importlib import import_module
from inspect import isfunction

import numpy as np
from jobflow import job, Flow


def get_function_dict(flow):
    return {
        job.uuid: job.function
        for job in flow.jobs
    }


def get_nodes_dict(function_dict):
    nodes_dict, nodes_mapping_dict = {}, {}
    # function_dict_len = len(function_dict)
    for i, [k, v] in enumerate(function_dict.items()):
        # nodes_dict[function_dict_len-i] = v
        # nodes_mapping_dict[k] = function_dict_len-i
        nodes_dict[i] = v
        nodes_mapping_dict[k] = i

    return nodes_dict, nodes_mapping_dict


def get_edge_from_dict(target, key, value_dict, nodes_mapping_dict):
    if len(value_dict['attributes']) == 1:
        return {'target': target, 'targetHandle': key, "source": nodes_mapping_dict[value_dict['uuid']], 'sourceHandle': value_dict['attributes'][0][1]}
    else:
        return {'target': target, 'targetHandle': key, "source": nodes_mapping_dict[value_dict['uuid']], 'sourceHandle': None}


def get_edges_and_extend_nodes(flow_dict, nodes_mapping_dict, nodes_dict):
    edges_lst = []
    for job in flow_dict['jobs']:
        for k, v in job['function_kwargs'].items():
            if isinstance(v, dict) and '@module' in v and '@class' in v and '@version' in v:
                edges_lst.append(get_edge_from_dict(
                    target=nodes_mapping_dict[job["uuid"]],
                    key=k,
                    value_dict=v,
                    nodes_mapping_dict=nodes_mapping_dict,
                ))
            elif isinstance(v, dict) and any([isinstance(el, dict) and '@module' in el and '@class' in el and '@version' in el for el in v.values()]):
                # print("found link in dict", v)
                node_dict_index = len(nodes_dict)
                nodes_dict[node_dict_index] = get_dict
                for kt, vt in v.items():
                    if isinstance(vt, dict) and '@module' in vt and '@class' in vt and '@version' in vt:
                        edges_lst.append(get_edge_from_dict(
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
                            # print(nodes_dict, vt)
                            node_index = {str(tv): tk for tk, tv in nodes_dict.items()}[str(vt)]
                        edges_lst.append({'target': node_dict_index, 'targetHandle': kt, "source": node_index, 'sourceHandle': None})
                edges_lst.append({'target': nodes_mapping_dict[job["uuid"]], 'targetHandle': k, "source": node_dict_index, 'sourceHandle': None})
            elif isinstance(v, list) and any([isinstance(el, dict) and '@module' in el and '@class' in el and '@version' in el for el in v]):
                # print("found link in list", v)
                node_list_index = len(nodes_dict)
                nodes_dict[node_list_index] = get_list
                for kt, vt in enumerate(v):
                    if isinstance(vt, dict) and '@module' in vt and '@class' in vt and '@version' in vt:
                        edges_lst.append(get_edge_from_dict(
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
                            # print(nodes_dict, vt)
                            node_index = {str(tv): tk for tk, tv in nodes_dict.items()}[str(vt)]
                        edges_lst.append({'target': node_list_index, 'targetHandle': kt, "source": node_index, 'sourceHandle': None})
                edges_lst.append({'target': nodes_mapping_dict[job["uuid"]], 'targetHandle': k, "source": node_list_index, 'sourceHandle': None})
            else:
                if v not in nodes_dict.values():
                    node_index = len(nodes_dict)
                    nodes_dict[node_index] = v
                else:
                    node_index = {tv: tk for tk, tv in nodes_dict.items()}[v]
                edges_lst.append({'target': nodes_mapping_dict[job["uuid"]], 'targetHandle': k, "source": node_index, 'sourceHandle': None})
    return edges_lst, nodes_dict


def get_dict(**kwargs):
    return {k: v for k, v in kwargs.items()}


def get_list(**kwargs):
    return list(kwargs.values())


def get_kwargs(lst):
    return {t['targetHandle']: {'source': t['source'], 'sourceHandle': t['sourceHandle']} for t in lst}


def resort_total_lst(total_dict, nodes_dict):
    nodes_with_dep_lst = list(sorted(total_dict.keys()))
    nodes_without_dep_lst = [k for k in nodes_dict.keys() if k not in nodes_with_dep_lst]
    ordered_lst = []
    total_new_dict = {}
    while len(total_new_dict) < len(total_dict):
        for ind in sorted(total_dict.keys()):
            connect = total_dict[ind]
            if ind not in ordered_lst:
                source_lst = [sd["source"] for sd in connect.values()]
                if all([s in ordered_lst or s in nodes_without_dep_lst for s in source_lst]):
                    ordered_lst.append(ind)
                    total_new_dict[ind] = connect
    return total_new_dict


def group_edges(edges_lst):
    # edges_sorted_lst = sorted(edges_lst, key=lambda x: x['target'], reverse=True)
    total_dict = {}
    for ed_major in edges_lst:
        target_id = ed_major["target"]
        tmp_lst = []
        if target_id not in total_dict.keys():
            for ed in edges_lst:
                if target_id == ed["target"]:
                    tmp_lst.append(ed)
            total_dict[target_id] = get_kwargs(lst=tmp_lst)
    # total_dict[target_id] = get_kwargs(lst=tmp_lst)
    return total_dict


def get_input_dict(nodes_dict):
    return {k:v for k, v in nodes_dict.items() if not isfunction(v)}


def get_workflow(nodes_dict, input_dict, total_dict, source_handles_dict):
    def get_attr_helper(obj, source_handle):
        # print("attr_helper", source_handle, getattr(obj, "output"), getattr(getattr(obj, "output"), source_handle))
        if source_handle is None:
            return getattr(obj, "output")
        else:
            return getattr(getattr(obj, "output"), source_handle)

    memory_dict = {}
    for k in total_dict.keys():
        v = nodes_dict[k]
        if isfunction(v):
            if k in source_handles_dict.keys():
                # print(k, {el: el for el in source_handles_dict[k] if el is not None})
                fn = job(method=v, data=[el for el in source_handles_dict[k] if el is not None])
            else:
                fn = job(method=v)
            kwargs = {
                kw: input_dict[vw['source']] if vw['source'] in input_dict else get_attr_helper(
                    obj=memory_dict[vw['source']], source_handle=vw['sourceHandle'])
                for kw, vw in total_dict[k].items()
            }
            # print(k, kwargs)
            memory_dict[k] = fn(**kwargs)
    return list(memory_dict.values())


def get_item_from_tuple(input_obj, index, index_lst):
    if isinstance(input_obj, dict):
        return input_obj[index]
    else:  # input_obj is a tuple
        return list(input_obj)[index_lst.index(index)]


def get_source_handles(edges_lst):
    source_handle_dict = {}
    for ed in edges_lst:
        if ed['source'] not in source_handle_dict.keys():
            source_handle_dict[ed['source']] = [ed['sourceHandle']]
        else:
            source_handle_dict[ed['source']].append(ed['sourceHandle'])
    return {
        k: list(range(len(v))) if len(v) > 1 and all([el is None for el in v]) else v
        for k, v in source_handle_dict.items()
    }


def load_workflow_json(file_name):
    with open(file_name, "r") as f:
        content = json.load(f)

    edges_new_lst = []
    for edge in content["edges"]:
        if edge['sourceHandle'] is None:
            edges_new_lst.append(edge)
        else:
            edges_new_lst.append(
                {
                    'target': edge['target'],
                    'targetHandle': edge['targetHandle'],
                    'source': edge['source'],
                    'sourceHandle': str(edge['sourceHandle']),
                }
            )

    nodes_new_dict = {}
    for k, v in content["nodes"].items():
        if isinstance(v, str) and "." in v:
            p, m = v.rsplit('.', 1)
            if p == "python_workflow_definition.pyiron_base":
                p = "python_workflow_definition.jobflow"
            mod = import_module(p)
            nodes_new_dict[int(k)] = getattr(mod, m)
        else:
            nodes_new_dict[int(k)] = v

    source_handles_dict = get_source_handles(edges_lst=edges_new_lst)
    total_dict = group_edges(edges_lst=edges_new_lst)
    input_dict = get_input_dict(nodes_dict=nodes_new_dict)
    new_total_dict = resort_total_lst(total_dict=total_dict, nodes_dict=nodes_new_dict)
    task_lst = get_workflow(
        nodes_dict=nodes_new_dict,
        input_dict=input_dict,
        total_dict=new_total_dict,
        source_handles_dict=source_handles_dict,
    )
    return Flow(task_lst)


def write_workflow_json(flow, file_name="workflow.json"):
    flow_dict = flow.as_dict()
    function_dict = get_function_dict(flow=flow)
    nodes_dict, nodes_mapping_dict = get_nodes_dict(function_dict=function_dict)
    edges_lst, nodes_dict = get_edges_and_extend_nodes(
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
