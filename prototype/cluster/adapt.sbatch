#!/bin/bash
# Play the learning games against a Red that changes type mid-game (adapt_experiments.py) on MIT Engaging.  Every array task is one worker that keeps taking the next unplayed
# game until none is left.  Games are stored in results_w2/adapt, so arrays on several partitions can run
# at the same time.
#   cd prototype && mkdir -p logs
#   sbatch --array=0-63 cluster/adapt.sbatch                                   # mit_normal
#   sbatch --array=0-199 -p mit_preemptable --requeue cluster/adapt.sbatch     # idle lab nodes
#   RESULTS=results_w2 python3 adapt_experiments.py plan                                      # progress
#SBATCH -J wgadapt
#SBATCH -p mit_normal
#SBATCH -c 1
#SBATCH --mem=2G
#SBATCH -t 12:00:00
#SBATCH -o logs/%x_%A_%a.out
module load miniforge 2>/dev/null || true
source ~/wargame-env/bin/activate
export RESULTS=${RESULTS:-results_w2}
python3 adapt_experiments.py worker
