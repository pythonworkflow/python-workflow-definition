from aiida_workgraph import task
from aiida import load_profile

load_profile()


@task(outputs=["prod", "div"])
def get_prod_and_div(x, y):
    return {"prod": x * y, "div": x / y}


@task
def get_sum(x, y):
    return x + y


@task
def get_square(x):
    return x**2


@task.graph
def nested_workflow(x, y):
    """Inner workflow from prod_div.json:
    - get_prod_and_div(x, y) → prod, div
    - get_sum(prod, div) → result
    - get_square(result) → result
    """
    prod_and_div = get_prod_and_div(x=x, y=y)
    sum_result = get_sum(x=prod_and_div.prod, y=prod_and_div.div)
    square_result = get_square(x=sum_result.result)
    return square_result.result


@task.graph
def main_workflow(a, b, c):
    """Outer workflow from main.pwd.json:
    - Pre-processing: get_prod_and_div(a, c) → prod, div
    - Nested workflow: nested_workflow(prod, div) → result
    - Post-processing: get_sum(result, b) → final_result
    """
    # Pre-processing step
    preprocessing = get_prod_and_div(x=a, y=c)

    # Nested workflow
    nested_result = nested_workflow(x=preprocessing.prod, y=preprocessing.div)

    # Post-processing step
    final_result = get_sum(x=nested_result.result, y=b)

    return final_result.result


wg = main_workflow.build(a=3, b=2, c=4)
wg.run()
