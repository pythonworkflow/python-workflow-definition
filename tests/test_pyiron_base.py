import json
import os
import unittest
from pyiron_base import job
from python_workflow_definition.pyiron_base import load_workflow_json, write_workflow_json


def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def get_square(x):
    return x ** 2


def echo(filename):
    return filename


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

    def test_pyiron_base_filename_input(self):
        """A filename string like 'image.png' must be passed through as a plain
        string input, not interpreted as a Python module path or a float."""
        workflow_json_filename = "pyiron_filename.json"
        echo_job_wrapper = job(echo)
        result_delayed = echo_job_wrapper(filename="image.png")

        write_workflow_json(delayed_object=result_delayed, file_name=workflow_json_filename)
        self.assertTrue(os.path.exists(workflow_json_filename))

        with open(workflow_json_filename) as f:
            saved = json.load(f)
        input_values = [
            n["value"]
            for n in saved["nodes"]
            if n["type"] == "input"
        ]
        self.assertIn("image.png", input_values)

        delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
        self.assertEqual(delayed_object_lst[-1].pull(), "image.png")
