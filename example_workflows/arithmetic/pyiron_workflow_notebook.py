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
# # pyiron_workflow
#
# This notebook defines the arithmetic workflow with [`pyiron_workflow`](https://github.com/pyiron/pyiron_workflow) and then loads the resulting `workflow.json` into `aiida-workgraph`, `jobflow` and `pyiron_base`.

# %% [markdown]
# ## Define workflow in pyiron_workflow
#
# `to_function_node` wraps a plain Python function into a `pyiron_workflow` node that can be added to a `Workflow` graph. Nodes are assembled into a graph with attribute access: assigning `wf.<name> = node(...)` both registers the node under that name and connects its inputs to the outputs of other nodes already on the graph.

# %%
from python_workflow_definition.pyiron_workflow import write_workflow_json

# %%
from pyiron_workflow._legacy import Workflow, to_function_node

# %%
from workflow import (
    get_prod_and_div as _get_prod_and_div,
    get_sum as _get_sum,
    get_square as _get_square,
)

# %%
workflow_json_filename = "pyiron_workflow_arithmetic.json"

# %%
get_prod_and_div = to_function_node(
    "get_prod_and_div", _get_prod_and_div, "get_prod_and_div"
)
get_sum = to_function_node("get_sum", _get_sum, "get_sum")
get_square = to_function_node("get_square", _get_square, "get_square")

# %%
wf = Workflow("my_workflow")

# %%
wf.x = 1
wf.y = 2
wf.prod_and_div = get_prod_and_div(x=wf.x, y=wf.y)
wf.tmp_sum = get_sum(x=wf.prod_and_div["prod"], y=wf.prod_and_div["div"])
wf.square_result = get_square(x=wf.tmp_sum)

# %% [markdown]
# `wf.draw()` renders the resulting node graph, and `write_workflow_json` serializes `wf.graph_as_dict` into the PWD `workflow.json` format.

# %%
wf.draw(size=(10, 10))

# %%
write_workflow_json(graph_as_dict=wf.graph_as_dict, file_name=workflow_json_filename)

# %%
# !cat workflow.json

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
# ## Load Workflow with pyiron_base
#
# Finally, the workflow is loaded into `pyiron_base`, producing a list of delayed jobs. `.draw()` visualizes the dependency graph and `.pull()` triggers delayed execution of the whole chain.

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[-1].pull()
