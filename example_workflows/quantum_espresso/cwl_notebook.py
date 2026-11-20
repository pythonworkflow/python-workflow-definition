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
# This notebook executes the Quantum Espresso energy-volume-curve `workflow.json` (produced by one of the other notebooks in this directory, e.g. `aiida.ipynb`) with the [Common Workflow Language](https://www.commonwl.org) via [`cwltool`](https://github.com/common-workflow-language/cwltool). Unlike the other engines, PWD does not build a CWL graph directly in Python - instead it translates an existing `workflow.json` into native CWL files, which `cwltool` then executes as a separate command line process.

# %%
import os

# %%
import pickle

# %% [markdown]
# ## Translate workflow.json to CWL
#
# `write_workflow` reads the existing `workflow.json` and generates: one `.cwl` `CommandLineTool` per PWD function node (each one invokes `python -m python_workflow_definition.cwl --function=...` to call the matching function in `workflow.py`), a top-level `workflow.cwl` that chains these steps together following the `workflow.json` edges, and a `workflow.yml` job file listing one input file per PWD input node. Since CWL only passes files between steps, every input and every function output is exchanged as a pickle file.

# %%
from python_workflow_definition.cwl import write_workflow

# %%
write_workflow(file_name="workflow.json")

# %% [markdown]
# ## Run the workflow with cwltool
#
# ASE's Quantum Espresso writer resolves the pseudopotential directory from the `ESPRESSO_PSEUDO` environment variable when no explicit path is given. Because `cwltool` runs every step in its own isolated temporary directory, the environment variable has to be forwarded explicitly with `--preserve-environment=ESPRESSO_PSEUDO`, so that `pw.x` can find the pseudopotential file shipped in [`espresso/pseudo`](espresso/pseudo) from any step.

# %%
os.environ["ESPRESSO_PSEUDO"] = os.path.abspath(os.path.join("../../espresso/pseudo"))

# %%
# ! cwltool --preserve-environment=ESPRESSO_PSEUDO workflow.cwl workflow.yml

# %% [markdown]
# `cwltool` runs one step per PWD function node - `get_bulk_structure`, the `vc-relax` `calculate_qe`, `generate_structures`, the five strained `scf` `calculate_qe` steps and finally `plot_energy_volume_curve` - each reading its input pickles and writing its output pickle(s), exactly mirroring the fan-out of one relax followed by five parallel SCF calculations seen in the other notebooks. The workflow's final output is declared as `result_file`, the pickle produced by the last step.

# %%
with open("result.pickle", "rb") as f:
    print(pickle.load(f))

# %% [markdown]
# `plot_energy_volume_curve` has no return value, so `result_file` unpickles to `None` here - that is expected. The actual output of this workflow is the `evcurve.png` plot, written as a side effect into the working directory of the last CWL step.

# %%
