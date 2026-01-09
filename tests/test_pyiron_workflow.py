import unittest
import os
from pyiron_workflow import Workflow, to_function_node
from python_workflow_definition.pyiron_workflow import load_workflow_json, write_workflow_json


def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def get_square(x):
    return x ** 2


class TestPyironWorkflow(unittest.TestCase):
    def test_pyiron_workflow(self):
        workflow_json_filename = "pyiron_workflow_arithmetic.json"
        get_prod_and_div_node = to_function_node("get_prod_and_div", get_prod_and_div, "get_prod_and_div")
        get_sum_node = to_function_node("get_sum", get_sum, "get_sum")
        get_square_node = to_function_node("get_square", get_square, "get_square")
        wf = Workflow("my_workflow")
        wf.x = 1
        wf.y = 2
        wf.prod_and_div = get_prod_and_div_node(x=wf.x, y=wf.y)
        wf.tmp_sum = get_sum_node(x=wf.prod_and_div["prod"], y=wf.prod_and_div["div"])
        wf.square_result = get_square_node(x=wf.tmp_sum)
        write_workflow_json(graph_as_dict=wf.graph_as_dict, file_name=workflow_json_filename)
        wf = load_workflow_json(file_name=workflow_json_filename)
        wf.run()

        self.assertTrue(os.path.exists(workflow_json_filename))
