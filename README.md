# 6.S974 Wargaming Term Project

Term project for MIT 6.S974 / 2.S988 / 1.S980, *Games, Learning, and Security* (Fall 2026).

**Team:** Sean Bowman, Tate Murphy, Matthew Newell

## Project

A simulated game of gray-zone maritime control in the East and South China Seas. Blue (US Navy
destroyers) and Red (Chinese Navy and coast guard) move ships between eight contested zones on a
network every two days and choose whether to patrol or assert. Control of a zone follows the local
force ratio; incidents between ships raise an escalation level whose top is war, which costs both
sides. Each side's allocation is solved as a mixed-integer program with an escalation-risk budget,
and weather (Nature) tests how robust each strategy and design is. The Workshop 1 report in
`deliverables/` has the full model, literature and results.

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
