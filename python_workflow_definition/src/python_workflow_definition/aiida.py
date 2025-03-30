from importlib import import_module
import traceback
from aiida_workgraph import WorkGraph, task
import json
from aiida import orm

@task.pythonjob()
def pickle_node(value):
    """Handle data nodes"""
    return value


def load_workflow_json(file_name):
    with open(file_name) as f:
        data = json.load(f)

    wg = WorkGraph()
    task_name_mapping = {}

    for id, identifier in data["nodes"].items():
        if isinstance(identifier, str) and "." in identifier:
            p, m = identifier.rsplit(".", 1)
            mod = import_module(p)
            _func = getattr(mod, m)
            func = task.pythonjob()(_func)
            # I use the register_pickle_by_value, because the function is defined in a local file
            wg.add_task(func, register_pickle_by_value=True)

            # Remove the default result output, because we will add the outputs later from the data in the link
            del wg.tasks[-1].outputs["result"]
        else:
            # data task
            wg.add_task(pickle_node, value=identifier)

        task_name_mapping[id] = wg.tasks[-1].name
    # add links
    for link in data["edges"]:
        if link["sh"] is None:
            link["sh"] = "result"
        try:
            from_task = wg.tasks[task_name_mapping[str(link["sn"])]]
            # because we are not define the outputs explicitly during the pythonjob creation
            # we add it here, and assume the output exit
            if link["sh"] not in from_task.outputs:
            # if str(link["sh"]) not in from_task.outputs:
                from_socket = from_task.add_output(
                    "workgraph.any",
                    name=link["sh"],
                    # name=str(link["sh"]),
                    metadata={"is_function_output": True},
                )
            else:
                from_socket = from_task.outputs[link["sh"]]
            to_task = wg.tasks[task_name_mapping[str(link["tn"])]]
            # if the input is not exit, it means we pass the data into to the kwargs
            # in this case, we add the input socket
            if link["th"] not in to_task.inputs:
                #
                to_socket = to_task.add_input(
                    "workgraph.any",
                    name=link["th"],
                    metadata={"is_function_input": True},
                )
            else:
                to_socket = to_task.inputs[link["th"]]
            wg.add_link(from_socket, to_socket)
        except Exception as e:
            traceback.print_exc()
            print("Failed to link", link, "with error:", e)
    return wg


def write_workflow_json(wg, file_name):
    data = {"nodes": {}, "edges": []}
    node_name_mapping = {}
    i = 0
    for node in wg.tasks:
        executor = node.get_executor()
        node_name_mapping[node.name] = i

        callable_name = executor["callable_name"]

        if callable_name == "pickle_node":
            input_value = data["nodes"][str(i)] = node.inputs.value.value
            try:
                if isinstance(input_value, orm.Data):
                    if isinstance(input_value, orm.List):
                        data["nodes"][str(i)] = input_value.get_list()
                    elif isinstance(input_value, orm.Dict):
                        data["nodes"][str(i)] = input_value.get_dict()
                    else:
                        data["nodes"][str(i)] = input_value.value
                else:
                    data["nodes"][str(i)] = input_value
            except:
                import traceback

                traceback.print_stack()
                raise
                # raise
                # import ipdb; ipdb.set_trace()

        else:
            callable_name = f"{executor['module_path']}.{callable_name}"

            data["nodes"][str(i)] = callable_name

        i += 1

    for link in wg.links:
        link_data = link.to_dict()
        # if the from socket is the default result, we set it to None
        if link_data["from_socket"] == "result":
            link_data["from_socket"] = None
        link_data["tn"] = node_name_mapping[link_data.pop("to_node")]
        link_data["th"] = link_data.pop("to_socket")
        link_data["sn"] = node_name_mapping[link_data.pop("from_node")]
        link_data["sh"] = link_data.pop("from_socket")
        data["edges"].append(link_data)

    with open(file_name, "w") as f:
        # json.dump({"nodes": data[], "edges": edges_new_lst}, f)
        json.dump(data, f, indent=2)

    return data
