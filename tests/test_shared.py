import unittest
from python_workflow_definition.shared import get_dict, get_list


class TestShared(unittest.TestCase):
    def test_get_dict(self):
        self.assertEqual({"a": 1, "b": 2, "c": 3}, get_dict(a=1, b=2, c=3))

    def test_get_list(self):
        self.assertEqual([1, 2, 3], get_list(a=1, b=2, c=3))
