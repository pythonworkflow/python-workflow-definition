from pathlib import Path
from typing import List, Union, Optional, Literal, Any, Annotated, Type, TypeVar, TYPE_CHECKING
from pydantic import BaseModel, Field, field_validator, field_serializer, model_validator
from pydantic import ValidationError
import json
import logging

logger = logging.getLogger(__name__)

INTERNAL_DEFAULT_HANDLE = "__result__"
T = TypeVar("T", bound="PythonWorkflowDefinitionWorkflow")

if TYPE_CHECKING:
    from typing import Self

__all__ = (
    "PythonWorkflowDefinitionInputNode",
    "PythonWorkflowDefinitionOutputNode",
    "PythonWorkflowDefinitionFunctionNode",
    "PythonWorkflowDefinitionWhileNode",
    "PythonWorkflowDefinitionEdge",
    "PythonWorkflowDefinitionWorkflow",
)


class PythonWorkflowDefinitionBaseNode(BaseModel):
    """Base model for all node types, containing common fields."""

    id: int
    # The 'type' field will be overridden in subclasses with Literal types
    # to enable discriminated unions.
    type: str


class PythonWorkflowDefinitionInputNode(PythonWorkflowDefinitionBaseNode):
    """Model for input nodes."""

    type: Literal["input"]
    name: str
    value: Optional[Any] = None


class PythonWorkflowDefinitionOutputNode(PythonWorkflowDefinitionBaseNode):
    """Model for output nodes."""

    type: Literal["output"]
    name: str


class PythonWorkflowDefinitionFunctionNode(PythonWorkflowDefinitionBaseNode):
    """
    Model for function execution nodes.
    The 'name' attribute is computed automatically from 'value'.
    """

    type: Literal["function"]
    value: str  # Expected format: 'module.function'

    @field_validator("value")
    @classmethod
    def check_value_format(cls, v: str):
        if not v or "." not in v or v.startswith(".") or v.endswith("."):
            msg = (
                "FunctionNode 'value' must be a non-empty string ",
                "in 'module.function' format with at least one period.",
            )
            raise ValueError(msg)
        return v


# class PythonWorkflowDefinitionWhileNode(PythonWorkflowDefinitionBaseNode):
#     """
#     Model for while loop control flow nodes.
#
#     Supports two modes of operation:
#     1. Simple mode: conditionFunction + bodyFunction (functions as strings)
#     2. Complex mode: conditionFunction/conditionExpression + bodyWorkflow (nested workflow)
#
#     Exactly one condition method (conditionFunction OR conditionExpression) must be specified.
#     Exactly one body method (bodyFunction OR bodyWorkflow) must be specified.
#     """
#
#     type: Literal["while"]
#
#     # Condition evaluation (exactly one must be set)
#     conditionFunction: Optional[str] = None  # Format: 'module.function' returns bool
#     conditionExpression: Optional[str] = None  # Safe expression like "m < n"
#
#     # Body execution (exactly one must be set)
#     bodyFunction: Optional[str] = None  # Format: 'module.function'
#     bodyWorkflow: Optional["PythonWorkflowDefinitionWorkflow"] = None  # Nested subgraph
#
#     # Safety and configuration
#     maxIterations: int = Field(default=1000, ge=1)
#
#     # Optional: Track specific state variables across iterations
#     stateVars: Optional[List[str]] = None
#
#     @field_validator("conditionFunction")
#     @classmethod
#     def check_condition_function_format(cls, v: Optional[str]) -> Optional[str]:
#         """Validate conditionFunction format if provided."""
#         if v is not None:
#             if not v or "." not in v or v.startswith(".") or v.endswith("."):
#                 msg = (
#                     "WhileNode 'conditionFunction' must be a non-empty string "
#                     "in 'module.function' format with at least one period."
#                 )
#                 raise ValueError(msg)
#         return v
#
#     @field_validator("bodyFunction")
#     @classmethod
#     def check_body_function_format(cls, v: Optional[str]) -> Optional[str]:
#         """Validate bodyFunction format if provided."""
#         if v is not None:
#             if not v or "." not in v or v.startswith(".") or v.endswith("."):
#                 msg = (
#                     "WhileNode 'bodyFunction' must be a non-empty string "
#                     "in 'module.function' format with at least one period."
#                 )
#                 raise ValueError(msg)
#         return v
#
#     @model_validator(mode="after")
#     def check_exactly_one_condition(self) -> "Self":
#         """Ensure exactly one condition method is specified."""
#         condition_count = sum([
#             self.conditionFunction is not None,
#             self.conditionExpression is not None,
#         ])
#         if condition_count == 0:
#             raise ValueError(
#                 "WhileNode must specify exactly one condition method: "
#                 "either 'conditionFunction' or 'conditionExpression'"
#             )
#         if condition_count > 1:
#             raise ValueError(
#                 "WhileNode must specify exactly one condition method, "
#                 f"but {condition_count} were provided"
#             )
#         return self
#
#     @model_validator(mode="after")
#     def check_exactly_one_body(self) -> "Self":
#         """Ensure exactly one body method is specified."""
#         body_count = sum([
#             self.bodyFunction is not None,
#             self.bodyWorkflow is not None,
#         ])
#         if body_count == 0:
#             raise ValueError(
#                 "WhileNode must specify exactly one body method: "
#                 "either 'bodyFunction' or 'bodyWorkflow'"
#             )
#         if body_count > 1:
#             raise ValueError(
#                 "WhileNode must specify exactly one body method, "
#                 f"but {body_count} were provided"
#             )
#         return self
#


