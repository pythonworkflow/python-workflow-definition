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
# # pyiron
#
# https://github.com/BAMresearch/NFDI4IngScientificWorkflowRequirements
#
# This notebook defines the NFDI4Ing file-based workflow benchmark with [`pyiron_base`](https://github.com/pyiron/pyiron_base) and then loads the resulting `workflow.json` into `aiida`, `jobflow` and `pyiron_workflow`. Every stage of the pipeline shells out to an external command-line tool (`gmsh`, `meshio`, a FEniCS-based Poisson solver, ParaView's `pvbatch`, `tectonic`) in its own conda environment and passes file paths between stages rather than in-memory Python objects — see [`workflow.py`](workflow.py).

# %% [markdown]
# ## Define workflow with pyiron_base
#
# The `job` decorator turns a plain Python function into a delayed pyiron job. Since `convert_to_xdmf` and `poisson` return a `dict`, they are decorated with `output_key_lst=[...]` so each dictionary key becomes a separately addressable output (e.g. `meshio_output_dict.output.xdmf_file`) that can be wired into the next job's input.

# %%
import os

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
from pyiron_base import job

from python_workflow_definition.pyiron_base import write_workflow_json

# %%
generate_mesh = job(_generate_mesh)
convert_to_xdmf = job(_convert_to_xdmf, output_key_lst=["xdmf_file", "h5_file"])
poisson = job(_poisson, output_key_lst=["numdofs", "pvd_file", "vtu_file"])
plot_over_line = job(_plot_over_line)
substitute_macros = job(_substitute_macros)
compile_paper = job(_compile_paper)

# %%
domain_size = 2.0

# %%
source_directory = os.path.abspath(os.path.join(os.curdir, "source"))

# %% [markdown]
# The calls below chain the six jobs together: mesh generation, XDMF conversion, the Poisson solve, line-plot postprocessing, LaTeX macro substitution and paper compilation. Since each stage runs an external tool in its own conda environment (see `source/envs/`), what is actually passed between jobs are file paths, not in-memory Python values.

# %%
gmsh_output_file = generate_mesh(
    domain_size=domain_size,
    source_directory=source_directory,
)

# %%
meshio_output_dict = convert_to_xdmf(
    gmsh_output_file=gmsh_output_file,
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
    pvbatch_output_file=pvbatch_output_file,
    ndofs=poisson_dict.output.numdofs,
    domain_size=domain_size,
    source_directory=source_directory,
)

# %%
paper_output = compile_paper(
    macros_tex=macros_tex_file,
    plot_file=pvbatch_output_file,
    source_directory=source_directory,
)

# %% [markdown]
# Because pyiron builds a delayed call graph rather than an explicit `Flow`/`WorkGraph` object, `write_workflow_json` only needs the final delayed object (`paper_output`) — it walks the graph backwards to discover every upstream job.

# %%
workflow_json_filename = "pyiron_base_nfdi.json"

# %%
write_workflow_json(delayed_object=paper_output, file_name=workflow_json_filename)

# %% [markdown]
# ## Load Workflow with aiida
#
# `load_workflow_json` rebuilds the pipeline as an `aiida-workgraph` `WorkGraph` from `pyiron_base_nfdi.json`, after connecting to a local AiiDA profile with `load_profile()`. `wg.run()` re-executes the whole pipeline under `aiida`.

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
# ## Load Workflow with jobflow
#
# The same JSON is reconstructed as a jobflow `Flow` and executed locally with `run_locally`, independently of the `pyiron_base` objects used to define it.

# %%
from python_workflow_definition.jobflow import load_workflow_json

# %%
from jobflow.managers.local import run_locally

# %%
flow = load_workflow_json(file_name=workflow_json_filename)

# %%
result = run_locally(flow)
result

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
