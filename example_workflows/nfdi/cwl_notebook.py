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
# This notebook executes the NFDI4Ing file-based workflow benchmark's `workflow.json` with the [Common Workflow Language](https://www.commonwl.org/) via [`cwltool`](https://github.com/common-workflow-language/cwltool), instead of generating the JSON from a Python workflow engine like the other notebooks in this directory. `python_workflow_definition.cwl.write_workflow` translates the PWD graph into a CWL `workflow.cwl` plus one `CommandLineTool` wrapper per pipeline function; CWL then passes data between steps as pickled files on disk rather than in-memory Python objects, which matches this benchmark's file-based nature.

# %%
import pickle

# %%
import json

# %%
import os

# %%
from python_workflow_definition.cwl import write_workflow

# %% [markdown]
# ## Overwrite source directory with absolute path
#
# `workflow.json` stores `source_directory` as the relative path `"source"`. Because `cwltool` stages each step's inputs into its own temporary working directory, a relative path would no longer resolve once execution starts, so it is rewritten to an absolute path before export.

# %%
with open("workflow.json") as f:
    content = json.load(f)

# %%
node_lst = []
for n in content["nodes"]:
    if "name" in n and n["name"] == "source_directory":
        n["value"] = os.path.abspath(n["value"])
    node_lst.append(n)

content["nodes"] = node_lst

# %%
with open("workflow.json", "w") as f:
    json.dump(content, f)

# %% [markdown]
# ## Execute workflow
#
# `write_workflow` reads `workflow.json` and writes out `workflow.cwl` (the CWL `Workflow` definition), one `<function>_<id>.cwl` `CommandLineTool` per pipeline step, and `workflow.yml` with the input values pickled to disk. `cwltool` then runs the six steps in dependency order, invoking `gmsh`, `meshio`, the Poisson solver, `pvbatch` and `tectonic` in turn, and writes the workflow's single output — the path to the compiled `paper.pdf` — to `result.pickle`.

# %%
write_workflow(file_name="workflow.json")

# %%
# ! cwltool --preserve-environment=CONDA_EXE workflow.cwl workflow.yml

# %% [markdown]
# The result is unpickled below to confirm it is the expected `paper.pdf` path.

# %%
with open("result.pickle", "rb") as f:
    print(pickle.load(f))

# %%
