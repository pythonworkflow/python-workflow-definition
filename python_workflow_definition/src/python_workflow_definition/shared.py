def get_dict(**kwargs):
    return {k: v for k, v in kwargs.items()}


def get_list(**kwargs):
    return list(kwargs.values())


def get_kwargs(lst):
    return {t['targetHandle']: {'source': t['source'], 'sourceHandle': t['sourceHandle']} for t in lst}


def get_item(data: dict, key: str):
    """Handle get item from the outputs"""
    return data[key]


def get_source_handles(edges_lst):
    source_handle_dict = {}
    for ed in edges_lst:
        if ed['source'] not in source_handle_dict.keys():
            source_handle_dict[ed['source']] = [ed['sourceHandle']]
        else:
            source_handle_dict[ed['source']].append(ed['sourceHandle'])
    return {
        k: list(range(len(v))) if len(v) > 1 and all([el is None for el in v]) else v
        for k, v in source_handle_dict.items()
    }