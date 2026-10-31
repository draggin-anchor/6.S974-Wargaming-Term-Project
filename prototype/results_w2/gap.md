Greedy heuristic vs exact MIP, 4537 Blue decisions in 30 games (mip_br vs mip_br, nominal weather):
  greedy plan optimal (within 1e-6) in 1101/4537 decisions (24%)
  mean objective loss 0.376 (total loss / total |MIP objective| = 5.8%), max 16.331
  among the 4042 greedy plans that respect the risk budget: mean loss 0.216, greedy optimal in 923
  risk-budget violations: greedy 495/4537, MIP 147/4537 (MIP only when forced returns alone exceed eps)
  decisions where greedy scored higher than the MIP: 561 (it can only do so by exceeding the risk budget)
