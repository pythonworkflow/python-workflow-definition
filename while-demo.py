from aiida import load_profile
from aiida_workgraph import While, WorkGraph
from aiida_workgraph import task

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


### task.graph

@task.graph
def WhileLoop(n, m):
    if m >= n:
        return m
    m = add(x=m, y=1).result
    return WhileLoop(n=n, m=m)


wg = WhileLoop.build(n=4, m=0)

wg.to_html()
wg.run()


### Context manager

with WorkGraph('while-context-manager') as wg:
    n = add(x=1, y=1).result
    wg.ctx.n = n

    (condition := wg.ctx.n < 8) << n

    with While(condition, max_iterations=10):
        n = add(x=wg.ctx.n, y=1).result
        wg.ctx.n = n

    wg.outputs.result = add(x=n, y=1).result

wg.to_html()
wg.run()

print(f'Result: {wg.outputs.result.value}')


### As task

wg = WorkGraph('while-task-example')

# Initialize 'n' with an initial value
initial_add_task = wg.add_task(add, x=1, y=1)  # n = 2
wg.ctx.n = initial_add_task.outputs.result

# Define the condition for the while loop: n < 8
# Here, we use the `compare` task as defined above
condition_task = wg.add_task(compare, x=wg.ctx.n, y=8)
# Ensure the condition task waits for the initial_add_task to complete
condition_task.waiting_on.add(initial_add_task)

# Start the While Zone
while_task = wg.add_task('workgraph.while_zone', max_iterations=10, conditions=condition_task.outputs.result)

# Tasks within the while loop
# First, add 1 to n
add_task_in_loop = while_task.add_task(add, x=wg.ctx.n, y=1)
# Then, multiply the result by 2
multiply_task_in_loop = while_task.add_task(multiply, x=add_task_in_loop.outputs.result, y=2)
# Update 'n' for the next iteration of the loop
wg.ctx.n = multiply_task_in_loop.outputs.result

# After the loop, add 1 to the final 'n'
final_add_task = wg.add_task(add, x=multiply_task_in_loop.outputs.result, y=1)
wg.outputs.result = final_add_task.outputs.result

# Run the workflow
wg.to_html()
wg.run()

print(f'State of WorkGraph: {wg.state}')
print(f'Result: {wg.outputs.result.value}')
