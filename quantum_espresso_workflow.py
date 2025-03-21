import os
import subprocess

from ase.atoms import Atoms
from ase.build import bulk
from ase.io import write
from adis_tools.parsers import parse_pw
import matplotlib.pyplot as plt
import numpy as np
from optimade.adapters.structures.ase import from_ase_atoms, get_ase_atoms
from optimade.models.structures import StructureResourceAttributes, StructureResource


def write_input(input_dict, working_directory="."):
    filename = os.path.join(working_directory, "input.pwi")
    os.makedirs(working_directory, exist_ok=True)
    write(
        filename=filename,
        images=json_to_ase(atoms_json=input_dict["structure"]),
        Crystal=True,
        kpts=input_dict["kpts"],
        input_data={
            "calculation": input_dict["calculation"],
            "occupations": "smearing",
            "degauss": input_dict["smearing"],
        },
        pseudopotentials=input_dict["pseudopotentials"],
        tstress=True,
        tprnfor=True,
    )


def collect_output(working_directory="."):
    output = parse_pw(os.path.join(working_directory, "pwscf.xml"))
    return {
        "structure": ase_to_json(atoms=output["ase_structure"]),
        "energy": output["energy"],
        "volume": output["ase_structure"].get_volume(),
    }


def calculate_qe(working_directory, input_dict):
    write_input(
        input_dict=input_dict,
        working_directory=working_directory,
    )
    subprocess.check_output(
        "mpirun -np 1 pw.x -in input.pwi > output.pwo",
        cwd=working_directory,
        shell=True,
    )
    return collect_output(working_directory=working_directory)


def generate_structures(structure, strain_lst):
    structure_lst = []
    for strain in strain_lst:
        structure_strain = json_to_ase(atoms_json=structure)
        structure_strain.set_cell(
            structure_strain.cell * strain ** (1 / 3), scale_atoms=True
        )
        structure_lst.append(structure_strain)
    return {f"s_{i}": ase_to_json(atoms=s) for i, s in enumerate(structure_lst)}


def plot_energy_volume_curve(volume_lst, energy_lst):
    plt.plot(volume_lst, energy_lst)
    plt.xlabel("Volume")
    plt.ylabel("Energy")
    plt.savefig("evcurve.png")


def get_bulk_structure(element, a, cubic):
    ase_atoms = bulk(
        name=element,
        a=a,
        cubic=cubic,
    )
    return ase_to_json(atoms=ase_atoms)


def ase_to_json(atoms):
    struct_opt = from_ase_atoms(atoms=atoms)
    return json.dumps(struct_opt.model_dump(mode="json"))


def json_to_ase(atoms_json):
    structure_restore = StructureResourceAttributes.model_validate_json(atoms_json))
    return get_ase_atoms(optimade_structure=StructureResource(id="ase", attributes=structure_restore))
