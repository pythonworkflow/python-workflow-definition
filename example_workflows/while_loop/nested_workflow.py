"""
Complex nested workflow example for geometry optimization.

This demonstrates a while loop with a nested workflow,
simulating an iterative geometry optimization algorithm.
"""


def not_converged(threshold, energy_change):
    """
    Check if the optimization has converged.

    Args:
        threshold: Convergence threshold for energy change
        energy_change: Change in energy from previous iteration

    Returns:
        bool: True if not converged (should continue)
    """
    return abs(energy_change) > threshold


def calculate_energy(structure):
    """
    Calculate the energy of a structure.

    This is a simplified placeholder for actual energy calculation.

    Args:
        structure: Structure data (e.g., atomic positions)

    Returns:
        float: Calculated energy
    """
    # Simplified energy calculation
    if isinstance(structure, dict) and "positions" in structure:
        positions = structure["positions"]
        # Simple harmonic potential around origin
        energy = sum(x**2 + y**2 + z**2 for x, y, z in positions)
        return energy
    return 0.0


def calculate_forces(structure, energy):
    """
    Calculate forces on atoms from energy.

    Args:
        structure: Structure data
        energy: Current energy

    Returns:
        dict: Forces on each atom
    """
    # Simplified force calculation (gradient of harmonic potential)
    if isinstance(structure, dict) and "positions" in structure:
        positions = structure["positions"]
        forces = [[-2*x, -2*y, -2*z] for x, y, z in positions]
        return {"forces": forces, "energy": energy}
    return {"forces": [], "energy": energy}


def update_geometry(structure, forces):
    """
    Update atomic positions based on forces.

    Args:
        structure: Current structure
        forces: Forces dict from calculate_forces

    Returns:
        dict: Updated structure with new positions
    """
    if isinstance(structure, dict) and "positions" in structure:
        positions = structure["positions"]
        force_vectors = forces["forces"]
        step_size = 0.1

        # Simple steepest descent update
        new_positions = [
            [x + step_size * fx, y + step_size * fy, z + step_size * fz]
            for (x, y, z), (fx, fy, fz) in zip(positions, force_vectors)
        ]

        return {
            "positions": new_positions,
            "atom_types": structure.get("atom_types", []),
        }
    return structure


def check_convergence(old_energy, new_structure):
    """
    Calculate energy change and check convergence.

    Args:
        old_energy: Energy from previous iteration
        new_structure: Updated structure

    Returns:
        dict: Contains new energy and energy change
    """
    new_energy = calculate_energy(new_structure)
    energy_change = new_energy - old_energy

    return {
        "energy": new_energy,
        "energy_change": energy_change,
        "structure": new_structure,
    }
