"""AiiDA graph-authoring adapter: PWD JSON to GraphIR and back.

The adapter speaks the ``@task`` and ``@graph`` language: PWD function nodes
become annotated wrapper tasks around the referenced Python functions, and one
generated ``@graph`` source wires them. Export walks a built ``GraphIR`` back
to PWD nodes and edges.

Scope: static DAGs plus nested graphs. Branch and loop placements raise
ValueError until PWD grows branch and loop node types.
"""

from __future__ import annotations

import importlib
import keyword
import re
import sys
import tempfile
import typing as t
from pathlib import Path

from aiida.engine.processes.graphs import GraphHandle
from aiida.engine.processes.graphs.ir import GraphIR

from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow
from python_workflow_definition.shared import (
    EDGES_LABEL,
    NODES_LABEL,
    SOURCE_LABEL,
    SOURCE_PORT_LABEL,
    TARGET_LABEL,
    TARGET_PORT_LABEL,
    VERSION_LABEL,
    VERSION_NUMBER,
)

__all__ = (
    "load_workflow_json",
    "write_workflow_json",
)

# PWD spells whole-value transfer as a null port; GraphIR names it ``result``.
_RESULT_PORT: t.Final = "result"

# Original module.name per generated task, for round trips.
_ORIGINS: dict[tuple[str, str], str] = {}

_GENERATED_PREFIX: t.Final = "pwd_generated_graph"


def _identifier(name: str, *, what: str) -> str:
    if not name.isidentifier():
        msg = f"{what} {name!r} is not a valid Python identifier."
        raise ValueError(msg)
    return name


def _order(
    wanted: list[int],
    edges: list[dict[str, t.Any]],
    node_ids: set[int],
) -> list[int]:
    """Order callable nodes so every upstream node comes first.

    :param wanted: ids of ``function`` and ``workflow`` nodes.
    :param edges: PWD edge dicts with integer endpoints.
    :param node_ids: ids of every node, for validation.
    :return: the callable ids in dependency order.
    :raises ValueError: on unknown endpoints or dependency cycles.
    """
    upstream: dict[int, set[int]] = {node_id: set() for node_id in wanted}
    for edge in edges:
        source: int = int(edge[SOURCE_LABEL])
        target: int = int(edge[TARGET_LABEL])
        if source not in node_ids or target not in node_ids:
            msg = f"Edge references unknown node: {edge}."
            raise ValueError(msg)
        if target in upstream and source in upstream:
            upstream[target].add(source)
    ordered: list[int] = []
    ready: list[int] = sorted(node_id for node_id in wanted if not upstream[node_id])
    while ready:
        node_id: int = ready.pop(0)
        ordered.append(node_id)
        for other in wanted:
            if node_id in upstream[other]:
                upstream[other].discard(node_id)
                if not upstream[other] and other not in ordered:
                    ready.append(other)
        ready.sort()
    if len(ordered) != len(wanted):
        msg = "Callable nodes contain a dependency cycle."
        raise ValueError(msg)
    return ordered


def _expression(
    source: int,
    port: str | None,
    variables: dict[int, str],
    inputs: dict[int, str],
) -> str:
    """Render the Python expression an edge source maps to.

    :param source: id of the edge source node.
    :param port: selected output port, or null for the whole value.
    :param variables: node id to assigned variable for callable nodes.
    :param inputs: node id to parameter name for input nodes.
    :return: an expression selecting the wired value.
    """
    if source in inputs:
        return inputs[source]
    variable: str = variables[source]
    if port is None or port == _RESULT_PORT:
        return variable
    return f"{variable}[{port!r}]"


def _port_map(
    nodes: dict[int, dict[str, t.Any]],
    edges: list[dict[str, t.Any]],
    node_id: int,
) -> dict[str, str]:
    """Map each wired target port to a valid Python parameter name."""
    mapping: dict[str, str] = {}
    ports: list[str] = sorted(
        {
            str(edge[TARGET_PORT_LABEL])
            for edge in edges
            if int(edge[TARGET_LABEL]) == node_id
            and edge[TARGET_PORT_LABEL] is not None
        }
    )
    for port in ports:
        if port.isidentifier() and not keyword.iskeyword(port):
            safe: str = port
        else:
            safe = "p_" + re.sub(r"\W", "_", port)
        while safe in mapping.values() or keyword.iskeyword(safe):
            safe = safe + "_"
        mapping[port] = safe
    return mapping


