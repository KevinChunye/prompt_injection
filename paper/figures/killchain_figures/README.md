# Kill-Chain Canaries: figures

The figures of the Kill-Chain Canaries paper, with the code that draws them.

| File (in `output/`) | Paper | What it shows | Built by |
|---|---|---|---|
| `figK1_same_score_different_story` | Fig. 1 (page-1 teaser) | Two same-model PDF-relay pipelines with the same 0/3 attack success; the canary token stops at different stages | `src/figK1.py` |
| `figK2_setup_channels_defenses` | Fig. 2 | Task, attacker payload, where each channel enters, where each defense looks | `src/figK2.py` |
| `figU_utility_vs_asr` | Fig. 3 | Task success on clean runs vs attack success (panel (a) of the v3 figure) | `src/fig_utility.py` |
| `figK3_where_it_stopped` | Fig. 4 | Last stage the canary token reached, per model (text relay; PDF relay, visible and white text) | `src/data_figs.py` |
| `figK4_surface_heatmap` | Fig. 5 | Attack success by model and channel, k/n with Wilson 95% CIs | `src/data_figs.py` |
| `figK5_relay_matrix` | Fig. 6 | Writer x reader pairs in the PDF relay | `src/data_figs.py` |
| `figA_drift_top`, `figA_drift_violins` | Fig. A1 | Objective drift: per-step trace, classifier feature importance, drift distributions (merges v3 Figs. 5-7) | `src/fig_drift.py` |

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
  Rows with `in_paper == True` give Tables 1-3 and Figs. 3-5 (text surfaces).
- `data/pdf_relay_cells.csv`: per-cell counts of Tables 5 and 6 (PDF relay). The per-run
  logs of the PDF relay experiment are not in this repository or the dataset, so these cells
  are transcribed from the tables of arXiv 2603.28013v3.
- Fig. A1: panel (a) reads Table 4 from `main.tex`; panel (b) uses the importances printed on
  the v3 figure (`scripts/generate_figures.py`); panel (c) reuses the plot area of the v3 raster
  `data/v3_fig8_drift_distributions.png` (the per-run drift values are not released) under
  redrawn vector axes and legend. The v3 legend called the grey violins "Clean (no injection)";
  the script that drew them splits *attacked* runs by harmful action, and the new legend says so.

### Known log / table disagreements (reported by the verifier)

- Table 3, GPT-5-mini `permission_esc`: the table says 1/36, the `in_paper` rows say 0/36
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
src/fig_utility.py   task success vs attack success
src/fig_drift.py     appendix drift figure
data/                result files (see above)
fonts/               Comic Neue + license
output/              generated figures
```
