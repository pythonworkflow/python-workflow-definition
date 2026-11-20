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
# # executorlib
#
# This notebook builds the Quantum Espresso energy-volume-curve workflow with [`executorlib`](https://github.com/pyiron/executorlib), a lightweight `concurrent.futures`-style executor. Tasks are submitted individually with `.submit()`, and the resulting graph is exported as a PWD `workflow.json` as a side effect. The second half of the notebook loads that same JSON with `aiida-workgraph`, `jobflow` and `pyiron_base`/`pyiron_workflow`.

# %% [markdown]
# ## Define workflow with executorlib
#
# `SingleNodeExecutor` runs submitted functions in local worker processes. Passing `export_workflow_filename` makes it record every `.submit()` call and its dependencies and write them out as `workflow_json_filename` once the `with` block exits - no separate `write_workflow_json` call is needed, unlike the other engines.

# %%
import numpy as np
from executorlib import SingleNodeExecutor, get_item_from_future

# %%
from workflow import (
    calculate_qe,
    generate_structures,
    get_bulk_structure,
    plot_energy_volume_curve,
)

# %%
workflow_json_filename = "executorlib_qe.json"

# %%
pseudopotentials = {"Al": "Al.pbe-n-kjpaw_psl.1.0.0.UPF"}

# %% [markdown]
# Each `exe.submit()` call schedules one function call and returns a `Future`. Since `calculate_qe` returns a dict, `get_item_from_future` extracts a single key (e.g. `"structure"`, `"energy"`, `"volume"`) from a future's eventual result so it can be passed as an argument to the next `submit()` call. The relaxed structure is strained into `number_of_strains` (5) structures by `generate_structures`, and each strained structure is submitted as its own independent `scf` `calculate_qe` call - the fan-out that produces the 5 points of the energy-volume curve.

# %%
with SingleNodeExecutor(export_workflow_filename=workflow_json_filename) as exe:
    structure_future = exe.submit(
        get_bulk_structure,
        element="Al",
        a=4.04,
        cubic=True,
    )
    calc_mini_future = exe.submit(
        calculate_qe,
        working_directory="mini",
        input_dict={
            "structure": structure_future,
            "pseudopotentials": pseudopotentials,
            "kpts": (3, 3, 3),
            "calculation": "vc-relax",
            "smearing": 0.02,
        },
    )
    number_of_strains = 5
    structure_lst_future = exe.submit(
        generate_structures,
        structure=get_item_from_future(calc_mini_future, key="structure"),
        strain_lst=np.linspace(0.9, 1.1, number_of_strains),
    )
    calc_future_lst = []
    for i, structure_strain in [
        [i, get_item_from_future(structure_lst_future, key="s_" + str(i))]
        for i in range(number_of_strains)
    ]:
        calc_future_lst.append(
            exe.submit(
                calculate_qe,
                working_directory="strain_" + str(i),
                input_dict={
                    "structure": structure_strain,
                    "pseudopotentials": pseudopotentials,
                    "kpts": (3, 3, 3),
                    "calculation": "scf",
                    "smearing": 0.02,
                },
            )
        )
    plot_future = exe.submit(
        plot_energy_volume_curve,
        volume_lst=[
            get_item_from_future(future=f, key="volume") for f in calc_future_lst
        ],
        energy_lst=[
            get_item_from_future(future=f, key="energy") for f in calc_future_lst
        ],
    )

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with aiida
#
# `load_workflow_json` reconstructs the graph as an `aiida-workgraph` `WorkGraph`. To demonstrate that the loaded graph can still be edited like one built natively with `aiida-workgraph`, the lattice constant `a` is overridden (4.04 -> 4.05) before running it with `wg.run()`.

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
# `pyiron_base`'s loader turns the graph into a list of delayed jobs. `.draw()` visualizes the dependency graph and `.pull()` executes the whole chain (relax + 5 strained SCF calculations), after the lattice constant override.

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
# Finally, the graph is loaded into a `pyiron_workflow` `Workflow`, its lattice constant overridden, drawn with `.draw()`, and executed with `.run()`.

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

# %%