def _emit_wrappers(
    lines: list[str],
    nodes: dict[int, dict[str, t.Any]],
    edges: list[dict[str, t.Any]],
    *,
    prefix: str,
) -> None:
    """Emit imports plus ``@task`` wrappers for the function nodes."""
    for node_id in sorted(nodes):
        node: dict[str, t.Any] = nodes[node_id]
        if node["type"] != "function":
            continue
        value: str = node["value"]
        module_path, _, func_name = value.rpartition(".")
        if not module_path:
            msg = f"Function node {node_id} value is not a module path: {value!r}."
            raise ValueError(msg)
        used: list[str] = sorted(
            {
                str(edge[SOURCE_PORT_LABEL])
                for edge in edges
                if int(edge[SOURCE_LABEL]) == node_id
                and edge[SOURCE_PORT_LABEL] not in (None, _RESULT_PORT)
            }
        )
        lines.append(f"from {module_path} import {func_name} as _orig_{node_id}")
        ports: dict[str, str] = _port_map(nodes, edges, node_id)
        task_params: str = ", ".join(f"{safe}: Any" for _, safe in ports.items())
        if used:
            lines.append(f"class {prefix}_Out{node_id}(t.TypedDict):")
            for port in used:
                lines.append(f"    {port}: Any")
            lines.append("")
        lines.append("@task")
        if used:
            lines.append(
                f"def {prefix}_task_{node_id}(*, {task_params}) -> {prefix}_Out{node_id}:"
            )
        else:
            lines.append(f"def {prefix}_task_{node_id}(*, {task_params}) -> Any:")
        plain: list[str] = [
            safe + "=" + safe for orig, safe in ports.items() if safe == orig
        ]
        packed: str = ", ".join(
            repr(orig) + ": " + safe for orig, safe in ports.items() if safe != orig
        )
        call: str = ", ".join(plain)
        if packed:
            call = (call + ", " if call else "") + "**{" + packed + "}"
        lines.append("    return _orig_" + str(node_id) + "(" + call + ")")
        lines.append("")


def _emit_graph_function(  # noqa: PLR0913
    lines: list[str],
    nodes: dict[int, dict[str, t.Any]],
    edges: list[dict[str, t.Any]],
    *,
    name: str,
    params: list[str],
    inputs: dict[int, str],
    outputs: dict[str, tuple[int, str | None]],
    prefix: str,
) -> None:
    """Append one ``@graph`` function definition wiring the given nodes."""
    callable_ids: list[int] = [
        node_id
        for node_id, node in nodes.items()
        if node["type"] in ("function", "workflow")
    ]
    order: list[int] = _order(callable_ids, edges, set(nodes.keys()))
    variables: dict[int, str] = {}
    renames: dict[int, dict[str, str]] = {
        node_id: _port_map(nodes, edges, node_id) for node_id in callable_ids
    }
    lines.append("@graph")
    lines.append("def " + name + "(" + ", ".join(params) + "):")
    for node_id in order:
        node: dict[str, t.Any] = nodes[node_id]
        variables[node_id] = "v" + str(node_id)
        if node["type"] == "function":
            callee: str = prefix + "_task_" + str(node_id)
        else:
            callee = prefix + "_graph_" + str(node_id)
        arguments: list[str] = []
        for edge in edges:
            if int(edge[TARGET_LABEL]) != node_id:
                continue
            expression: str = _expression(
                int(edge[SOURCE_LABEL]),
                edge[SOURCE_PORT_LABEL],
                variables,
                inputs,
            )
            arguments.append(
                renames[node_id][str(edge[TARGET_PORT_LABEL])] + "=" + expression
            )
        lines.append(
            "    v" + str(node_id) + " = " + callee + "(" + ", ".join(arguments) + ")"
        )
    returned: list[str] = []
    for output_name, (source_id, source_port) in outputs.items():
        expression = _expression(source_id, source_port, variables, inputs)
        returned.append(repr(output_name) + ": " + expression)
    lines.append("    return {" + ", ".join(returned) + "}")
    lines.append("")


