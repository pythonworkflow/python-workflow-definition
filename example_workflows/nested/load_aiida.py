from python_workflow_definition.aiida import load_workflow_json

from aiida import load_profile

load_profile()

workflow_json_filename = "main.pwd.json"

wg = load_workflow_json(workflow_json_filename)

wg.to_html()
wg.run()
