import unittest
import json
from pathlib import Path
from unittest import mock
from pydantic import ValidationError
from python_workflow_definition.models import (
    PythonWorkflowDefinitionInputNode,
    PythonWorkflowDefinitionOutputNode,
    PythonWorkflowDefinitionFunctionNode,
    PythonWorkflowDefinitionEdge,
    PythonWorkflowDefinitionWorkflow,
    INTERNAL_DEFAULT_HANDLE,
)

class TestModels(unittest.TestCase):
    def setUp(self):
        self.valid_workflow_dict = {
            "version": "1.0",
            "nodes": [
                {"id": 1, "type": "input", "name": "a", "value": 1},
                {"id": 2, "type": "function", "value": "math.add"},
                {"id": 3, "type": "output", "name": "result"},
            ],
            "edges": [
                {"source": 1, "target": 2, "targetPort": "x"},
                {"source": 2, "target": 3, "sourcePort": None},
            ],
        }
        self.workflow = PythonWorkflowDefinitionWorkflow(**self.valid_workflow_dict)

    def test_input_node(self):
        node = PythonWorkflowDefinitionInputNode(id=1, type="input", name="test_input")
        self.assertEqual(node.id, 1)
        self.assertEqual(node.type, "input")
        self.assertEqual(node.name, "test_input")
        self.assertIsNone(node.value)

        node_with_value = PythonWorkflowDefinitionInputNode(
            id=2, type="input", name="test_input_2", value=42
        )
        self.assertEqual(node_with_value.value, 42)

    def test_output_node(self):
        node = PythonWorkflowDefinitionOutputNode(id=1, type="output", name="test_output")
        self.assertEqual(node.id, 1)
        self.assertEqual(node.type, "output")
        self.assertEqual(node.name, "test_output")

    def test_function_node(self):
        node = PythonWorkflowDefinitionFunctionNode(
            id=1, type="function", value="module.function"
        )
        self.assertEqual(node.id, 1)
        self.assertEqual(node.type, "function")
        self.assertEqual(node.value, "module.function")

    def test_function_node_invalid_value(self):
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionFunctionNode(id=1, type="function", value="")
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionFunctionNode(id=1, type="function", value="module")
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionFunctionNode(id=1, type="function", value=".function")
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionFunctionNode(id=1, type="function", value="module.")

    def test_edge(self):
        edge = PythonWorkflowDefinitionEdge(source=1, target=2)
        self.assertEqual(edge.source, 1)
        self.assertEqual(edge.target, 2)
        self.assertEqual(edge.sourcePort, INTERNAL_DEFAULT_HANDLE)
        self.assertIsNone(edge.targetPort)

        edge_with_ports = PythonWorkflowDefinitionEdge(
            source=1, sourcePort="out", target=2, targetPort="in"
        )
        self.assertEqual(edge_with_ports.sourcePort, "out")
        self.assertEqual(edge_with_ports.targetPort, "in")

    def test_edge_default_source_handle(self):
        edge = PythonWorkflowDefinitionEdge(source=1, target=2, sourcePort=None)
        self.assertEqual(edge.sourcePort, INTERNAL_DEFAULT_HANDLE)

    def test_edge_explicit_default_source_handle(self):
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionEdge(
                source=1, target=2, sourcePort=INTERNAL_DEFAULT_HANDLE
            )

    def test_edge_serialization(self):
        edge = PythonWorkflowDefinitionEdge(source=1, target=2, sourcePort=None)
        self.assertIsNone(edge.model_dump(mode="json")["sourcePort"])

        edge_with_port = PythonWorkflowDefinitionEdge(
            source=1, target=2, sourcePort="out"
        )
        self.assertEqual(edge_with_port.model_dump(mode="json")["sourcePort"], "out")

    def test_workflow_model(self):
        self.assertEqual(len(self.workflow.nodes), 3)
        self.assertEqual(len(self.workflow.edges), 2)
        self.assertIsInstance(
            self.workflow.nodes[0], PythonWorkflowDefinitionInputNode
        )

    def test_dump_json(self):
        json_str = self.workflow.dump_json()
        data = json.loads(json_str)
        self.assertEqual(data["version"], self.valid_workflow_dict["version"])
        self.assertEqual(len(data["nodes"]), 3)
        self.assertEqual(len(data["edges"]), 2)
        self.assertIsNone(data["edges"][1]["sourcePort"])

    def test_dump_json_file(self):
        file_path = Path("test_workflow.json")
        if file_path.exists():
            file_path.unlink()
        self.workflow.dump_json_file(file_path)
        self.assertTrue(file_path.exists())
        with open(file_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["version"], self.valid_workflow_dict["version"])
        file_path.unlink()

    def test_load_json_str(self):
        json_str = self.workflow.dump_json()
        loaded_workflow_dict = PythonWorkflowDefinitionWorkflow.load_json_str(json_str)
        reloaded_workflow = PythonWorkflowDefinitionWorkflow(**loaded_workflow_dict)
        self.assertEqual(reloaded_workflow.edges[1].sourcePort, INTERNAL_DEFAULT_HANDLE)

    def test_load_json_str_invalid(self):
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionWorkflow.load_json_str('{"version": "1.0", "nodes": [], "edges": "not_a_list"}')
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionWorkflow.load_json_str('{"version": "1.0", "nodes": []')
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionWorkflow.load_json_str(123)

    def test_load_json_file(self):
        file_path = Path("test_workflow.json")
        self.workflow.dump_json_file(file_path)
        loaded_workflow_dict = PythonWorkflowDefinitionWorkflow.load_json_file(file_path)
        reloaded_workflow = PythonWorkflowDefinitionWorkflow(**loaded_workflow_dict)
        self.assertEqual(reloaded_workflow.edges[1].sourcePort, INTERNAL_DEFAULT_HANDLE)
        file_path.unlink()

    def test_load_json_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            PythonWorkflowDefinitionWorkflow.load_json_file("non_existent_file.json")

    def test_load_json_file_invalid_json(self):
        file_path = Path("invalid_workflow.json")
        with open(file_path, "w") as f:
            f.write('{"version": "1.0", "nodes": "invalid"}')
        with self.assertRaises(ValidationError):
            PythonWorkflowDefinitionWorkflow.load_json_file(file_path)
        file_path.unlink()

    def test_dump_json_file_io_error(self):
        with self.assertRaises(IOError):
            self.workflow.dump_json_file("/")

    @mock.patch("json.dumps")
    def test_dump_json_type_error(self, mock_dumps):
        mock_dumps.side_effect = TypeError("test error")
        with self.assertRaises(TypeError):
            self.workflow.dump_json()

    @mock.patch("python_workflow_definition.models.PythonWorkflowDefinitionWorkflow.model_validate_json")
    def test_load_json_str_generic_exception(self, mock_validate):
        mock_validate.side_effect = Exception("generic error")
        with self.assertRaises(Exception) as cm:
            PythonWorkflowDefinitionWorkflow.load_json_str('{}')
        self.assertEqual(str(cm.exception), "generic error")

    def test_load_json_file_io_error(self):
        with self.assertRaises(IOError):
            PythonWorkflowDefinitionWorkflow.load_json_file("/")
