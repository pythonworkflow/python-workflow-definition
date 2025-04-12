# Simple Workflow
As a first example we define two Python functions which add multiple inputs: 
```python
def add_x_and_y(x, y):
    z = x + y
    return x, y, z

def add_x_and_y_and_z(x, y, z):
    w = x + y + z
    return w
```
These two Python functions are combined in the following example workflow:
```python
x, y, z = add_x_and_y(x=1, y=2)
w = add_x_and_y_and_z(x=x, y=y, z=z)
```
For the workflow representation of these Python functions the Python functions are stored in the [simple_workflow.py](simple_workflow.py)
Python module. The connection of the Python functions are stored in the [workflow_simple.json](workflow_simple.json) 
JSON file:
```
{
  "nodes": {
    "0": "simple_workflow.add_x_and_y_and_z",
    "1": "simple_workflow.add_x_and_y",
    "2": "simple_workflow.add_x_and_y",
    "3": "simple_workflow.add_x_and_y",
    "4": 1,
    "5": 2
  },
  "edges": [
    {"target": 0, "targetPort": "x", "source": 1, "sourcePort": "x"},
    {"target": 1, "targetPort": "x", "source": 4, "sourcePort": null},
    {"target": 1, "targetPort": "y", "source": 5, "sourcePort": null},
    {"target": 0, "targetPort": "y", "source": 2, "sourcePort": "y"},
    {"target": 2, "targetPort": "x", "source": 4, "sourcePort": null},
    {"target": 2, "targetPort": "y", "source": 5, "sourcePort": null},
    {"target": 0, "targetPort": "z", "source": 3, "sourcePort": "z"},
    {"target": 3, "targetPort": "x", "source": 4, "sourcePort": null},
    {"target": 3, "targetPort": "y", "source": 5, "sourcePort": null}
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
