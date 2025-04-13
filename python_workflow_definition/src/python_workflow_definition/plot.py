import json

from IPython.display import SVG, display
import networkx as nx


from python_workflow_definition.purepython import group_edges
from python_workflow_definition.shared import (
    get_kwargs,
    convert_nodes_list_to_dict,
    NODES_LABEL,
    EDGES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
)


def plot(file_name):
    with open(file_name, "r") as f:
        content = json.load(f)

    graph = nx.DiGraph()
    node_dict = convert_nodes_list_to_dict(nodes_list=content[NODES_LABEL])
    total_lst = group_edges(edges_lst=content[EDGES_LABEL])

    for node_id, node_name in node_dict.items():
        graph.add_node(node_id, name=str(node_name), label=str(node_name))

    for edge_tuple in total_lst:
        target_node, edge_dict = edge_tuple
        edge_label_dict = {}
        for k, v in edge_dict.items():
            if v[SOURCE_LABEL] not in edge_label_dict:
                edge_label_dict[v[SOURCE_LABEL]] = []
            if v[SOURCE_PORT_LABEL] is None:
                edge_label_dict[v[SOURCE_LABEL]].append(k)
            else:
                edge_label_dict[v[SOURCE_LABEL]].append(
                    k + "=result[" + v[SOURCE_PORT_LABEL] + "]"
                )
        for k, v in edge_label_dict.items():
            graph.add_edge(str(k), str(target_node), label=", ".join(v))

    svg = nx.nx_agraph.to_agraph(graph).draw(prog="dot", format="svg")
    display(SVG(svg))
