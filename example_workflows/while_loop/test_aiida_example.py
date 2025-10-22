"""
Test AiiDA WorkGraph with while loop integration.

This script demonstrates a realistic workflow:
1. Arithmetic pre-processing (prod_and_div, sum)
2. While loop (count from 0 to result)
3. Post-processing (square)
"""

import sys
from pathlib import Path
from python_workflow_definition.aiida import load_workflow_json, write_workflow_json
from aiida import load_profile
from aiida_workgraph import task

# Add source to path
src_path = Path(__file__).parent.parent.parent / "python_workflow_definition" / "src"
sys.path.insert(0, str(src_path))

# Add while_loop directory to path so we can import arithmetic_workflow and while_workflow
while_loop_path = Path(__file__).parent
sys.path.insert(0, str(while_loop_path))


from typing import Callable, Any

def my_while(
    input_ports: dict, 
    condition_f: Callable[[dict, dict], bool], 
    body_f: Callable[[dict, dict], dict], 
    finalizer: Callable[[dict, dict], Any]
) -> Any:
    ctx = {}
    while condition_f(input_ports, ctx):
        ctx = body_f(input_ports, ctx)
    return finalizer(input_ports, ctx)


# Example: Sum numbers from 0 to limit
def condition_f(input_ports: dict, ctx: dict) -> bool:
    limit = input_ports.get('limit', 0)
    current = ctx.get('current', 0)
    return current < limit

def body_f(input_ports: dict, ctx: dict) -> dict:
    current = ctx.get('current', 0)
    total = ctx.get('total', 0)
    return {
        'current': current + 1,
        'total': total + current
    }

def finalizer(input_ports: dict, ctx: dict) -> dict:
    return {
        'result': ctx.get('total', 0),
        'iterations': ctx.get('current', 0)
    }


# Run it
result = my_while(
    input_ports={'limit': 10},
    condition_f=condition_f,
    body_f=body_f,
    finalizer=finalizer
)

print(result)  # {'result': 45, 'iterations': 10}

raise SystemExit()

# from typing import Callable
#
# def condition_f(x, limit):
#     return limit > x
#
# def body_f(x):
#     return x + 1
#
# # def abstract_while(x, limit):
# #     if not condition(x=x, limit=limit):
# #         return x
# #     x = function_body(x=x)
# #     return abstract_while(x=x, limit=limit)
#
#
# def my_while(input_ports: dict, condition_f=Callable, body_f=Callable, finalizer=Callable):
#     ctx = {}
#     while condition_f(input_ports, ctx):
#         ctx = body_f(input_ports, ctx)
#     return finalizer(input_ports, ctx) # these become output ports
#
# my_while()

# load_profile()
#
#
# @task
# def add(x, y):
#     return x + y
#
# @task
# def compare(x, y):
#     return x < y
#
# @task
# def multiply(x, y):
#     return x * y
#
# @task.graph
# def WhileLoop(n, m):
#     if m >= n:
#         return m
#     m = add(x=m, y=1).result
#     return WhileLoop(n=n, m=m)
#
#
# wg = WhileLoop.build(n=4, m=0)
#
# wg.to_html()
#
# write_workflow_json(wg=wg, file_name='write_while_loop.json')
