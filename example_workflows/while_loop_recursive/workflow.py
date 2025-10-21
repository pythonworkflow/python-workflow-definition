"""
Recursive while loop implementation.

This demonstrates the recursive approach where a function calls itself
until a condition is met, creating a cycle in the workflow graph.
"""


def while_loop(n, m):
    """
    Recursive while loop: increment m until m >= n.

    This function demonstrates the recursive pattern:
    - If condition is met (m >= n), return the result
    - Otherwise, increment m and recursively call itself

    Args:
        n: Upper bound (target value)
        m: Current value (counter)

    Returns:
        int: Final value of m (should equal n)
    """
    if m >= n:
        return m
    m = m + 1
    return while_loop(n=n, m=m)


def while_loop_with_accumulator(n, m, accumulator):
    """
    Recursive while loop with accumulator pattern.

    This demonstrates collecting results across iterations.

    Args:
        n: Upper bound
        m: Current counter
        accumulator: List collecting values

    Returns:
        dict: Final state with counter and accumulated values
    """
    if m >= n:
        return {"m": m, "accumulator": accumulator}

    # Add current value to accumulator
    new_accumulator = accumulator + [m]
    m = m + 1

    return while_loop_with_accumulator(n=n, m=m, accumulator=new_accumulator)


def fibonacci_recursive(n, current, a, b, results):
    """
    Generate Fibonacci sequence recursively.

    Args:
        n: Number of terms to generate
        current: Current iteration index
        a: Previous Fibonacci number
        b: Current Fibonacci number
        results: List of Fibonacci numbers generated so far

    Returns:
        dict: Final results with Fibonacci sequence
    """
    if current >= n:
        return {"results": results, "count": current}

    # Calculate next Fibonacci number
    next_fib = a + b
    new_results = results + [b]

    return fibonacci_recursive(
        n=n, current=current + 1, a=b, b=next_fib, results=new_results
    )


def converge_to_zero(value, threshold, iterations):
    """
    Recursively reduce a value until it's below threshold.

    Simulates an iterative algorithm that converges.

    Args:
        value: Current value
        threshold: Convergence threshold
        iterations: Number of iterations performed

    Returns:
        dict: Final value and iteration count
    """
    if abs(value) <= threshold:
        return {"value": value, "iterations": iterations, "converged": True}

    if iterations >= 1000:  # Safety limit
        return {"value": value, "iterations": iterations, "converged": False}

    # Reduce value by 50% each iteration
    new_value = value * 0.5

    return converge_to_zero(
        value=new_value, threshold=threshold, iterations=iterations + 1
    )