class PythonWorkflowDefinitionWhileNode(PythonWorkflowDefinitionBaseNode):
    """
    Model for while loop control flow nodes.
    
    Supports multiple execution modes:
    1. Function-based: conditionFunction + bodyFunction
    2. Workflow-based: conditionWorkflow + bodyWorkflow (nested subgraphs)
    3. Expression-based: conditionExpression + bodyFunction/bodyWorkflow
    """
    
    type: Literal["while"]
    
    # Condition evaluation (exactly one must be set)
    conditionFunction: Optional[str] = None  # 'module.function' returns bool
    conditionExpression: Optional[str] = None  # Expression like "ctx.n < 8"
    conditionWorkflow: Optional["PythonWorkflowDefinitionWorkflow"] = None  # Subgraph returning bool
    
    # Body execution (exactly one must be set)
    bodyFunction: Optional[str] = None  # 'module.function'
    bodyWorkflow: Optional["PythonWorkflowDefinitionWorkflow"] = None  # Nested subgraph
    
    # Context state management
    contextVars: Optional[List[str]] = None  # Variables tracked in loop context (e.g., ["n", "sum"])
    
    # Input/output port mappings for the while loop
    inputPorts: Optional[dict[str, Any]] = None  # Initial values for context vars
    outputPorts: Optional[dict[str, str]] = None  # Map context vars to output ports
    
    # Safety and configuration
    maxIterations: int = Field(default=1000, ge=1)
    
    # Optional: Specify which context variables to pass between iterations
    stateMapping: Optional[dict[str, str]] = None  # Map outputs to next iteration inputs

    @field_validator("conditionFunction")
    @classmethod
    def check_condition_function_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or "." not in v or v.startswith(".") or v.endswith("."):
                raise ValueError(
                    "WhileNode 'conditionFunction' must be in 'module.function' format"
                )
        return v

    @field_validator("bodyFunction")
    @classmethod
    def check_body_function_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or "." not in v or v.startswith(".") or v.endswith("."):
                raise ValueError(
                    "WhileNode 'bodyFunction' must be in 'module.function' format"
                )
        return v

    @model_validator(mode="after")
    def check_exactly_one_condition(self) -> "Self":
        """Ensure exactly one condition method is specified."""
        condition_count = sum([
            self.conditionFunction is not None,
            self.conditionExpression is not None,
            self.conditionWorkflow is not None,
        ])
        if condition_count == 0:
            raise ValueError(
                "WhileNode must specify exactly one condition method: "
                "'conditionFunction', 'conditionExpression', or 'conditionWorkflow'"
            )
        if condition_count > 1:
            raise ValueError(
                f"WhileNode must specify exactly one condition method, "
                f"but {condition_count} were provided"
            )
        return self

    @model_validator(mode="after")
    def check_exactly_one_body(self) -> "Self":
        """Ensure exactly one body method is specified."""
        body_count = sum([
            self.bodyFunction is not None,
            self.bodyWorkflow is not None,
        ])
        if body_count == 0:
            raise ValueError(
                "WhileNode must specify exactly one body method: "
                "'bodyFunction' or 'bodyWorkflow'"
            )
        if body_count > 1:
            raise ValueError(
                f"WhileNode must specify exactly one body method, "
                f"but {body_count} were provided"
            )
        return self
    
    @model_validator(mode="after")
    def check_context_vars_consistency(self) -> "Self":
        """Ensure contextVars aligns with inputPorts/outputPorts if specified."""
        if self.contextVars:
            if self.inputPorts:
                for var in self.contextVars:
                    if var not in self.inputPorts:
                        raise ValueError(
                            f"Context variable '{var}' declared but not in inputPorts"
                        )
            if self.outputPorts:
                for var in self.contextVars:
                    if var not in self.outputPorts:
                        raise ValueError(
                            f"Context variable '{var}' declared but not in outputPorts"
                        )
        return self


