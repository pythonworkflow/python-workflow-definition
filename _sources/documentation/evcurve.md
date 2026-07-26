# Energy Volume Curve
Based on [previous work](https://materialdigital.github.io/ADIS2023/README.html) from the [ADIS 2023 workshop](https://www.mpie.de/4902385/adis2023)
the calculation of an energy volume curve with the [quantum espresso](https://www.quantum-espresso.org) density 
functional theory (DFT) simulation code is implemented in the Python Workflow Definition.

## Workflow
An energy-volume curve is computed by relaxing a bulk crystal structure, straining it to a series of volumes and
computing the total energy at each volume with a self-consistent-field (SCF) calculation. The pipeline is implemented
as five Python functions in [workflow.py](example_workflows/quantum_espresso/workflow.py):
```python
def get_bulk_structure(element, a, cubic):
    # build an ASE bulk crystal structure, e.g. Al

def calculate_qe(working_directory, input_dict):
    # write a pw.x input file, run "pw.x -in input.pwi > output.pwo" and parse the pwscf.xml output;
    # input_dict["calculation"] selects "vc-relax" (cell + geometry relaxation) or "scf" (single-point energy)

def generate_structures(structure, strain_lst):
    # apply each volumetric strain in strain_lst to a structure, returning one structure per strain

def plot_energy_volume_curve(volume_lst, energy_lst):
    # plot energy against volume and save it as evcurve.png
```
`write_input`/`collect_output` handle the file-based `pw.x` input/output (`.pwi`/`.pwo`/`.xml` files), and
`ase_to_json`/`json_to_ase` (de)serialize ASE `Atoms` objects to/from OPTIMADE-JSON strings, so structures can be
passed between functions as plain JSON data instead of Python objects.

The workflow combines these functions as: `get_bulk_structure` -> `calculate_qe` (`vc-relax`, once) -> 
`generate_structures` -> `calculate_qe` (`scf`, once per strained structure) -> `plot_energy_volume_curve`. With five
strains this means one relaxation followed by five independent SCF calculations that fan out from
`generate_structures` and feed back into a single plot.

## workflow.json
[workflow.json](example_workflows/quantum_espresso/workflow.json) encodes this fan-out as five separate
`workflow.calculate_qe` function nodes, each connected to its own strained structure and its own `working_directory`
input, all reading the same shared inputs (`pseudopotentials`, `kpts`, `calculation`, `smearing`) via
`python_workflow_definition.shared.get_dict`. An excerpt showing the pattern for two of the five strained
calculations:
```
{
  "nodes": [
    {"id": 2, "type": "function", "value": "workflow.generate_structures"},
    {"id": 3, "type": "function", "value": "workflow.calculate_qe"},
    {"id": 4, "type": "function", "value": "workflow.calculate_qe"},
    {"id": 19, "type": "input", "value": "strain_0", "name": "working_directory_1"},
    {"id": 20, "type": "function", "value": "python_workflow_definition.shared.get_dict"},
    {"id": 22, "type": "input", "value": "strain_1", "name": "working_directory_2"},
    {"id": 23, "type": "function", "value": "python_workflow_definition.shared.get_dict"}
  ],
  "edges": [
    {"target": 3, "targetPort": "working_directory", "source": 19, "sourcePort": null},
    {"target": 20, "targetPort": "structure", "source": 2, "sourcePort": "s_0"},
    {"target": 3, "targetPort": "input_dict", "source": 20, "sourcePort": null},
    {"target": 4, "targetPort": "working_directory", "source": 22, "sourcePort": null},
    {"target": 23, "targetPort": "structure", "source": 2, "sourcePort": "s_1"},
    {"target": 4, "targetPort": "input_dict", "source": 23, "sourcePort": null}
  ]
}
```
Node 2 (`generate_structures`) exposes one output port per strain (`s_0`, `s_1`, ...); each port is wired into its
own `get_dict`/`calculate_qe` pair. The energy and volume outputs of all five `calculate_qe` nodes are collected back
into lists with `python_workflow_definition.shared.get_list` before being passed to `plot_energy_volume_curve`.

## Requirements
Running this workflow (rather than just loading/inspecting the JSON) requires the Quantum Espresso `pw.x` binary,
matching pseudopotential files (see [espresso/pseudo](example_workflows/quantum_espresso/espresso/pseudo)) and the
Python dependencies listed in [environment.yml](example_workflows/quantum_espresso/environment.yml).