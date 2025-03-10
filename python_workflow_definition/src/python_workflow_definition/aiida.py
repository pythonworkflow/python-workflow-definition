import json
from importlib import import_module
from inspect import isfunction
import numpy as np

from aiida.engine import calcfunction
from aiida_workgraph import WorkGraph
from aiida_workgraph.decorator import build_task_from_callable


def get_edges_label_lst(work_graph_dict):
    edges_label_lst = []
    for link_dict in work_graph_dict["links"]:
        if link_dict['from_socket'] == "result":
            edges_label_lst.append(
                {
                    'target': link_dict['to_node'],
                    'targetHandle': link_dict['to_socket'],
                    'source': link_dict['from_node'],
                    'sourceHandle': None,
                }
            )
        else:
            edges_label_lst.append(
                {
                    'target': link_dict['to_node'],
                    'targetHandle': link_dict['to_socket'],
                    'source': link_dict['from_node'],
                    'sourceHandle': link_dict['from_socket'],
                }
            )

    return edges_label_lst


def get_function_dict(work_graph_dict):
    kwargs_dict, function_dict = {}, {}
    for task_name, task_dict in work_graph_dict["tasks"].items():
        input_variables = [
            input_parameter
            for input_parameter in task_dict['inputs'].keys()
            if not input_parameter.startswith("metadata") and not input_parameter.startswith("_wait")
        ]
        input_kwargs = {
            input_parameter: task_dict['inputs'][input_parameter]['property']["value"].value if isinstance(
                task_dict['inputs'][input_parameter]['property']["value"], dict) else
            task_dict['inputs'][input_parameter]['property']["value"]
            for input_parameter in input_variables
        }
        kwargs_dict[task_name] = input_kwargs
        function_dict[task_name] = task_dict['executor']['callable'].process_class._func
    return kwargs_dict, function_dict


def get_mapping(function_dict):
    nodes_dict, mapping_dict = {}, {}
    for i, [k, v] in enumerate(function_dict.items()):
        nodes_dict[i] = v
        mapping_dict[k] = i

    return nodes_dict, mapping_dict


def get_value_dict(kwargs_dict):
    value_dict = {}
    for func_name, val_dict in kwargs_dict.items():
        for k, v in val_dict.items():
            if v is not None:
                if func_name not in value_dict.keys():
                    value_dict[func_name] = {}
                value_dict[func_name][k] = v

    return value_dict


def extend_mapping(nodes_dict, value_dict, mapping_dict):
    i = len(nodes_dict)
    for val_dict in value_dict.values():
        for k, v in val_dict.items():
            nodes_dict[i] = v
            mapping_dict[v] = i
            i += 1

    return nodes_dict, mapping_dict


def extend_edges_label_lst(kwargs_dict, edges_label_lst):
    for func_name, val_dict in kwargs_dict.items():
        for k, v in val_dict.items():
            if v is not None:
                edges_label_lst.append({'target': func_name, 'targetHandle': k, 'source': v, 'sourceHandle': None})
    return edges_label_lst


def get_edges_lst(edges_label_lst, mapping_dict):
    edges_lst = []
    for edge in edges_label_lst:
        edges_lst.append({'target': mapping_dict[edge['target']], 'targetHandle': edge['targetHandle'],
                          'source': mapping_dict[edge['source']], 'sourceHandle': edge['sourceHandle']})

    return edges_lst


def get_kwargs(lst):
    return {t['targetHandle']: {'source': t['source'], 'sourceHandle': t['sourceHandle']} for t in lst}


def wrap_function(func, **kwargs):
    # First, apply the calcfunction decorator
    func_decorated = calcfunction(func)
    # Then, apply task decorator
    task_decorated = build_task_from_callable(
        func_decorated,
        inputs=kwargs.get("inputs", []),
        outputs=kwargs.get("outputs", []),
    )
    identifier = kwargs.get("identifier", None)
    func_decorated.identifier = identifier if identifier else func.__name__
    func_decorated.task = func_decorated.node = task_decorated
    return func_decorated


def group_edges(edges_lst):
    # edges_sorted_lst = sorted(edges_lst, key=lambda x: x['target'], reverse=True)
    total_dict = {}
    tmp_lst = []
    target_id = edges_lst[0]['target']
    for ed in edges_lst:
        if target_id == ed["target"]:
            tmp_lst.append(ed)
        else:
            total_dict[target_id] = get_kwargs(lst=tmp_lst)
            target_id = ed["target"]
            tmp_lst = [ed]
    total_dict[target_id] = get_kwargs(lst=tmp_lst)
    return total_dict


def get_output_labels(edges_lst):
    output_label_dict = {}
    for ed in edges_lst:
        if ed['sourceHandle'] is not None:
            if ed["source"] not in output_label_dict.keys():
                output_label_dict[ed["source"]] = []
            output_label_dict[ed["source"]].append(ed['sourceHandle'])
    return output_label_dict


def get_wrap_function_dict(nodes_dict, output_label_dict):
    function_dict = {}
    for k, v in nodes_dict.items():
        if isfunction(v):
            if k in output_label_dict.keys():
                kwargs = {"outputs": [{"name": label} for label in output_label_dict[k]]}
                function_dict[k] = wrap_function(func=v, **kwargs)
            else:
                function_dict[k] = wrap_function(func=v)

    return function_dict


def build_workgraph(function_dict, total_dict, nodes_dict, label="my_workflow"):
    wg = WorkGraph(label)
    mapping_dict = {}
    for k, v in function_dict.items():
        name = v.__name__
        mapping_dict[k] = name
        total_item_dict = total_dict[k]
        kwargs = {}
        for tk, tv in total_item_dict.items():
            if tv['source'] in mapping_dict.keys():
                kwargs[tk] = wg.tasks[mapping_dict[tv['source']]].outputs[tv['sourceHandle']]
            elif tv['sourceHandle'] is None:
                kwargs[tk] = nodes_dict[tv['source']]
            else:
                raise ValueError()
        wg.add_task(v, name=name, **kwargs)
    return wg


def write_workflow_json(work_graph_dict, file_name="workflow.json"):
    edges_label_lst = get_edges_label_lst(work_graph_dict=work_graph_dict)
    kwargs_dict, function_dict = get_function_dict(work_graph_dict=work_graph_dict)
    nodes_dict, mapping_dict = get_mapping(function_dict=function_dict)
    value_dict = get_value_dict(kwargs_dict=kwargs_dict)
    nodes_dict, mapping_dict = extend_mapping(nodes_dict=nodes_dict, value_dict=value_dict, mapping_dict=mapping_dict)
    edges_label_lst = extend_edges_label_lst(kwargs_dict=kwargs_dict, edges_label_lst=edges_label_lst)
    edges_lst = get_edges_lst(edges_label_lst=edges_label_lst, mapping_dict=mapping_dict)

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


def load_workflow_json(file_name, label="my_workflow"):
    with open(file_name, "r") as f:
        content = json.load(f)

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

    output_label_dict = get_output_labels(edges_lst=content["edges"])
    total_dict = group_edges(edges_lst=content["edges"])
    function_dict = get_wrap_function_dict(nodes_dict=nodes_new_dict, output_label_dict=output_label_dict)
    return build_workgraph(
        function_dict=function_dict,
        total_dict=total_dict,
        nodes_dict=nodes_new_dict,
        label=label,
    )