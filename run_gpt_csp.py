"""
Ask GPT to generate CIF files for benchmark structures,
then compare with ground truth using pymatgen StructureMatcher.
"""
import os
import sys
import json
import time
import pandas as pd
import argparse
import logging
from ast import literal_eval
from tqdm import tqdm
from openai import OpenAI
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher, ElementComparator
from pymatgen.io.cif import CifParser
import io
import re
import traceback

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# ── API config ──────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE_URL", "https://luckyapi.chat/v1")
API_KEY = os.environ.get("API_KEY", "")
MODEL = "gemini-3-pro-preview-thinking"  # default, overridden by --model

# ── MP API config ───────────────────────────────────────────
MP_API_KEY = os.environ.get("MP_API_KEY", "")


def load_benchmark(path, dataset_id=None):
    """Load benchmark dataset, optionally filter by dataset id."""
    data = pd.read_pickle(path)
    if dataset_id is not None and 'dataset' in data.columns:
        data = data[data['dataset'] == dataset_id].reset_index(drop=True)
    entries = []
    for _, row in data.iterrows():
        sd = row['structure']
        if isinstance(sd, str):
            sd = literal_eval(sd)
        gt = Structure.from_dict(sd)
        entries.append({
            'formula': gt.reduced_formula,
            'composition': gt.composition.reduced_formula,
            'spg': row.get('space_group_num'),
            'n_atoms': len(gt),
            'gt_struct': gt,
        })
    return entries


def ask_gpt_for_cif(client, formula, model, n_atoms=None, simple=False):
    """Ask GPT to generate a CIF file for the given formula."""
    if simple:
        prompt = (
            f"Generate a CIF file for the most stable crystal structure of {formula}. "
            f"Use space group P1 (no symmetry operations). "
            f"List ALL atoms explicitly with their fractional coordinates. "
            f"Only include: data block, cell parameters, and atom_site loop "
            f"(label, type_symbol, fract_x, fract_y, fract_z). "
            f"No symmetry_equiv_pos, no occupancy, no other fields. "
            f"Output ONLY the CIF content between ```cif and ```."
        )
    else:
        hint = ""
        if n_atoms:
            hint = f" The conventional unit cell contains {n_atoms} atoms."
        prompt = (
            f"Generate a complete CIF (Crystallographic Information File) for the most stable "
            f"crystal structure of {formula}.{hint}\n"
            f"Output ONLY the CIF content between ```cif and ```. "
            f"Include all necessary fields: cell parameters, space group, "
            f"atom sites with fractional coordinates."
        )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert crystallographer. Generate accurate CIF files."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    return resp.choices[0].message.content


def parse_cif_from_response(text):
    """Extract CIF content from GPT response and parse to Structure."""
    # Try to extract from code block
    m = re.search(r'```(?:cif)?\s*\n(.*?)```', text, re.DOTALL)
    cif_text = m.group(1).strip() if m else text.strip()

    # Try pymatgen CifParser
    try:
        parser = CifParser(io.StringIO(cif_text))
        structs = parser.parse_structures(primitive=False)
        if structs:
            return structs[0], cif_text
    except Exception:
        pass

    # Fallback: try primitive=True
    try:
        parser = CifParser(io.StringIO(cif_text))
        structs = parser.parse_structures(primitive=True)
        if structs:
            return structs[0], cif_text
    except Exception:
        pass

    return None, cif_text


