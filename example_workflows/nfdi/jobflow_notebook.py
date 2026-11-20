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
# # jobflow

# %% [markdown]
# https://github.com/BAMresearch/NFDI4IngScientificWorkflowRequirements
#
# This notebook defines the NFDI4Ing file-based workflow benchmark with [`jobflow`](https://github.com/materialsproject/jobflow) and then loads the resulting `workflow.json` into `aiida`, `pyiron_base` and `pyiron_workflow`. Every stage of the pipeline shells out to an external command-line tool (`gmsh`, `meshio`, a FEniCS-based Poisson solver, ParaView's `pvbatch`, `tectonic`) in its own conda environment and passes file paths between stages rather than in-memory Python objects — see [`workflow.py`](workflow.py).

# %% [markdown]
# ## Define workflow with jobflow
#
# The `job` decorator turns each of the six pipeline functions into a jobflow `Job` that delays execution until the `Flow` is run. Because `convert_to_xdmf` and `poisson` return a `dict`, their outputs are accessed downstream as `<job>.output.<key>` (e.g. `meshio_output_dict.output.xdmf_file`) to wire a single dictionary entry into the next job's input.

# %%
import os

# %%
from jobflow import job, Flow

from python_workflow_definition.jobflow import write_workflow_json

# %%
from workflow import (
    generate_mesh as _generate_mesh,
    convert_to_xdmf as _convert_to_xdmf,
    poisson as _poisson,
    plot_over_line as _plot_over_line,
    substitute_macros as _substitute_macros,
    compile_paper as _compile_paper,
)

# %%
generate_mesh = job(_generate_mesh)
convert_to_xdmf = job(_convert_to_xdmf)
poisson = job(_poisson)
plot_over_line = job(_plot_over_line)
substitute_macros = job(_substitute_macros)
compile_paper = job(_compile_paper)

# %%
source_directory = os.path.abspath(os.path.join(os.curdir, "source"))

# %% [markdown]
# With `source_directory` and `domain_size` fixed, the calls below chain the six jobs together: mesh generation, XDMF conversion, the Poisson solve, line-plot postprocessing, LaTeX macro substitution and paper compilation. Each job runs in its own subdirectory and conda environment (see `source/envs/`), so what actually flows from one job to the next are file paths, not in-memory results.

# %%
domain_size = 2.0

# %%
gmsh_output_file = generate_mesh(
    domain_size=domain_size,
    source_directory=source_directory,
)

# %%
meshio_output_dict = convert_to_xdmf(
    gmsh_output_file=gmsh_output_file.output,
)

# %%
poisson_dict = poisson(
    meshio_output_xdmf=meshio_output_dict.output.xdmf_file,
    meshio_output_h5=meshio_output_dict.output.h5_file,
    source_directory=source_directory,
)

# %%
pvbatch_output_file = plot_over_line(
    poisson_output_pvd_file=poisson_dict.output.pvd_file,
    poisson_output_vtu_file=poisson_dict.output.vtu_file,
    source_directory=source_directory,
)

# %%
macros_tex_file = substitute_macros(
    pvbatch_output_file=pvbatch_output_file.output,
    ndofs=poisson_dict.output.numdofs,
    domain_size=domain_size,
    source_directory=source_directory,
)

# %%
paper_output = compile_paper(
    macros_tex=macros_tex_file.output,
    plot_file=pvbatch_output_file.output,
    source_directory=source_directory,
)

# %%
flow = Flow(
    [
        gmsh_output_file,
        meshio_output_dict,
        poisson_dict,
        pvbatch_output_file,
        macros_tex_file,
        paper_output,
    ]
)

# %% [markdown]
# The six jobs are collected into a `Flow`, which `write_workflow_json` then serializes to the PWD `workflow.json` format for the other engines to load.

# %%
workflow_json_filename = "jobflow_nfdi.json"

# %%
write_workflow_json(flow=flow, file_name=workflow_json_filename)

# %% [markdown]
# ## Load Workflow with aiida
#
# `load_workflow_json` rebuilds the pipeline as an `aiida-workgraph` `WorkGraph` from `jobflow_nfdi.json`, after connecting to a local AiiDA profile with `load_profile()`. `wg.run()` re-executes the whole pipeline under `aiida`.

# %%
from aiida import load_profile

load_profile()

# %%
from python_workflow_definition.aiida import load_workflow_json

# %%
wg = load_workflow_json(file_name=workflow_json_filename)
wg

# %%
wg.run()

# %% [markdown]
# ## Load Workflow with pyiron_base
#
# The same JSON is loaded into a list of delayed pyiron jobs; `.draw()` visualizes their dependencies and `.pull()` triggers execution, returning the final `paper.pdf` path.

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[-1].pull()

# %% [markdown]
# ## Load Workflow with pyiron_workflow
#
# Finally, the graph is loaded into a `pyiron_workflow` `Workflow`. `.draw()` shows the node graph and `.run()` executes it end to end.

# %%
from python_workflow_definition.pyiron_workflow import load_workflow_json

# %%
wf = load_workflow_json(file_name=workflow_json_filename)

# %%
wf.draw(size=(10, 10))

# %%
wf.run()
