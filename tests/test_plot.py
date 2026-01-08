import json
import os
import unittest
from unittest.mock import patch, MagicMock
import networkx as nx
from pydantic import ValidationError
from python_workflow_definition.plot import plot
from python_workflow_definition.shared import (
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    TARGET_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_PORT_LABEL,
)


class TestPlot(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_workflow.json"
        self.workflow_data = {
            "version": "0.0.1",
            NODES_LABEL: [
                {"id": 1, "name": "Node 1", "type": "function", "value": "a.b"},
                {"id": 2, "name": "Node 2", "type": "function", "value": "c.d"},
                {"id": 3, "name": "Node 3", "type": "function", "value": "e.f"},
            ],
            EDGES_LABEL: [
                {
                    SOURCE_LABEL: 1,
                    TARGET_LABEL: 2,
                    SOURCE_PORT_LABEL: "out1",
                    TARGET_PORT_LABEL: "in1",
                },
                {
                    SOURCE_LABEL: 2,
                    TARGET_LABEL: 3,
                    SOURCE_PORT_LABEL: "out2",
                    TARGET_PORT_LABEL: "in2",
                },
                {
                    SOURCE_LABEL: 1,
                    TARGET_LABEL: 3,
                    SOURCE_PORT_LABEL: None,
                    TARGET_PORT_LABEL: "in3",
                },
            ],
        }
        with open(self.test_file, "w") as f:
            json.dump(self.workflow_data, f)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch("python_workflow_definition.plot.display")
    @patch("python_workflow_definition.plot.SVG")
    @patch("networkx.nx_agraph.to_agraph")
    def test_plot(self, mock_to_agraph, mock_svg, mock_display):
        mock_agraph = MagicMock()
        mock_to_agraph.return_value = mock_agraph
        mock_agraph.draw.return_value = "<svg></svg>"

        plot(self.test_file)

        self.assertEqual(1, mock_to_agraph.call_count)
        graph = mock_to_agraph.call_args[0][0]
        self.assertIsInstance(graph, nx.DiGraph)

        self.assertCountEqual(["1", "2", "3"], graph.nodes)
        self.assertEqual("a.b", graph.nodes["1"]["name"])
        self.assertEqual("c.d", graph.nodes["2"]["name"])
        self.assertEqual("e.f", graph.nodes["3"]["name"])

        self.assertCountEqual([("1", "2"), ("2", "3"), ("1", "3")], graph.edges)

        edge_n1_n2_data = graph.get_edge_data("1", "2")
        self.assertIn("label", edge_n1_n2_data)
        self.assertEqual("in1=result[out1]", edge_n1_n2_data["label"])

        edge_n1_n3_data = graph.get_edge_data("1", "3")
        self.assertIn("label", edge_n1_n3_data)
        self.assertEqual("in3", edge_n1_n3_data["label"])

        mock_svg.assert_called_once_with("<svg></svg>")
        mock_display.assert_called_once()

    @patch("python_workflow_definition.plot.display")
    @patch("python_workflow_definition.plot.SVG")
    @patch("networkx.nx_agraph.to_agraph")
    def test_plot_multiple_edges_same_source(self, mock_to_agraph, mock_svg, mock_display):
        self.workflow_data[EDGES_LABEL].append(
            {
                SOURCE_LABEL: 1,
                TARGET_LABEL: 2,
                SOURCE_PORT_LABEL: "out2",
                TARGET_PORT_LABEL: "in2",
            }
        )
        with open(self.test_file, "w") as f:
            json.dump(self.workflow_data, f)

        mock_agraph = MagicMock()
        mock_to_agraph.return_value = mock_agraph
        mock_agraph.draw.return_value = "<svg></svg>"

        plot(self.test_file)

        self.assertEqual(1, mock_to_agraph.call_count)
        graph = mock_to_agraph.call_args[0][0]
        self.assertIsInstance(graph, nx.DiGraph)

        # This assertion is correct due to the logic in `plot.py`. The function
        # groups all connections between a single source node and a single target
        # node. If it finds more than one connection (e.g., from different
        # source ports to different target ports), it creates a single,
        # unlabeled edge in the graph to represent the multiple connections.
        edge_n1_n2_data = graph.get_edge_data("1", "2")
        self.assertNotIn("label", edge_n1_n2_data)

    def test_plot_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            plot("non_existent_file.json")

    def test_plot_invalid_json(self):
        with open(self.test_file, "w") as f:
            f.write("{'invalid': 'json'")
        with self.assertRaises(ValidationError):
            plot(self.test_file)

    def test_plot_missing_keys(self):
        invalid_data = {"version": "0.0.1", "edges": []}
        with open(self.test_file, "w") as f:
            json.dump(invalid_data, f)
        with self.assertRaises(ValidationError):
            plot(self.test_file)


if __name__ == "__main__":
    unittest.main()
