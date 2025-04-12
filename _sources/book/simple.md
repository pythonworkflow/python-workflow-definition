# Simple Workflow
As a first example we define two Python functions which add multiple inputs: 
```python
def add_x_and_y(x, y):
    return x + y
    
def get_prod_and_div(x: float, y: float) -> dict:
    return {"prod": x * y, "div": x / y}
```
These two Python functions are combined in the following example workflow:
```python
tmp_dict = get_prod_and_div(x=1, y=2)
result = add_x_and_y(x=tmp_dict["prod"], y=tmp_dict["div"])
```
For the workflow representation of these Python functions the Python functions are stored in the [simple_workflow.py](simple_workflow.py)
Python module. The connection of the Python functions are stored in the [workflow_simple.json](workflow_simple.json) 
JSON file:
```
{
  "nodes": [
    {"id": 0, "function": "simple_workflow.get_prod_and_div"},
    {"id": 1, "function": "simple_workflow.add_x_and_y"},
    {"id": 2, "value": 1},
    {"id": 3, "value": 2}
  ],
  "edges": [
    {"target": 0, "targetPort": "x", "source": 2, "sourcePort": null},
    {"target": 0, "targetPort": "y", "source": 3, "sourcePort": null},
    {"target": 1, "targetPort": "x", "source": 0, "sourcePort": "prod"},
    {"target": 1, "targetPort": "y", "source": 0, "sourcePort": "div"}
  ]
}
```
The abbreviations in the definition of the edges are:
* `target` - target node 
* `targetPort` - target port - for a node with multiple input parameters the target port specifies which input parameter to use.
* `source` - source node 
* `sourcePort` - source port - for a node with multiple output parameters the source port specifies which output parameter to use.

As the workflow does not require any additional resources, as it is only using built-in functionality of the Python standard 
library.
