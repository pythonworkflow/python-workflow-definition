from typing import List, Union, Optional, Literal, Any, Annotated
from pydantic import BaseModel, Field, field_validator, computed_field
import logging

logger = logging.getLogger(__name__)

INTERNAL_DEFAULT_HANDLE = "__result__"


class BaseNode(BaseModel):
    """Base model for all node types, containing common fields."""

    id: int
    # The 'type' field will be overridden in subclasses with Literal types
    # to enable discriminated unions.
    type: str


class InputNode(BaseNode):
    """Model for input nodes."""

    type: Literal["input"]
    name: str
    value: Optional[Any] = None


class OutputNode(BaseNode):
    """Model for output nodes."""

    type: Literal["output"]
    name: str


class FunctionNode(BaseNode):
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

    @computed_field
    @property
    def name(self) -> str:
        """Dynamically computes the function name from the 'value' field."""
        try:
            return self.value.rsplit(".", 1)[-1]
        except IndexError:
            msg = (
                f"Could not extract function name from invalid FunctionNode value: '{self.value}' (ID: {self.id}). Check validation."
            )
            raise ValueError(msg)
        except Exception as e:
            logger.error(
                f"Unexpected error computing name for FunctionNode value: '{self.value}' (ID: {self.id}): {e}",
                exc_info=True,
            )
            raise


# Discriminated Union for Nodes
Node = Annotated[
    Union[InputNode, OutputNode, FunctionNode], Field(discriminator="type")
]


class Edge(BaseModel):
    """Model for edges connecting nodes."""

    target: Optional[int] = None
    targetHandle: Optional[str] = None
    source: Optional[int] = None
    sourceHandle: Optional[str] = None

    @field_validator("sourceHandle", mode="before")
    @classmethod
    def handle_default_source(cls, v: Any) -> Optional[str]:
        """
        Transforms incoming None/null for sourceHandle to INTERNAL_DEFAULT_HANDLE.
        Runs before standard validation.
        """
        # Allow not specifying the sourceHandle -> null gets resolved to __result__
        if v is None:
            return INTERNAL_DEFAULT_HANDLE
        elif v == INTERNAL_DEFAULT_HANDLE:
            # Disallow explicit use of the internal reserved handle name
            msg = (
                f"Explicit use of reserved sourceHandle '{INTERNAL_DEFAULT_HANDLE}' "
                f"is not allowed. Use null/None for default output."
            )
            raise ValueError(msg)
        return v


class Workflow(BaseModel):
    """The main workflow model."""

    nodes: List[Node]
    edges: List[Edge]
