# Conclusion 
Based on the Python Workflow Definition three rather different workflows were implemented in rather different workflow 
engines: a simple arithmetic example coupling two Python functions, a Quantum Espresso energy volume curve calculation 
with fan-out parallelism, and a file based, multi-tool NFDI4Ing benchmark. In each case the same `workflow.json` was 
written by one workflow engine and successfully loaded and executed by the others, without any change to the underlying 
Python functions in `workflow.py`. This demonstrates the interoperability achieved with the Python Workflow Definition, 
and shows that it scales from small, in-memory Python workflows to larger, file based, multi-environment scientific 
workflows.

## Where to go next
* Browse the [example_workflows](https://github.com/pythonworkflow/python-workflow-definition/tree/main/example_workflows) 
  directory for the full set of notebooks, including engines not covered in this book such as `pyiron_workflow`, 
  `executorlib` and CWL.
* See the [README](https://github.com/pythonworkflow/python-workflow-definition) for installation instructions via 
  `pip` or `conda`.
* Read the accompanying publication: [J. Janssen et al., A python workflow definition for computational materials 
  design, Digital Discovery, 2025](https://doi.org/10.1039/D5DD00231A).