import unittest
import os
from aiida_workgraph import WorkGraph, task
from aiida import orm, load_profile
load_profile()

from python_workflow_definition.aiida import load_workflow_json, write_workflow_json


def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def get_square(x):
    return x ** 2


class TestAiiDA(unittest.TestCase):
    def test_aiida(self):
        workflow_json_filename = "aiida_simple.json"
        wg = WorkGraph("arithmetic")
        get_prod_and_div_task = wg.add_task(
            task(outputs=['prod', 'div'])(get_prod_and_div),
            x=orm.Float(1),
            y=orm.Float(2),
        )
        get_sum_task = wg.add_task(
            get_sum,
            x=get_prod_and_div_task.outputs.prod,
            y=get_prod_and_div_task.outputs.div,
        )
        get_square_task = wg.add_task(
            get_square,
            x=get_sum_task.outputs.result,
        )
        write_workflow_json(wg=wg, file_name=workflow_json_filename)
        workgraph = load_workflow_json(file_name='workflow.json')
        workgraph.run()

        self.assertTrue(os.path.exists(workflow_json_filename))