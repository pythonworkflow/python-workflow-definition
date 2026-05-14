import sys
import unittest
from python_workflow_definition.purepython import load_workflow_json

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

echo_function_str = """
def echo(filename):
    return filename
"""

filename_workflow_str = """
{
  "version": "0.1.0",
  "nodes": [
    {"id": 0, "type": "function", "value": "echo_module.echo"},
    {"id": 1, "type": "input", "value": "image.png", "name": "filename"},
    {"id": 2, "type": "output", "name": "result"}
  ],
  "edges": [
    {"target": 0, "targetPort": "filename", "source": 1, "sourcePort": null},
    {"target": 2, "targetPort": null, "source": 0, "sourcePort": null}
  ]
}"""


class TestPurePython(unittest.TestCase):
    def test_pure_python(self):
        with open("workflow.py", "w") as f:
            f.write(function_str)

        with open("workflow.json", "w") as f:
            f.write(workflow_str)

        self.assertEqual(load_workflow_json(file_name="workflow.json"), 6.25)

    def test_purepython_filename_input(self):
        """A filename string like 'image.png' must be passed through as a plain
        string input, not interpreted as a Python module path or a float."""
        with open("echo_module.py", "w") as f:
            f.write(echo_function_str)
        sys.modules.pop("echo_module", None)

        with open("filename_workflow.json", "w") as f:
            f.write(filename_workflow_str)

        result = load_workflow_json(file_name="filename_workflow.json")
        self.assertEqual(result, "image.png")

    def test_purepython_filename_input_multiple_dots(self):
        """Filenames with multiple dots (e.g. 'archive.tar.gz') must also be
        treated as plain string inputs, not as nested module references."""
        multi_dot_workflow_str = """
{
  "version": "0.1.0",
  "nodes": [
    {"id": 0, "type": "function", "value": "echo_module.echo"},
    {"id": 1, "type": "input", "value": "archive.tar.gz", "name": "filename"},
    {"id": 2, "type": "output", "name": "result"}
  ],
  "edges": [
    {"target": 0, "targetPort": "filename", "source": 1, "sourcePort": null},
    {"target": 2, "targetPort": null, "source": 0, "sourcePort": null}
  ]
}"""
        with open("echo_module.py", "w") as f:
            f.write(echo_function_str)
        sys.modules.pop("echo_module", None)

        with open("multi_dot_workflow.json", "w") as f:
            f.write(multi_dot_workflow_str)

        result = load_workflow_json(file_name="multi_dot_workflow.json")
        self.assertEqual(result, "archive.tar.gz")
