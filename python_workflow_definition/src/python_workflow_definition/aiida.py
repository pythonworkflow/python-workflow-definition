from importlib import import_module
import traceback
from aiida_workgraph import WorkGraph, task
import json
from aiida import orm


def pickle_node(value):
    """Handle data nodes"""
    return value


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


def write_workflow_json(wg, file_name):
    wgdata = wg.to_dict()
    data = {"nodes": {}, "edges": []}
    node_name_mapping = {}
    i = 0
    for name, node in wgdata["tasks"].items():
        node_name_mapping[name] = i

        callable_name = node["executor"]["callable_name"]

        if callable_name == "pickle_node":
            aiida_node = data["nodes"][i] = node["inputs"]["sockets"]["value"][
                "property"
            ]["value"]
            try:
                if isinstance(aiida_node, orm.List):
                    data["nodes"][i] = aiida_node.get_list()
                elif isinstance(aiida_node, orm.Dict):
                    data["nodes"][i] = aiida_node.get_dict()
                else:
                    data["nodes"][i] = aiida_node.value
            except:
                import traceback

                traceback.print_stack()
                raise
                # raise
                # import ipdb; ipdb.set_trace()

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
        del link["from_node"]
        link["target"] = node_name_mapping[link["to_node"]]
        del link["to_node"]
        link["sourceHandle"] = link.pop("from_socket")
        link["targetHandle"] = link.pop("to_socket")
        data["edges"].append(link)

    with open(file_name, "w") as f:
        # json.dump({"nodes": data[], "edges": edges_new_lst}, f)
        json.dump(data, f)

    return data


def construct_wg_simple(add_x_and_y_func, add_x_and_y_and_z_func) -> WorkGraph:
    helper_1 = task.pythonjob()(pickle_node)
    helper_2 = task.pythonjob()(pickle_node)

    add_x_and_y = task.pythonjob(outputs=["x", "y", "z"])(add_x_and_y_func)
    add_x_and_y_and_z = task.pythonjob()(add_x_and_y_and_z_func)

    # TODO: Create inputs rather than tasks out of data nodes
    wg = WorkGraph("wg-simple")

    helper_task1 = wg.add_task(helper_1, name="x", value=1)

    helper_task2 = wg.add_task(helper_2, name="y", value=2)

    add_x_and_y_task = wg.add_task(
        add_x_and_y,
        name="add_x_and_y",
        x=helper_task1.outputs.result,
        y=helper_task2.outputs.result,
    )

    add_x_and_y_and_z_task = wg.add_task(
        add_x_and_y_and_z,
        name="add_x_and_y_and_z",
        x=add_x_and_y_task.outputs.x,
        y=add_x_and_y_task.outputs.y,
        z=add_x_and_y_task.outputs.z,
    )

    return wg


