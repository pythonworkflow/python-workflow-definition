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
# This notebook defines the arithmetic workflow with [`executorlib`](https://github.com/pyiron/executorlib), a lightweight `concurrent.futures`-style executor for up-scaling Python functions to HPC resources, and then loads the resulting `workflow.json` into `aiida-workgraph`, `jobflow`, `pyiron_base` and `pyiron_workflow`.

# %% [markdown]
# ## Define workflow with executorlib
#
# `executorlib`'s `SingleNodeExecutor` implements the standard `Executor` interface: `.submit()` schedules a function call and immediately returns a `Future`. Passing `export_workflow_filename` to the executor records every submitted call and its dependencies as a side effect and writes them out as a PWD `workflow.json` once the `with` block exits.

# %%
from executorlib import SingleNodeExecutor, get_item_from_future

# %%
from workflow import get_sum, get_prod_and_div, get_square

# %%
workflow_json_filename = "executorlib_arithmetic.json"

# %% [markdown]
# `get_prod_and_div` returns a dictionary, so `get_item_from_future` is used to extract the `prod` and `div` keys from its future's result before they can be passed on as separate arguments to `get_sum`.

# %%
with SingleNodeExecutor(export_workflow_filename=workflow_json_filename) as exe:
    future_prod_and_div = exe.submit(get_prod_and_div, x=1, y=2)
    future_prod = get_item_from_future(future_prod_and_div, key="prod")
    future_div = get_item_from_future(future_prod_and_div, key="div")
    future_sum = exe.submit(get_sum, x=future_prod, y=future_div)
    future_result = exe.submit(get_square, x=future_sum)

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with aiida
#
# The exported `workflow.json` is loaded into `aiida-workgraph`. As with the other notebooks, an AiiDA profile must be connected via `load_profile()` before the resulting `WorkGraph` can be run.

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
# The same JSON is loaded into a jobflow `Flow` and executed locally with `run_locally`.

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
# Loading the workflow into `pyiron_base` produces a list of delayed jobs; `.draw()` visualizes the dependency graph and `.pull()` triggers delayed execution of the whole chain.

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
# Finally, the workflow is loaded into a `pyiron_workflow` `Workflow` object, drawn with `.draw()` and executed with `.run()`.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%
wf.draw(size=(10, 10))

# %%
wf.run()

# %%
