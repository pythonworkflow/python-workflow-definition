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
# This notebook defines the arithmetic workflow with [`pyiron_base`](https://github.com/pyiron/pyiron_base) and then loads the resulting `workflow.json` into `aiida-workgraph`, `jobflow` and `pyiron_workflow`.

# %% [markdown]
# ## Define workflow with pyiron_base
#
# The `job` decorator from `pyiron_base` turns a plain Python function into a pyiron job: calling the decorated function no longer executes it immediately, but returns a delayed object that can be chained with other jobs. For functions such as `get_prod_and_div` that return a dictionary, `output_key_lst` declares the dictionary keys so that individual entries (`prod`, `div`) can be wired as separate outputs to downstream jobs.

# %%
from pyiron_base import job

# %%
from python_workflow_definition.pyiron_base import write_workflow_json

# %%
from workflow import (
    get_sum as _get_sum,
    get_prod_and_div as _get_prod_and_div,
    get_square as _get_square,
)

# %%
workflow_json_filename = "pyiron_arithmetic.json"

# %%
get_sum = job(_get_sum)
get_prod_and_div = job(_get_prod_and_div, output_key_lst=["prod", "div"])
get_square = job(_get_square)

# %%
prod_and_div = get_prod_and_div(x=1, y=2)

# %%
tmp_sum = get_sum(x=prod_and_div.output.prod, y=prod_and_div.output.div)

# %%
result = get_square(x=tmp_sum)

# %% [markdown]
# None of these calls run yet, they only build up a graph of delayed jobs. `write_workflow_json` walks that graph starting from the final `result` job and serializes it into the PWD `workflow.json` format.

# %%
write_workflow_json(delayed_object=result, file_name=workflow_json_filename)

# %%
# !cat {workflow_json_filename}

# %% [markdown]
# ## Load Workflow with aiida
#
# The exported `workflow.json` is loaded into `aiida-workgraph`. An AiiDA profile must be connected via `load_profile()` before the resulting `WorkGraph` can be run.

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
