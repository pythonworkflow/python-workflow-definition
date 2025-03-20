# %%
from python_workflow_definition.aiida import load_workflow_json

# %%
workgraph = load_workflow_json(filename='workflow_qe.json')

# %%

# TODO: Create inputs rather than tasks out of data nodes
# workgraph

# %%
workgraph.tasks.get_bulk_structure.inputs.element

# %%
from aiida import load_profile
load_profile()

workgraph.run()


# %%



