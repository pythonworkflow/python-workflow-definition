import unittest
import os
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