def _emit_level(
    lines: list[str],
    nodes: dict[int, dict[str, t.Any]],
    edges: list[dict[str, t.Any]],
    *,
    graph_name: str,
    prefix: str,
) -> None:
    """Emit wrapper tasks, nested graphs, and one ``@graph`` definition."""
    inputs: dict[int, str] = {}
    params: list[str] = []
    taken: set[str] = set()
    for node_id in sorted(nodes):
        node: dict[str, t.Any] = nodes[node_id]
        if node["type"] == "input":
            param: str = _identifier(node["name"], what="Input")
            # Distinct nodes may share a name with different defaults.
            # Keep the first name, suffix later ones deterministically.
            base: str = param
            counter: int = 2
            while param in taken:
                param = base + "_" + str(counter)
                counter += 1
            taken.add(param)
            inputs[node_id] = param
            params.append(param + "=" + repr(node["value"]))
    _emit_wrappers(lines, nodes, edges, prefix=prefix)
    for node_id in sorted(nodes):
        node = nodes[node_id]
        if node["type"] != "workflow":
            continue
        template: dict[str, t.Any] = node.get("graph", {})
        inner_nodes: dict[int, dict[str, t.Any]] = {
            int(item["id"]): item for item in template.get(NODES_LABEL, [])
        }
        inner_edges: list[dict[str, t.Any]] = [
            {
                TARGET_LABEL: int(item[TARGET_LABEL]),
                TARGET_PORT_LABEL: item[TARGET_PORT_LABEL],
                SOURCE_LABEL: int(item[SOURCE_LABEL]),
                SOURCE_PORT_LABEL: item[SOURCE_PORT_LABEL],
            }
            for item in template.get(EDGES_LABEL, [])
        ]
        _emit_level(
            lines,
            inner_nodes,
            inner_edges,
            graph_name=prefix + "_graph_" + str(node_id),
            prefix=prefix + "_g" + str(node_id),
        )
    outputs: dict[str, tuple[int, str | None]] = {}
    for node_id in sorted(nodes):
        node = nodes[node_id]
        if node["type"] != "output":
            continue
        output_name: str = _identifier(node["name"], what="Output")
        for edge in edges:
            if int(edge[TARGET_LABEL]) == node_id:
                outputs[output_name] = (
                    int(edge[SOURCE_LABEL]),
                    edge[SOURCE_PORT_LABEL],
                )
    _emit_graph_function(
        lines,
        nodes,
        edges,
        name=graph_name,
        params=params,
        inputs=inputs,
        outputs=outputs,
        prefix=prefix,
    )


def _pwd_to_graph_source(
    workflow: dict[str, t.Any],
    *,
    module_name: str = _GENERATED_PREFIX,
) -> str:
    """Render ``@task`` and ``@graph`` source for one PWD workflow dict.

    Function nodes become annotated wrapper tasks around the referenced
    functions: a synthesized ``TypedDict`` declares the output ports named by
    downstream edges, otherwise the wrapper returns ``Any``. Nested
    ``workflow`` nodes become nested ``@graph`` definitions.

    :param workflow: validated PWD mapping with ``nodes`` and ``edges``.
    :param module_name: name carried in the module docstring only.
    :return: importable Python source using the ``@task``/``@graph`` language.
    :raises ValueError: on unwritable PWD content.
    """
    nodes: dict[int, dict[str, t.Any]] = {
        int(node["id"]): node for node in workflow[NODES_LABEL]
    }
    edges: list[dict[str, t.Any]] = [
        {
            TARGET_LABEL: int(edge[TARGET_LABEL]),
            TARGET_PORT_LABEL: edge[TARGET_PORT_LABEL],
            SOURCE_LABEL: int(edge[SOURCE_LABEL]),
            SOURCE_PORT_LABEL: edge[SOURCE_PORT_LABEL],
        }
        for edge in workflow[EDGES_LABEL]
    ]
    for node in nodes.values():
        if node["type"] not in ("function", "input", "output", "workflow"):
            msg = (
                "Node "
                + str(node["id"])
                + " of type "
                + repr(node["type"])
                + " has no PWD representation in this adapter."
            )
            raise ValueError(msg)
    lines: list[str] = [
        '"""Generated from PWD (' + module_name + '); do not edit by hand."""',
        "from __future__ import annotations",
        "",
        "import typing as t",
        "from typing import Any",
        "",
        "from aiida.engine import graph, task",
        "",
    ]
    _emit_level(lines, nodes, edges, graph_name="graph_main", prefix="pwd")
    return "\n".join(lines) + "\n"


