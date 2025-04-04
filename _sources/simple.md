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
    {"tn": 0, "th": "x", "sn": 1, "sh": "x"},
    {"tn": 1, "th": "x", "sn": 4, "sh": null},
    {"tn": 1, "th": "y", "sn": 5, "sh": null},
    {"tn": 0, "th": "y", "sn": 2, "sh": "y"},
    {"tn": 2, "th": "x", "sn": 4, "sh": null},
    {"tn": 2, "th": "y", "sn": 5, "sh": null},
    {"tn": 0, "th": "z", "sn": 3, "sh": "z"},
    {"tn": 3, "th": "x", "sn": 4, "sh": null},
    {"tn": 3, "th": "y", "sn": 5, "sh": null}
  ]
}
```
The abbreviations in the definition of the edges are:
* `tn` - target node 
* `th` - target handle - for a node with multiple input parameters the target handle specifies which input parameter to use.
* `sn` - source node 
* `sh` - source handle - for a node with multiple output parameters the source handle specifies which output parameter to use.

As the workflow does not require any additional resources, as it is only using built-in functionality of the Python standard 
library.
