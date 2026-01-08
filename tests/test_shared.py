import unittest
from python_workflow_definition.shared import (
    get_dict,
    get_list,
    get_kwargs,
    get_source_handles,
    convert_nodes_list_to_dict,
    update_node_names,
    set_result_node,
    remove_result,
    EDGES_LABEL,
    NODES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
)


class TestShared(unittest.TestCase):
    def test_get_dict(self):
        self.assertEqual({"a": 1, "b": 2, "c": 3}, get_dict(a=1, b=2, c=3))

    def test_get_list(self):
        self.assertEqual([1, 2, 3], get_list(a=1, b=2, c=3))

    def test_get_kwargs(self):
        lst = [
            {
                TARGET_PORT_LABEL: "a",
                SOURCE_LABEL: "s1",
                SOURCE_PORT_LABEL: "sp1",
            },
            {
                TARGET_PORT_LABEL: "b",
                SOURCE_LABEL: "s2",
                SOURCE_PORT_LABEL: "sp2",
            },
        ]
        self.assertEqual(
            {
                "a": {SOURCE_LABEL: "s1", SOURCE_PORT_LABEL: "sp1"},
                "b": {SOURCE_LABEL: "s2", SOURCE_PORT_LABEL: "sp2"},
            },
            get_kwargs(lst),
        )

    def test_get_kwargs_empty(self):
        self.assertEqual({}, get_kwargs([]))

    def test_get_source_handles(self):
        edges_lst = [
            {SOURCE_LABEL: "s1", SOURCE_PORT_LABEL: "sp1"},
            {SOURCE_LABEL: "s1", SOURCE_PORT_LABEL: "sp2"},
            {SOURCE_LABEL: "s2", SOURCE_PORT_LABEL: "sp3"},
        ]
        self.assertEqual(
            {"s1": ["sp1", "sp2"], "s2": ["sp3"]}, get_source_handles(edges_lst)
        )

    def test_get_source_handles_no_port(self):
        edges_lst = [
            {SOURCE_LABEL: "s1", SOURCE_PORT_LABEL: None},
            {SOURCE_LABEL: "s1", SOURCE_PORT_LABEL: None},
        ]
        self.assertEqual({"s1": [0, 1]}, get_source_handles(edges_lst))

    def test_get_source_handles_empty(self):
        self.assertEqual({}, get_source_handles([]))

    def test_convert_nodes_list_to_dict(self):
        nodes_list = [
            {"id": 1, "name": "n1"},
            {"id": 2, "value": "v2"},
            {"id": 0, "name": "n0"},
        ]
        self.assertEqual(
            {"0": "n0", "1": "n1", "2": "v2"},
            convert_nodes_list_to_dict(nodes_list),
        )

    def test_convert_nodes_list_to_dict_empty(self):
        self.assertEqual({}, convert_nodes_list_to_dict([]))

    def test_update_node_names(self):
        workflow_dict = {
            NODES_LABEL: [
                {"id": 0, "type": "input", "name": ""},
                {"id": 1, "type": "input", "name": ""},
                {"id": 2, "type": "input", "name": ""},
                {"id": 3, "type": "other", "name": ""},
            ],
            EDGES_LABEL: [
                {SOURCE_LABEL: 0, TARGET_PORT_LABEL: "a"},
                {SOURCE_LABEL: 1, TARGET_PORT_LABEL: "b"},
                {SOURCE_LABEL: 2, TARGET_PORT_LABEL: "a"},
            ],
        }
        update_node_names(workflow_dict)
        self.assertEqual("a_0", workflow_dict[NODES_LABEL][0]["name"])
        self.assertEqual("b", workflow_dict[NODES_LABEL][1]["name"])
        self.assertEqual("a_1", workflow_dict[NODES_LABEL][2]["name"])

    def test_set_result_node(self):
        workflow_dict = {
            NODES_LABEL: [{"id": 0, "type": "input"}],
            EDGES_LABEL: [],
        }
        set_result_node(workflow_dict)
        self.assertEqual(2, len(workflow_dict[NODES_LABEL]))
        self.assertEqual("output", workflow_dict[NODES_LABEL][1]["type"])
        self.assertEqual(1, len(workflow_dict[EDGES_LABEL]))

    def test_set_result_node_already_exists(self):
        workflow_dict = {
            NODES_LABEL: [
                {"id": 0, "type": "input"},
                {"id": 1, "type": "output"},
            ],
            EDGES_LABEL: [{SOURCE_LABEL: 0, TARGET_LABEL: 1}],
        }
        set_result_node(workflow_dict)
        self.assertEqual(3, len(workflow_dict[NODES_LABEL]))
        self.assertEqual("output", workflow_dict[NODES_LABEL][2]["type"])
        self.assertEqual(2, len(workflow_dict[EDGES_LABEL]))

    def test_set_result_node_no_end_node(self):
        workflow_dict = {
            NODES_LABEL: [{"id": 0}, {"id": 1}],
            EDGES_LABEL: [
                {SOURCE_LABEL: 0, TARGET_LABEL: 1},
                {SOURCE_LABEL: 1, TARGET_LABEL: 0},
            ],
        }
        with self.assertRaises(IndexError):
            set_result_node(workflow_dict)

    def test_remove_result(self):
        workflow_dict = {
            NODES_LABEL: [
                {"id": 0, "type": "input"},
                {"id": 1, "type": "output"},
            ],
            EDGES_LABEL: [{SOURCE_LABEL: 0, TARGET_LABEL: 1}],
        }
        new_workflow = remove_result(workflow_dict)
        self.assertEqual(1, len(new_workflow[NODES_LABEL]))
        self.assertEqual(0, len(new_workflow[EDGES_LABEL]))

    def test_remove_result_no_output(self):
        workflow_dict = {
            NODES_LABEL: [{"id": 0, "type": "input"}],
            EDGES_LABEL: [],
        }
        with self.assertRaises(IndexError):
            remove_result(workflow_dict)
