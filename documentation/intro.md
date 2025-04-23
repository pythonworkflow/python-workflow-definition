# Definition
In the Python Workflow Definition (PWD) each node represents a Python function, with the edges defining the connection 
between input and output of the different Python functions. 

## Format
Each workflow consists of three files, a Python module which defines the individual Pythons, a JSON file which defines
the connections between the different Python functions and a conda environment file to define the software dependencies.
The files are not intended to be human readable, but rather interact as a machine readable exchange format between the 
different workflow engines to enable interoperability. 

## Workflow Engines
Currently supported workflow engines: 
* [aiida-workgraph](https://github.com/aiidateam/aiida-workgraph)
* [jobflow](https://github.com/materialsproject/jobflow)
* [pyiron_base](https://github.com/pyiron/pyiron_base)

## Example Workflows
Three workflows are implemented:
* Simple workflow coupling two python functions
* Calculation of an energy volume curve with quantum espresso
* File based workflow benchmark from [NFDI4Ing](https://www.inggrid.org/article/id/3726/)
