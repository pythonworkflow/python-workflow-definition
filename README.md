# Python Workflow Definition
[![Pipeline](https://github.com/pythonworkflow/python-workflow-definition/actions/workflows/pipeline.yml/badge.svg)](https://github.com/pythonworkflow/python-workflow-definition/actions/workflows/pipeline.yml)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/pythonworkflow/python-workflow-definition/HEAD)
[![arXiv](https://img.shields.io/badge/arXiv-2505.20366-b31b1b.svg)](https://arxiv.org/abs/2505.20366)
[![DOI](https://zenodo.org/badge/945869529.svg)](https://doi.org/10.5281/zenodo.15516179)

## Definition
In the Python Workflow Definition (PWD) each node represents a Python function, with the edges defining the connection 
between input and output of the different Python functions. 

## Format
Each workflow consists of three files, a Python module which defines the individual Pythons, a JSON file which defines
the connections between the different Python functions and a conda environment file to define the software dependencies.
The files are not intended to be human readable, but rather interact as a machine readable exchange format between the 
different workflow engines to enable interoperability. 

## Installation
The Python Workflow Definition can either be installed via pypi or via conda. For the [pypi installation](https://pypi.org/project/python-workflow-definition/) use:
```
pip install python-workflow-definition
```
For the conda installation via the [conda-forge community channel](https://anaconda.org/conda-forge/python-workflow-definition) use: 
```
conda install conda-forge::python-workflow-definition
```

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
def combined_workflow(x=1, y=2):
    tmp_dict = get_prod_and_div(x=x, y=y)
    return get_sum(x=tmp_dict["prod"], y=tmp_dict["div"])
```
For the workflow representation of these Python functions the Python functions are stored in the [example_workflows/arithmetic/workflow.py](example_workflows/arithmetic/workflow.py)
Python module. The connection of the Python functions are stored in the [example_workflows/arithmetic/workflow.json](example_workflows/arithmetic/workflow.json) 
JSON file:
```JSON
{
  "nodes": [
    {"id": 0, "type": "function", "value": "workflow.get_prod_and_div"},
    {"id": 1, "type": "function", "value": "workflow.get_sum"},
    {"id": 2, "type": "input", "value": 1, "name": "x"},
    {"id": 3, "type": "input", "value": 2, "name": "y"},
    {"id": 4, "type": "output", "name": "result"}
  ],
  "edges": [
    {"target": 0, "targetPort": "x", "source": 2, "sourcePort": null},
    {"target": 0, "targetPort": "y", "source": 3, "sourcePort": null},
    {"target": 1, "targetPort": "x", "source": 0, "sourcePort": "prod"},
    {"target": 1, "targetPort": "y", "source": 0, "sourcePort": "div"},
    {"target": 4, "targetPort": null, "source": 1, "sourcePort": null}
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

| Example                                                                                                        | Explanation                                                                                                               | 
|----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [example_workflows/arithmetic/aiida.ipynb](example_workflows/arithmetic/aiida.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [example_workflows/arithmetic/jobflow.ipynb](example_workflows/arithmetic/jobflow.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [example_workflows/arithmetic/pyiron_base.ipynb](example_workflows/arithmetic/pyiron_base.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [example_workflows/arithmetic/universal_workflow.ipynb](example_workflows/arithmetic/universal_workflow.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |

### Quantum Espresso Workflow
The second workflow example is the calculation of an energy volume curve with Quantum Espresso. In the first step the 
initial structure is relaxed, afterward it is strained and the total energy is calculated. 
* [example_workflows/quantum_espresso/workflow.py](example_workflows/quantum_espresso/workflow.py) Python functions 
* [example_workflows/quantum_espresso/workflow.json](example_workflows/quantum_espresso/workflow.json) Workflow definition in the Python Workflow Definition.
* [example_workflows/quantum_espresso/environment.yml](example_workflows/quantum_espresso/environment.yml) Conda environment

| Example                                                                                                                    | Explanation                                                                                                               | 
|----------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [example_workflows/quantum_espresso/aiida.ipynb](example_workflows/quantum_espresso/aiida.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [example_workflows/quantum_espresso/jobflow.ipynb](example_workflows/quantum_espresso/jobflow.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [example_workflows/quantum_espresso/pyiron_base.ipynb](example_workflows/quantum_espresso/pyiron_base.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [example_workflows/quantum_espresso/universal_workflow.ipynb](example_workflows/quantum_espresso/universal_workflow.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |

### NFDI4Ing Scientific Workflow Requirements
To demonstrate the compatibility of the Python Workflow Definition to file based workflows, the workflow benchmark developed as part of [NFDI4Ing](https://github.com/BAMresearch/NFDI4IngScientificWorkflowRequirements)
is implemented for all three simulation codes based on a shared workflow definition. 
* [example_workflows/nfdi/workflow.py](example_workflows/nfdi/workflow.py) Python functions 
* [example_workflows/nfdi/workflow.json](example_workflows/nfdi/workflow.json) Workflow definition in the Python Workflow Definition.

Additional source files provided with the workflow benchmark:
* [example_workflows/nfdi/source/envs/preprocessing.yaml](example_workflows/nfdi/source/envs/preprocessing.yaml) Conda environment for preprocessing
* [example_workflows/nfdi/source/envs/processing.yaml](example_workflows/nfdi/source/envs/processing.yaml) Conda environment for processing
* [example_workflows/nfdi/source/envs/postprocessing.yaml](example_workflows/nfdi/source/envs/postprocessing.yaml) Conda environment for postprocessing
* [example_workflows/nfdi/source/macros.tex.template](example_workflows/nfdi/source/macros.tex.template) LaTeX module template 
* [example_workflows/nfdi/source/paper.tex](example_workflows/nfdi/source/paper.tex) LaTeX paper template 
* [example_workflows/nfdi/source/poisson.py](example_workflows/nfdi/source/poisson.py) Poisson Python script 
* [example_workflows/nfdi/source/postprocessing.py](example_workflows/nfdi/source/postprocessing.py) Postprocessing Python script
* [example_workflows/nfdi/source/prepare_paper_macros.py](example_workflows/nfdi/source/prepare_paper_macros.py) LaTeX preprocessing Python script
* [example_workflows/nfdi/source/unit_square.geo](example_workflows/nfdi/source/unit_square.geo) Input structure 

| Example                                                                                            | Explanation                                                                                                               | 
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [example_workflows/nfdi/aiida.ipynb](example_workflows/nfdi/aiida.ipynb)                           | Define Workflow with aiida and execute it with jobflow and pyiron_base.                                                   |
| [example_workflows/nfdi/jobflow.ipynb](example_workflows/nfdi/jobflow.ipynb)                       | Define Workflow with jobflow and execute it with aiida and pyiron_base.                                                   |
| [example_workflows/nfdi/pyiron_base.ipynb](example_workflows/nfdi/pyiron_base.ipynb)               | Define Workflow with pyiron_base and execute it with aiida and jobflow.                                                   |
| [example_workflows/nfdi/universal_workflow.ipynb](example_workflows/nfdi/universal_workflow.ipynb) | Execute workflow defined in the Python Workflow Definition with aiida, executorlib, jobflow, pyiron_base and pure Python. |
