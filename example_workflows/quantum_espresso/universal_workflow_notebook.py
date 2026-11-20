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
# # Load Quantum Espresso Energy Volume Curve Workflow
#
# This notebook loads the same, already-exported [`workflow.json`](workflow.json) with six different backends in turn - `aiida-workgraph`, `executorlib`, `jobflow`, `pyiron_base`, `pyiron_workflow` and plain Python - to demonstrate that the PWD format is interoperable regardless of which engine originally produced it.

# %% [markdown]
# ## Plot
#
# `python_workflow_definition.plot.plot` renders the raw node/edge structure of `workflow.json` as a graph, independent of any workflow engine - useful to inspect the relax -> strain -> 5x scf -> plot pipeline before executing it.

# %%
from python_workflow_definition.plot import plot

# %%
plot(file_name="workflow.json")

# %% [markdown]
# ## Aiida
#
# `load_workflow_json` reconstructs the graph as an `aiida-workgraph` `WorkGraph`, after connecting to the local AiiDA profile with `load_profile()`. `wg.run()` executes the relax step followed by the 5 parallel strained SCF calculations and the final plot.

# %%
from python_workflow_definition.aiida import load_workflow_json
from aiida import load_profile

load_profile()

# %%
wg = load_workflow_json(file_name="workflow.json")

# %%
wg

# %%
wg.run()


# %% [markdown]
# ## executorlib
#
# Here `load_workflow_json` takes a live `exe` (a `SingleNodeExecutor`) and submits the whole graph to it, returning a `Future` for the final result; `.result()` blocks until every node - including the 5 fanned-out SCF calculations - has finished executing.

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
# ## jobflow
#
# The graph is loaded as a `jobflow` `Flow` and executed locally with `run_locally`, which runs the relax job, the 5 strained SCF jobs and the plotting job in dependency order.

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
# ## pyiron_base
#
# `load_workflow_json` turns the graph into a list of delayed pyiron jobs; `.draw()` visualizes the dependency graph (including the fan-out into 5 strained SCF jobs) and `.pull()` executes the whole chain.

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
# The graph is loaded into a `pyiron_workflow` `Workflow`, drawn with `.draw()`, and executed with `.run()`.

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
# `python_workflow_definition.purepython.load_workflow_json` is a minimal reference implementation with no external workflow engine: it topologically sorts the nodes by their edges and calls each function directly in plain Python, returning the final result.

# %%
from python_workflow_definition.purepython import load_workflow_json

# %%
load_workflow_json(file_name="workflow.json")
