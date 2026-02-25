# LLM Crystal Structure Prediction Benchmark

Benchmarking frontier LLMs on crystal structure prediction (CSP): given a chemical formula, can an LLM generate a valid CIF file that matches the known ground truth structure?

Ground truth structures are from the [CrystalFormer-CSP](https://arxiv.org/abs/2512.18251) benchmark (Dataset I, 40 structures spanning 2–104 atoms per unit cell).

## Prompts

Two prompt strategies are tested. In both cases, the system message is:

```
You are an expert crystallographer. Generate accurate CIF files.
```

### Prompt 1: Default (model chooses CIF format freely)

```
Generate a complete CIF (Crystallographic Information File) for the most stable
crystal structure of {formula}. The conventional unit cell contains {n_atoms} atoms.
Output ONLY the CIF content between ```cif and ```.
Include all necessary fields: cell parameters, space group,
atom sites with fractional coordinates.
```

### Prompt 2: P1 (no symmetry operations, all atoms explicit)

```
Generate a CIF file for the most stable crystal structure of {formula}.
Use space group P1 (no symmetry operations).
List ALL atoms explicitly with their fractional coordinates.
Only include: data block, cell parameters, and atom_site loop
(label, type_symbol, fract_x, fract_y, fract_z).
No symmetry_equiv_pos, no occupancy, no other fields.
Output ONLY the CIF content between ```cif and ```.
```

## Evaluation

- **Parser**: `pymatgen.io.cif.CifParser`, trying `primitive=False` then `primitive=True`
- **Matcher**: `pymatgen.analysis.structure_matcher.StructureMatcher(comparator=ElementComparator())` with default tolerances (ltol=0.2, stol=0.3, angle_tol=5)
- **API**: All models accessed via OpenAI-compatible endpoint
- **Temperature**: 0.2, max_tokens: 4096

## Results

### Prompt 1: Default

| Model | CIF Parsed | Match Rate |
|-------|-----------|------------|
| gemini-3-pro-preview-thinking | 31/40 (77.5%) | 11/40 (27.5%) |
| claude-opus-4-6 | 35/40 (87.5%) | 11/40 (27.5%) |
| gpt-5-chat | 33/40 (82.5%) | 0/40 (0.0%) |

### Prompt 2: P1

| Model | CIF Parsed | Match Rate |
|-------|-----------|------------|
| gemini-3-pro-preview-thinking | 16/40 (40.0%) | 6/40 (15.0%) |
| claude-opus-4-6 | 28/40 (70.0%) | 6/40 (15.0%) |
| gpt-5-chat | 40/40 (100.0%) | 3/40 (7.5%) |

For comparison, [CrystalFormer-CSP](https://arxiv.org/abs/2512.18251) achieves 82.5% (w/o RL) and 95% (w/ RL) on the same dataset.

### Matched structures

**Prompt 1 (Default):**
- Gemini & Opus both match: GaAs, Bi2Te3, Ba(FeAs)2, ZrO2, LiFePO4
- Only Gemini: LiPF6, ZrTe5, Si3N4, ZnSb, Y2Co17, Cu12Sb4S13
- Only Opus: Si, ZnO, VO2, Al2O3, CaCO3, CoSb3

**Prompt 2 (P1):**
- All three models: Si, GaAs, ZnO
- Gemini & Opus additionally: BN, Ba(FeAs)2, ZrO2

### Key findings

1. **GPT-5-chat scores 0% with Prompt 1** due to generating incorrect symmetry operations in CIF files. The P1 prompt (Prompt 2) fixes parsing to 100% and reveals 7.5% match rate.
2. **Gemini and Opus have complementary knowledge** — they match 11/40 each but on different structures.
3. **No model matches structures with >32 atoms** in either prompt mode.
4. **Wrong polymorph selection** is common (e.g., all models generate cubic SrTiO3 instead of the tetragonal I4/mcm ground state).

## Usage

```bash
# Setup
uv venv .venv && source .venv/bin/activate
uv pip install pymatgen mp-api openai tqdm

# Set API credentials
export API_BASE_URL="https://your-api-endpoint/v1"
export API_KEY="your-api-key"

# Run benchmark (Prompt 1, Dataset I)
python run_llm_csp.py --dataid 1 --model <model-name> --output results/<model>

# Run benchmark (Prompt 2: P1, Dataset I)
python run_llm_csp.py --dataid 1 --simple-prompt --model <model-name> --output results/<model>_p1
```

## Reference

Cao, Ou & Wang, "CrystalFormer-CSP: Thinking Fast and Slow for Crystal Structure Prediction", [arXiv:2512.18251](https://arxiv.org/abs/2512.18251) (2024)