def load_workflow_json(
    file_name: str | Path,
    *,
    module_name: str = _GENERATED_PREFIX,
    source_file: str | Path | None = None,
) -> GraphHandle:
    """Build a ``GraphHandle`` from one PWD JSON file.

    The PWD workflow renders to ``@task`` and ``@graph`` source, which is
    imported so the graph language lowers it. The generated module name is
    recorded with the original ``module.name`` of every task for round trips
    through :func:`write_workflow_json`.

    :param file_name: path of the PWD JSON file.
    :param module_name: name of the generated module.
    :param source_file: optional path persisting the generated source;
        otherwise a temporary file is used.
    :return: the imported graph handle; call ``.build()`` for the template.
    :raises ValueError: on unwritable PWD content.
    """
    data: dict[str, t.Any] = PythonWorkflowDefinitionWorkflow.load_json_file(
        file_name=file_name
    )
    source: str = _pwd_to_graph_source(data, module_name=module_name)
    if source_file is None:
        directory: str = tempfile.mkdtemp(prefix="pwd_graph_")
        module_path: Path = Path(directory) / (module_name + ".py")
        module_path.write_text(source, encoding="utf-8")
    else:
        module_path = Path(source_file)
        module_path.write_text(source, encoding="utf-8")
        directory = str(module_path.parent)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    module = importlib.import_module(module_name)
    handle: GraphHandle = module.graph_main
    for node in data[NODES_LABEL]:
        if node["type"] == "function":
            _ORIGINS[(module_name, "pwd_task_" + str(node["id"]))] = node["value"]
    return handle


def _placement_value(module_name: str, task_name: str, spec: dict[str, t.Any]) -> str:
    """Resolve the PWD function value for one placement.

    :param module_name: module of the lowered graph template.
    :param task_name: placement name in the template.
    :param spec: task spec with ``identifier`` and ``executor`` entries.
    :return: the original ``module.name`` when recorded, else the spec one.
    """
    executor: dict[str, t.Any] = spec.get("executor", {})
    return _ORIGINS.get(
        (executor.get("module", module_name), task_name),
        str(executor.get("module")) + "." + str(executor.get("name")),
    )


def _emit_template(
    template: dict[str, t.Any],
    module_name: str,
    nodes: list[dict[str, t.Any]],
    edges: list[dict[str, t.Any]],
    counter: list[int],
) -> None:
    """Append PWD nodes and edges for one GraphIR template level.

    :param template: ``to_dict`` mapping of a graph template.
    :param module_name: module recorded for origin lookups.
    :param nodes: PWD nodes to extend.
    :param edges: PWD edges to extend.
    :param counter: single running node id counter.
    :raises ValueError: on branch or loop placements.
    """
    placement_ids: dict[str, int] = {}
    for placement in template.get("tasks", []):
        kind: str = placement.get("kind", "process")
        if kind not in ("process", "graph"):
            msg = (
                "Placement "
                + str(placement.get("name"))
                + " of kind "
                + repr(kind)
                + " has no PWD representation yet; PWD covers static DAGs plus nested graphs."
            )
            raise ValueError(msg)
        placement_ids[placement["name"]] = counter[0]
        counter[0] += 1
    name_to_id: dict[str, int] = dict(placement_ids)
    input_ids: dict[str, int] = {}
    fields: dict[str, dict[str, t.Any]] = template.get("input_namespace", {}).get(
        "fields", {}
    )
    for input_name in template.get("inputs", {}):
        input_ids[input_name] = counter[0]
        default: t.Any = fields.get(input_name, {}).get("default")
        nodes.append(
            {"id": counter[0], "type": "input", "value": default, "name": input_name}
        )
        counter[0] += 1
    for placement in template.get("tasks", []):
        node_id: int = name_to_id[placement["name"]]
        if placement["kind"] == "process":
            value: str = _placement_value(
                module_name, placement["name"], placement.get("spec", {})
            )
            nodes.append({"id": node_id, "type": "function", "value": value})
            for port_name, port_value in placement.get("inputs", {}).items():
                value_id: int = counter[0]
                nodes.append({"id": value_id, "type": "input", "value": port_value})
                edges.append(
                    {
                        TARGET_LABEL: node_id,
                        TARGET_PORT_LABEL: port_name,
                        SOURCE_LABEL: value_id,
                        SOURCE_PORT_LABEL: None,
                    }
                )
                counter[0] += 1
        else:
            body: dict[str, t.Any] = placement.get("body", {})
            inner_nodes: list[dict[str, t.Any]] = []
            inner_edges: list[dict[str, t.Any]] = []
            inner_counter: list[int] = [0]
            _emit_template(body, module_name, inner_nodes, inner_edges, inner_counter)
            graph_body: dict[str, t.Any] = {
                NODES_LABEL: inner_nodes,
                EDGES_LABEL: inner_edges,
                "inputs": list(body.get("inputs", {}).keys()),
                "outputs": list(body.get("outputs", {}).keys()),
            }
            nodes.append({"id": node_id, "type": "workflow", "graph": graph_body})
    for dependency in template.get("dependencies", []):
        source_port: str | None = dependency.get("source_port")
        edges.append(
            {
                TARGET_LABEL: name_to_id[dependency["target"]],
                TARGET_PORT_LABEL: dependency.get("target_port"),
                SOURCE_LABEL: name_to_id[dependency["source"]],
                SOURCE_PORT_LABEL: (
                    None if source_port == _RESULT_PORT else source_port
                ),
            }
        )
    for input_name, routes in template.get("inputs", {}).items():
        for route in routes:
            edges.append(
                {
                    TARGET_LABEL: name_to_id[route[0]],
                    TARGET_PORT_LABEL: route[1],
                    SOURCE_LABEL: input_ids[input_name],
                    SOURCE_PORT_LABEL: None,
                }
            )
    for output_name, endpoint in template.get("outputs", {}).items():
        output_id: int = counter[0]
        nodes.append({"id": output_id, "type": "output", "name": output_name})
        endpoint_port: str | None = endpoint.get("port")
        edges.append(
            {
                TARGET_LABEL: output_id,
                TARGET_PORT_LABEL: None,
                SOURCE_LABEL: name_to_id[endpoint["task"]],
                SOURCE_PORT_LABEL: (
                    None if endpoint_port == _RESULT_PORT else endpoint_port
                ),
            }
        )
        counter[0] += 1


