RQ3 robustness to weather: Blue policy vs Red mip_br (ε_R = 0.15), design D0. Entry: u_B / u_R / war rate. Scenario weights pi = {'calm': 0.25, 'nominal': 0.4, 'typhoon': 0.25, 'extreme': 0.1}. s.e. of u_B about 9

| Blue policy | calm | nominal | typhoon | extreme | Blue expected (Σ π_ω J) | Blue worst case (min_ω J) |
|---|---|---|---|---|---|---|
| moderate | -746 / 732 / 0.14 | -713 / 708 / 0.12 | -660 / 687 / 0.09 | -614 / 687 / 0.03 | -698 | -746 (calm) |
| greedy_br (ε=0.15) | -518 / 499 / 0.20 | -501 / 494 / 0.16 | -494 / 507 / 0.13 | -472 / 515 / 0.08 | -500 | -518 (calm) |
| mip_br (ε=0.05) | -1056 / 1175 / 0.03 | -1022 / 1143 / 0.01 | -946 / 1052 / 0.03 | -852 / 972 / 0.01 | -994 | -1056 (calm) |
| mip_br (ε=0.15) | -458 / 382 / 0.34 | -430 / 385 / 0.26 | -399 / 372 / 0.21 | -366 / 376 / 0.16 | -423 | -458 (calm) |
| mip_br (ε=0.4) | 52 / -74 / 0.22 | 20 / -50 / 0.22 | -38 / 10 / 0.22 | -88 / 95 / 0.15 | 3 | -88 (extreme) |
| equilibrium | -733 / 745 / 0.12 | -718 / 745 / 0.08 | -721 / 747 / 0.12 | -706 / 791 / 0.02 | -722 | -733 (calm) |
| maximin | -714 / 710 / 0.12 | -710 / 729 / 0.08 | -709 / 740 / 0.09 | -694 / 754 / 0.07 | -709 | -714 (calm) |

Ranking of Blue policies by u_B in each scenario:
  calm: mip_br (ε=0.4) > mip_br (ε=0.15) > greedy_br (ε=0.15) > maximin > equilibrium > moderate > mip_br (ε=0.05)
  nominal: mip_br (ε=0.4) > mip_br (ε=0.15) > greedy_br (ε=0.15) > maximin > moderate > equilibrium > mip_br (ε=0.05)
  typhoon: mip_br (ε=0.4) > mip_br (ε=0.15) > greedy_br (ε=0.15) > moderate > maximin > equilibrium > mip_br (ε=0.05)
  extreme: mip_br (ε=0.4) > mip_br (ε=0.15) > greedy_br (ε=0.15) > moderate > maximin > equilibrium > mip_br (ε=0.05)
Ranking identical in every scenario: False
