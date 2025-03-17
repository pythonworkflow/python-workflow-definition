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
            p, m = identifier.rsplit(".", 1)
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


def write_workflow_json(wg, file_name):
    wgdata = wg.to_dict()
    data = {"nodes": {}, "edges": []}
    node_name_mapping = {}
    i = 0
    for name, node in wgdata["tasks"].items():
        node_name_mapping[name] = i

        callable_name = node["executor"]["callable_name"]

        if callable_name == "pickle_node":
            data["nodes"][i] = node["inputs"]["sockets"]["value"]["property"][
                "value"
            ].value

        else:

            callable_name = f"{node['executor']['module_path']}.{callable_name}"

            data["nodes"][i] = callable_name

        i += 1

    for link in wgdata["links"]:
        if (
            wgdata["tasks"][link["from_node"]]["executor"]["callable_name"]
            == "pickle_node"
        ):
            link["from_socket"] = None
        link["source"] = node_name_mapping[link["from_node"]]
        del link['from_node']
        link["target"] = node_name_mapping[link["to_node"]]
        del link['to_node']
        link["sourceHandle"] = link.pop("from_socket")
        link["targetHandle"] = link.pop("to_socket")
        data["edges"].append(link)

    with open(file_name, "w") as f:
        # json.dump({"nodes": data[], "edges": edges_new_lst}, f)
        json.dump(data, f)

    return data

def pickle_node(value):
    """Handle data nodes"""
    return value

def construct_wg_simple(add_x_and_y_func, add_x_and_y_and_z_func) -> WorkGraph:

    helper_1 = task.pythonjob()(pickle_node)
    helper_2 = task.pythonjob()(pickle_node)

    add_x_and_y = task.pythonjob(outputs=["x", "y", "z"])(add_x_and_y_func)
    add_x_and_y_and_z = task.pythonjob()(add_x_and_y_and_z_func)

    # TODO: Create inputs rather than tasks out of data nodes
    wg = WorkGraph('wg-simple')

    helper_task1 = wg.add_task(
        helper_1,
        name="x",
        value=1
    )

    helper_task2 = wg.add_task(
        helper_2,
        name="y",
        value=2
    )

    add_x_and_y_task = wg.add_task(
        add_x_and_y,
        name='add_x_and_y',
        x=helper_task1.outputs.result,
        y=helper_task2.outputs.result,
    )

    add_x_and_y_and_z_task = wg.add_task(
        add_x_and_y_and_z,
        name='add_x_and_y_and_z',
        x=add_x_and_y_task.outputs.x,
        y=add_x_and_y_task.outputs.y,
        z=add_x_and_y_task.outputs.z,
    )

    return wg


def construct_wg_qe(
    get_dict_task,
    get_list_task,
    pickle_node_task,
    get_bulk_structure_task,
    calculate_qe_task,
    generate_structures_task,
    plot_energy_volume_curve_task,
    strain_lst,
):

    wg = WorkGraph()
    wg.add_task(
        get_bulk_structure_task,
        name="bulk",
        element="Al",
        a=4.05,
        cubic=True,
        register_pickle_by_value=True,
    )
    wg.add_task(pickle_node_task, name="calculation", value="vc-relax")
    wg.add_task(pickle_node_task, name="kpts", value=[3, 3, 3])
    wg.add_task(
        pickle_node_task,
        name="pseudopotentials",
        value={"Al": "Al.pbe-n-kjpaw_psl.1.0.0.UPF"},
    )
    wg.add_task(pickle_node_task, name="smearing", value=0.02)
    wg.add_task(
        get_dict_task,
        name="get_dict",
        structure=wg.tasks.bulk.outputs.result,
        calculation=wg.tasks.calculation.outputs.result,
        kpts=wg.tasks.kpts.outputs.result,
        pseudopotentials=wg.tasks.pseudopotentials.outputs.result,
        smearing=wg.tasks.smearing.outputs.result,
        register_pickle_by_value=True,
    )
    wg.add_task(
        calculate_qe_task,
        name=f"relax",
        input_dict=wg.tasks.get_dict.outputs.result,
        working_directory="mini",
        register_pickle_by_value=True,
    )
    wg.add_task(
        generate_structures_task,
        name="generate_structures",
        structure=wg.tasks.relax.outputs.structure,
        strain_lst=strain_lst,
        register_pickle_by_value=True,
    )
    # here we add the structure outputs based on the number of strains
    del wg.tasks.generate_structures.outputs["result"]
    for i in range(len(strain_lst)):
        wg.tasks.generate_structures.add_output("workgraph.any", f"s_{i}")

    wg.add_task(get_list_task, name="get_energies", register_pickle_by_value=True)
    wg.add_task(get_list_task, name="get_volumes", register_pickle_by_value=True)
    wg.add_task(pickle_node_task, name="calculation_scf", value="scf")

    for i, strain in enumerate(strain_lst):
        get_dict_task_ = wg.add_task(
            get_dict_task,
            name=f"get_dict_{i}",
            calculation=wg.tasks.calculation_scf.outputs.result,
            structure=wg.tasks.generate_structures.outputs[f"s_{i}"],
            kpts=wg.tasks.kpts.outputs.result,
            pseudopotentials=wg.tasks.pseudopotentials.outputs.result,
            smearing=wg.tasks.smearing.outputs.result,
            register_pickle_by_value=True,
        )
        qe_task = wg.add_task(
            calculate_qe_task,
            name=f"qe_{i}",
            input_dict=get_dict_task_.outputs.result,
            working_directory=f"strain_{i}",
            register_pickle_by_value=True,
        )
        # collect energy and volume
        wg.add_link(qe_task.outputs.energy, wg.tasks.get_energies.inputs.kwargs)
        wg.add_link(qe_task.outputs.volume, wg.tasks.get_volumes.inputs.kwargs)

        wg.add_task(
            plot_energy_volume_curve_task,
            volume_lst=wg.tasks.get_volumes.outputs.result,
            energy_lst=wg.tasks.get_energies.outputs.result,
            register_pickle_by_value=True,
        )

    return wg
