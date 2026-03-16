from python_workflow_definition.jobflow import load_workflow_json

flow=load_workflow_json("main2.pwd.json")

from jobflow import run_locally
flow.draw_graph(figsize=(3, 3)).show()
print(flow.as_dict())
print(run_locally(flow))
