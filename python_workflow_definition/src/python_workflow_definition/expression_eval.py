"""
Safe expression evaluator for while loop conditions.

This module provides safe evaluation of Python expressions with restricted
operators and no access to dangerous built-ins or imports.
"""

import ast
from typing import Any, Dict, Set


# Define allowed AST node types for safe expression evaluation
SAFE_NODES: Set[type] = {
    # Literals
    ast.Constant,  # Python 3.8+ (replaces Num, Str, Bytes, NameConstant, etc.)
    ast.Num,  # Legacy: numbers
    ast.Str,  # Legacy: strings
    ast.Bytes,  # Legacy: bytes
    ast.NameConstant,  # Legacy: None, True, False
    ast.List,
    ast.Tuple,
    ast.Dict,
    # Variables
    ast.Name,
    ast.Load,  # Context for loading variables
    # Expressions
    ast.Expression,
    ast.Expr,
    # Comparison operators
    ast.Compare,
    ast.Lt,  # <
    ast.LtE,  # <=
    ast.Gt,  # >
    ast.GtE,  # >=
    ast.Eq,  # ==
    ast.NotEq,  # !=
    ast.Is,  # is
    ast.IsNot,  # is not
    ast.In,  # in
    ast.NotIn,  # not in
    # Boolean operators
    ast.BoolOp,
    ast.And,
    ast.Or,
    # Unary operators
    ast.UnaryOp,
    ast.Not,  # not
    ast.UAdd,  # +x
    ast.USub,  # -x
    # Binary operators (arithmetic)
    ast.BinOp,
    ast.Add,  # +
    ast.Sub,  # -
    ast.Mult,  # *
    ast.Div,  # /
    ast.FloorDiv,  # //
    ast.Mod,  # %
    ast.Pow,  # **
    # Subscripting (for list/dict access)
    ast.Subscript,
    ast.Index,  # Legacy: indexing
    ast.Slice,
}


class UnsafeExpressionError(ValueError):
    """Raised when an expression contains unsafe operations."""

    pass


def validate_expression_ast(node: ast.AST, expr: str) -> None:
    """
    Recursively validate that an AST only contains safe nodes.

    Args:
        node: AST node to validate
        expr: Original expression string (for error messages)

    Raises:
        UnsafeExpressionError: If unsafe operations are detected
    """
    node_type = type(node)

    if node_type not in SAFE_NODES:
        raise UnsafeExpressionError(
            f"Unsafe operation detected in expression '{expr}': "
            f"{node_type.__name__} is not allowed"
        )

    # Special checks for specific node types
    if isinstance(node, ast.Name):
        # Prevent access to dangerous built-ins
        if node.id.startswith("__"):
            raise UnsafeExpressionError(
                f"Access to dunder attributes is not allowed: '{node.id}'"
            )

    if isinstance(node, ast.Call):
        # Function calls are not allowed in safe expressions
        raise UnsafeExpressionError(
            f"Function calls are not allowed in expression '{expr}'"
        )

    if isinstance(node, (ast.Import, ast.ImportFrom)):
        raise UnsafeExpressionError("Import statements are not allowed")

    # Recursively validate child nodes
    for child in ast.iter_child_nodes(node):
        validate_expression_ast(child, expr)


def evaluate_expression(
    expression: str,
    variables: Dict[str, Any],
    max_length: int = 500,
) -> Any:
    """
    Safely evaluate a Python expression with restricted operations.

    This function:
    1. Parses the expression into an AST
    2. Validates that only safe operations are used
    3. Evaluates the expression with controlled namespace

    Args:
        expression: Python expression string to evaluate
        variables: Dictionary of variables available in the expression
        max_length: Maximum allowed expression length

    Returns:
        Result of the expression evaluation

    Raises:
        UnsafeExpressionError: If the expression contains unsafe operations
        SyntaxError: If the expression has invalid Python syntax
        ValueError: If the expression is too long

    Examples:
        >>> evaluate_expression("a < b", {"a": 1, "b": 2})
        True
        >>> evaluate_expression("x + y * 2", {"x": 10, "y": 5})
        20
        >>> evaluate_expression("not (a > 5 and b < 10)", {"a": 3, "b": 7})
        False
    """
    # Check expression length
    if len(expression) > max_length:
        raise ValueError(
            f"Expression too long ({len(expression)} > {max_length} characters)"
        )

    # Parse the expression
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        raise SyntaxError(f"Invalid expression syntax: {e}") from e

    # Validate the AST contains only safe operations
    validate_expression_ast(tree.body, expression)

    # Create a safe namespace with no built-ins
    safe_globals = {
        "__builtins__": {},
        # Add safe built-in constants
        "True": True,
        "False": False,
        "None": None,
    }

    # Evaluate the expression
    try:
        compiled = compile(tree, "<expression>", "eval")
        result = eval(compiled, safe_globals, variables)
        return result
    except Exception as e:
        raise ValueError(f"Error evaluating expression '{expression}': {e}") from e


def evaluate_condition(
    expression: str,
    variables: Dict[str, Any],
) -> bool:
    """
    Evaluate a condition expression and ensure it returns a boolean.

    This is a convenience wrapper around evaluate_expression that
    validates the result is a boolean value.

    Args:
        expression: Condition expression (should evaluate to bool)
        variables: Dictionary of variables available in the expression

    Returns:
        Boolean result of the condition

    Raises:
        TypeError: If the expression doesn't evaluate to a boolean
        UnsafeExpressionError: If the expression contains unsafe operations
        SyntaxError: If the expression has invalid syntax

    Examples:
        >>> evaluate_condition("a < b", {"a": 1, "b": 2})
        True
        >>> evaluate_condition("x in [1, 2, 3]", {"x": 2})
        True
    """
    result = evaluate_expression(expression, variables)

    if not isinstance(result, bool):
        raise TypeError(
            f"Condition expression must evaluate to boolean, got {type(result).__name__}: {result}"
        )

    return result
