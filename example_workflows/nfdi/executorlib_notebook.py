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
# https://github.com/BAMresearch/NFDI4IngScientificWorkflowRequirements
#
# This notebook defines the NFDI4Ing file-based workflow benchmark with [`executorlib`](https://github.com/pyiron/executorlib) and then loads the resulting `workflow.json` into `aiida`, `jobflow`, `pyiron_base` and `pyiron_workflow`. Every stage of the pipeline shells out to an external command-line tool (`gmsh`, `meshio`, a FEniCS-based Poisson solver, ParaView's `pvbatch`, `tectonic`) in its own conda environment and passes file paths between stages rather than in-memory Python objects — see [`workflow.py`](workflow.py).

# %% [markdown]
# ## Define workflow with executorlib
#
# `executorlib` provides a `concurrent.futures`-compatible `SingleNodeExecutor`: each `exe.submit(func, ...)` call schedules a function call and immediately returns a `Future`. Since `convert_to_xdmf` and `poisson` return a `dict`, `get_item_from_future` is used to pick a single key (e.g. `"xdmf_file"`) out of a future's eventual result before passing it on as an input to the next stage.

# %%
import os

# %%
from workflow import (
    generate_mesh,
    convert_to_xdmf,
    poisson,
    plot_over_line,
    substitute_macros,
    compile_paper,
)

# %%
from executorlib import SingleNodeExecutor, get_item_from_future

# %%
domain_size = 2.0

# %%
source_directory = os.path.abspath(os.path.join(os.curdir, "source"))

# %%
workflow_json_filename = "executorlib_nfdi.json"

# %% [markdown]
# Passing `export_workflow_filename` to `SingleNodeExecutor` makes it record every `submit` call as a side effect and write them out as a PWD `workflow.json` once the `with` block exits — no separate `write_workflow_json` call is needed. The six `submit` calls below mirror the six pipeline stages: mesh generation, XDMF conversion, the Poisson solve, line-plot postprocessing, LaTeX macro substitution and paper compilation.

# %%
with SingleNodeExecutor(export_workflow_filename=workflow_json_filename) as exe:
    gmsh_output_file = exe.submit(
        generate_mesh,
        domain_size=domain_size,
        source_directory=source_directory,
    )
    meshio_output_dict = exe.submit(
        convert_to_xdmf,
        gmsh_output_file=gmsh_output_file,
    )
    poisson_dict = exe.submit(
        poisson,
        meshio_output_xdmf=get_item_from_future(meshio_output_dict, key="xdmf_file"),
        meshio_output_h5=get_item_from_future(meshio_output_dict, key="h5_file"),
        source_directory=source_directory,
    )
    pvbatch_output_file = exe.submit(
        plot_over_line,
        poisson_output_pvd_file=get_item_from_future(poisson_dict, key="pvd_file"),
        poisson_output_vtu_file=get_item_from_future(poisson_dict, key="vtu_file"),
        source_directory=source_directory,
    )
    macros_tex_file = exe.submit(
        substitute_macros,
        pvbatch_output_file=pvbatch_output_file,
        ndofs=get_item_from_future(poisson_dict, key="numdofs"),
        domain_size=domain_size,
        source_directory=source_directory,
    )
    paper_output = exe.submit(
        compile_paper,
        macros_tex=macros_tex_file,
        plot_file=pvbatch_output_file,
        source_directory=source_directory,
    )

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with aiida
#
# The JSON produced by `executorlib` is loaded into an `aiida-workgraph` `WorkGraph` via `load_workflow_json`, after connecting to a local AiiDA profile with `load_profile()`. `wg.run()` then re-executes the whole pipeline under `aiida`.

# %%
from aiida import load_profile

load_profile()

# %%
from python_workflow_definition.aiida import load_workflow_json

# %%
wg = load_workflow_json(file_name=workflow_json_filename)
wg

# %%
wg.run()

# %% [markdown]
# ## Load Workflow with jobflow
#
# The same `workflow.json` is reconstructed as a jobflow `Flow` and executed locally with `run_locally`, independently of the `executorlib` objects used to define it.

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
# `load_workflow_json` turns the graph into a list of delayed pyiron jobs; `.draw()` visualizes the dependency chain and `.pull()` triggers execution, returning the path to the final `paper.pdf`.

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
# Finally, the graph is loaded into a `pyiron_workflow` `Workflow`. `.draw()` shows the node graph and `.run()` executes it end to end.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%
wf.draw(size=(10, 10))

# %%
wf.run()

# %%
