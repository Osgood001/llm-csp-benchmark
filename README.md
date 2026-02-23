# LLM Crystal Structure Prediction (CSP) Benchmark

Evaluating how well frontier LLMs can generate valid CIF files for crystal structures, compared against ground truth from the [CrystalFormer-CSP benchmark](https://arxiv.org/abs/2512.18251) (Dataset I, 40 structures).

## Setup

- **Matching**: `pymatgen.StructureMatcher(comparator=ElementComparator())` with default tolerances (ltol=0.2, stol=0.3, angle_tol=5)
- **Ground truth**: Benchmark dataset from CrystalFormer-CSP (Wang et al., 2024), same structures used in Tables 2-3 of the paper
- **API**: All models accessed via luckyapi.chat OpenAI-compatible endpoint

Two prompt strategies tested:
1. **Default prompt**: `"Generate a CIF file for {formula}."` — model chooses its own format
2. **P1 prompt**: Forces space group P1, all atoms explicit, no symmetry operations — avoids symmetry-related parse failures

## Results Summary

### Default Prompt (model chooses format)

| Model | CIF Parsed | Match Rate |
|-------|-----------|------------|
| gemini-3-pro-preview-thinking | 31/40 (77.5%) | 11/40 (27.5%) |
| claude-opus-4-6 | 35/40 (87.5%) | 11/40 (27.5%) |
| gpt-5-chat | 33/40 (82.5%) | 0/40 (0.0%) |

### P1 Prompt (no symmetry, all atoms explicit)

| Model | CIF Parsed | Match Rate |
|-------|-----------|------------|
| gemini-3-pro-preview-thinking | 16/40 (40.0%) | 6/40 (15.0%) |
| claude-opus-4-6 | 28/40 (70.0%) | 6/40 (15.0%) |
| gpt-5-chat | 40/40 (100.0%) | 3/40 (7.5%) |

P1 matched formulas (all 3 models agree on): Si, GaAs, ZnO, BN, Ba(FeAs)2, ZrO2 (Gemini/Opus); Si, GaAs, ZnO (GPT-5).

For comparison, **CrystalFormer-CSP** achieves **82.5%** (w/o RL) and **95%** (w/ RL) on this same dataset.

## Detailed Results (Dataset I)

| Formula | SG | Atoms | Gemini Parse | Gemini Match | Opus Parse | Opus Match | GPT-5 Parse | GPT-5 Match |
|---------|-----|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| C | 166 | 4 | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Si | 227 | 2 | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ |
| GaAs | 216 | 2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| ZnO | 186 | 4 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ |
| BN | 194 | 4 | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |
| LiCoO2 | 227 | 16 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| Bi2Te3 | 166 | 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Ba(FeAs)2 | 139 | 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| SiO2 | 122 | 6 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| VO2 | 136 | 6 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| La2CuO4 | 139 | 7 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| LiPF6 | 148 | 8 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| Al2O3 | 167 | 10 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ |
| SrTiO3 | 140 | 10 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| CaCO3 | 167 | 10 | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ |
| TiO2 | 12 | 12 | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| ZrO2 | 14 | 12 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| ZrTe5 | 63 | 12 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| V2O5 | 59 | 14 | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |
| Si3N4 | 176 | 14 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| Fe3O4 | 227 | 14 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| Mn(FeO2)2 | 227 | 14 | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |
| ZnSb | 61 | 16 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| CoSb3 | 204 | 16 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ |
| LiBF4 | 152 | 18 | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Y2Co17 | 166 | 19 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| GeH4 | 13 | 20 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| CsPbI3 | 62 | 20 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| NaCaAlPHO5F2 | 11 | 24 | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| LiFePO4 | 62 | 28 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Cu12Sb4S13 | 217 | 29 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| MgB7 | 74 | 32 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Li3PS4 | 62 | 32 | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Cd3As2 | 142 | 80 | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Li4Ti5O12 | 15 | 42 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Ba2CaSi4(BO7)2 | 121 | 46 | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Ag8GeS6 | 33 | 60 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| Nd2Fe14B | 136 | 68 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| Y3Al5O12 | 230 | 80 | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| Ca14MnSb11 | 142 | 104 | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |

For comparison, CrystalFormer-CSP achieves 82.5% (w/o RL) and 95% (w/ RL) on this same dataset.

## Analysis

### Prompt strategy tradeoff

The P1 prompt reveals a clear tradeoff:
- **GPT-5-chat benefits**: parse rate 82.5% → 100%, match rate 0% → 7.5%. Its symmetry operations were always wrong, so removing them helps.
- **Gemini/Opus hurt**: parse rates drop (77.5% → 40%, 87.5% → 70%), match rates drop (27.5% → 15%). These models generate reasonable symmetry operations, and forcing P1 means they must enumerate all atoms — which fails for structures with >14 atoms.

### Why GPT-5-chat scores 0% with default prompt

GPT-5-chat generates CIF files with **incorrect symmetry operations**. For example, for Si (Fd-3m, SG 227):
- Correct: 192 symmetry operations, 2 Wyckoff positions → 8 atoms in conventional cell
- GPT-5-chat: 24 operations (incomplete subset) → pymatgen builds 12 atoms → wrong structure → no match

### Common failure modes

1. **Wrong polymorph**: SrTiO3 ground truth is tetragonal I4/mcm (SG 140), but all models generate cubic Pm-3m (SG 221)
2. **Incomplete symmetry operations**: Models list partial symmetry ops for complex space groups
3. **Large unit cells**: No model matches any structure with >32 atoms in either prompt mode
4. **P1 atom enumeration**: When forced to list all atoms, models fail for structures with many atoms (>14)

### Complementary knowledge (default prompt)

Gemini and Opus both match 11/40 but different structures:
- **Both match**: GaAs, Bi2Te3, Ba(FeAs)2, ZrO2, LiFePO4
- **Only Gemini**: LiPF6, ZrTe5, Si3N4, ZnSb, Y2Co17, Cu12Sb4S13
- **Only Opus**: Si, ZnO, VO2, Al2O3, CaCO3, CoSb3

## Reproduction

```bash
# Install dependencies
uv venv .venv && source .venv/bin/activate
uv pip install pymatgen mp-api openai tqdm

# Run benchmark (simple prompt, Dataset I)
python run_gpt_csp.py --dataid 1 --simple-prompt --model <model-name> --output results_<model>
```

## Reference

Wang et al., "CrystalFormer-CSP: Thinking Fast and Slow for Crystal Structure Prediction", arXiv:2512.18251 (2024)
