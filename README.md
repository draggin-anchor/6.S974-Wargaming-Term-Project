# 6.S974 Wargaming Term Project

Term project for MIT 6.S974 / 2.S988 / 1.S980, *Games, Learning, and Security* (Fall 2026).

**Team:** Sean Bowman, Tate Murphy, Matthew Newell

## Project

A simulated game of maritime control in the East and South China Seas, played between US and
Chinese naval forces competing for control of contested waters (around Taiwan and the First
Island Chain) without escalating to war. Players allocate forces to areas and choose follow-on
actions (presence, surveillance, attack, retreat) under food, fuel and maintenance constraints.
See the proposal in `deliverables/` for the full model and literature.

## Layout

| Path | Contents |
| --- | --- |
| `deliverables/` | Submitted deliverables: `01-proposal.pdf`, `02-workshop1-report.pdf`, `02-workshop1-slides.pptx` |
| `prototype/` | Simulator and GUI (`wargame_gui.py`), experiment scripts, and all Workshop 1 results (`results/`); see `prototype/README.md` |
| `report/` | LaTeX source of the Workshop 1 report (`pdflatex report.tex`, twice) |
| `slides/` | Script that builds the Workshop 1 slides (`npm install && node build.js`) |
| `course-materials/` | Instructor handouts: wargame scope sheet and deliverable instructions |

## Reproducing the Workshop 1 results

```
cd prototype
python3 wargame_gui.py            # interactive GUI
python3 experiments.py all        # every table and figure in the report (needs gurobipy, matplotlib)
```
