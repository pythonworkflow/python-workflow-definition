from aiida_workgraph import task, WorkGraph, namespace
from aiida import load_profile, orm
from python_workflow_definition.aiida import write_workflow_json
from workflow import get_prod_and_div as _get_prod_and_div, get_sum as _get_sum, get_square as _get_square

load_profile()


# Wrap the functions with @task decorator
get_prod_and_div = task(outputs=["prod", "div"])(_get_prod_and_div)
get_sum = task(_get_sum)
get_square = task(_get_square)


# Create nested workflow manually (corresponds to prod_div.json)
nested_wg = WorkGraph(
    name="nested_workflow",
    inputs=namespace(x=namespace, y=namespace),
    outputs=namespace(result=namespace),
)

# Add tasks to nested workflow
t1 = nested_wg.add_task(get_prod_and_div)
t2 = nested_wg.add_task(get_sum)
t3 = nested_wg.add_task(get_square)

# Connect nested workflow inputs to first task
nested_wg.add_link(nested_wg.inputs.x, t1.inputs.x)
nested_wg.add_link(nested_wg.inputs.y, t1.inputs.y)

# Connect tasks within nested workflow
nested_wg.add_link(t1.outputs.prod, t2.inputs.x)
nested_wg.add_link(t1.outputs.div, t2.inputs.y)
nested_wg.add_link(t2.outputs.result, t3.inputs.x)

# Connect nested workflow output
nested_wg.outputs.result = t3.outputs.result

# Set default values for nested workflow inputs
nested_wg.inputs.x.value = orm.Float(1)
nested_wg.inputs.y.value = orm.Float(2)


# Create main workflow (corresponds to main.pwd.json)
main_wg = WorkGraph(
    name="main_workflow",
    inputs=namespace(a=namespace, b=namespace, c=namespace),
    outputs=namespace(final_result=namespace),
)

# Add tasks to main workflow
preprocessing = main_wg.add_task(get_prod_and_div)
nested_task = main_wg.add_task(nested_wg)  # Add the nested workflow as a task
postprocessing = main_wg.add_task(get_sum)

# Connect main workflow inputs to preprocessing
main_wg.add_link(main_wg.inputs.a, preprocessing.inputs.x)
main_wg.add_link(main_wg.inputs.c, preprocessing.inputs.y)

# Connect preprocessing to nested workflow
main_wg.add_link(preprocessing.outputs.prod, nested_task.inputs.x)
main_wg.add_link(preprocessing.outputs.div, nested_task.inputs.y)

# Connect nested workflow to postprocessing
main_wg.add_link(nested_task.outputs.result, postprocessing.inputs.x)
main_wg.add_link(main_wg.inputs.b, postprocessing.inputs.y)

# Connect main workflow output
main_wg.outputs.final_result = postprocessing.outputs.result

# Set default values for main workflow inputs
main_wg.inputs.a.value = orm.Float(3)
main_wg.inputs.b.value = orm.Float(2)
main_wg.inputs.c.value = orm.Float(4)


# Export to JSON (will create main_generated.pwd.json and nested_1.json)
print("Exporting workflow to JSON files...")
write_workflow_json(wg=main_wg, file_name="main_generated.pwd.json")
print("✓ Exported to main_generated.pwd.json and nested_1.json")

# Optionally run the workflow
# main_wg.run()
