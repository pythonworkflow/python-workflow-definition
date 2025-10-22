"""
Example workflow functions for while loop demonstration.

This module contains:
1. Simple counter increment functions for while loops
2. Convergence checking for iterative algorithms
3. Arithmetic functions for testing workflows
"""


def double(x):
    """Double a number."""
    return x * 2


def get_square(x):
    """Square a number or extract 'm' from dict and square it."""
    return x ** 2


def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


def get_sum(x, y):
    return x + y


def is_less_than(n, m):
    """
    Condition function: Check if m < n.

    Args:
        n: Upper bound
        m: Current value

    Returns:
        bool: True if m < n, False otherwise
    """
    return m < n


def increment_m(n, m):
    """
    Body function: Increment m by 1.

    This function maintains the loop state by returning
    a dictionary with updated values.

    Args:
        n: Upper bound (unchanged)
        m: Current value

    Returns:
        dict: Updated state with incremented m
    """
    return {"n": n, "m": m + 1}


def increment_simple(n, m):
    """
    Simple increment that returns just m (for single-output workflows).

    Args:
        n: Upper bound (unchanged)
        m: Current value

    Returns:
        int: Incremented m value
    """
    return m + 1


def not_converged(threshold, current_error):
    """
    Condition function: Check if iteration should continue.

    Args:
        threshold: Convergence threshold
        current_error: Current error value

    Returns:
        bool: True if not converged (error > threshold)
    """
    return current_error > threshold


def iterative_step(threshold, current_error, data):
    """
    Body function: Perform one iteration of an algorithm.

    This is a placeholder for more complex iterative algorithms.

    Args:
        threshold: Convergence threshold
        current_error: Current error value
        data: Input data to process

    Returns:
        dict: Updated state with new error and processed data
    """
    # Simulate error reduction
    new_error = current_error * 0.5
    # Simulate data transformation
    new_data = [x * 1.1 for x in data]

    return {
        "threshold": threshold,
        "current_error": new_error,
        "data": new_data,
    }


# Pre-processing and post-processing functions for realistic workflows


def add_numbers(x, y):
    """
    Add two numbers together.

    Args:
        x: First number
        y: Second number

    Returns:
        int/float: Sum of x and y
    """
    return x + y
