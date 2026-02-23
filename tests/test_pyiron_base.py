import unittest
import os
from pyiron_base import job
from python_workflow_definition.pyiron_base import load_workflow_json, write_workflow_json


def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def get_square(x):
    return x ** 2


class TestPyironBase(unittest.TestCase):
    def test_pyiron_base(self):
        workflow_json_filename = "pyiron_arithmetic.json"
        get_sum_job_wrapper = job(get_sum)
        get_prod_and_div_job_wrapper = job(get_prod_and_div, output_key_lst=["prod", "div"])
        get_square_job_wrapper = job(get_square)

        prod_and_div = get_prod_and_div_job_wrapper(x=1, y=2)
        tmp_sum = get_sum_job_wrapper(x=prod_and_div.output.prod, y=prod_and_div.output.div)
        result = get_square_job_wrapper(x=tmp_sum)
        write_workflow_json(delayed_object=result, file_name=workflow_json_filename)
        delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)

        self.assertTrue(os.path.exists(workflow_json_filename))
        self.assertEqual(delayed_object_lst[-1].pull(), 6.25)