def construct_wg_qe(
    get_bulk_structure,
    calculate_qe,
    generate_structures,
    plot_energy_volume_curve,
    strain_lst,
):

    from .shared import get_dict
    from .shared import get_list

    # NOTE: `get_dict` is `get_input_dict`, to compile the input values for the calc tasks
    # NOTE: `add_link` must be from outputs to inputs
    wg = WorkGraph("wg-qe")

    get_bulk_structure_task = wg.add_task(
        get_bulk_structure,
        name="get_bulk_structure",
        register_pickle_by_value=True,
    )

    relax_task = wg.add_task(
        calculate_qe,
        # ! I don't like the `mini` name...
        name="mini",
        register_pickle_by_value=True,
    )

    generate_structures_task = wg.add_task(
        generate_structures,
        name="generate_structures",
        register_pickle_by_value=True,
    )

    # here we add the structure outputs based on the number of strains
    del wg.tasks.generate_structures.outputs["result"]

    scf_qe_tasks = []
    for i, strain in enumerate(strain_lst):
        generate_structures_task.add_output("workgraph.any", f"s_{i}")

        scf_qe_task = wg.add_task(
            calculate_qe,
            name=f"qe_{i}",
            register_pickle_by_value=True,
        )
        scf_qe_tasks.append(scf_qe_task)

    plot_energy_volume_curve_task = wg.add_task(
        plot_energy_volume_curve,
        name="plot_energy_volume_curve",
        register_pickle_by_value=True,
    )

    pickle_element_task = wg.add_task(
        task.pythonjob(outputs=["element"])(pickle_node),
        name="pickle_element",
        value="Al",
    )
    del pickle_node.TaskCls

    pickle_a_task = wg.add_task(
        task.pythonjob(outputs=["a"])(pickle_node), name="pickle_a", value=4.05
    )
    del pickle_node.TaskCls

    pickle_cubic_task = wg.add_task(
        task.pythonjob(outputs=["cubic"])(pickle_node), name="pickle_cubic", value=True
    )
    del pickle_node.TaskCls

    pickle_relax_workdir_task = wg.add_task(
        task.pythonjob(outputs=["relax_workdir"])(pickle_node),
        name="pickle_relax_workdir",
        value="mini",
    )
    del pickle_node.TaskCls

    # ? relax or SCF, or general? -> Should be relax
    relax_get_dict_task = wg.add_task(
        task.pythonjob(
            # outputs=["structure", "calculation", "kpts", "pseudopotentials", "smearing"]
            # outputs=["dict"]
        )(get_dict),
        name="relax_get_dict",
        register_pickle_by_value=True,
    )
    del get_dict.TaskCls

    pickle_pp_task = wg.add_task(
        task.pythonjob(outputs=["pp"])(pickle_node),
        name="pseudopotentials",
        value={"Al": "Al.pbe-n-kjpaw_psl.1.0.0.UPF"},
    )
    del pickle_node.TaskCls

    pickle_kpts_task = wg.add_task(
        task.pythonjob(outputs=["kpts"])(pickle_node), name="kpts_task", value=[1, 1, 1]  # FIXME: Back to [3, 3, 3]
    )
    del pickle_node.TaskCls

    pickle_calc_type_relax_task = wg.add_task(
        task.pythonjob(outputs=["calc"])(pickle_node),
        name="calc_type_relax",
        value="vc-relax",
    )
    del pickle_node.TaskCls

    pickle_smearing_task = wg.add_task(
        task.pythonjob(outputs=["smearing"])(pickle_node), name="smearing", value=0.02
    )
    del pickle_node.TaskCls

    strain_lst_task = wg.add_task(
        task.pythonjob(outputs=["strain_lst"])(pickle_node),
        name="pickle_strain_lst",
        value=strain_lst,
    )
    del pickle_node.TaskCls

    strain_dir_tasks, scf_get_dict_tasks = [], []
    for i, strain in enumerate(strain_lst):
        strain_dir = f"strain_{i}"

        strain_dir_task = wg.add_task(
            task.pythonjob()(pickle_node),
            name=f"pickle_{strain_dir}_dir",
            value=strain_dir,
            register_pickle_by_value=True,
        )
        del pickle_node.TaskCls
        strain_dir_tasks.append(strain_dir_task)

        scf_get_dict_task = wg.add_task(
            task.pythonjob(
                # outputs=[
                #     "dict"
                #     # "structure",
                #     # "calculation",
                #     # "kpts",
                #     # "pseudopotentials",
                #     # "smearing",
                # ]
            )(get_dict),
            name=f"get_dict_{i}",
            register_pickle_by_value=True,
        )
        del get_dict.TaskCls
        scf_get_dict_tasks.append(scf_get_dict_task)

        if i == 0:
            pickle_calc_type_scf_task = wg.add_task(
                task.pythonjob(outputs=["calc"])(pickle_node),
                name="calc_type_scf",
                value="scf",
            )
            del pickle_node.TaskCls

    get_energies_task = wg.add_task(
        task.pythonjob(outputs=["energies"])(get_list),
        name="get_energies",
        register_pickle_by_value=True,
    )
    del get_list.TaskCls

    get_volumes_task = wg.add_task(
        task.pythonjob(outputs=["volumes"])(get_list),
        name="get_volumes",
        register_pickle_by_value=True,
    )
    del get_list.TaskCls

    # Add remaining links
    wg.add_link(
        pickle_element_task.outputs.element, get_bulk_structure_task.inputs.element
    )
    wg.add_link(pickle_a_task.outputs.a, get_bulk_structure_task.inputs.a)
    wg.add_link(pickle_cubic_task.outputs.cubic, get_bulk_structure_task.inputs.cubic)

    # `.set` rather than `.add_link`, as get_dict takes `**kwargs` as input
    relax_get_dict_task.set(
        {
            "structure": get_bulk_structure_task.outputs.structure,
            "calculation": pickle_calc_type_relax_task.outputs.calc,
            "kpts": pickle_kpts_task.outputs.kpts,
            "pseudopotentials": pickle_pp_task.outputs.pp,
            "smearing": pickle_smearing_task.outputs.smearing,
        }
    )

    wg.add_link(relax_get_dict_task.outputs.result, relax_task.inputs.input_dict)
    wg.add_link(
        pickle_relax_workdir_task.outputs.relax_workdir,
        relax_task.inputs.working_directory,
    )

    wg.add_link(relax_task.outputs.structure, generate_structures_task.inputs.structure)
    wg.add_link(
        strain_lst_task.outputs.strain_lst, generate_structures_task.inputs.strain_lst
    )

    for i, (scf_get_dict_task, scf_qe_task, strain_dir_task) in enumerate(
        list(zip(scf_get_dict_tasks, scf_qe_tasks, strain_dir_tasks))
    ):
        scf_get_dict_task.set(
            {
                "structure": generate_structures_task.outputs[f"s_{i}"],
                "calculation": pickle_calc_type_scf_task.outputs.calc,
                "kpts": pickle_kpts_task.outputs.kpts,
                "pseudopotentials": pickle_pp_task.outputs.pp,
                "smearing": pickle_smearing_task.outputs.smearing,
            }
        )

        # import ipdb; ipdb.set_trace()
        wg.add_link(scf_get_dict_task.outputs.result, scf_qe_task.inputs.input_dict)
        wg.add_link(
            strain_dir_task.outputs.result, scf_qe_task.inputs.working_directory
        )

        # collect energy and volume
        wg.add_link(scf_qe_task.outputs.energy, get_energies_task.inputs.kwargs)
        wg.add_link(scf_qe_task.outputs.volume, get_volumes_task.inputs.kwargs)

    wg.add_link(
        get_volumes_task.outputs.volumes,
        plot_energy_volume_curve_task.inputs.volume_lst,
    )
    wg.add_link(
        get_energies_task.outputs.energies,
        plot_energy_volume_curve_task.inputs.energy_lst,
    )

    return wg
