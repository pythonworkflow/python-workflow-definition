from concurrent.futures import Executor
from importlib import import_module
from inspect import isfunction


from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow
from python_workflow_definition.shared import (
    get_dict,
    get_list,
    get_kwargs,
    get_source_handles,
    convert_nodes_list_to_dict,
    remove_result,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
)
from python_workflow_definition.purepython import resort_total_lst, group_edges


def get_item(obj, key):
    return obj[key]


def _get_value(result_dict: dict, nodes_new_dict: dict, link_dict: dict, exe: Executor):
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
        return exe.submit(get_item, obj=result, key=source_handle)


def load_workflow_json(file_name: str, exe: Executor):
    content = remove_result(
        workflow_dict=PythonWorkflowDefinitionWorkflow.load_json_file(
            file_name=file_name
        )
    )

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
                    result_dict=result_dict,
                    nodes_new_dict=nodes_new_dict,
                    link_dict=v,
                    exe=exe,
                )
                for k, v in lst[1].items()
            }
            result_dict[lst[0]] = exe.submit(node, **kwargs)
            last_key = lst[0]

    return result_dict[last_key]
