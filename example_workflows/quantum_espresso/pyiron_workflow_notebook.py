# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # pyiron_workflow
# ## Define workflow with pyiron_workflow
#
# This notebook builds the Quantum Espresso energy-volume-curve workflow with [`pyiron_workflow`](https://github.com/pyiron/pyiron_workflow). Plain functions are converted to graph nodes with `to_function_node`, assembled into a `Workflow` via attribute access, and exported as a PWD `workflow.json`. The second half of the notebook loads that same JSON with `aiida-workgraph`, `jobflow` and `pyiron_base`.

# %%
from inspect import isfunction
import numpy as np
from pyiron_workflow._legacy import Workflow, to_function_node, as_function_node
from pyiron_workflow._legacy.api import inputs_to_dict
from python_workflow_definition.pyiron_workflow import write_workflow_json

# %%
from workflow import (
    calculate_qe as _calculate_qe,
    generate_structures as _generate_structures,
    get_bulk_structure as _get_bulk_structure,
    plot_energy_volume_curve as _plot_energy_volume_curve,
)


# %% [markdown]
# `pyiron_workflow` has no built-in equivalent of the `get_list` helper the other engines use to collect several outputs into a list, so `get_values_from_dict` is defined here as a custom node with `as_function_node` to turn a dict of energies/volumes into a plain list for the final plot.


# %%
@as_function_node("output_dict")
def get_values_from_dict(input_dict):
    return list(input_dict.values())


# %%
workflow_json_filename = "pyiron_workflow_qe.json"

# %%
calculate_qe = to_function_node("calculate_qe", _calculate_qe, "calculate_qe")
generate_structures = to_function_node(
    "generate_structures", _generate_structures, "generate_structures"
)
get_bulk_structure = to_function_node(
    "get_bulk_structure", _get_bulk_structure, "get_bulk_structure"
)
plot_energy_volume_curve = to_function_node(
    "plot_energy_volume_curve",
    _plot_energy_volume_curve,
    "plot_energy_volume_curve",
    validate_output_labels=False,
)

# %% [markdown]
# `to_function_node` wraps each plain Python function into a `pyiron_workflow` node type. `plot_energy_volume_curve` passes `validate_output_labels=False` since it has no return value, so its output cannot be matched to an explicit output label.

# %%
wf = Workflow("my_workflow")

# %%
wf.pseudopotentials = {"Al": "Al.pbe-n-kjpaw_psl.1.0.0.UPF"}

# %% [markdown]
# Nodes are added to the `Workflow` by assigning their result to an attribute of `wf` (e.g. `wf.structure = get_bulk_structure(...)`), which both registers the node and gives it a name in the graph. Since `calculate_qe` expects a single `input_dict` argument, `inputs_to_dict` is used to bundle the structure, pseudopotentials, k-points, calculation type and smearing into one dict-valued node before the first (`vc-relax`) QE calculation.

# %%
wf.element = "Al"
wf.a = 4.04
wf.cubic = True
wf.structure = get_bulk_structure(
    element=wf.element,
    a=wf.a,
    cubic=wf.cubic,
)

# %%
wf.working_directory_0 = "mini"
input_dict = {
    "structure": wf.structure,
    "pseudopotentials": wf.pseudopotentials,
    "kpts": (3, 3, 3),
    "calculation": "vc-relax",
    "smearing": 0.02,
}
wf.input_dict_0 = inputs_to_dict(
    input_specification=list(input_dict.keys()), **input_dict
)

# %%
wf.calc_mini = calculate_qe(
    working_directory=wf.working_directory_0,
    input_dict=wf.input_dict_0,
)

# %% [markdown]
# `generate_structures` fans out the relaxed structure into `number_of_strains` (5) strained structures (`wf.structure_lst["s_0"]` ... `["s_4"]`). The loop below builds one `input_dict` and one independent `scf` `calculate_qe` node per strained structure, so five QE calculations run to sample the energy-volume curve.

