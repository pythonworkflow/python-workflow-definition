# %%
from python_workflow_definition.aiida import write_workflow_json, construct_wg_qe
from python_workflow_definition.pyiron_base import load_workflow_json
from pyiron_base import Project

from aiida import load_profile

load_profile()

workflow_json_filename = "workflow_qe_aiida.json"

from aiida_workgraph import WorkGraph, task
from typing import Any

from quantum_espresso_workflow import generate_structures as _generate_structures
from quantum_espresso_workflow import get_bulk_structure as _get_bulk_structure
from quantum_espresso_workflow import calculate_qe as _calculate_qe
from quantum_espresso_workflow import (
    plot_energy_volume_curve as _plot_energy_volume_curve,
)

from python_workflow_definition.aiida import pickle_node, construct_wg_qe

load_profile()

get_bulk_structure = task.pythonjob(outputs=["structure"])(_get_bulk_structure)
generate_structures = task.pythonjob()(_generate_structures)
calculate_qe = task.pythonjob(outputs=["energy", "volume", "structure"])(_calculate_qe)
plot_energy_volume_curve = task.pythonjob()(_plot_energy_volume_curve)

strain_lst = [0.9, 0.95, 1.0, 1.05, 1.1]

wg = construct_wg_qe(
    get_bulk_structure=get_bulk_structure,
    calculate_qe=calculate_qe,
    generate_structures=generate_structures,
    plot_energy_volume_curve=plot_energy_volume_curve,
    strain_lst=strain_lst,
)

# raise SystemExit()

# %%

write_workflow_json(wg=wg, file_name=workflow_json_filename)
wg.to_html('workflow_qe_aiida.html')

wg.run()

# %%

pr = Project("test")
pr.remove_jobs(recursive=True, silently=True)


delayed_object = load_workflow_json(project=pr, file_name=workflow_json_filename)
delayed_object.draw()


delayed_object.pull()
