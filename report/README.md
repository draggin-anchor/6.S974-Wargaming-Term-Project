# Workshop 1 report

`report.tex` is the main source. It includes `results.tex`, `results_rq3.tex`,
`prototype.tex`, and `plan.tex`, and uses the existing assets in `figures/`.

## Build

From this directory, run:

```text
tectonic --keep-logs report.tex
```

The revised deliverable was compiled with Tectonic 0.17.0. It has five content
pages followed by one reference page. Inspect pagination before replacing
`../deliverables/02-workshop1-report.pdf`, particularly after changing text or
using a different TeX engine. Conventional `pdflatex report.tex` (twice) remains
an alternative, but that engine's pagination has not been checked for this revision.

## Editorial and formulation refinements

- Place the network beside its introduction, add a notation table, separate
  zone values from other parameters, and label individual MIP constraints.
- Use a fleet movement budget instead of implying an explicit fuel inventory.
- Describe the implemented Bernoulli observations, last-seen state estimates,
  return priority, design costs, and penalized incident-risk slack.
- Scope best-response, equilibrium, repeated-game, and robustness claims to
  the specific surrogate, template game, or tested opponents.
- Correct mixed-equilibrium payoffs and report MIP risk violations using
  `prototype/results/chicken.md` and `prototype/results/gap.md`.
- Retain the existing simulation outputs. Full policy control/war-rate tables
  and design war rates remain in `prototype/results/`; the report emphasizes
  payoff tables and discusses the main control/war comparisons in the text.

The simulator and experiment outputs were not changed or rerun. Remaining
implementation questions, including prescribed versus executed return moves
when the movement cap binds, are disclosed as limitations and follow-up work.
