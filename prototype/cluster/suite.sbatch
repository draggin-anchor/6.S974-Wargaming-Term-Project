#!/bin/bash
# Play the experiment suite on MIT Engaging.  Every array task is one worker that keeps taking
# the next unplayed game (headline setups first) until none is left; workers share the game
# store in results_w2/games, so arrays on several partitions can run at the same time.
#   cd prototype && mkdir -p logs
#   sbatch --array=0-63 cluster/suite.sbatch                                   # mit_normal
#   sbatch --array=0-199 -p mit_preemptable --requeue cluster/suite.sbatch     # idle lab nodes
#   python3 experiments.py plan                                                 # progress
#SBATCH -J wargame
#SBATCH -p mit_normal
#SBATCH -c 1
#SBATCH --mem=2G
#SBATCH -t 12:00:00
#SBATCH -o logs/%x_%A_%a.out
module load miniforge 2>/dev/null || true
source ~/wargame-env/bin/activate
export RESULTS=${RESULTS:-results_w2}
python3 experiments.py worker
