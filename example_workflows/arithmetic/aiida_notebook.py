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
# This notebook defines the arithmetic workflow with [`aiida-workgraph`](https://github.com/aiidateam/aiida-workgraph) and then loads the resulting `workflow.json` into `jobflow`, `pyiron_base` and `pyiron_workflow`, to demonstrate that the same workflow definition can be executed by several different engines.

# %% [markdown]
# ## Define workflow with aiida
#
# `aiida-workgraph` represents a workflow as a `WorkGraph` of `Task`s. Tasks are executed and stored by the AiiDA engine, so we first need to connect to an AiiDA profile with `load_profile()` before any task can run.

# %%
from python_workflow_definition.aiida import write_workflow_json

from aiida_workgraph import WorkGraph, task
from aiida import orm, load_profile

load_profile()

workflow_json_filename = "aiida_simple.json"

# %%
from workflow import (
    get_sum as _get_sum,
    get_prod_and_div as _get_prod_and_div,
    get_square as _get_square,
)

# %% [markdown]
# The arithmetic functions are imported under a leading underscore because they are still plain Python functions at this point; `wg.add_task` below turns each one into an AiiDA `Task` that can be linked to other tasks' inputs and outputs. `get_prod_and_div` returns a dictionary, so it is wrapped with `task(outputs=['prod', 'div'])` to expose `prod` and `div` as separate output sockets.

# %%
wg = WorkGraph("arithmetic")

# %%
get_prod_and_div_task = wg.add_task(
    task(outputs=["prod", "div"])(_get_prod_and_div),
    x=orm.Float(1),
    y=orm.Float(2),
)

# %%
get_sum_task = wg.add_task(
    _get_sum,
    x=get_prod_and_div_task.outputs.prod,
    y=get_prod_and_div_task.outputs.div,
)

# %%
get_square_task = wg.add_task(
    _get_square,
    x=get_sum_task.outputs.result,
)

# %% [markdown]
# With all tasks connected, `write_workflow_json` walks the `WorkGraph`'s tasks and links and serializes them into the PWD `workflow.json` format: each task becomes a `function` node and each link becomes an edge between an input and an output port.

# %%
write_workflow_json(wg=wg, file_name=workflow_json_filename)

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with jobflow
#
# The same `workflow.json` can now be loaded by a different engine. `python_workflow_definition.jobflow.load_workflow_json` reconstructs a jobflow `Flow` from the JSON, which is then executed locally with `run_locally`.

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
# The same JSON file is loaded into `pyiron_base`, producing a list of delayed jobs. `.draw()` visualizes the dependency graph and `.pull()` triggers delayed execution, running each job in turn and returning the final result.

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
# Finally, the workflow is loaded into `pyiron_workflow`, producing a `Workflow` object whose node graph can be visualized with `.draw()` and executed with `.run()`.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%
wf.draw(size=(10, 10))

# %%
wf.run()
