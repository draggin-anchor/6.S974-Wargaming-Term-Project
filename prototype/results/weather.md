RQ3 robustness to weather: Blue policy vs Red mip_br (ε_R = 0.15), design D0. Entry: u_B / u_R / war rate. Scenario weights pi = {'calm': 0.25, 'nominal': 0.4, 'typhoon': 0.25, 'extreme': 0.1}. s.e. of u_B about 7

| Blue policy | calm | nominal | typhoon | extreme | Blue expected (Σ π_ω J) | Blue worst case (min_ω J) |
|---|---|---|---|---|---|---|
| moderate | -194 / 201 / 0.10 | -184 / 205 / 0.06 | -177 / 199 / 0.06 | -172 / 214 / 0.02 | -183 | -194 (calm) |
| greedy_br (ε=0.15) | -146 / 133 / 0.16 | -137 / 131 / 0.14 | -130 / 132 / 0.11 | -126 / 148 / 0.07 | -136 | -146 (calm) |
| mip_br (ε=0.05) | -316 / 324 / 0.11 | -303 / 315 / 0.11 | -298 / 313 / 0.10 | -270 / 311 / 0.05 | -302 | -316 (calm) |
| mip_br (ε=0.15) | -164 / 96 / 0.24 | -144 / 101 / 0.20 | -134 / 125 / 0.12 | -119 / 125 / 0.10 | -144 | -164 (calm) |
| mip_br (ε=0.4) | -98 / 12 / 0.29 | -83 / 16 / 0.25 | -73 / 28 / 0.20 | -65 / 59 / 0.12 | -82 | -98 (calm) |
| equilibrium | -126 / 109 / 0.15 | -116 / 113 / 0.10 | -120 / 121 / 0.11 | -100 / 143 / 0.03 | -118 | -126 (calm) |
| maximin | -219 / 237 / 0.04 | -221 / 227 / 0.08 | -222 / 231 / 0.07 | -210 / 249 / 0.03 | -220 | -222 (typhoon) |

Ranking of Blue policies by u_B in each scenario:
  calm: mip_br (ε=0.4) > equilibrium > greedy_br (ε=0.15) > mip_br (ε=0.15) > moderate > maximin > mip_br (ε=0.05)
  nominal: mip_br (ε=0.4) > equilibrium > greedy_br (ε=0.15) > mip_br (ε=0.15) > moderate > maximin > mip_br (ε=0.05)
  typhoon: mip_br (ε=0.4) > equilibrium > greedy_br (ε=0.15) > mip_br (ε=0.15) > moderate > maximin > mip_br (ε=0.05)
  extreme: mip_br (ε=0.4) > equilibrium > mip_br (ε=0.15) > greedy_br (ε=0.15) > moderate > maximin > mip_br (ε=0.05)
Ranking identical in every scenario: False