def write_workflow_json(
    graph: GraphHandle | GraphIR,
    file_name: str | Path,
    inputs: dict[str, t.Any] | None = None,
) -> None:
    """Write one built graph to a PWD JSON file.

    Static DAGs plus nested graphs round-trip; branch and loop placements
    raise ValueError until PWD grows those node types. ``inputs`` sets values
    for template inputs that have no literal default, such as computed paths.

    :param graph: a ``GraphHandle`` (built on the spot) or a ``GraphIR``.
    :param file_name: path of the PWD JSON file to write.
    :param inputs: input name to value, applied over template defaults.
    :raises ValueError: on unknown input names.
    """
    template: GraphIR = graph.build() if isinstance(graph, GraphHandle) else graph
    payload: dict[str, t.Any] = template.to_dict()
    nodes: list[dict[str, t.Any]] = []
    edges: list[dict[str, t.Any]] = []
    _emit_template(payload, template.identifier or "", nodes, edges, [0])
    counts: dict[str, int] = {}
    for node in nodes:
        if node["type"] != "input" or "name" in node:
            continue
        ports: list[str] = sorted(
            {
                str(edge[TARGET_PORT_LABEL])
                for edge in edges
                if edge[SOURCE_LABEL] == node["id"]
                and edge[TARGET_PORT_LABEL] is not None
            }
        )
        port: str = ports[0] if ports else "value"
        counts[port] = counts.get(port, 0) + 1
        node["name"] = port + "_" + str(counts[port] - 1)
    for node in nodes:
        if node["type"] == "input" and inputs and node["name"] in inputs:
            node["value"] = inputs[node["name"]]
    if inputs:
        unknown: list[str] = sorted(
            name
            for name in inputs
            if name not in {node["name"] for node in nodes if node["type"] == "input"}
        )
        if unknown:
            msg = f"Unknown graph inputs: {', '.join(unknown)}."
            raise ValueError(msg)
    data: dict[str, t.Any] = {
        NODES_LABEL: nodes,
        EDGES_LABEL: edges,
        VERSION_LABEL: VERSION_NUMBER,
    }
    PythonWorkflowDefinitionWorkflow(**data).dump_json_file(
        file_name=file_name, indent=2
    )
