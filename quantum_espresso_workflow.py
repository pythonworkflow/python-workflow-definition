import os
import subprocess

from ase.atoms import Atoms
from ase.build import bulk
from ase.io import write
from adis_tools.parsers import parse_pw
import matplotlib.pyplot as plt
import numpy as np


def write_input(input_dict, working_directory="."):
    filename = os.path.join(working_directory, "input.pwi")
    os.makedirs(working_directory, exist_ok=True)
    write(
        filename=filename,
        images=Atoms(**input_dict["structure"]),
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
        "structure": atoms_to_json_dict(atoms=output["ase_structure"]),
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
        structure_strain = Atoms(**structure)
        structure_strain.set_cell(
            structure_strain.cell * strain ** (1 / 3), scale_atoms=True
        )
        structure_lst.append(structure_strain)
    return {f"s_{i}": atoms_to_json_dict(atoms=s) for i, s in enumerate(structure_lst)}


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
    return atoms_to_json_dict(atoms=ase_atoms)


def atoms_to_json_dict(atoms):
    """
    Convert an ASE Atoms object to a fully JSON-serializable dictionary
    that uses only Python base data types.

    Parameters:
    -----------
    atoms : ase.Atoms
        The Atoms object to convert

    Returns:
    --------
    dict
        A dictionary representation using only Python base types
    """
    # Get the dictionary representation from ASE
    atoms_dict = atoms.todict()

    # Create a new dictionary with JSON-serializable values
    json_dict = {}

    # Convert numpy arrays to lists
    for key, value in atoms_dict.items():
        if isinstance(value, np.ndarray):
            # Convert numpy boolean values to Python booleans
            if value.dtype == np.bool_ or value.dtype == bool:
                json_dict[key] = value.tolist()
            # Convert numpy arrays of numbers to Python lists
            else:
                json_dict[key] = value.tolist()
        else:
            json_dict[key] = value

    return json_dict