# %%
number_of_strains = 5
wf.strain_lst = np.linspace(0.9, 1.1, number_of_strains)
wf.structure_lst = generate_structures(  # the generate_structures() function is not available in the workflow graph
    structure=wf.calc_mini["structure"],
    strain_lst=wf.strain_lst,
)

# %%
job_strain_lst = []
for i in range(number_of_strains):
    setattr(
        wf,
        "input_dict_" + str(i + 1),
        inputs_to_dict(
            input_specification=[
                "structure",
                "pseudopotentials",
                "kpts",
                "calculation",
                "smearing",
            ],
            structure=wf.structure_lst["s_" + str(i)],
            pseudopotentials=wf.pseudopotentials,
            kpts=(3, 3, 3),
            calculation="scf",
            smearing=0.02,
        ),
    )
    setattr(
        wf,
        "calc_strain_" + str(i),
        calculate_qe(
            working_directory="strain_" + str(i),
            input_dict=getattr(wf, "input_dict_" + str(i + 1)),
        ),
    )
    job_strain_lst.append(getattr(wf, "calc_strain_" + str(i)))

# %% [markdown]
# The `energy` and `volume` outputs of the five strained calculations are bundled with `inputs_to_dict` and then flattened into two plain lists with the `get_values_from_dict` node defined above, ready to be passed to `plot_energy_volume_curve`.

# %%
volume_dict = {"s_" + str(i): j["volume"] for i, j in enumerate(job_strain_lst)}
wf.volume_dict = inputs_to_dict(
    input_specification=list(volume_dict.keys()), **volume_dict
)
energy_dict = {"s_" + str(i): j["energy"] for i, j in enumerate(job_strain_lst)}
wf.energy_dict = inputs_to_dict(
    input_specification=list(energy_dict.keys()),
    **energy_dict,
)
wf.volume_lst = get_values_from_dict(input_dict=wf.volume_dict)
wf.energy_lst = get_values_from_dict(input_dict=wf.energy_dict)

# %%
wf.plot = plot_energy_volume_curve(volume_lst=wf.volume_lst, energy_lst=wf.energy_lst)

# %% [markdown]
# `.draw()` renders the assembled node graph, and `write_workflow_json` exports it - using `wf.graph_as_dict` - to the PWD `workflow.json` format so it can be loaded by another engine.

# %%
wf.draw(size=(10, 10))

# %%
write_workflow_json(graph_as_dict=wf.graph_as_dict, file_name=workflow_json_filename)

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with aiida
#
# `load_workflow_json` reconstructs the graph as an `aiida-workgraph` `WorkGraph`. The lattice constant `a` is overridden (4.04 -> 4.05) to show the loaded graph can still be edited like one built natively with `aiida-workgraph`, before running it with `wg.run()`.

# %%
from aiida import orm, load_profile

load_profile()

# %%
from python_workflow_definition.aiida import load_workflow_json

# %%
wg = load_workflow_json(file_name=workflow_json_filename)

# %%
wg.tasks.get_bulk_structure.inputs.a.value = orm.Float(4.05)

# %%
wg.run()

# %% [markdown]
# ## Load Workflow with jobflow
#
# The same JSON is loaded as a `jobflow` `Flow` and executed locally with `run_locally`, again after overriding the lattice constant `a`.

# %%
from python_workflow_definition.jobflow import load_workflow_json

# %%
from jobflow.managers.local import run_locally

# %%
flow = load_workflow_json(file_name=workflow_json_filename)

# %%
flow[0].function_kwargs["a"] = 4.05

# %%
result = run_locally(flow)
result

# %% [markdown]
# ## Load Workflow with pyiron_base
#
# Finally, `pyiron_base`'s loader turns the graph into a list of delayed jobs. `.draw()` visualizes the dependency graph and `.pull()` executes the whole chain (relax + 5 strained SCF calculations), after overriding the lattice constant `a`.

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name="workflow.json")
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[0].input["a"] = 4.05

# %%
delayed_object_lst[-1].pull()

# %%
