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
# # aiida-workgraph
#
# This notebook builds the Quantum Espresso energy-volume-curve workflow directly with [`aiida-workgraph`](https://github.com/aiidateam/aiida-workgraph) and exports it as a PWD `workflow.json`. The second half of the notebook loads that same JSON file with `jobflow`, `pyiron_base` and `pyiron_workflow` to show that a graph built with one engine can be executed by another.

# %% [markdown]
# ## Define workflow with aiida
#
# `aiida-workgraph` represents a workflow as a `WorkGraph` built from `task`s, each wrapping a Python function; connecting a task's output to another task's input builds up the graph. `load_profile()` connects to the local AiiDA profile/database, which is required before any AiiDA node can be created, since every task and its result are stored there for provenance.

# %%
from python_workflow_definition.aiida import write_workflow_json
from python_workflow_definition.shared import get_dict, get_list

from aiida import load_profile, orm

load_profile()

workflow_json_filename = "aiida_qe.json"

# %%
from aiida_workgraph import task, WorkGraph

# %%
from workflow import (
    generate_structures,
    get_bulk_structure,
    calculate_qe as _calculate_qe,
    plot_energy_volume_curve,
)

# %% [markdown]
# `calculate_qe` (defined in [`workflow.py`](workflow.py)) returns a dict with `energy`, `volume` and `structure` keys. Wrapping it with `task(outputs=[...])` tells `aiida-workgraph` to expose these as separate output sockets (`.outputs.energy`, `.outputs.volume`, `.outputs.structure`) instead of a single opaque result, so downstream tasks can connect to individual keys.

# %%
calculate_qe = task(outputs=["energy", "volume", "structure"])(_calculate_qe)

# %%
wg = WorkGraph("wg-qe")

# %% [markdown]
# ### Prepare the inputs
#
# Scalar inputs are wrapped as AiiDA data types (`orm.Str`, `orm.Float`, `orm.Bool`, `orm.Dict`, `orm.List`) so AiiDA can track their provenance. `strain_lst` are the five volumetric strains (0.9-1.1) that will later be applied to the relaxed structure to sample the energy-volume curve.

# %%
element = orm.Str("Al")
a = orm.Float(4.04)
cubic = orm.Bool(True)
relax_workdir = orm.Str("mini")
pseudopotentials = orm.Dict({"Al": "Al.pbe-n-kjpaw_psl.1.0.0.UPF"})
kpts = orm.List([3, 3, 3])
calc_type_relax = orm.Str("vc-relax")
calc_type_scf = orm.Str("scf")
smearing = orm.Float(0.02)
strain_lst = orm.List([0.9, 0.95, 1.0, 1.05, 1.1])

# %% [markdown]
# ### Build the task graph
#
# The pipeline is: `get_bulk_structure` builds the initial Al structure, `calculate_qe` relaxes it (`vc-relax`), `generate_structures` applies the strains, and one `calculate_qe` (`scf`) task per strained structure computes its energy and volume. `get_dict` bundles the structure, calculation type, k-points, pseudopotentials and smearing into the `input_dict` argument `calculate_qe` expects.

# %%
get_bulk_structure_task = wg.add_task(
    get_bulk_structure,
    element=element,
    a=a,
    cubic=cubic,
)

# %%
relax_prepare_input_dict_task = wg.add_task(
    get_dict,
    structure=get_bulk_structure_task.outputs.result,
    calculation=calc_type_relax,
    kpts=kpts,
    pseudopotentials=pseudopotentials,
    smearing=smearing,
)

relax_task = wg.add_task(
    calculate_qe,
    input_dict=relax_prepare_input_dict_task.outputs.result,
    working_directory=relax_workdir,
)

# %% [markdown]
# `generate_structures` applies each of the five strains to the relaxed structure, producing five strained structures (`s_0` ... `s_4`). This is the fan-out point of the workflow: the loop below adds one independent `scf` `calculate_qe` task per strained structure, and their `energy`/`volume` outputs are collected into two lists (via `get_list` tasks) for the final plot.

# %%
generate_structures_task = wg.add_task(
    generate_structures,
    structure=relax_task.outputs.structure,
    strain_lst=strain_lst,
)

# %%
get_volumes_task = wg.add_task(get_list)

# %%
get_energies_task = wg.add_task(get_list)

# %%
strain_dir_tasks, scf_qe_tasks, scf_get_dict_tasks = [], [], []

for i, strain in enumerate(strain_lst):
    structure_key = f"s_{i}"
    strain_dir = orm.Str(f"strain_{i}")
    generate_structures_task.add_output("workgraph.any", structure_key)

    scf_prepare_input_dict_task = wg.add_task(
        get_dict,
        structure=generate_structures_task.outputs[structure_key],
        calculation=calc_type_scf,
        kpts=kpts,
        pseudopotentials=pseudopotentials,
        smearing=smearing,
    )

    scf_qe_task = wg.add_task(
        calculate_qe,
        input_dict=scf_prepare_input_dict_task.outputs.result,
        working_directory=strain_dir,
    )

    # collect energy and volume
    get_energies_task.set_inputs({f"{i}": scf_qe_task.outputs.energy})
    get_volumes_task.set_inputs({f"{i}": scf_qe_task.outputs.volume})

# %%
plot_energy_volume_curve_task = wg.add_task(
    plot_energy_volume_curve,
    volume_lst=get_volumes_task.outputs.result,
    energy_lst=get_energies_task.outputs.result,
)

# %% [markdown]
# Displaying `wg` renders an interactive `NodeGraphWidget` of the task graph, which is useful to check the wiring before running it. `write_workflow_json` then serializes the `WorkGraph` into the PWD `workflow.json` format (nodes = functions/inputs/outputs, edges = data connections) so it can be loaded by another engine.

# %%
wg

# %%
_ = write_workflow_json(wg=wg, file_name=workflow_json_filename)


# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with jobflow
#
# `load_workflow_json` reconstructs the same graph as a `jobflow` `Flow` of `Job`s. To show that the loaded graph behaves like a native `jobflow` object, the lattice constant `a` of the first job is overridden (4.04 -> 4.05) before the flow is executed locally with `run_locally`.

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
# `pyiron_base`'s `load_workflow_json` turns each node into a delayed pyiron job. `.draw()` renders the dependency graph, and `.pull()` triggers execution of the whole chain, saving every intermediate job (relax + 5 strained SCF calculations) to the pyiron project.

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[0].input["a"] = 4.05

# %%
delayed_object_lst[-1].pull()

# %% [markdown]
# ## Load Workflow with pyiron_workflow
#
# Finally, the same JSON is loaded into a `pyiron_workflow` `Workflow` object. Nodes become graph nodes reachable via attribute access (e.g. `wf.get_bulk_structure`), and `.run()` executes them in dependency order.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%
wf.get_bulk_structure.inputs.a.value = 4.05

# %%
wf.draw(size=(10, 10))

# %%
wf.run()
