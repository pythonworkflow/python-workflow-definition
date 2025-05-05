from importlib import import_module
from typing import Dict, Any, Union, List, Tuple, Optional
import logging


from aiida import orm
from aiida_workgraph import WorkGraph
from aiida_workgraph.task import Task
from aiida_workgraph.socket import TaskSocketNamespace
from aiida_pythonjob.data.serializer import general_serializer
from python_workflow_definition.models import (
    PwdWorkflow,
    PwdNode,
    PwdEdge,
    PwdFunctionNode,
    PwdInputNode,
    PwdOutputNode,
    INTERNAL_DEFAULT_HANDLE,
)


# --- Constants ---
AIIDA_WG_DEFAULT_HANDLE = "result"
ANY_SOCKET_TYPE = "workgraph.any"


class AiidaPwdConverter:
    """
    Provides methods to convert between AiiDA WorkGraph instances
    and PWD workflows as Pydantic models.
    """

    def __init__(self):
        """Initializes the converter and sets up logger."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._reset_state()

    def model_to_workgraph(self, workflow_model: PwdWorkflow) -> WorkGraph:
        """
        Converts a PWD Workflow Pydantic model into an AiiDA WorkGraph.
        """
        self.logger.info("Starting model to WorkGraph conversion...")
        self._reset_state()
        self.workflow_model = workflow_model
        # Create WG instance, potentially using name from model (if we add that?)
        self.wg = WorkGraph(f"wg_{getattr(workflow_model, 'name', 'from_model')}")

        # Call internal helper methods
        self._m2w_create_nodes()
        self._m2w_link_nodes()
        self._m2w_create_group_io()

        self.logger.info("Finished model to WorkGraph conversion.")
        return self.wg

    def workgraph_to_model(self, wg: WorkGraph) -> PwdWorkflow:
        """
        Converts an AiiDA WorkGraph into a PWD Workflow Pydantic model.
        """
        self.logger.info(
            f"Starting WorkGraph to model conversion for WG '{wg.name}'..."
        )
        self._reset_state()
        self.wg = wg
        self.wg_protected_outputs = ("_wait", "_outputs", "exit_code")
        self.wg_protected_inputs = (
            "_wait",
            "metadata",
            "function_data",
            "process_label",
            "function_inputs",
            "deserializers",
            "serializers",
            "handler_overrides",
            "metadata_overrides",
            "name",
            "ctx",
        )

        # Call internal helper methods
        self._w2m_create_function_nodes()
        self._w2m_create_input_nodes()
        self._w2m_create_link_edges()
        self._w2m_create_output_nodes()
        self._w2m_adjust_node_names()

        # Assemble final Workflow model from instance attributes
        # TODO: Ensure Workflow model accepts 'name' field if needed
        workflow_model = PwdWorkflow(
            nodes=self._pydantic_nodes, edges=self._pydantic_edges
        )

        self.logger.info(
            f"Finished WorkGraph to model conversion. Model has {len(self._pydantic_nodes)} nodes, {len(self._pydantic_edges)} edges."
        )
        return workflow_model

    @staticmethod
    def _extract_aiida_value(data_node: orm.Data) -> Any:
        logger_ext = logging.getLogger(f"{__name__}._extract_aiida_value")
        node_info = (
            f"PK {getattr(data_node, 'pk', 'Unstored')} (Type: {type(data_node)})"
        )
        logger_ext.debug(f"Extracting Python value from {node_info}")
        if isinstance(data_node, (orm.Str, orm.Int, orm.Float, orm.Bool)):
            return data_node.value
        elif isinstance(data_node, orm.List):
            return data_node.get_list()
        elif isinstance(data_node, orm.Dict):
            return data_node.get_dict()
        elif isinstance(data_node, orm.ArrayData):
            try:
                array_names = data_node.get_arraynames()
                if array_names:
                    return data_node.get_array(array_names[0]).tolist()
                else:
                    logger_ext.warning(f"No arrays in {node_info}")
                    return []
            except Exception as e:
                logger_ext.warning(f"Array extraction failed for {node_info}: {e}")
                return []
        elif isinstance(data_node, orm.SinglefileData):
            return data_node.filename
        else:
            if hasattr(data_node, "value"):
                logger_ext.warning(
                    f"Attempting basic '.value' access for unhandled {node_info}."
                )
                try:
                    return data_node.value
                except Exception:
                    pass
            logger_ext.warning(
                f"Unhandled AiiDA type: {node_info}. Returning placeholder."
            )
            return f"<AiiDA Node: {type(data_node).__name__} PK: {getattr(data_node, 'pk', 'Unstored')}>"

    def _reset_state(self) -> None:
        """Resets internal state variables before starting a new conversion."""
        self.logger.debug("Resetting internal converter state.")
        # Inputs for conversion
        self.workflow_model: Optional[PwdWorkflow] = None
        self.wg: Optional[WorkGraph] = None
        # Intermediate state for model -> workgraph
        self._node_map: Dict[int, Union[Task, orm.Data, PwdNode]] = {}
        # Intermediate state for workgraph -> model
        self._pydantic_nodes: List[PwdNode] = []
        self._pydantic_edges: List[PwdEdge] = []
        self._aiida_task_name_to_pydantic_id: Dict[str, int] = {}
        self._aiida_data_map_key_to_pydantic_id: Dict[int, int] = {}
        self._static_input_to_node_id: Dict[Tuple[str, str], int] = {}
        self._workflow_output_to_node_id: Dict[Tuple[str, str], int] = {}
        self._current_id: int = 0

    def _m2w_create_nodes(self):
        self.logger.info(
            f"Starting model to WorkGraph conversion for model '{getattr(self.workflow_model, 'name', 'Unnamed')}'..."
        )

        self.logger.debug(
            f"Processing {len(self.workflow_model.nodes)} nodes from model."
        )
        for node in self.workflow_model.nodes:
            if not isinstance(node, PwdFunctionNode):
                node_info = f"node {node.id} (name: {getattr(node, 'name')}, type: {node.type})"
            else:
                node_info = f"node {node.id} (name: {getattr(node, 'value')}, type: {node.type})"
            self.logger.debug(f"Processing {node_info}.")

            if isinstance(node, PwdFunctionNode):
                try:
                    p, m = node.value.rsplit(".", 1)
                    mod = import_module(p)
                    func = getattr(mod, m)
                    task_name = f"{m}_{node.id}"
                    self.logger.debug(
                        f"Adding task '{task_name}' for function '{node.value}' from {node_info}."
                    )
                    aiida_task = self.wg.add_task(func, name=task_name)
                    if "result" in aiida_task.outputs:
                        self.logger.debug(
                            f"Removing default 'result' output from task '{task_name}'."
                        )
                        del aiida_task.outputs["result"]
                    self._node_map[node.id] = aiida_task
                except (ImportError, AttributeError, ValueError) as e:
                    self.logger.error(
                        f"Failed processing FunctionNode {node.id} ('{node.value}'): {e}",
                        exc_info=True,
                    )
                    raise AttributeError(
                        f"Failed processing FunctionNode {node.id}: {e}"
                    ) from e
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error creating task for {node_info}: {e}",
                        exc_info=True,
                    )
                    raise RuntimeError(
                        f"Error creating task for node {node.id}: {e}"
                    ) from e
            elif isinstance(node, PwdInputNode):
                try:
                    self.logger.debug(f"Serializing value for {node_info}.")
                    data_node = general_serializer(node.value)
                    if not isinstance(data_node, orm.Data):
                        self.logger.debug(
                            f"Value for {node_info} not an AiiDA node, wrapping with to_aiida_type."
                        )
                        data_node = orm.to_aiida_type(node.value)  # Pass original value
                    self.logger.info(
                        f"Created AiiDA Data node (PK: {getattr(data_node, 'pk', 'Unstored')}) for {node_info}."
                    )
                    self._node_map[node.id] = data_node
                except Exception as e:
                    self.logger.warning(
                        f"Could not serialize value for {node_info} (value: {node.value}). Error: {e}",
                        exc_info=True,
                    )
                    self._node_map[node.id] = None
            elif isinstance(node, PwdOutputNode):
                self.logger.debug(f"OutputNode {node_info} defines an endpoint.")
                self._node_map[node.id] = node
            else:
                self.logger.warning(
                    f"Unsupported node type: {type(node)} for node ID {node.id}. Skipping."
                )

    def _m2w_link_nodes(self):
        self.logger.debug(
            f"Processing {len(self.workflow_model.edges)} edges from model."
        )
        for edge_idx, edge in enumerate(self.workflow_model.edges):
            edge_info = f"edge {edge_idx} (source: {edge.source}:{edge.sourcePort or 'default'} -> target: {edge.target}:{edge.targetPort or 'default'})"
            self.logger.debug(f"Processing {edge_info}.")
            source_obj = self._node_map.get(edge.source)
            target_obj = self._node_map.get(edge.target)
            if source_obj is None:
                self.logger.warning(
                    f"Source obj missing for ID {edge.source}. Skipping {edge_info}."
                )
                continue
            if target_obj is None:
                self.logger.warning(
                    f"Target obj missing for ID {edge.target}. Skipping {edge_info}."
                )
                continue

            # Case 1: Connection *to* an OutputNode model
            if isinstance(target_obj, PwdOutputNode):
                if not isinstance(source_obj, Task):
                    self.logger.error(
                        f"Cannot connect non-Task source ID {edge.source} to OutputNode {target_obj.id}. Skipping."
                    )
                    continue
                # This is None or a specific string
                model_source_handle = edge.sourcePort

                aiida_source_socket_name = (
                    AIIDA_WG_DEFAULT_HANDLE
                    if model_source_handle == INTERNAL_DEFAULT_HANDLE
                    else model_source_handle
                )
                if aiida_source_socket_name not in source_obj.outputs:
                    self.logger.info(
                        f"Adding inferred output socket '{aiida_source_socket_name}' to task '{source_obj.name}'."
                    )
                    source_obj.add_output(
                        ANY_SOCKET_TYPE, name=aiida_source_socket_name
                    )
                continue

            # Case 2: Connection *to* a Task
            if isinstance(target_obj, Task):
                to_task_obj = target_obj
                # ... (check targetPort, ensure target input socket exists) ...
                target_port_name = edge.targetPort
                if not target_port_name:
                    self.logger.error(...)
                    raise ValueError(...)
                if target_port_name not in to_task_obj.inputs:
                    self.logger.info(
                        f"Adding inferred input socket '{target_port_name}' to task '{to_task_obj.name}'."
                    )
                    to_socket = to_task_obj.add_input(
                        ANY_SOCKET_TYPE, name=target_port_name
                    )
                else:
                    to_socket = to_task_obj.inputs[target_port_name]

                # Handle the source of the connection
                if isinstance(source_obj, orm.Data):
                    # ... (handle static input linking - no handle mapping needed here) ...
                    if edge.sourcePort != INTERNAL_DEFAULT_HANDLE:
                        self.logger.warning(
                            f"Ignoring non-default sourcePort '{edge.sourcePort}' for Data node source {edge.source}."
                        )
                elif isinstance(source_obj, Task):
                    from_task_obj = source_obj
                    # --- MAP MODEL HANDLE TO AIIDA HANDLE ---
                    model_source_handle = (
                        edge.sourcePort
                    )  # This is None or a specific string
                    aiida_source_socket_name = (
                        AIIDA_WG_DEFAULT_HANDLE
                        if model_source_handle == INTERNAL_DEFAULT_HANDLE
                        else model_source_handle
                    )

                    # Ensure output socket exists on source task using the AiiDA name
                    if aiida_source_socket_name not in from_task_obj.outputs:
                        self.logger.info(
                            f"Adding inferred output socket '{aiida_source_socket_name}' to task '{from_task_obj.name}'."
                        )
                        from_socket = from_task_obj.add_output(
                            ANY_SOCKET_TYPE, name=aiida_source_socket_name
                        )
                    else:
                        from_socket = from_task_obj.outputs[aiida_source_socket_name]

                    self.logger.info(
                        f"Linking task output '{from_task_obj.name}.{from_socket._name}' to task input '{to_task_obj.name}.{to_socket._name}'."
                    )  # Log uses AiiDA names
                    self.wg.add_link(from_socket, to_socket)

                else:
                    self.logger.error(
                        f"Unexpected source type {type(source_obj)} for edge {edge_info}. Skipping."
                    )
            else:
                self.logger.error(
                    f"Unexpected target type {type(target_obj)} for edge {edge_info}. Skipping."
                )

    def _m2w_create_group_io(self):
        self.logger.debug(
            "Creating group_inputs and group_outputs from model definition."
        )
        group_inputs = []
        group_outputs = []
        pydantic_nodes_by_id = {node.id: node for node in self.workflow_model.nodes}
        for edge in self.workflow_model.edges:
            source_node_model = pydantic_nodes_by_id.get(edge.source)
            target_node_model = pydantic_nodes_by_id.get(edge.target)
            if isinstance(source_node_model, PwdInputNode):
                target_task_obj = self._node_map.get(edge.target)
                if isinstance(target_task_obj, Task) and edge.targetPort:
                    input_entry = {
                        "name": source_node_model.name,
                        "to": f"{target_task_obj.name}.{edge.targetPort}",
                    }
                    if not any(
                        gi["name"] == input_entry["name"] for gi in group_inputs
                    ):
                        group_inputs.append(input_entry)
                        self.logger.debug(f"Added group input: {input_entry}")
                    else:
                        self.logger.warning(
                            f"Duplicate group input name '{input_entry['name']}'. Skipping."
                        )

            elif isinstance(target_node_model, PwdOutputNode):
                source_task_obj = self._node_map.get(edge.source)
                if isinstance(source_task_obj, Task):
                    model_source_handle = edge.sourcePort
                    aiida_source_socket_name = (
                        AIIDA_WG_DEFAULT_HANDLE
                        if model_source_handle == INTERNAL_DEFAULT_HANDLE
                        else model_source_handle
                    )
                    output_entry = {
                        "name": target_node_model.name,
                        "from": f"{source_task_obj.name}.{aiida_source_socket_name}",
                    }
                    if not any(
                        go["name"] == output_entry["name"] for go in group_outputs
                    ):
                        group_outputs.append(output_entry)
                        self.logger.debug(f"Added group output: {output_entry}")
                    else:
                        self.logger.warning(
                            f"Duplicate group output name '{output_entry['name']}'. Skipping."
                        )

        self.wg.group_inputs = group_inputs
        self.wg.group_outputs = group_outputs
        self.logger.info(
            f"Assigned {len(self.wg.group_inputs)} group inputs and {len(self.wg.group_outputs)} group outputs."
        )
        self.logger.info("Finished model to WorkGraph conversion.")
        import ipdb; ipdb.set_trace()
        pass

    def _w2m_create_function_nodes(self):
        self.logger.debug(f"Processing {len(self.wg.tasks)} tasks.")
        for task in self.wg.tasks:
            if not isinstance(task, Task):
                self.logger.warning(f"Skipping non-Task item: {task}.")
                continue
            try:
                executor_info = task.get_executor()
                idf = f"{executor_info.get('module_path', '?')}.{executor_info.get('callable_name', '?')}"
                node = PwdFunctionNode(id=self._current_id, type="function", value=idf)
                self._pydantic_nodes.append(node)
                self._aiida_task_name_to_pydantic_id[task.name] = self._current_id
                self.logger.info(
                    f"Created FunctionNode ID {self._current_id} for task '{task.name}' ({idf})."
                )
                self._current_id += 1
            except Exception as e:
                self.logger.error(
                    f"Error processing task '{task.name}': {e}", exc_info=True
                )

    def _w2m_create_input_nodes(self):
        self.logger.debug("Processing static inputs.")
        for task in self.wg.tasks:
            task_name = task.name
            target_task_id = self._aiida_task_name_to_pydantic_id.get(task_name)
            if target_task_id is None:
                continue
            for input_socket in task.inputs:
                if isinstance(input_socket, TaskSocketNamespace):
                    continue
                input_name = input_socket._name
                socket_info = f"'{task_name}.{input_name}'"
                if input_name in self.wg_protected_inputs:
                    continue
                input_value = input_socket.value
                if isinstance(input_value, orm.Data):
                    data_node = input_value
                    assignment_key = (task_name, input_name)
                    try:
                        data_pk = data_node.pk
                        map_key = data_pk if data_pk is not None else id(data_node)
                        if map_key in self._aiida_data_map_key_to_pydantic_id:
                            input_node_id = self._aiida_data_map_key_to_pydantic_id[
                                map_key
                            ]
                            self._static_input_to_node_id[assignment_key] = (
                                input_node_id  # Still map this connection
                            )
                            self.logger.debug(
                                f"Reusing InputNode ID {input_node_id} for {socket_info}."
                            )
                        else:
                            raw_value = AiidaPwdConverter._extract_aiida_value(
                                data_node
                            )
                            input_node = PwdInputNode(
                                id=self._current_id,
                                type="input",
                                name=input_name,
                                value=raw_value,
                            )
                            self._pydantic_nodes.append(input_node)
                            input_node_id = self._current_id
                            self._aiida_data_map_key_to_pydantic_id[map_key] = (
                                input_node_id
                            )
                            self._static_input_to_node_id[assignment_key] = (
                                input_node_id
                            )
                            self.logger.info(
                                f"Created InputNode ID {input_node_id} (default name: {input_name}) for {socket_info}."
                            )
                            self._current_id += 1
                        edge = PwdEdge(
                            source=input_node_id,
                            sourcePort=None,
                            target=target_task_id,
                            targetPort=input_name,
                        )
                        self._pydantic_edges.append(edge)
                        self.logger.debug(
                            f"Created edge from InputNode {input_node_id} to {socket_info}."
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error processing static {socket_info}: {e}", exc_info=True
                        )

    def _w2m_create_link_edges(self):
        self.logger.debug(f"Processing {len(self.wg.links)} links.")
        for link in self.wg.links:
            if not isinstance(link.from_node, Task) or not isinstance(
                link.to_node, Task
            ):
                continue
            try:
                from_task_name = link.from_node.name
                to_task_name = link.to_node.name
                source_id = self._aiida_task_name_to_pydantic_id.get(from_task_name)
                target_id = self._aiida_task_name_to_pydantic_id.get(to_task_name)
                if source_id is None or target_id is None:
                    continue

                aiida_from_socket_name = link.from_socket._name
                aiida_to_socket_name = link.to_socket._name

                # --- MAP AIIDA HANDLE TO MODEL HANDLE ---
                model_source_handle = (
                    None
                    if aiida_from_socket_name == AIIDA_WG_DEFAULT_HANDLE
                    else aiida_from_socket_name
                )

                model_target_handle = aiida_to_socket_name

                self.logger.debug(
                    f"Mapping link to Pydantic Edge: source={source_id}, sourcePort='{model_source_handle}', target={target_id}, targetPort='{model_target_handle}'."
                )

                edge = PwdEdge(
                    source=source_id,
                    sourcePort=model_source_handle,
                    target=target_id,
                    targetPort=model_target_handle,
                )
                self._pydantic_edges.append(edge)
            except Exception as e:
                self.logger.error(f"Error processing link {link}: {e}", exc_info=True)

    def _w2m_create_output_nodes(self):
        self.logger.debug("Identifying workflow outputs.")
        all_link_sources = set(
            (link.from_node.name, link.from_socket._name)
            for link in self.wg.links
            if isinstance(link.from_node, Task)
        )
        for task in self.wg.tasks:
            task_name = task.name
            source_task_id = self._aiida_task_name_to_pydantic_id.get(task_name)
            if source_task_id is None:
                continue
            for output_socket in task.outputs:
                if isinstance(output_socket, TaskSocketNamespace):
                    continue
                output_name = output_socket._name
                if output_name in self.wg_protected_outputs:
                    continue
                output_key = (task_name, output_name)
                if output_key not in all_link_sources:
                    try:
                        value = None
                        if output_socket.value is not None:
                            aiida_value_node = output_socket.value
                            if isinstance(aiida_value_node, orm.Data):
                                # Use the existing helper to get a JSON-friendly value
                                value = self._extract_aiida_value(aiida_value_node)
                            else:
                                self.warning(
                                    f"  Value for output '{task_name}' is not an AiiDA Data node (type: {type(aiida_value_node)}). Skipping value embedding."
                                )

                        output_node = PwdOutputNode(
                            id=self._current_id,
                            type="output",
                            name=output_name,
                            value=value,
                        )
                        self._pydantic_nodes.append(output_node)
                        output_node_id = self._current_id
                        self._workflow_output_to_node_id[output_key] = output_node_id
                        self.logger.info(
                            f"Created OutputNode ID {output_node_id} (default name: {output_name}) for output '{task_name}.{output_name}'."
                        )
                        self._current_id += 1
                        ps_port = None if output_name == "result" else output_name
                        edge = PwdEdge(
                            source=source_task_id,
                            sourcePort=ps_port,
                            target=output_node_id,
                            targetPort=None,
                        )
                        self._pydantic_edges.append(edge)
                        self.logger.debug(
                            f"Created edge from '{task_name}.{output_name}' to OutputNode {output_node_id}."
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error creating OutputNode/Edge for '{task_name}.{output_name}': {e}",
                            exc_info=True,
                        )

    def _w2m_adjust_node_names(self):
        self.logger.debug("Attempting to override I/O node names from group lists.")
        pydantic_nodes_dict = {node.id: node for node in self._pydantic_nodes}
        # Process group_inputs
        if hasattr(self.wg, "group_inputs") and isinstance(self.wg.group_inputs, list):
            for entry in self.wg.group_inputs:
                if isinstance(entry, dict) and "name" in entry and "to" in entry:
                    try:
                        tn, sn = entry["to"].split(".", 1)
                        key = (tn, sn)
                        if key in self._static_input_to_node_id:
                            node_id = self._static_input_to_node_id[key]
                            if node_id in pydantic_nodes_dict and isinstance(
                                pydantic_nodes_dict[node_id], PwdInputNode
                            ):
                                pydantic_nodes_dict[node_id].name = entry["name"]
                                self.logger.info(
                                    f"Overrode InputNode ID {node_id} name to '{entry['name']}' from group_inputs."
                                )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed processing group_input entry {entry}: {e}"
                        )

        # Process group_outputs
        if hasattr(self.wg, "group_outputs") and isinstance(
            self.wg.group_outputs, list
        ):
            for entry in self.wg.group_outputs:
                if isinstance(entry, dict) and "name" in entry and "from" in entry:
                    try:
                        tn, sn = entry["from"].split(".", 1)
                        key = (tn, sn)
                        if key in self._workflow_output_to_node_id:
                            node_id = self._workflow_output_to_node_id[key]
                            if node_id in pydantic_nodes_dict and isinstance(
                                pydantic_nodes_dict[node_id], PwdOutputNode
                            ):
                                pydantic_nodes_dict[node_id].name = entry["name"]
                                self.logger.info(
                                    f"Overrode OutputNode ID {node_id} name to '{entry['name']}' from group_outputs."
                                )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed processing group_output entry {entry}: {e}"
                        )
