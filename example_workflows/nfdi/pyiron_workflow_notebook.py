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
# This notebook defines the NFDI4Ing file-based workflow benchmark with [`pyiron_workflow`](https://github.com/pyiron/pyiron_workflow) and then loads the resulting `workflow.json` into `aiida`, `jobflow` and `pyiron_base`. Every stage of the pipeline shells out to an external command-line tool (`gmsh`, `meshio`, a FEniCS-based Poisson solver, ParaView's `pvbatch`, `tectonic`) in its own conda environment and passes file paths between stages rather than in-memory Python objects — see [`workflow.py`](workflow.py).

# %% [markdown]
# ## Define workflow with pyiron_workflow
#
# `to_function_node` wraps each plain Python function into a `pyiron_workflow` node; the three arguments are the node's registered class name, the function itself, and the name of its (single, unlabeled) output. Nodes are assembled into a graph by assigning them as attributes of a `Workflow` object (`wf.<name> = node(...)`), and dictionary outputs such as `convert_to_xdmf`'s are indexed with `wf.meshio_output_dict["xdmf_file"]` when wiring the next node's input.

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
from pyiron_workflow._legacy import Workflow, to_function_node

from python_workflow_definition.pyiron_workflow import write_workflow_json

# %%
generate_mesh = to_function_node("generate_mesh", _generate_mesh, "generate_mesh")
convert_to_xdmf = to_function_node(
    "convert_to_xdmf", _convert_to_xdmf, "convert_to_xdmf"
)
poisson = to_function_node("poisson", _poisson, "poisson")
plot_over_line = to_function_node("plot_over_line", _plot_over_line, "plot_over_line")
substitute_macros = to_function_node(
    "substitute_macros", _substitute_macros, "substitute_macros"
)
compile_paper = to_function_node("compile_paper", _compile_paper, "compile_paper")

# %%
wf = Workflow("my_workflow")

# %%
wf.domain_size = 2.0

# %%
wf.source_directory = os.path.abspath(os.path.join(os.curdir, "source"))

# %% [markdown]
# The assignments below build the six-stage pipeline as attributes of `wf`: mesh generation, XDMF conversion, the Poisson solve, line-plot postprocessing, LaTeX macro substitution and paper compilation. Each stage runs an external tool in its own conda environment (see `source/envs/`), so the values connecting them are file paths on disk rather than shared Python objects.

# %%
wf.gmsh_output_file = generate_mesh(
    domain_size=wf.domain_size,
    source_directory=wf.source_directory,
)

# %%
wf.meshio_output_dict = convert_to_xdmf(
    gmsh_output_file=wf.gmsh_output_file,
)

# %%
wf.poisson_dict = poisson(
    meshio_output_xdmf=wf.meshio_output_dict["xdmf_file"],
    meshio_output_h5=wf.meshio_output_dict["h5_file"],
    source_directory=wf.source_directory,
)

# %%
wf.pvbatch_output_file = plot_over_line(
    poisson_output_pvd_file=wf.poisson_dict["pvd_file"],
    poisson_output_vtu_file=wf.poisson_dict["vtu_file"],
    source_directory=wf.source_directory,
)

# %%
wf.macros_tex_file = substitute_macros(
    pvbatch_output_file=wf.pvbatch_output_file,
    ndofs=wf.poisson_dict["numdofs"],
    domain_size=wf.domain_size,
    source_directory=wf.source_directory,
)

# %%
wf.paper_output = compile_paper(
    macros_tex=wf.macros_tex_file,
    plot_file=wf.pvbatch_output_file,
    source_directory=wf.source_directory,
)

# %% [markdown]
# `wf.draw()` renders the assembled node graph; `wf.graph_as_dict` is then handed to `write_workflow_json`, which serializes it into the PWD `workflow.json` format for the other engines to load.

# %%
wf.draw(size=(10, 10))

# %%
workflow_json_filename = "pyiron_workflow_nfdi.json"

# %%
write_workflow_json(graph_as_dict=wf.graph_as_dict, file_name=workflow_json_filename)

# %% [markdown]
# ## Load Workflow with aiida
#
# `load_workflow_json` rebuilds the pipeline as an `aiida-workgraph` `WorkGraph` from `pyiron_workflow_nfdi.json`, after connecting to a local AiiDA profile with `load_profile()`. `wg.run()` re-executes the whole pipeline under `aiida`.

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
# The same JSON is reconstructed as a jobflow `Flow` and executed locally with `run_locally`, independently of the `pyiron_workflow` objects used to define it.

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
# ## Load Workflow with pyiron_base
#
# Finally, the graph is loaded into a list of delayed `pyiron_base` jobs. `.draw()` visualizes the dependency chain and `.pull()` triggers execution, returning the final `paper.pdf` path.

# %%
from python_workflow_definition.pyiron_base import load_workflow_json

# %%
delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
delayed_object_lst[-1].draw()

# %%
delayed_object_lst[-1].pull()

# %%