def get_mp_structure(formula):
    """Fetch ground truth structure from Materials Project."""
    try:
        from mp_api.client import MPRester
        with MPRester(MP_API_KEY) as mpr:
            docs = mpr.materials.summary.search(
                formula=formula,
                fields=["material_id", "structure", "energy_above_hull", "is_stable"]
            )
            if not docs:
                return None, None
            # Pick the most stable one
            docs_sorted = sorted(docs, key=lambda d: d.energy_above_hull if d.energy_above_hull is not None else 999)
            best = docs_sorted[0]
            return best.structure, best.material_id
    except Exception as e:
        logging.warning(f"MP lookup failed for {formula}: {e}")
        return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str,
                        default="/tmp/crystal_gpt/data/benchmark/Dataset_I_II_III_with_predictions.pd")
    parser.add_argument("--dataid", type=int, default=None,
                        help="Dataset id (1/2/3), None=all")
    parser.add_argument("--model", type=str, default=MODEL,
                        help="Model name to use")
    parser.add_argument("--output", type=str, default="/home/osgood/gptcsp/results")
    parser.add_argument("--simple-prompt", action="store_true",
                        help="Use simple prompt (formula only, no hints)")
    parser.add_argument("--use-mp", action="store_true",
                        help="Also compare with Materials Project structures")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Load benchmark
    entries = load_benchmark(args.dataset, args.dataid)
    logging.info(f"Loaded {len(entries)} benchmark entries")

    # Init OpenAI client
    client = OpenAI(base_url=API_BASE, api_key=API_KEY)

    # Init matcher (same as CrystalFormer-CSP paper)
    matcher = StructureMatcher(comparator=ElementComparator())

    model_name = args.model
    logging.info(f"Using model: {model_name}")

    results = []
    for entry in tqdm(entries, desc="Processing"):
        formula = entry['formula']
        gt_struct = entry['gt_struct']
        logging.info(f"\n{'='*50}\nProcessing: {formula} (SG: {entry['spg']}, atoms: {entry['n_atoms']})")

        row = {'formula': formula, 'spg': entry['spg'], 'n_atoms': entry['n_atoms'], 'model': model_name}

        # Ask GPT
        try:
            raw = ask_gpt_for_cif(client, formula, model_name, entry['n_atoms'], simple=args.simple_prompt)
            row['gpt_raw'] = raw
        except Exception as e:
            logging.error(f"GPT call failed for {formula}: {e}")
            row['gpt_raw'] = None
            row['gpt_match_gt'] = False
            row['parse_ok'] = False
            results.append(row)
            continue

        # Parse CIF
        pred_struct, cif_text = parse_cif_from_response(raw)
        row['cif_text'] = cif_text
        row['parse_ok'] = pred_struct is not None

        if pred_struct is None:
            logging.warning(f"Failed to parse CIF for {formula}")
            row['gpt_match_gt'] = False
            results.append(row)
            continue

        # Match vs ground truth from benchmark dataset
        try:
            row['gpt_match_gt'] = bool(matcher.fit(gt_struct, pred_struct))
        except Exception as e:
            logging.warning(f"Matcher failed for {formula}: {e}")
            row['gpt_match_gt'] = False

        # Optionally match vs MP
        if args.use_mp:
            mp_struct, mp_id = get_mp_structure(formula)
            row['mp_id'] = mp_id
            if mp_struct is not None:
                try:
                    row['gpt_match_mp'] = bool(matcher.fit(mp_struct, pred_struct))
                except Exception:
                    row['gpt_match_mp'] = False
            else:
                row['gpt_match_mp'] = None

        logging.info(f"  parse_ok={row['parse_ok']}, match_gt={row.get('gpt_match_gt')}")
        results.append(row)

        # Save CIF file
        cif_path = os.path.join(args.output, f"{formula}.cif")
        with open(cif_path, 'w') as f:
            f.write(cif_text)

        # Be polite to the API
        time.sleep(1)

    # ── Summary ─────────────────────────────────────────────
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(args.output, "gpt_csp_results.csv"), index=False)

    total = len(df)
    parsed = df['parse_ok'].sum()
    matched_gt = df['gpt_match_gt'].sum()

    print("\n" + "=" * 60)
    print("GPT CSP BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total structures:     {total}")
    print(f"CIF parsed OK:        {parsed}/{total} ({100*parsed/total:.1f}%)")
    print(f"Match ground truth:   {matched_gt}/{total} ({100*matched_gt/total:.1f}%)")

    if 'gpt_match_mp' in df.columns:
        mp_valid = df['gpt_match_mp'].notna().sum()
        mp_matched = df[df['gpt_match_mp'] == True].shape[0]
        print(f"Match MP (of found):  {mp_matched}/{mp_valid} ({100*mp_matched/mp_valid:.1f}%)" if mp_valid else "Match MP: no MP data")

    print("=" * 60)

    # Per-dataset breakdown if available
    if args.dataid is None:
        data_full = pd.read_pickle(args.dataset)
        formula_to_ds = {}
        for _, r in data_full.iterrows():
            sd = r['structure']
            if isinstance(sd, str):
                sd = literal_eval(sd)
            s = Structure.from_dict(sd)
            formula_to_ds[s.reduced_formula] = r['dataset']
        df['dataset'] = df['formula'].map(formula_to_ds)
        for ds in sorted(df['dataset'].dropna().unique()):
            sub = df[df['dataset'] == ds]
            m = sub['gpt_match_gt'].sum()
            print(f"  Dataset {int(ds)}: {m}/{len(sub)} ({100*m/len(sub):.1f}%)")


if __name__ == "__main__":
    main()
