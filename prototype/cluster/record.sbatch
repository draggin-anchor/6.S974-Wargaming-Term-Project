#!/bin/bash
# Record MIP-BR decisions for the GUI on MIT Engaging (first REPLAY_SEEDS games of every MIP-BR setup).
# Each worker takes the next unrecorded game until none is left. Recordings go to results_w2/replays,
# so arrays on several partitions can run at the same time.
#   cd prototype && mkdir -p logs
#   sbatch --array=0-63 cluster/record.sbatch                                   # mit_normal
#   sbatch --array=0-199 -p mit_preemptable --requeue cluster/record.sbatch     # idle lab nodes
#   RESULTS=results_w2 python3 experiments.py plan                                                 # progress
#SBATCH -J wgrecord
#SBATCH -p mit_normal
#SBATCH -c 1
#SBATCH --mem=2G
#SBATCH -t 12:00:00
#SBATCH -o logs/%x_%A_%a.out
module load miniforge 2>/dev/null || true
source ~/wargame-env/bin/activate
export RESULTS=${RESULTS:-results_w2}
python3 experiments.py recorder
