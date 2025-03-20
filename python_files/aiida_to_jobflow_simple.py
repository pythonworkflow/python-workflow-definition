# %%

from python_workflow_definition.aiida import write_workflow_json
from python_workflow_definition.jobflow import load_workflow_json
from aiida_workgraph import task, WorkGraph

from aiida import load_profile
load_profile()

# %%
from simple_workflow import (
    add_x_and_y as _add_x_and_y,
    add_x_and_y_and_z as _add_x_and_y_and_z,
)

# %%
from aiida import orm

add_x_and_y = task.pythonjob(outputs=["x", "y", "z"])(_add_x_and_y)
add_x_and_y_and_z = task.pythonjob()(_add_x_and_y_and_z)

# workgraph = write_workflow_json(filename='workflow_simple.json')

# TODO: Create inputs rather than tasks out of data nodes
wg = WorkGraph('wg-simple')

add_x_and_y_task = wg.add_task(
    add_x_and_y,
    name='add_x_and_y',
    x=orm.Int(1),
    y=orm.Int(2),
)

add_x_and_y_and_z_task = wg.add_task(
    add_x_and_y_and_z,
    name='add_x_and_y_and_z',
    x=add_x_and_y_task.outputs.x,
    y=add_x_and_y_task.outputs.y,
    z=add_x_and_y_task.outputs.z,
)

wg

# %%
def pickle_node(value):
    """Handle data nodes"""
    return value

helper_1 = task.pythonjob()(pickle_node)
helper_2 = task.pythonjob()(pickle_node)

add_x_and_y = task.pythonjob(outputs=["x", "y", "z"])(_add_x_and_y)
add_x_and_y_and_z = task.pythonjob()(_add_x_and_y_and_z)

# workgraph = write_workflow_json(filename='workflow_simple.json')

# TODO: Create inputs rather than tasks out of data nodes
wg = WorkGraph('wg-simple')

helper_task1 = wg.add_task(
    helper_1,
    name="x",
    value=1
)

helper_task2 = wg.add_task(
    helper_2,
    name="y",
    value=2
)

add_x_and_y_task = wg.add_task(
    add_x_and_y,
    name='add_x_and_y',
    x=helper_task1.outputs.result,
    y=helper_task2.outputs.result,
)

add_x_and_y_and_z_task = wg.add_task(
    add_x_and_y_and_z,
    name='add_x_and_y_and_z',
    x=add_x_and_y_task.outputs.x,
    y=add_x_and_y_task.outputs.y,
    z=add_x_and_y_task.outputs.z,
)

wg

# %%
write_workflow_json(wg=wg, file_name="workflow_simple_aiida.json")



