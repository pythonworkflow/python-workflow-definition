import json
import pickle
from yaml import CDumper as Dumper, dump


from python_workflow_definition.purepython import (
    group_edges,
    resort_total_lst,
)
from python_workflow_definition.shared import (
    convert_nodes_list_to_dict,
    remove_result,
    EDGES_LABEL,
    NODES_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
)


def get_function_argument(argument: str, position: int = 3) -> dict:
    return {
        argument + '_file': {
            'type': 'File',
            'inputBinding': {'prefix': '--arg_' + argument + '=', 'separate': False, 'position': position},
        },
    }


def get_function_template(function_name: str) -> dict:
    return {
        'function': {
            'default': function_name,
            'inputBinding': {'position': 2, 'prefix': '--function=', 'separate': False},
            'type': 'string',
        },
    }


def get_output_name(output_name: str) -> dict:
    return {
        output_name + '_file': {
            'type': 'File',
            'outputBinding': {
                'glob': output_name + '.pickle'
            }
        }
    }


def get_function(workflow):
    function_nodes_dict = {
        n['id']: n['value']
        for n in workflow[NODES_LABEL] if n["type"] == "function"
    }
    funct_dict = {}
    for funct_id in function_nodes_dict.keys():
        target_ports = list(set([e[TARGET_PORT_LABEL] for e in workflow[EDGES_LABEL] if e["target"] == funct_id]))
        source_ports = list(set([e[SOURCE_PORT_LABEL] for e in workflow[EDGES_LABEL] if e["source"] == funct_id]))
        funct_dict[funct_id] = {"targetPorts": target_ports, "sourcePorts": source_ports}
    return function_nodes_dict, funct_dict


def write_function_cwl(workflow):
    function_nodes_dict, funct_dict = get_function(workflow)
    file_lst = []

    for i in range(len(function_nodes_dict)):
        template = {
            'cwlVersion': 'v1.2',
            'class': 'CommandLineTool',
            'baseCommand': 'python',
            'inputs': {
                'wrapper': {
                    'type': 'File',
                    'inputBinding': {'position': 1},
                    'default': {'class': 'File', 'location': 'wrapper.py'}
                },
            },
            'outputs': {
            }
        }
        file_name = function_nodes_dict[i].split(".")[-1] + ".cwl"
        if file_name not in file_lst:
            file_lst.append(file_name)
            template["inputs"].update(get_function_template(function_name=function_nodes_dict[i]))
            for j, arg in enumerate(funct_dict[i]['targetPorts']):
                template["inputs"].update(get_function_argument(argument=arg, position=3+j))
            for out in funct_dict[i]['sourcePorts']:
                if out is None:
                    template["outputs"].update(get_output_name(output_name="result"))
                else:
                    template["outputs"].update(get_output_name(output_name=out))
            with open(file_name, "w") as f:
                dump(template, f, Dumper=Dumper)


def write_workflow_config(workflow):
    input_dict = {
        n["name"]: n["value"]
        for n in workflow[NODES_LABEL] if n["type"] == "input"
    }
    with open("workflow.yml", "w") as f:
        dump(
            {
                k + "_file": {"class": "File", "path": k + ".pickle"}
                for k in input_dict.keys()
            },
            f,
            Dumper=Dumper,
        )
    for k, v in input_dict.items():
        with open(k + ".pickle", "wb") as f:
            pickle.dump(v, f)


def write_workflow(workflow):
    workflow_template = {
        'cwlVersion': 'v1.2',
        'class': 'Workflow',
        'inputs': {},
        'steps': {},
        'outputs': {},
    }
    input_dict = {
        n["name"]: n["value"]
        for n in workflow[NODES_LABEL] if n["type"] == "input"
    }
    function_nodes_dict, funct_dict = get_function(workflow)
    result_id = [n["id"] for n in workflow[NODES_LABEL] if n["type"] == "output"][0]
    last_compute_id = [e[SOURCE_LABEL] for e in workflow[EDGES_LABEL] if e[TARGET_LABEL] == result_id][0]
    workflow_template["inputs"].update({k + "_file": "File" for k in input_dict.keys()})
    if funct_dict[last_compute_id]["sourcePorts"] == [None]:
        workflow_template["outputs"] = {
            "result_file": {
                "type": "File",
                "outputSource": function_nodes_dict[last_compute_id].split(".")[-1] + "/result_file"
            },
        }
    else:
        raise ValueError()

    content = remove_result(workflow_dict=workflow)
    edges_new_lst = content[EDGES_LABEL]
    total_lst = group_edges(edges_new_lst)
    nodes_new_dict = {
        int(k): v for k, v in convert_nodes_list_to_dict(nodes_list=content[NODES_LABEL]).items()
    }
    total_new_lst = resort_total_lst(total_lst=total_lst, nodes_dict=nodes_new_dict)
    step_name_lst = {t[0]: function_nodes_dict[t[0]].split(".")[-1] for t in total_new_lst}
    input_id_dict = {n["id"]: n["name"] for n in workflow[NODES_LABEL] if n["type"] == "input"}
    for t in total_new_lst:
        ind = t[0]
        node_script = step_name_lst[ind] + ".cwl"
        output = [o + "_file" if o is not None else "result_file" for o in funct_dict[ind]['sourcePorts']]
        in_dict = {}
        for k, v in t[1].items():
            if v[SOURCE_LABEL] in input_id_dict:
                in_dict[k + "_file"] = input_id_dict[v[SOURCE_LABEL]] + "_file"
            else:
                in_dict[k + "_file"] = step_name_lst[v[SOURCE_LABEL]] + "/" + v[SOURCE_PORT_LABEL] + "_file"
        workflow_template["steps"].update({step_name_lst[ind]: {"run": node_script, "in": in_dict, "out": output}})
    with open("workflow.cwl", "w") as f:
        dump(workflow_template, f, Dumper=Dumper)


def load_workflow_json(file_name: str):
    with open(file_name, "r") as f:
        workflow = json.load(f)

    write_function_cwl(workflow=workflow)
    write_workflow_config(workflow=workflow)
    write_workflow(workflow=workflow)
