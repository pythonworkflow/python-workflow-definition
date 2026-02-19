from pathlib import Path
from typing import List, Union, Optional, Literal, Any, Annotated, Type, TypeVar
from pydantic import BaseModel, Field, field_validator, field_serializer
from pydantic import ValidationError
import json
import logging

logger = logging.getLogger(__name__)

INTERNAL_DEFAULT_HANDLE = "__result__"
T = TypeVar("T", bound="PythonWorkflowDefinitionWorkflow")

__all__ = (
    "PythonWorkflowDefinitionInputNode",
    "PythonWorkflowDefinitionOutputNode",
    "PythonWorkflowDefinitionFunctionNode",
    "PythonWorkflowDefinitionEdge",
    "PythonWorkflowDefinitionWorkflow",
)

JsonPrimitive = Union[str, int, float, bool, None]


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
    value: Optional[JsonPrimitive] = None


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


# Discriminated Union for Nodes
PythonWorkflowDefinitionNode = Annotated[
    Union[
        PythonWorkflowDefinitionInputNode,
        PythonWorkflowDefinitionOutputNode,
        PythonWorkflowDefinitionFunctionNode,
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
