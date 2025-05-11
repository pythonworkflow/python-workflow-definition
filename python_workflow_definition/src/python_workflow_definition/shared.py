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
        str(el["id"]): el["value"] if "value" in el else el["name"]
        for el in sorted(nodes_list, key=lambda d: d["id"])
    }


def update_node_names(workflow_dict: dict) -> dict:
    node_names_final_dict = {}
    input_nodes = [n for n in workflow_dict[NODES_LABEL] if n["type"] == "input"]
    node_names_dict = {
        n["id"]: list(
            set(
                [
                    e[TARGET_PORT_LABEL]
                    for e in workflow_dict[EDGES_LABEL]
                    if e[SOURCE_LABEL] == n["id"]
                ]
            )
        )[0]
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

    for n in workflow_dict[NODES_LABEL]:
        if n["type"] == "input":
            n["name"] = node_names_final_dict[n["id"]]
    return workflow_dict


def set_result_node(workflow_dict):
    node_id_lst = [n["id"] for n in workflow_dict[NODES_LABEL]]
    source_lst = list(set([e[SOURCE_LABEL] for e in workflow_dict[EDGES_LABEL]]))

    end_node_lst = []
    for ni in node_id_lst:
        if ni not in source_lst:
            end_node_lst.append(ni)

    node_id = len(workflow_dict[NODES_LABEL])
    workflow_dict[NODES_LABEL].append(
        {"id": node_id, "type": "output", "name": "result"}
    )
    workflow_dict[EDGES_LABEL].append(
        {
            TARGET_LABEL: node_id,
            TARGET_PORT_LABEL: None,
            SOURCE_LABEL: end_node_lst[0],
            SOURCE_PORT_LABEL: None,
        }
    )

    return workflow_dict


def remove_result(workflow_dict):
    node_output_id = [
        n["id"] for n in workflow_dict[NODES_LABEL] if n["type"] == "output"
    ][0]
    return {
        NODES_LABEL: [n for n in workflow_dict[NODES_LABEL] if n["type"] != "output"],
        EDGES_LABEL: [
            e for e in workflow_dict[EDGES_LABEL] if e[TARGET_LABEL] != node_output_id
        ],
    }