# Discriminated Union for Nodes
PythonWorkflowDefinitionNode = Annotated[
    Union[
        PythonWorkflowDefinitionInputNode,
        PythonWorkflowDefinitionOutputNode,
        PythonWorkflowDefinitionFunctionNode,
        PythonWorkflowDefinitionWhileNode,
    ],
    Field(discriminator="type"),
]


class PythonWorkflowDefinitionEdge(BaseModel):
    """Model for edges connecting nodes."""

    target: int
    targetPort: Optional[str] = None
    source: int
    sourcePort: Optional[str] = None

    @field_validator("sourcePort", mode="before")
    @classmethod
    def handle_default_source(cls, v: Any) -> Optional[str]:
        """
        Transforms incoming None/null for sourcePort to INTERNAL_DEFAULT_HANDLE.
        Runs before standard validation.
        """
        # Allow not specifying the sourcePort -> null gets resolved to __result__
        if v is None:
            return INTERNAL_DEFAULT_HANDLE
        elif v == INTERNAL_DEFAULT_HANDLE:
            # Disallow explicit use of the internal reserved handle name
            msg = (
                f"Explicit use of reserved sourcePort '{INTERNAL_DEFAULT_HANDLE}' "
                f"is not allowed. Use null/None for default output."
            )
            raise ValueError(msg)
        return v

    @field_serializer("sourcePort")
    def serialize_source_handle(self, v: Optional[str]) -> Optional[str]:
        """
        SERIALIZATION (Output): Converts internal INTERNAL_DEFAULT_HANDLE ("__result__")
        back to None.
        """
        if v == INTERNAL_DEFAULT_HANDLE:
            return None  # Map "__result__" back to None for JSON output
        return v  # Keep other handle names as they are


