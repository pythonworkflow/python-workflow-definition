import json
import sys
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from python_workflow_definition.aiida import (
    load_workflow_json,
    write_workflow_json,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "example_workflows"
sys.path.insert(0, str(EXAMPLES / "arithmetic"))


class TestAiiDAGraphs(unittest.TestCase):
    def test_arithmetic_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = EXAMPLES / "arithmetic" / "workflow.json"
            handle = load_workflow_json(source, module_name="pwd_test_arith")
            template = handle.build().to_dict()
            self.assertEqual(
                sorted(task["name"] for task in template["tasks"]),
                ["pwd_task_0", "pwd_task_1", "pwd_task_2"],
            )
            exported = tmp_path / "arithmetic.json"
            write_workflow_json(handle, exported)
            values = sorted(
                node["value"]
                for node in json.loads(exported.read_text())["nodes"]
                if node["type"] == "function"
            )
            self.assertEqual(
                values,
                [
                    "workflow.get_prod_and_div",
                    "workflow.get_square",
                    "workflow.get_sum",
                ],
            )
            inputs = sorted(
                (node["name"], node["value"])
                for node in json.loads(exported.read_text())["nodes"]
                if node["type"] == "input"
            )
            self.assertEqual(inputs, [("x", 1), ("y", 2)])
            round_tripped = (
                load_workflow_json(exported, module_name="pwd_test_arith_rt")
                .build()
                .to_dict()
            )
            self.assertEqual(
                sorted(task["name"] for task in round_tripped["tasks"]),
                ["pwd_task_0", "pwd_task_1", "pwd_task_2"],
            )

    def test_workflow_node_rejected(self):
        nested = {
            "version": "0.1.1",
            "nodes": [
                {
                    "id": 0,
                    "type": "workflow",
                    "graph": {"nodes": [], "edges": []},
                },
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            nested_file = Path(tmp) / "nested.json"
            nested_file.write_text(json.dumps(nested))
            with self.assertRaisesRegex(ValidationError, "workflow"):
                load_workflow_json(nested_file, module_name="pwd_test_nested")

    def test_duplicate_input_names_suffixed(self):
        duplicate = {
            "version": "0.1.0",
            "nodes": [
                {"id": 0, "type": "input", "name": "x", "value": 1},
                {"id": 1, "type": "input", "name": "x", "value": 2},
                {
                    "id": 2,
                    "type": "function",
                    "value": "python_workflow_definition.shared.get_dict",
                },
                {"id": 3, "type": "output", "name": "result"},
            ],
            "edges": [
                {
                    "target": 2,
                    "targetPort": "a",
                    "source": 0,
                    "sourcePort": None,
                },
                {
                    "target": 2,
                    "targetPort": "b",
                    "source": 1,
                    "sourcePort": None,
                },
                {
                    "target": 3,
                    "targetPort": None,
                    "source": 2,
                    "sourcePort": None,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            duplicate_file = Path(tmp) / "duplicate.json"
            duplicate_file.write_text(json.dumps(duplicate))
            tasks = (
                load_workflow_json(duplicate_file, module_name="pwd_test_dup")
                .build()
                .to_dict()["tasks"]
            )
            self.assertEqual(
                sorted(task["name"] for task in tasks),
                ["pwd_task_2"],
            )


if __name__ == "__main__":
    unittest.main()
