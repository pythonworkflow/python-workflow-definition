# %% [markdown]
# # Aiida

# %% [markdown]
# ## Define workflow with aiida

# %%
from python_workflow_definition.aiida import AiidaPwdConverter

from aiida_workgraph import WorkGraph, task
from aiida import orm, load_profile
from rich.pretty import pprint

load_profile()

workflow_json_filename =  "aiida_simple.json"

# %%
from workflow import (
    get_sum as _get_sum,
    get_prod_and_div as _get_prod_and_div,
    square as _square
)

# %%
wg = WorkGraph("arithmetic")

# %%
get_prod_and_div_task = wg.add_task(
    task(outputs=['prod', 'div'])(_get_prod_and_div),
    name="get_prod_and_div",
    x=orm.Float(1),
    y=orm.Float(2),
)

# %%
get_sum_task = wg.add_task(
    _get_sum,
    name="get_sum",
    x=get_prod_and_div_task.outputs.prod,
    y=get_prod_and_div_task.outputs.div,
)

# %%
square_task = wg.add_task(
    _square,
    name="square",
    x=get_sum_task.outputs.result,
)

# %%
aiida_converter = AiidaPwdConverter()
model = aiida_converter.workgraph_to_model(wg=wg)
pprint(model.model_dump())

# model.dump_json_file(file_name=workflow_json_filename)

wg = aiida_converter.model_to_workgraph(model)
wg
# model.dump_json_file(file_name=workflow_json_filename)

# %%
# Currently conversion PWD <-> WG is not atomic, as information is lost due to the `group_outputs` workaround, and the
# fact that `group_inputs` is not implemented in WG, at all

# pwd_wf = PwdWorkflow.load_json_file(workflow_json_filename)
# wg = aiida_converter.model_to_workgraph(workflow_model=pwd_wf)

# model = aiida_converter.workgraph_to_model(wg)
# pprint(model.model_dump())

# %%

# %% [markdown]
# ## Load Workflow with jobflow

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

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[-1].pull()


