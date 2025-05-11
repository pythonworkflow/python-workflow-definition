from collections import Counter

NODES_LABEL = "nodes"
EDGES_LABEL = "edges"
SOURCE_LABEL = "source"
SOURCE_PORT_LABEL = "sourcePort"
TARGET_LABEL = "target"
TARGET_PORT_LABEL = "targetPort"


def get_dict(**kwargs) -> dict:
    # NOTE: In WG, this will automatically be wrapped in a dict with the `result` key
    return {k: v for k, v in kwargs.items()}
    # return {'dict': {k: v for k, v in kwargs.items()}}


def get_list(**kwargs) -> list:
    return list(kwargs.values())


def get_kwargs(lst: list) -> dict:
    return {
        t[TARGET_PORT_LABEL]: {
            SOURCE_LABEL: t[SOURCE_LABEL],
            SOURCE_PORT_LABEL: t[SOURCE_PORT_LABEL],
        }
        for t in lst
    }


def get_source_handles(edges_lst: list) -> dict:
    source_handle_dict = {}
    for ed in edges_lst:
        if ed[SOURCE_LABEL] not in source_handle_dict.keys():
            source_handle_dict[ed[SOURCE_LABEL]] = []
        source_handle_dict[ed[SOURCE_LABEL]].append(ed[SOURCE_PORT_LABEL])
    return {
        k: list(range(len(v))) if len(v) > 1 and all([el is None for el in v]) else v
        for k, v in source_handle_dict.items()
    }


def convert_nodes_list_to_dict(nodes_list: list) -> dict:
    return {
        str(el["id"]): el["value"] for el in sorted(nodes_list, key=lambda d: d["id"])
    }


def update_node_names(content: dict) -> dict:
    node_names_final_dict = {}
    input_nodes = [n for n in content[NODES_LABEL] if n["type"] == "input"]
    node_names_dict = {
        n["id"]: list(set([e[TARGET_PORT_LABEL] for e in content[EDGES_LABEL] if e[SOURCE_LABEL] == n["id"]]))[0]
        for n in input_nodes
    }

    counter_dict = Counter(node_names_dict.values())
    node_names_useage_dict = {k: -1 for k in counter_dict.keys()}
    for k, v in node_names_dict.items():
        node_names_useage_dict[v] += 1
        if counter_dict[v] > 1:
            node_names_final_dict[k] = v + "_" + str(node_names_useage_dict[v])
        else:
            node_names_final_dict[k] = v

    for n in content[NODES_LABEL]:
        if n["type"] == "input":
            n["name"] = node_names_final_dict[n["id"]]
    return content