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


load_profile()


@task
def add(x, y):
    return x + y

@task
def compare(x, y):
    return x < y

@task
def multiply(x, y):
    return x * y

@task.graph
def WhileLoop(n, m):
    if m >= n:
        return m
    m = add(x=m, y=1).result
    return WhileLoop(n=n, m=m)


wg = WhileLoop.build(n=4, m=0)

wg.to_html()

write_workflow_json(wg=wg, file_name='write_while_loop.json')
