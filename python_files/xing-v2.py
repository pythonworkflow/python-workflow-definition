# %% [markdown]
# # WorkGraph version
#
#

# %%
import json
from aiida import load_profile
from simple_workflow import add_x_and_y, add_x_and_y_and_z
from quantum_espresso_workflow import (
    get_bulk_structure,
    calculate_qe,
    plot_energy_volume_curve,
)
from aiida_workgraph import WorkGraph, task
import traceback


load_profile()


# -------------------------------------------------------------
# from python_workflow_definition.base
# I modified the kwargs["kwargs"] to kwargs, not sure why it is kwargs["kwargs"]
@task.pythonjob()
def get_list(**kwargs):
    return list(kwargs.values())


# from python_workflow_definition.base
@task.pythonjob()
def get_dict(**kwargs):
    return {k: v for k, v in kwargs.items()}


# I modified this function so the keys is a valid key allowed by AiiDA
def generate_structures(structure, strain_lst):
    from ase import Atoms

    structure_lst = []
    for strain in strain_lst:
        structure_strain = Atoms(**structure)
        structure_strain.set_cell(
            structure_strain.cell * strain ** (1 / 3), scale_atoms=True
        )
        structure_lst.append(structure_strain)
    return {f"s_{i}": s.todict() for i, s in enumerate(structure_lst)}


# I defined the function mapping here
# but in principle, this is not needed, because one can import the function from the module path
func_mapping = {
    "simple_workflow.add_x_and_y": task.pythonjob()(add_x_and_y),
    "simple_workflow.add_x_and_y_and_z": task.pythonjob()(add_x_and_y_and_z),
    "quantum_espresso_workflow.get_bulk_structure": task.pythonjob()(
        get_bulk_structure
    ),
    "quantum_espresso_workflow.calculate_qe": task.pythonjob()(calculate_qe),
    "quantum_espresso_workflow.plot_energy_volume_curve": task.pythonjob()(
        plot_energy_volume_curve
    ),
    "python_workflow_definition.pyiron_base.get_dict": task.pythonjob()(get_dict),
    "python_workflow_definition.pyiron_base.get_list": task.pythonjob()(get_list),
    "quantum_espresso_workflow.generate_structures": task.pythonjob()(
        generate_structures
    ),
}


# -------------------------------------------------------------
# These is the helper functions for the WorkGraph onlly
@task.pythonjob()
def pickle_node(value):
    """Handle data nodes"""
    return value


@task.pythonjob()
def get_item(data: dict, key: str):
    """Handle get item from the outputs"""
    return data[key]


# -------------------------------------------------------------
def load_workflow_json(filename):
    with open(filename) as f:
        data = json.load(f)

    wg = WorkGraph()
    task_name_mapping = {}
    # add tasks
    for name, identifer in data["nodes"].items():
        if isinstance(identifer, str) and identifer in func_mapping:
            func = func_mapping[identifer]
            # I use the register_pickle_by_value, because the function is defined in a local file
            wg.add_task(func, register_pickle_by_value=True)
            # Remove the default result output, because we will add the outputs later from the data in the link
            del wg.tasks[-1].outputs["result"]
        else:
            # data task
            wg.add_task(pickle_node, value=identifer)
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


# %%


filename = "workflow_simple.json"
filename = "workflow_qe.json"

wg = load_workflow_json(filename)
# wg


# %%
# wg.run()

# %%


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
            try:
                data["nodes"][i] = node["inputs"]["value"]["property"]["value"].value
            except KeyError:
                import ipdb

                ipdb.set_trace()
        i += 1

    for link in wgdata["links"]:
        if (
            wgdata["tasks"][link["from_node"]]["executor"]["callable_name"]
            == "pickle_node"
        ):
            link["from_socket"] = None
        link["from_node"] = node_name_mapping[link["from_node"]]
        link["to_node"] = node_name_mapping[link["to_node"]]
        data["edges"].append(link)

    return data


# %%

filename = "workgraph_qe_xing-v2.json"
data = write_workflow_json(wg)
with open(filename, "w") as f:
    json.dump(data, f, indent=4)


# %% [markdown]
# ### EOS WorkGraph
# Here we try to implement the EOS workflow mannuallly.

# %%
import json
from aiida import load_profile
from quantum_espresso_workflow import (
    get_bulk_structure,
    calculate_qe,
    plot_energy_volume_curve,
)

# from python_workflow_definition.pyiron_base import  get_dict
from aiida_workgraph import WorkGraph, task
from typing import Any

load_profile()


# from python_workflow_definition.base
@task.pythonjob()
def get_list(**kwargs):
    return list(kwargs.values())


# from python_workflow_definition.base
@task.pythonjob()
def get_dict(**kwargs):
    return {k: v for k, v in kwargs.items()}


# I modified this function so the keys is a valid key allowed by AiiDA
def generate_structures(structure, strain_lst):
    from ase import Atoms

    structure_lst = []
    for strain in strain_lst:
        structure_strain = Atoms(**structure)
        structure_strain.set_cell(
            structure_strain.cell * strain ** (1 / 3), scale_atoms=True
        )
        structure_lst.append(structure_strain)
    return {f"s_{i}": s.todict() for i, s in enumerate(structure_lst)}


# -------------------------------------------------------------
# These is the helper functions for the WorkGraph onlly
@task.pythonjob()
def pickle_node(value):
    """Handle data nodes"""
    return value


get_bulk_structure_task = task.pythonjob()(get_bulk_structure)
generate_structures_task = task.pythonjob()(generate_structures)
calculate_qe_task = task.pythonjob(outputs=["energy", "volume", "structure"])(
    calculate_qe
)
plot_energy_volume_curve_task = task.pythonjob()(plot_energy_volume_curve)

strain_lst = [0.9, 0.95, 1.0, 1.05, 1.1]
wg = WorkGraph()
wg.add_task(
    get_bulk_structure_task,
    name="bulk",
    element="Al",
    a=4.05,
    cubic=True,
    register_pickle_by_value=True,
)
wg.add_task(pickle_node, name="calculation", value="vc-relax")
wg.add_task(pickle_node, name="kpts", value=[3, 3, 3])
wg.add_task(
    pickle_node, name="pseudopotentials", value={"Al": "Al.pbe-n-kjpaw_psl.1.0.0.UPF"}
)
wg.add_task(pickle_node, name="smearing", value=0.02)
wg.add_task(
    get_dict,
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
wg.add_task(get_list, name="get_energies", register_pickle_by_value=True)
wg.add_task(get_list, name="get_volumes", register_pickle_by_value=True)
wg.add_task(pickle_node, name="calculation_scf", value="scf")
for i, strain in enumerate(strain_lst):
    get_dict_task = wg.add_task(
        get_dict,
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
        input_dict=get_dict_task.outputs.result,
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
wg
# wg.to_html()


# %%
wg.run()

# %%
