# Python Workflow Definition
[![Pipeline](https://github.com/pyiron-dev/python-workflow-definition/actions/workflows/pipeline.yml/badge.svg)](https://github.com/pyiron-dev/python-workflow-definition/actions/workflows/pipeline.yml)
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
def get_sum(x, y):
    return x + y
    
def get_prod_and_div(x: float, y: float) -> dict:
    return {"prod": x * y, "div": x / y}
```
These two Python functions are combined in the following example workflow:
```python
tmp_dict = get_prod_and_div(x=1, y=2)
result = get_sum(x=tmp_dict["prod"], y=tmp_dict["div"])
```
For the workflow representation of these Python functions the Python functions are stored in the [arithmetic_workflow.py](example_workflows/arithmetic/arithmetic_workflow.py)
Python module. The connection of the Python functions are stored in the [workflow_arithmetic.json](example_workflows/arithmetic/workflow_arithmetic.json) 
JSON file:
```
{
  "nodes": [
    {"id": 0, "function": "simple_workflow.get_prod_and_div"},
    {"id": 1, "function": "simple_workflow.get_sum"},
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

The corresponding Jupyter notebooks demonstrate this functionality:

| Example                                                                    | Explanation                                                                                                               | 
|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [aiida_arithmetic.ipynb](example_workflows/arithmetic/aiida_arithmetic.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [jobflow_arithmetic.ipynb](example_workflows/arithmetic/jobflow_arithmetic.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [pyiron_base_arithmetic.ipynb](example_workflows/arithmetic/pyiron_base_arithmetic.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [universal_workflow_arithmetic.ipynb](example_workflows/arithmetic/universal_workflow_arithmetic.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |

### Quantum Espresso Workflow
The second workflow example is the calculation of an energy volume curve with Quantum Espresso. In the first step the 
initial structure is relaxed, afterward it is strained and the total energy is calculated. 
* [quantum_espresso_workflow.py](example_workflows/quantum_espresso/quantum_espresso_workflow.py) Python functions 
* [workflow_qe.json](example_workflows/quantum_espresso/workflow_qe.json) Workflow definition in the Python Workflow Definition.
* [environment_qe.yml](example_workflows/quantum_espresso/environment_qe.yml) Conda environment

| Example                                                    | Explanation                                                                                                               | 
|------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [aiida_qe.ipynb](example_workflows/quantum_espresso/aiida_qe.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [jobflow_qe.ipynb](example_workflows/quantum_espresso/jobflow_qe.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [pyiron_base_qe.ipynb](example_workflows/quantum_espresso/pyiron_base_qe.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [universal_workflow_qe.ipynb](example_workflows/quantum_espresso/universal_workflow_qe.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |

### NFDI4Ing Scientific Workflow Requirements
To demonstrate the compatibility of the Python Workflow Definition to file based workflows, the workflow benchmark developed as part of [NFDI4Ing](https://github.com/BAMresearch/NFDI4IngScientificWorkflowRequirements)
is implemented for all three simulation codes based on a shared workflow definition. 
* [nfdi_ing_workflow.py](example_workflows/nfdi/nfdi_ing_workflow.py) Python functions 
* [workflow_nfdi.json](example_workflows/nfdi/workflow_nfdi.json) Workflow definition in the Python Workflow Definition.

Additional source files provided with the workflow benchmark:
* [source/envs/preprocessing.yaml](example_workflows/nfdi/source/envs/preprocessing.yaml) Conda environment for preprocessing
* [source/envs/processing.yaml](example_workflows/nfdi/source/envs/processing.yaml) Conda environment for processing
* [source/envs/postprocessing.yaml](example_workflows/nfdi/source/envs/postprocessing.yaml) Conda environment for postprocessing
* [source/macros.tex.template](example_workflows/nfdi/source/macros.tex.template) LaTeX module template 
* [source/paper.tex](example_workflows/nfdi/source/paper.tex) LaTeX paper template 
* [source/poisson.py](example_workflows/nfdi/source/poisson.py) Poisson Python script 
* [source/postprocessing.py](example_workflows/nfdi/source/postprocessing.py) Postprocessing Python script
* [source/prepare_paper_macros.py](example_workflows/nfdi/source/prepare_paper_macros.py) LaTeX preprocessing Python script
* [source/unit_square.geo](example_workflows/nfdi/source/unit_square.geo) Input structure 

| Example                                                        | Explanation                                                                                                               | 
|----------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [aiida_nfdi.ipynb](example_workflows/nfdi/aiida_nfdi.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [jobflow_nfdi.ipynb](example_workflows/nfdi/jobflow_nfdi.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [pyiron_base_nfdi.ipynb](example_workflows/nfdi/pyiron_base_nfdi.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [universal_workflow_nfdi.ipynb](example_workflows/nfdi/universal_workflow_nfdi.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |