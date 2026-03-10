#!/usr/bin/env python3
"""
Compare LLM CSP results with CrystalFormer results.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_crystalformer_results(benchmark_dir):
    """Load CrystalFormer benchmark results."""
    results_file = Path(benchmark_dir) / "benchmark_results.csv"
    if results_file.exists():
        df = pd.read_csv(results_file)
        return df
    return None

def load_llm_results(llm_dir):
    """Load LLM relaxed results."""
    results = {}
    relaxed_dir = Path(llm_dir) / "relaxed_results"

    for csv_file in relaxed_dir.glob("*_relaxed.csv"):
        model_name = csv_file.stem.replace("_relaxed", "")
        df = pd.read_csv(csv_file)
        results[model_name] = df

    return results

def compare_results(cf_results, llm_results, output_file):
    """Compare CrystalFormer and LLM results."""

    # Prepare comparison data
    comparison = []

    for _, cf_row in cf_results.iterrows():
        formula = cf_row['formula']

        row_data = {
            'formula': formula,
            'gt_spg': cf_row['space_group_num'],
            'cf_struct_match': '✓' if cf_row['struct_match'] == 1 else '✗',
            'cf_pred_spg': int(cf_row['pred_spg_num']) if pd.notna(cf_row['pred_spg_num']) else 'N/A',
            'cf_ehull': f"{cf_row['relaxed_ehull']:.4f}" if pd.notna(cf_row['relaxed_ehull']) else 'N/A',
        }

        # Add LLM results
        for model_name, llm_df in llm_results.items():
            llm_row = llm_df[llm_df['formula'] == formula]
            if len(llm_row) > 0:
                llm_row = llm_row.iloc[0]
                row_data[f'{model_name}_relaxed'] = '✓' if llm_row['relaxed'] else '✗'
                row_data[f'{model_name}_spg'] = int(llm_row['relaxed_spg']) if pd.notna(llm_row['relaxed_spg']) else 'N/A'
                row_data[f'{model_name}_ehull'] = f"{llm_row['ehull']:.4f}" if pd.notna(llm_row['ehull']) else 'N/A'
            else:
                row_data[f'{model_name}_relaxed'] = 'N/A'
                row_data[f'{model_name}_spg'] = 'N/A'
                row_data[f'{model_name}_ehull'] = 'N/A'

        comparison.append(row_data)

    df = pd.DataFrame(comparison)
    df.to_csv(output_file, index=False)

    # Print summary
    print("=" * 80)
    print("Comparison Summary")
    print("=" * 80)

    print(f"\nCrystalFormer (cfg_0.1 epoch_44000):")
    cf_match = (cf_results['struct_match'] == 1).sum()
    print(f"  Structure Match: {cf_match}/{len(cf_results)} ({cf_match/len(cf_results)*100:.1f}%)")

    for model_name, llm_df in llm_results.items():
        print(f"\n{model_name}:")
        relaxed = llm_df['relaxed'].sum()
        print(f"  Successfully Relaxed: {relaxed}/{len(llm_df)} ({relaxed/len(llm_df)*100:.1f}%)")

        # Count structures with low E-hull (< 0.1 eV/atom)
        low_ehull = (llm_df['ehull'].notna() & (llm_df['ehull'] < 0.1)).sum()
        print(f"  Low E-hull (<0.1 eV/atom): {low_ehull}/{len(llm_df)}")

    print(f"\nDetailed comparison saved to {output_file}")

    return df

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cf_dir', default='benchmark/K40_M500_X10000_cfg01_epoch44000_ds1_2026-03-04_223048',
                        help='CrystalFormer benchmark directory')
    parser.add_argument('--llm_dir', default='/home/user_osgood/Workspace/CSP/llm-csp-benchmark',
                        help='LLM benchmark directory')
    parser.add_argument('--output', default='comparison_cf_vs_llm.csv',
                        help='Output CSV file')
    args = parser.parse_args()

    print("Loading CrystalFormer results...")
    cf_results = load_crystalformer_results(args.cf_dir)

    print("Loading LLM results...")
    llm_results = load_llm_results(args.llm_dir)

    print(f"Found LLM models: {list(llm_results.keys())}")

    compare_results(cf_results, llm_results, args.output)

if __name__ == '__main__':
    main()
