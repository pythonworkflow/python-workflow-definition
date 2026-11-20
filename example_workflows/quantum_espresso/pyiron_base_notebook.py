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
# # pyiron
#
# This notebook builds the Quantum Espresso energy-volume-curve workflow with [`pyiron_base`](https://github.com/pyiron/pyiron_base). The `job` decorator turns plain functions into delayed pyiron jobs that are only executed once `.pull()` is called on the final result, and the whole chain of jobs is exported as a PWD `workflow.json`. The second half of the notebook loads that same JSON with `aiida-workgraph`, `jobflow` and `pyiron_workflow`.

# %% [markdown]
# ## Define workflow with pyiron_base
#
# We import the `job` decorator from `pyiron_base` and the PWD writer for `pyiron_base`, together with the Quantum Espresso functions from `workflow.py`.

# %%
import numpy as np
from pyiron_base import job
from python_workflow_definition.pyiron_base import write_workflow_json

# %%
from workflow import (
    calculate_qe as _calculate_qe,
    generate_structures as _generate_structures,
    get_bulk_structure as _get_bulk_structure,
    plot_energy_volume_curve as _plot_energy_volume_curve,
)

# %%
workflow_json_filename = "pyiron_base_qe.json"

# %% [markdown]
# `calculate_qe` returns a dict with `energy`, `volume` and `structure` keys. `job(..., output_key_lst=[...])` tells `pyiron_base` which keys to expose as separate delayed outputs (e.g. `calc_mini.output.structure`), so a single downstream job can depend on just one of them instead of the whole dict.

# %%
calculate_qe = job(_calculate_qe, output_key_lst=["energy", "volume", "structure"])
generate_structures = job(_generate_structures)
plot_energy_volume_curve = job(_plot_energy_volume_curve)
get_bulk_structure = job(_get_bulk_structure)

# %%
pseudopotentials = {"Al": "Al.pbe-n-kjpaw_psl.1.0.0.UPF"}

# %%
structure = get_bulk_structure(
    element="Al",
    a=4.04,
    cubic=True,
)

# %%
calc_mini = calculate_qe(
    working_directory="mini",
    input_dict={
        "structure": structure,
        "pseudopotentials": pseudopotentials,
        "kpts": (3, 3, 3),
        "calculation": "vc-relax",
        "smearing": 0.02,
    },
)

# %% [markdown]
# `generate_structures` fans out the relaxed structure into `number_of_strains` (5) strained structures. Since `pyiron_base` builds the graph lazily, it cannot know how many items a delayed dict result will contain, so `list_length` is passed explicitly - this lets `structure_lst` be iterated with `enumerate()` below to create one independent `scf` `calculate_qe` job per strained structure, before anything has actually run.

# %%
number_of_strains = 5
structure_lst = generate_structures(  # the generate_structures() function is not available in the workflow graph
    structure=calc_mini.output.structure,
    strain_lst=np.linspace(0.9, 1.1, number_of_strains),
    list_length=number_of_strains,
)

# %%
job_strain_lst = []
for i, structure_strain in enumerate(structure_lst):
    calc_strain = calculate_qe(
        working_directory="strain_" + str(i),
        input_dict={
            "structure": structure_strain,
            "pseudopotentials": pseudopotentials,
            "kpts": (3, 3, 3),
            "calculation": "scf",
            "smearing": 0.02,
        },
    )
    job_strain_lst.append(calc_strain)

# %%
plot = plot_energy_volume_curve(
    volume_lst=[job.output.volume for job in job_strain_lst],
    energy_lst=[job.output.energy for job in job_strain_lst],
)

# %% [markdown]
# `write_workflow_json` only needs the single terminal delayed object (`plot`, the plotting job) - `pyiron_base` walks its dependency chain backwards to discover the full graph, unlike `jobflow`'s `Flow` which needs an explicit list of jobs.

# %%
write_workflow_json(delayed_object=plot, file_name=workflow_json_filename)

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
# ## Load Workflow with pyiron_workflow
#
# Finally, the graph is loaded into a `pyiron_workflow` `Workflow`, its lattice constant overridden, drawn with `.draw()`, and executed with `.run()`.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%

# %%
wf.get_bulk_structure.inputs.a.value = 4.05

# %%
wf.draw(size=(10, 10))

# %%
wf.run()

# %%
