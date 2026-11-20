# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # CWL
#
# [`cwltool`](https://github.com/common-workflow-language/cwltool) is the reference implementation of the [Common Workflow Language (CWL)](https://www.commonwl.org/), a standard for describing command-line based workflows. Unlike the other engines in this repository, CWL has no Python API: workflows are described in YAML/JSON documents and executed by the external `cwltool` command. This notebook converts the arithmetic `workflow.json` into an equivalent set of CWL files and executes them with `cwltool`.

# %%
import pickle

# %%
from python_workflow_definition.cwl import write_workflow

# %% [markdown]
# `write_workflow` reads the existing `workflow.json` and generates the corresponding CWL description: one `CommandLineTool` `.cwl` file per function node, a `workflow.cwl` file that wires the steps together, and a `workflow.yml` file listing the input values (each serialized to its own pickle file). Every generated tool invokes `python -m python_workflow_definition.cwl`, which loads the target function from `workflow.py` and calls it with the pickled inputs.

# %%
write_workflow(file_name="workflow.json")

# %% [markdown]
# Running `cwltool workflow.cwl workflow.yml` executes the steps in dependency order, passing intermediate results between steps as pickle files, and prints the location of the final output file.

# %%
# ! cwltool workflow.cwl workflow.yml

# %% [markdown]
# The workflow's final output is written to `result.pickle`; unpickling it gives the same numeric result produced by the other engines.

# %%
with open("result.pickle", "rb") as f:
    print(pickle.load(f))

# %%
