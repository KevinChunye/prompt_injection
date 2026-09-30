# Kill-Chain Canaries: figures

The figures of the Kill-Chain Canaries paper, with the code that draws them.

| File (in `output/`) | Paper | What it shows | Built by |
|---|---|---|---|
| `figK1_same_score_different_story` | Fig. 1 (page-1 teaser) | Two same-model PDF-relay pipelines with the same 0/3 attack success; the canary token stops at different stages | `src/figK1.py` |
| `figK2_setup_channels_defenses` | Fig. 2 | Task, attacker payload, the attack surfaces (named as in the paper), where each defense looks, the single-agent `tool_poison` path | `src/figK2.py` |
| `figK3_where_it_stopped` | Fig. 3 | Last stage the canary token reached, per model (text relay; PDF relay, visible and white text) | `src/data_figs.py` |
| `figK4_surface_heatmap` | Fig. 4 | Attack success by model and attack surface, k/n with Wilson 95% CIs; headers give surface and scenario | `src/data_figs.py` |
| `figK5_relay_matrix` | Fig. 5 | Writer x reader pairs in the PDF relay; the caption carries the cross-model CIs (v3 Table 6) | `src/data_figs.py` |
| `figA_drift_top` | Fig. A1 | Objective drift: per-step trace and classifier feature importance (merges v3 Figs. 5 and 7) | `src/fig_drift.py` |

Each figure is saved as PDF (used by LaTeX), PNG (preview) and SVG (editable).
All figures are drawn at their printed width (`\textwidth` = 7.0 in, `\columnwidth` = 3.375 in),
so sizes in the source are sizes on paper. No text is smaller than 7.2 pt:
K1/K2 are 1400 px wide and printed at 0.36 bp/px, and `common.text_line` refuses anything
under 20 px; the matplotlib figures use 7.5 pt or larger.

## Rebuild

```
pip install -r requirements.txt
python build_all.py
```

- `cairosvg` needs the Cairo library. On macOS: `brew install cairo`.
- K1 and K2 use the Comic Neue font (in `fonts/`, SIL Open Font License, see `fonts/OFL.txt`).
  Install both `.ttf` files before rebuilding, or the SVG renderer falls back to a default font.
  The other figures use DejaVu Sans / DejaVu Sans Mono, which ship with matplotlib.

## Where the numbers come from

`src/paper_data.py` computes every plotted cell and checks it against the tables of
`../../main.tex`; `build_all.py` writes the report to `output/verification.txt`.

- `data/runs.csv`: the per-run log released with the paper, Hugging Face dataset
  `kevinwhc/kill-chain-canaries` (revision `9f816110eb3499b02983bd807f55d36eff692897`,
  sha256 `dde4f5f3d07079290e0199eb3b7c77701e08702ea1e6e110f29f1e0f1e4068cb`).
  Rows with `in_paper == True` give Tables 1, 2 and A1 and Figs. 3-4 (text surfaces).
- `data/pdf_relay_cells.csv`: per-cell counts of v3 Tables 5 and 6 (PDF relay; now Table 4 and
  the Fig. 5 caption). The per-run
  logs of the PDF relay experiment are not in this repository or the dataset, so these cells
  are transcribed from the tables of arXiv 2603.28013v3.
- Fig. A1: panel (a) reads Table 3 (per-step drift) from `main.tex`; panel (b) uses the
  importances printed on the v3 figure (`scripts/generate_figures.py`). The v3 drift-distribution
  violins are not reproduced: the per-run drift values are not in the released logs, so their
  per-violin run counts cannot be stated.
- `paper_data.text_facts()` recomputes every count the text quotes from the logs (no-tool-call
  runs, the 22 traced runs, the defense-ablation counts, the `multi_surface` footnote) and checks
  that the exact sentence appears in `main.tex`.

### Known log / table disagreements (reported by the verifier)

- Table A1 (v3 Table 3), GPT-5-mini `permission_esc`: the table says 1/36, the `in_paper` rows say 0/36
  (the only GPT-5-mini `permission_esc` success is in batch `high_n_v2`, `in_paper == False`).
  Table 1's GPT-5-mini 3% (1-7%) = 4/136 follows the table. The figures follow the table via
  `TABLE_OVERRIDES` in `src/paper_data.py`; delete that entry to plot the log value.
- Table 1, DeepSeek Chat: Wilson 95% CI for 17/68 is 16-36%; the table prints 16-37%.

## Layout

```
build_all.py         rebuild everything (and output/verification.txt)
src/paper_data.py    reads the result files, verifies against main.tex
src/common.py        drawing helpers (avatars, bubbles, tool cards, text measuring)
src/kc_common.py     kill-chain helpers (canary bird, PDF, memory, checkpoints, shields)
src/figK1.py         teaser
src/figK2.py         setup figure
src/data_figs.py     K3, K4, K5 (matplotlib)
src/fig_drift.py     appendix drift figure
data/                result files (see above)
fonts/               Comic Neue + license
output/              generated figures
```
