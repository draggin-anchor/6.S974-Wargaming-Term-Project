Greedy heuristic vs exact MIP, 1524 Blue decisions in 30 games (mip_br vs mip_br, nominal weather):
  greedy plan optimal (within 1e-6) in 1026/1524 decisions (67%)
  mean objective loss 0.467 (total loss / total |MIP objective| = 8.5%), max 13.354
  among the 1316 greedy plans that respect the risk budget: mean loss 0.134, greedy optimal in 984
  risk-budget violations: greedy 208/1524, MIP 37/1524 (MIP only when forced returns alone exceed eps)
  decisions where greedy scored higher than the MIP: 125 (it can only do so by exceeding the risk budget)
