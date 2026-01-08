import unittest
import os
from jobflow import job, Flow
from jobflow.managers.local import run_locally
from python_workflow_definition.jobflow import load_workflow_json, write_workflow_json


def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def get_square(x):
    return x ** 2


class TestJobflow(unittest.TestCase):
    def test_jobflow(self):
        workflow_json_filename = "jobflow_simple.json"
        get_sum_job = job(get_sum)
        get_prod_and_div_job = job(get_prod_and_div)
        get_square_job = job(get_square)
        prod_and_div = get_prod_and_div_job(x=1, y=2)
        tmp_sum = get_sum_job(x=prod_and_div.output.prod, y=prod_and_div.output.div)
        result = get_square_job(x=tmp_sum.output)
        flow = Flow([prod_and_div, tmp_sum, result])
        write_workflow_json(flow=flow, file_name=workflow_json_filename)
        flow = load_workflow_json(file_name=workflow_json_filename)
        result = run_locally(flow)

        self.assertTrue(os.path.exists(workflow_json_filename))
        self.assertEqual(result[result.keys()[-1]][1].output, 6.25)