class PythonWorkflowDefinitionWorkflow(BaseModel):
    """The main workflow model."""

    version: str
    nodes: List[PythonWorkflowDefinitionNode]
    edges: List[PythonWorkflowDefinitionEdge]

    def dump_json(
        self,
        *,
        indent: Optional[int] = 2,
        **kwargs,
    ) -> str:
        """
        Dumps the workflow model to a JSON string.

        Args:
            indent: JSON indentation level.
            exclude_computed_function_names: If True (default), excludes the computed
                                             'name' field from FunctionNode objects
                                             in the output.
            **kwargs: Additional keyword arguments passed to Pydantic's model_dump.

        Returns:
            JSON string representation of the workflow.
        """

        # Dump the model to a dictionary first, using mode='json' for compatible types
        # Pass any extra kwargs (like custom 'exclude' rules for other fields)
        workflow_dict = self.model_dump(mode="json", **kwargs)

        # Dump the dictionary to a JSON string
        try:
            json_string = json.dumps(workflow_dict, indent=indent)
            logger.info("Successfully dumped workflow model to JSON string.")
            return json_string
        except TypeError as e:
            logger.error(
                f"Error serializing workflow dictionary to JSON: {e}", exc_info=True
            )
            raise  # Re-raise after logging

    def dump_json_file(
        self,
        file_name: Union[str, Path],
        *,
        indent: Optional[int] = 2,
        **kwargs,
    ) -> None:
        """
        Dumps the workflow model to a JSON file.

        Args:
            file_path: Path to the output JSON file.
            indent: JSON indentation level.
            exclude_computed_function_names: If True, excludes the computed 'name' field
                                             from FunctionNode objects.
            **kwargs: Additional keyword arguments passed to Pydantic's model_dump.
        """
        logger.info(f"Dumping workflow model to JSON file: {file_name}")
        # Pass kwargs to dump_json, which passes them to model_dump
        json_string = self.dump_json(
            indent=indent,
            **kwargs,
        )
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(json_string)
            logger.info(f"Successfully wrote workflow model to {file_name}.")
        except IOError as e:
            logger.error(
                f"Error writing workflow model to file {file_name}: {e}", exc_info=True
            )
            raise

    @classmethod
    def load_json_str(cls: Type[T], json_data: Union[str, bytes]) -> dict:
        """
        Loads and validates workflow data from a JSON string or bytes.

        Args:
            json_data: The JSON data as a string or bytes.

        Returns:
            An instance of PwdWorkflow.

        Raises:
            pydantic.ValidationError: If validation fails.
            json.JSONDecodeError: If json_data is not valid JSON.
        """
        logger.info("Loading workflow model from JSON data...")
        try:
            # Pydantic v2 method handles bytes or str directly
            instance = cls.model_validate_json(json_data)
            # Pydantic v1 equivalent: instance = cls.parse_raw(json_data)
            logger.info(
                "Successfully loaded and validated workflow model from JSON data."
            )
            return instance.model_dump()
        except ValidationError:  # Catch validation errors specifically
            logger.error("Workflow model validation failed.", exc_info=True)
            raise
        except json.JSONDecodeError:  # Catch JSON parsing errors specifically
            logger.error("Invalid JSON format encountered.", exc_info=True)
            raise
        except Exception as e:  # Catch any other unexpected errors
            logger.error(
                f"An unexpected error occurred during JSON loading: {e}", exc_info=True
            )
            raise

    @classmethod
    def load_json_file(cls: Type[T], file_name: Union[str, Path]) -> dict:
        """
        Loads and validates workflow data from a JSON file.

        Args:
            file_path: The path to the JSON file.

        Returns:
            An instance of PwdWorkflow.

        Raises:
            FileNotFoundError: If the file is not found.
            pydantic.ValidationError: If validation fails.
            json.JSONDecodeError: If the file is not valid JSON.
            IOError: If there are other file reading issues.
        """
        logger.info(f"Loading workflow model from JSON file: {file_name}")
        try:
            file_content = Path(file_name).read_text(encoding="utf-8")
            # Delegate validation to the string loading method
            return cls.load_json_str(file_content)
        except FileNotFoundError:
            logger.error(f"JSON file not found: {file_name}", exc_info=True)
            raise
        except IOError as e:
            logger.error(f"Error reading JSON file {file_name}: {e}", exc_info=True)
            raise
