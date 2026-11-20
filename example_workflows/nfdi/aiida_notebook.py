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
# # Aiida
#
# https://github.com/BAMresearch/NFDI4IngScientificWorkflowRequirements
#
# This notebook defines the NFDI4Ing file-based workflow benchmark with [`aiida-workgraph`](https://github.com/aiidateam/aiida-workgraph) and then loads the resulting `workflow.json` into `jobflow`, `pyiron_base` and `pyiron_workflow` to show that the same JSON file can be executed by different engines. Every stage of the workflow calls an external command-line tool (`gmsh`, `meshio`, a FEniCS-based Poisson solver, ParaView's `pvbatch`, `tectonic`) in its own conda environment and passes file paths between stages rather than in-memory Python objects — see [`workflow.py`](workflow.py) for the six pipeline functions.

# %% [markdown]
# ## Define workflow with aiida
#
# `aiida-workgraph` represents a workflow as a `WorkGraph` of `Task`s. `load_profile()` connects to the local AiiDA profile/database that stores provenance and results for every task. `generate_mesh`, `plot_over_line`, `substitute_macros` and `compile_paper` each return a single value and can be added to the graph unchanged, but `convert_to_xdmf` and `poisson` return a `dict`, so they are wrapped with `task(outputs=[...])` to expose each dictionary key as its own output socket that later tasks can connect to.

# %%
import os

# %%
from python_workflow_definition.aiida import write_workflow_json

from aiida_workgraph import WorkGraph, task
from aiida import orm, load_profile

load_profile()

# %%
from workflow import (
    generate_mesh,
    convert_to_xdmf as _convert_to_xdmf,
    poisson as _poisson,
    plot_over_line,
    substitute_macros,
    compile_paper,
)

# %%
convert_to_xdmf = task(outputs=["xdmf_file", "h5_file"])(_convert_to_xdmf)
poisson = task(outputs=["numdofs", "pvd_file", "vtu_file"])(_poisson)

# %% [markdown]
# AiiDA tracks every input as a typed, storable node, so the shared `domain_size` and `source_directory` values are wrapped as `orm.Float` and `orm.Str` before being connected to any task.

# %%
source_directory = orm.Str(os.path.abspath(os.path.join(os.curdir, "source")))

# %%
domain_size = orm.Float(2.0)

# %%
wg = WorkGraph("wg-nfdi")

# %% [markdown]
# Each `wg.add_task` call below adds one stage of the pipeline: mesh generation, XDMF conversion, the Poisson solve, line-plot postprocessing, LaTeX macro substitution and paper compilation. Outputs are wired to the next task's inputs with `.outputs.<name>`; since the underlying functions communicate through files on disk, these connections are really file paths handed from one task to the next, not shared Python objects.

# %%
gmsh_output_file = wg.add_task(
    generate_mesh,
    domain_size=domain_size,
    source_directory=source_directory,
)

# %%
meshio_output_dict = wg.add_task(
    convert_to_xdmf,
    gmsh_output_file=gmsh_output_file.outputs.result,
)

# %%
poisson_dict = wg.add_task(
    poisson,
    meshio_output_xdmf=meshio_output_dict.outputs.xdmf_file,
    meshio_output_h5=meshio_output_dict.outputs.h5_file,
    source_directory=source_directory,
)

# %%
pvbatch_output_file = wg.add_task(
    plot_over_line,
    poisson_output_pvd_file=poisson_dict.outputs.pvd_file,
    poisson_output_vtu_file=poisson_dict.outputs.vtu_file,
    source_directory=source_directory,
)

# %%
macros_tex_file = wg.add_task(
    substitute_macros,
    pvbatch_output_file=pvbatch_output_file.outputs.result,
    ndofs=poisson_dict.outputs.numdofs,
    domain_size=domain_size,
    source_directory=source_directory,
)

# %%
paper_output = wg.add_task(
    compile_paper,
    macros_tex=macros_tex_file.outputs.result,
    plot_file=pvbatch_output_file.outputs.result,
    source_directory=source_directory,
)

# %%
wg

# %% [markdown]
# The `wg` widget above renders the assembled task graph. Once satisfied, `write_workflow_json` serializes it into the PWD `workflow.json` format — one `function` node per task, `input` nodes for `domain_size`/`source_directory`, and edges recording which task output feeds which task's input port, as shown by the `cat` output below.

# %%
workflow_json_filename = "aiida_nfdi.json"

# %%
write_workflow_json(wg=wg, file_name=workflow_json_filename)

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with jobflow
#
# `python_workflow_definition.jobflow.load_workflow_json` reconstructs the same six-stage pipeline as a jobflow `Flow`, purely from `aiida_nfdi.json` — no reference to the `aiida-workgraph` objects defined above. `run_locally` then executes the jobs in dependency order, re-running `gmsh`, `meshio`, the Poisson solver, `pvbatch` and `tectonic` exactly as before.

# %%
from python_workflow_definition.jobflow import load_workflow_json

# %%
from jobflow.managers.local import run_locally

# %%
flow = load_workflow_json(file_name=workflow_json_filename)

# %%
result = run_locally(flow)
result

# %% [markdown]
# ## Load Workflow with pyiron_base
#
# `python_workflow_definition.pyiron_base.load_workflow_json` turns the JSON graph into a list of delayed pyiron jobs; `.draw()` visualizes their dependencies and `.pull()` triggers execution, running each job in turn and returning the final `paper.pdf` path.

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[-1].pull()

# %% [markdown]
# ## Load Workflow with pyiron_workflow
#
# Finally, the same JSON is loaded into a `pyiron_workflow` `Workflow` object. `.draw()` shows the node graph and `.run()` executes it end to end, again shelling out to each external tool in turn.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%
wf.draw(size=(10, 10))

# %%
wf.run()
