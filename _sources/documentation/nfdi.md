# NFDI4Ing Benchmark
To demonstrate the compatibility of the Python Workflow Definition to file based workflows, the workflow benchmark
developed as part of [NFDI4Ing](https://www.inggrid.org/article/id/3726/) is implemented for all workflow engines
based on the Python Workflow Definition.

## Workflow
Unlike the [arithmetic](arithmetic.md) and energy-volume-curve examples, which pass Python objects between functions,
this benchmark chains together external command line tools that each require their own conda environment (defined in
`source/envs/*.yaml`) and communicate through files rather than in-memory values. The
pipeline is defined by six Python functions in [workflow.py](example_workflows/nfdi/workflow.py), each of which
copies its inputs into a stage-specific subdirectory (`preprocessing`, `processing` or `postprocessing`) and calls
its external tool with `conda_subprocess.check_output`:
```python
def generate_mesh(domain_size: float, source_directory: str) -> str: ...
def convert_to_xdmf(gmsh_output_file: str) -> dict: ...
def poisson(meshio_output_xdmf: str, meshio_output_h5: str, source_directory: str) -> dict: ...
def plot_over_line(poisson_output_pvd_file: str, poisson_output_vtu_file: str, source_directory: str) -> str: ...
def substitute_macros(pvbatch_output_file: str, ndofs: int, domain_size: float, source_directory: str) -> str: ...
def compile_paper(macros_tex: str, plot_file: str, source_directory: str) -> str: ...
```
* `generate_mesh` runs [`gmsh`](https://gmsh.info) on `unit_square.geo` to mesh a 2D square whose side length is set
  by the `domain_size` parameter, producing a `.msh` file.
* `convert_to_xdmf` runs `meshio convert` to turn the gmsh mesh into an XDMF/H5 file pair that the FEM solver can read.
* `poisson` runs a [FEniCS](https://fenicsproject.org)-based `poisson.py` script that solves the Poisson equation on
  the mesh, returning the number of degrees of freedom (`numdofs`) alongside the `.pvd`/`.vtu` result files.
* `plot_over_line` runs ParaView's `pvbatch` with `postprocessing.py` to sample the FEM solution along a line and
  write it out as a CSV file.
* `substitute_macros` runs `prepare_paper_macros.py` to fill a LaTeX macro template with the plot data path, the
  domain size and the number of degrees of freedom.
* `compile_paper` runs [`tectonic`](https://tectonic-typesetting.github.io) to compile `paper.tex`, which references
  those macros and the plot, into `paper.pdf`.

The connection of these Python functions is stored in the [workflow.json](example_workflows/nfdi/workflow.json)
JSON file, following the same `nodes`/`edges` structure as the other examples. Each function is a `function` node,
`domain_size` and `source_directory` are `input` nodes, and edges connect a function's input port either to another
function's output port or directly to an input node:
```
{
  "version": "0.1.0",
  "nodes": [
    {"id": 0, "type": "function", "value": "workflow.generate_mesh"},
    {"id": 1, "type": "function", "value": "workflow.convert_to_xdmf"},
    {"id": 6, "type": "input", "value": 2.0, "name": "domain_size"},
    {"id": 7, "type": "input", "value": "source", "name": "source_directory"},
    {"id": 8, "type": "output", "name": "result"}
  ],
  "edges": [
    {"target": 0, "targetPort": "domain_size", "source": 6, "sourcePort": null},
    {"target": 0, "targetPort": "source_directory", "source": 7, "sourcePort": null},
    {"target": 1, "targetPort": "gmsh_output_file", "source": 0, "sourcePort": null}
  ]
}
```
Since `convert_to_xdmf` and `poisson` return a `dict` instead of a single value, the edges that read their output
set `sourcePort` to the specific dictionary key (e.g. `"xdmf_file"` or `"numdofs"`) rather than `null`.

Because every stage shells out to a different external tool in a different conda environment and passes file paths
along the graph, this benchmark exercises a different part of the Python Workflow Definition than the arithmetic and
energy-volume-curve examples: it shows that the same `workflow.json` produced by one engine can be handed to another
engine, an execution manager like [CWL](https://www.commonwl.org)/`cwltool`, or plain Python, and still reproduce the
same chain of `gmsh`, `meshio`, FEniCS, `pvbatch` and `tectonic` calls end to end.
