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
# # jobflow

# %% [markdown] jupyter={"outputs_hidden": false}
# [`jobflow`](https://materialsproject.github.io/jobflow/index.html) and [`atomate2`](https://materialsproject.github.io/atomate2/index.html) are key packages of the [Materials Project](https://materialsproject.org/) . `jobflow` was especially designed to simplify the execution of dynamic workflows -- when the actual number of jobs is dynamically determined upon runtime instead of being statically fixed before running the workflow(s). `jobflow`'s overall flexibility allows for building workflows that go beyond the usage in materials science. `jobflow` serves as the basis of `atomate2`, which implements data generation workflows in the context of materials science and will be used for data generation in the Materials Project in the future.

# %% [markdown]
# ## Define workflow with jobflow
#
# We start by importing the job decorator and Flow class from `jobflow` and the respective PWD tools.

# %%
import numpy as np

# %%
from jobflow import job, Flow

# %%
from python_workflow_definition.jobflow import write_workflow_json

# %% [markdown] jupyter={"outputs_hidden": false}
# ## Quantum Espresso Workflow
# We will use the knowledge from the previous arithmetic workflow example to create the Quantum Espresso-related tasks for calculating an "Energy vs. Volume" curve. It’s important to note that this is only a basic implementation, and further extensions towards data validation or for a simplified user experience can be added. For example, one can typically configure run commands for quantum-chemical programs via configuration files in atomate2.

# %%
from workflow import (
    calculate_qe as _calculate_qe,
    generate_structures as _generate_structures,
    get_bulk_structure as _get_bulk_structure,
    plot_energy_volume_curve as _plot_energy_volume_curve,
)

# %%
workflow_json_filename = "jobflow_qe.json"

# %%
calculate_qe = job(_calculate_qe)
generate_structures = job(_generate_structures)
plot_energy_volume_curve = job(_plot_energy_volume_curve)
get_bulk_structure = job(_get_bulk_structure)

# %% [markdown] jupyter={"outputs_hidden": false}
# We need to specify the typical QE input like pseudopotential(s) and structure model.

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
        "structure": structure.output,
        "pseudopotentials": pseudopotentials,
        "kpts": (3, 3, 3),
        "calculation": "vc-relax",
        "smearing": 0.02,
    },
)

# %% [markdown] jupyter={"outputs_hidden": false}
# Next, for the "Energy vs. Volume" curve, we need to specify the number of strained structures and save them into a list object. This is the fan-out point of the workflow: for each of the `number_of_strains` (5) strained structures, an independent `scf` QE calculation is carried out below.

# %%
number_of_strains = 5
structure_lst = generate_structures(
    structure=calc_mini.output.structure,
    strain_lst=np.linspace(0.9, 1.1, number_of_strains),
)

# %%
job_strain_lst = []
for i in range(number_of_strains):
    calc_strain = calculate_qe(
        working_directory="strain_" + str(i),
        input_dict={
            "structure": getattr(structure_lst.output, f"s_{i}"),
            "pseudopotentials": pseudopotentials,
            "kpts": (3, 3, 3),
            "calculation": "scf",
            "smearing": 0.02,
        },
    )
    job_strain_lst.append(calc_strain)

# %% [markdown] jupyter={"outputs_hidden": false}
# Finally, we specify a plotter for the "Energy vs. Volume" curve and can export the workflow.

# %%
plot = plot_energy_volume_curve(
    volume_lst=[job.output.volume for job in job_strain_lst],
    energy_lst=[job.output.energy for job in job_strain_lst],
)

# %%
flow = Flow([structure, calc_mini, structure_lst] + job_strain_lst + [plot])

# %%
write_workflow_json(flow=flow, file_name=workflow_json_filename)

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with aiida
#
# Now, we can import the workflow, run it with `aiida` and plot the "Energy vs. Volume" curve.

# %%
from aiida import orm, load_profile

load_profile()

# %%
from python_workflow_definition.aiida import load_workflow_json

# %%
wg = load_workflow_json(workflow_json_filename)

# %%
wg.tasks.get_bulk_structure.inputs.a.value = orm.Float(4.05)

# %%
wg

# %%
wg.run()

# %% [markdown]
# ## Load Workflow with pyiron_base
#
# And we can repeat the same process using `pyiron_base`: `load_workflow_json` turns the graph into a list of delayed jobs, `.draw()` visualizes the dependency graph, and `.pull()` executes the whole chain (relax + 5 strained SCF calculations) after overriding the lattice constant `a`.

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
# Finally, the same JSON is loaded into a `pyiron_workflow` `Workflow`; nodes become graph nodes reachable via attribute access (e.g. `wf.get_bulk_structure`). The lattice constant `a` is overridden again before drawing the graph with `.draw()` and executing it with `.run()`.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%

# %%

# %%
wf.get_bulk_structure.inputs.a.value = 4.05

# %%
wf.draw(size=(10, 10))

# %%
wf.run()
