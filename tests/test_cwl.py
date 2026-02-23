import unittest
import pickle
import subprocess
from python_workflow_definition.cwl import write_workflow

function_str = """
def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def get_square(x):
    return x ** 2
"""

workflow_str = """
{
  "version": "0.1.0",
  "nodes": [
    {"id": 0, "type": "function", "value": "workflow.get_prod_and_div"},
    {"id": 1, "type": "function", "value": "workflow.get_sum"},
    {"id": 2, "type": "function", "value": "workflow.get_square"},
    {"id": 3, "type": "input", "value": 1, "name": "x"},
    {"id": 4, "type": "input", "value": 2, "name": "y"},
    {"id": 5, "type": "output", "name": "result"}
  ],
  "edges": [
    {"target": 0, "targetPort": "x", "source": 3, "sourcePort": null},
    {"target": 0, "targetPort": "y", "source": 4, "sourcePort": null},
    {"target": 1, "targetPort": "x", "source": 0, "sourcePort": "prod"},
    {"target": 1, "targetPort": "y", "source": 0, "sourcePort": "div"},
    {"target": 2, "targetPort": "x", "source": 1, "sourcePort": null},
    {"target": 5, "targetPort": null, "source": 2, "sourcePort": null}
  ]
}"""

class TestCommonWorkflowLanguage(unittest.TestCase):
    def test_common_workflow_language(self):
        with open("workflow.py", "w") as f:
            f.write(function_str)

        with open("workflow.json", "w") as f:
            f.write(workflow_str)

        write_workflow(file_name="workflow.json")
        subprocess.check_output(["cwltool", "workflow.cwl", "workflow.yml"])
        with open("result.pickle", "rb") as f:
            self.assertEqual(pickle.load(f), 6.25)
