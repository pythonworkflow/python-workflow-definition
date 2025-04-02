# Python Workflow Definition
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/pyiron-dev/python-workflow-definition/HEAD)

## Definition
In the Python Workflow Definition (PWD) each node represents a Python function, with the edges defining the connection 
between input and output of the different Python functions. 

## Format
Each workflow consists of three files, a Python module which defines the individual Pythons, a JSON file which defines
the connections between the different Python functions and a conda environment file to define the software dependencies.
The files are not intended to be human readable, but rather interact as a machine readable exchange format between the 
different workflow engines to enable interoperability. 

## Examples
### Simple Example 
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

The corresponding Jupyter notebooks demonstrate this functionality:

| Example                                                            | Explanation                                                                                                               | 
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [aiida_simple.ipynb](aiida_simple.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [jobflow_simple.ipynb](jobflow_simple.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [pyiron_base_simple.ipynb](pyiron_base_simple.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [universal_workflow_simple.ipynb](universal_workflow_simple.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |

### Quantum Espresso Workflow
The second workflow example is the calculation of an energy volume curve with Quantum Espresso. In the first step the 
initial structure is relaxed, afterward it is strained and the total energy is calculated. 
* [quantum_espresso_workflow.py](quantum_espresso_workflow.py) Python functions 
* [workflow_qe.json](workflow_qe.json) Workflow definition in the Python Workflow Definition.
* [environment_qe.yml](environment_qe.yml) Conda environment

| Example                                                    | Explanation                                                                                                               | 
|------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [aiida_qe.ipynb](aiida_qe.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [jobflow_qe.ipynb](jobflow_qe.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [pyiron_base_qe.ipynb](pyiron_base_qe.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [universal_workflow_qe.ipynb](universal_workflow_qe.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |

### NFDI4Ing Scientific Workflow Requirements
To demonstrate the compatibility of the Python Workflow Definition to file based workflows, the workflow benchmark developed as part of [NFDI4Ing](https://github.com/BAMresearch/NFDI4IngScientificWorkflowRequirements)
is implemented for all three simulation codes based on a shared workflow definition. 
* [nfdi_ing_workflow.py](nfdi_ing_workflow.py) Python functions 
* [workflow_nfdi.json](workflow_nfdi.json) Workflow definition in the Python Workflow Definition.

Additional source files provided with the workflow benchmark:
* [source/envs/preprocessing.yaml](source/envs/preprocessing.yaml) Conda environment for preprocessing
* [source/envs/processing.yaml](source/envs/processing.yaml) Conda environment for processing
* [source/envs/postprocessing.yaml](source/envs/postprocessing.yaml) Conda environment for postprocessing
* [source/macros.tex.template](source/macros.tex.template) LaTeX module template 
* [source/paper.tex](source/paper.tex) LaTeX paper template 
* [source/poisson.py](source/poisson.py) Poisson Python script 
* [source/postprocessing.py](source/postprocessing.py) Postprocessing Python script
* [source/prepare_paper_macros.py](source/prepare_paper_macros.py) LaTeX preprocessing Python script
* [source/unit_square.geo](source/unit_square.geo) Input structure 

| Example                                                        | Explanation                                                                                                               | 
|----------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [aiida_nfdi.ipynb](aiida_nfdi.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [jobflow_nfdi.ipynb](jobflow_nfdi.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [pyiron_base_nfdi.ipynb](pyiron_base_nfdi.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [universal_workflow_nfdi.ipynb](universal_workflow_nfdi.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |