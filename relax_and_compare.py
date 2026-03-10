#!/usr/bin/env python3
"""
Relax LLM-generated CIF structures and compare with CrystalFormer results.
"""

import os
import sys
import json
import bz2
import pandas as pd
import numpy as np
from pathlib import Path
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher

# Add crystal_gpt to path
sys.path.insert(0, '/opt/data/bcmdata/ZONES/home/PROJECTS/homefile/PRIVATE/osgood/Workspace/CSP/crystal_gpt')

def load_convex_hull(path):
    """Load convex hull data for E-hull calculation."""
    with bz2.open(path, 'rt') as f:
        return json.load(f)

def calculate_ehull(structure, energy, convex_hull_data):
    """Calculate energy above hull."""
    from pymatgen.entries.computed_entries import ComputedStructureEntry
    from pymatgen.analysis.phase_diagram import PhaseDiagram

    try:
        composition = structure.composition
        elements = [str(e) for e in composition.elements]

        # Get relevant entries from convex hull
        relevant_entries = []
        for entry_dict in convex_hull_data:
            entry_elements = set(entry_dict.get('elements', []))
            if entry_elements.issubset(set(elements)) or set(elements).issubset(entry_elements):
                from pymatgen.entries.computed_entries import ComputedEntry
                entry = ComputedEntry(
                    entry_dict['composition'],
                    entry_dict['energy'],
                )
                relevant_entries.append(entry)

        if not relevant_entries:
            return None

        # Add current structure entry
        current_entry = ComputedStructureEntry(structure, energy)
        relevant_entries.append(current_entry)

        # Build phase diagram
        pd = PhaseDiagram(relevant_entries)
        ehull = pd.get_e_above_hull(current_entry)

        return ehull
    except Exception as e:
        print(f"  E-hull calculation failed: {e}")
        return None

def relax_structure(structure, model_path):
    """Relax structure using ORB model."""
    try:
        from orb_models.forcefield import pretrained
        from orb_models.forcefield.calculator import ORBCalculator
        from ase.optimize import LBFGS
        from ase import Atoms
        from pymatgen.io.ase import AseAtomsAdaptor

        # Load model
        orbff = pretrained.orb_v3_conservative_inf_mpa(weights_path=model_path, device="cuda")
        calc = ORBCalculator(orbff, device="cuda")

        # Convert to ASE
        adaptor = AseAtomsAdaptor()
        atoms = adaptor.get_atoms(structure)
        atoms.calc = calc

        # Relax
        opt = LBFGS(atoms, logfile=None)
        opt.run(fmax=0.05, steps=100)

        # Get energy
        energy = atoms.get_potential_energy()

        # Convert back to pymatgen
        relaxed_structure = adaptor.get_structure(atoms)

        return relaxed_structure, energy
    except Exception as e:
        print(f"  Relaxation failed: {e}")
        return None, None

def process_cif_directory(cif_dir, model_path, convex_hull_path, output_csv):
    """Process all CIF files in a directory."""
    convex_hull_data = load_convex_hull(convex_hull_path)

    results = []
    cif_files = sorted(Path(cif_dir).glob("*.cif"))

    print(f"Processing {len(cif_files)} CIF files from {cif_dir}")

    for cif_file in cif_files:
        formula = cif_file.stem
        print(f"\nProcessing {formula}...")

        try:
            # Load structure
            structure = Structure.from_file(str(cif_file))
            print(f"  Loaded: {len(structure)} atoms, SG={structure.get_space_group_info()[1]}")

            # Relax
            relaxed_struct, energy = relax_structure(structure, model_path)

            if relaxed_struct is None:
                results.append({
                    'formula': formula,
                    'original_atoms': len(structure),
                    'relaxed': False,
                    'energy': None,
                    'ehull': None,
                    'original_spg': structure.get_space_group_info()[1],
                    'relaxed_spg': None
                })
                continue

            # Calculate E-hull
            ehull = calculate_ehull(relaxed_struct, energy, convex_hull_data)

            # Get space groups
            original_spg = structure.get_space_group_info()[1]
            try:
                relaxed_spg = relaxed_struct.get_space_group_info()[1]
            except:
                relaxed_spg = None

            energy_per_atom = energy / len(relaxed_struct) if energy else None
            ehull_per_atom = ehull if ehull else None

            print(f"  Relaxed: E={energy_per_atom:.4f} eV/atom, E-hull={ehull_per_atom}")
            print(f"  SPG: {original_spg} -> {relaxed_spg}")

            results.append({
                'formula': formula,
                'original_atoms': len(structure),
                'relaxed': True,
                'energy': energy_per_atom,
                'ehull': ehull_per_atom,
                'original_spg': original_spg,
                'relaxed_spg': relaxed_spg
            })

        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                'formula': formula,
                'original_atoms': None,
                'relaxed': False,
                'energy': None,
                'ehull': None,
                'original_spg': None,
                'relaxed_spg': None
            })

    # Save results
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"\nResults saved to {output_csv}")

    return df

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cif_dir', required=True, help='Directory containing CIF files')
    parser.add_argument('--model_path', default='./model/orb-v3-conservative-inf-mpa-20250404.ckpt')
    parser.add_argument('--convex_hull', default='./model/convex_hull_pbe.json.bz2')
    parser.add_argument('--output', required=True, help='Output CSV file')
    args = parser.parse_args()

    process_cif_directory(args.cif_dir, args.model_path, args.convex_hull, args.output)

if __name__ == '__main__':
    main()
