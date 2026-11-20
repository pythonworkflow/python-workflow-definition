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
# # Load Simple Workflow
#
# This notebook loads the single, pre-existing NFDI4Ing `workflow.json` — the file-based benchmark from [`workflow.py`](workflow.py) that runs `gmsh`, `meshio`, a FEniCS-based Poisson solver, ParaView's `pvbatch` and `tectonic` in turn — with several different engines. Since the JSON only describes function nodes, inputs, outputs and the edges between them, it does not matter which engine originally wrote it; any of the engines below can load and execute it, each re-running the same chain of external tools.

# %% [markdown]
# ## Plot
#
# Before running the workflow with any engine, `python_workflow_definition.plot.plot` renders `workflow.json` directly as a graph of function, input and output nodes — independent of any particular workflow engine.

# %%
from python_workflow_definition.plot import plot

# %%
plot(file_name="workflow.json")

# %% [markdown]
# ## Aiida
#
# Loading the JSON into `aiida-workgraph` requires connecting to an AiiDA profile first via `load_profile()`; the workflow is then reconstructed as a `WorkGraph` and executed with `.run()`, which re-runs `generate_mesh`, `convert_to_xdmf`, `poisson`, `plot_over_line`, `substitute_macros` and `compile_paper` in order.

# %%
from python_workflow_definition.aiida import load_workflow_json

from aiida import load_profile

load_profile()

# %%
workgraph = load_workflow_json(file_name="workflow.json")

# %%
# TODO: Create inputs rather than tasks out of data nodes
workgraph

# %%

workgraph.run()

# %% [markdown]
# ## executorlib
#
# `python_workflow_definition.executorlib.load_workflow_json` submits each function node to the given `Executor` and returns the `Future` of the final node (the compiled `paper.pdf` path); calling `.result()` blocks until the whole chain of external tools has completed.

# %%
from executorlib import SingleNodeExecutor

# %%
from python_workflow_definition.executorlib import load_workflow_json

# %%
with SingleNodeExecutor(max_workers=1) as exe:
    result = load_workflow_json(file_name="workflow.json", exe=exe).result()

# %%
result

# %% [markdown]
# ## Jobflow
#
# The JSON is reconstructed as a jobflow `Flow` and executed locally with `run_locally`.

# %%
from jobflow.managers.local import run_locally

# %%
from python_workflow_definition.jobflow import load_workflow_json

# %%
flow = load_workflow_json(file_name="workflow.json")

# %%
result = run_locally(flow)
result

# %% [markdown]
# ## pyiron
#
# Loading the JSON into `pyiron_base` produces a list of delayed jobs; `.draw()` visualizes the dependency graph and `.pull()` triggers execution of the whole chain, again writing intermediate files to `preprocessing/`, `processing/` and `postprocessing/`.

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name="workflow.json")
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[-1].pull()

# %% [markdown]
# ## Load Workflow with pyiron_workflow
#
# Finally, the workflow is loaded into a `pyiron_workflow` `Workflow` object, drawn with `.draw()` and executed with `.run()`.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name="workflow.json")

# %%
wf.draw(size=(10, 10))

# %%
wf.run()

# %% [markdown]
# ## Python
#
# As a baseline, `python_workflow_definition.purepython.load_workflow_json` interprets the JSON directly in plain Python, with no workflow engine involved: it evaluates each function node in dependency order — invoking `gmsh`, `meshio`, the Poisson solver, `pvbatch` and `tectonic` via `conda_subprocess` exactly as `workflow.py` defines — and returns the final result.

# %%
from python_workflow_definition.purepython import load_workflow_json

# %%
load_workflow_json(file_name="workflow.json")
