import json
import os
import sys
import unittest
from pyiron_workflow import Workflow, to_function_node
from python_workflow_definition.pyiron_workflow import load_workflow_json, write_workflow_json

function_str = """
def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def get_square(x):
    return x ** 2
"""

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


class TestPyironWorkflow(unittest.TestCase):
    def test_pyiron_workflow(self):
        workflow_json_filename = "pyiron_workflow_arithmetic.json"
        with open("workflow.py", "w") as f:
            f.write(function_str)

        from workflow import get_prod_and_div as _get_prod_and_div
        from workflow import get_sum as _get_sum
        from workflow import get_square as _get_square

        get_prod_and_div = to_function_node("get_prod_and_div", _get_prod_and_div, "get_prod_and_div")
        get_sum = to_function_node("get_sum", _get_sum, "get_sum")
        get_square = to_function_node("get_square", _get_square, "get_square")
        wf = Workflow("my_workflow")
        wf.x = 1
        wf.y = 2
        wf.prod_and_div = get_prod_and_div(x=wf.x, y=wf.y)
        wf.tmp_sum = get_sum(x=wf.prod_and_div["prod"], y=wf.prod_and_div["div"])
        wf.square_result = get_square(x=wf.tmp_sum)
        write_workflow_json(graph_as_dict=wf.graph_as_dict, file_name=workflow_json_filename)
        wf = load_workflow_json(file_name=workflow_json_filename)
        wf.run()

        self.assertTrue(os.path.exists(workflow_json_filename))

    def test_pyiron_workflow_filename_input(self):
        """A filename string like 'image.png' must be passed through as a plain
        string input, not interpreted as a Python module path or a float."""
        workflow_json_filename = "pyiron_workflow_filename.json"
        with open("echo_module.py", "w") as f:
            f.write(echo_function_str)
        sys.modules.pop("echo_module", None)

        with open(workflow_json_filename, "w") as f:
            f.write(filename_workflow_str)

        with open(workflow_json_filename) as f:
            saved = json.load(f)
        input_values = [
            n["value"]
            for n in saved["nodes"]
            if n["type"] == "input"
        ]
        self.assertIn("image.png", input_values)

        wf = load_workflow_json(file_name=workflow_json_filename)
        wf.run()
        self.assertTrue(os.path.exists(workflow_json_filename))

    def test_pyiron_workflow_filename_input_programmatic(self):
        """Write and round-trip a workflow with a filename input using the
        programmatic write_workflow_json / load_workflow_json path."""
        workflow_json_filename = "pyiron_workflow_filename_prog.json"
        with open("echo_module.py", "w") as f:
            f.write(echo_function_str)
        sys.modules.pop("echo_module", None)

        from echo_module import echo as _echo

        echo_node = to_function_node("echo", _echo, "echo")
        wf = Workflow("filename_workflow")
        wf.filename = "image.png"
        wf.result = echo_node(filename=wf.filename)
        write_workflow_json(graph_as_dict=wf.graph_as_dict, file_name=workflow_json_filename)
        self.assertTrue(os.path.exists(workflow_json_filename))

        with open(workflow_json_filename) as f:
            saved = json.load(f)
        input_values = [
            n["value"]
            for n in saved["nodes"]
            if n["type"] == "input"
        ]
        self.assertIn("image.png", input_values)

        sys.modules.pop("echo_module", None)
        wf2 = load_workflow_json(file_name=workflow_json_filename)
        wf2.run()
        self.assertTrue(os.path.exists(workflow_json_filename))
