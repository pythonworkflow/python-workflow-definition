# %%
from python_workflow_definition.aiida import load_workflow_json, write_workflow_json
from aiida import load_profile
load_profile()
# %%
workgraph = load_workflow_json(filename='workflow_qe.json')

# %%

# TODO: Create inputs rather than tasks out of data nodes
# workgraph


# %%
# workgraph.run()


# %%
# compare the two json files
import json

with open('workflow_qe.json', 'r') as f:
    reference = json.loads(f.read())
new_data = write_workflow_json(workgraph, file_name='workflow_qe_aiida.json')

def check_diff(reference, new_data):
    for key, data in reference['nodes'].items():
        if key not in new_data['nodes']:
            print(f"Key {key} not in new_data")
        if data != new_data['nodes'][key]:
            print(f"Data for key {key} is different")
    for data in reference['edges']:
        if data not in new_data['edges']:
            print(f"Data {data} not in new_data")

check_diff(reference, new_data)
print("Reverse check")
check_diff(new_data, reference)
    



