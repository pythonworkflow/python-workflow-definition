from importlib import import_module
import traceback
from aiida_workgraph import WorkGraph, task
import json

def pickle_node(value):
    """Handle data nodes"""
    return value


def get_item(data: dict, key: str):
    """Handle get item from the outputs"""
    return data[key]

# I defined the function mapping here
# but in principle, this is not needed, because one can import the function from the module path
# func_mapping = {
#     "simple_workflow.add_x_and_y": task.pythonjob()(add_x_and_y),
#     "simple_workflow.add_x_and_y_and_z": task.pythonjob()(add_x_and_y_and_z),
#     "quantum_espresso_workflow.get_bulk_structure": task.pythonjob()(
#         get_bulk_structure
#     ),
#     "quantum_espresso_workflow.calculate_qe": task.pythonjob()(calculate_qe),
#     "quantum_espresso_workflow.plot_energy_volume_curve": task.pythonjob()(
#         plot_energy_volume_curve
#     ),
#     "python_workflow_definition.pyiron_base.get_dict": task.pythonjob()(get_dict),
#     "python_workflow_definition.pyiron_base.get_list": task.pythonjob()(get_list),
#     "quantum_espresso_workflow.generate_structures": task.pythonjob()(
#         generate_structures
#     ),
# }


def write_workflow_json(wg):
    wgdata = wg.to_dict()
    data = {"nodes": {}, "edges": []}
    node_name_mapping = {}
    i = 0
    for name, node in wgdata["tasks"].items():
        node_name_mapping[name] = i
        callable_name = node["executor"]["callable_name"]
        data["nodes"][i] = callable_name
        if callable_name == "pickle_node":
            data["nodes"][i] = node["inputs"]["value"]["property"]["value"].value
        i += 1

    for link in wgdata["links"]:
        if wgdata["tasks"][link["from_node"]]["executor"]["callable_name"] == "pickle_node":
            link["from_socket"] = None
        link["from_node"] = node_name_mapping[link["from_node"]]
        link["to_node"] = node_name_mapping[link["to_node"]]
        data["edges"].append(link)

    return data


def load_workflow_json(filename):

    with open(filename) as f:
        data = json.load(f)

    wg = WorkGraph()
    task_name_mapping = {}
    # add tasks
    name_counter = {}

    for name, identifier in data["nodes"].items():
        # if isinstance(identifier, str) and identifier in func_mapping:
        if isinstance(identifier, str) and "." in identifier:
            p, m = identifier.rsplit('.', 1)
            mod = import_module(p)
            _func = getattr(mod, m)
            func = task.pythonjob()(_func)
            # func = func_mapping[identifier]
            # I use the register_pickle_by_value, because the function is defined in a local file
            try:
                wg.add_task(func, register_pickle_by_value=True, name=m)
            except ValueError:
                if m in name_counter:
                    name_counter[m] += 1
                else:
                    name_counter[m] = 0
                name_ = f"{m}_{name_counter[m]}"

                wg.add_task(func, register_pickle_by_value=True, name=name_)

            # Remove the default result output, because we will add the outputs later from the data in the link
            del wg.tasks[-1].outputs["result"]
        else:
            # data task
            wg.add_task(pickle_node, value=identifier, name=name)

        task_name_mapping[name] = wg.tasks[-1].name
    # add links
    for link in data["edges"]:
        if link["sourceHandle"] is None:
            link["sourceHandle"] = "result"
        try:
            from_task = wg.tasks[task_name_mapping[str(link["source"])]]
            # because we are not define the outputs explicitly during the pythonjob creation
            # we add it here, and assume the output exit
            if link["sourceHandle"] not in from_task.outputs:
                from_socket = from_task.add_output(
                    "workgraph.any",
                    name=link["sourceHandle"],
                    metadata={"is_function_output": True},
                )
            else:
                from_socket = from_task.outputs[link["sourceHandle"]]
            to_task = wg.tasks[task_name_mapping[str(link["target"])]]
            # if the input is not exit, it means we pass the data into to the kwargs
            # in this case, we add the input socket
            if link["targetHandle"] not in to_task.inputs:
                #
                to_socket = to_task.add_input(
                    "workgraph.any",
                    name=link["targetHandle"],
                    metadata={"is_function_input": True},
                )
            else:
                to_socket = to_task.inputs[link["targetHandle"]]
            wg.add_link(from_socket, to_socket)
        except Exception as e:
            traceback.print_exc()
            print("Failed to link", link, "with error:", e)
    return wg

def get_list(**kwargs):
    return list(kwargs.values())

def get_dict(**kwargs):
    return {k: v for k, v in kwargs.items()}