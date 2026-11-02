#!/bin/bash
# Play the Workshop 2 learning games (learn_experiments.py) on MIT Engaging.  Every array task is
# one worker that keeps taking the next unplayed game until none is left.  Games are stored in
# results_w2/learning, so arrays on several partitions can run at the same time.
#   cd prototype && mkdir -p logs
#   sbatch --array=0-63 cluster/learn.sbatch                                   # mit_normal
#   sbatch --array=0-199 -p mit_preemptable --requeue cluster/learn.sbatch     # idle lab nodes
#   RESULTS=results_w2 python3 learn_experiments.py plan                       # progress
#SBATCH -J wglearn
#SBATCH -p mit_normal
#SBATCH -c 1
#SBATCH --mem=2G
#SBATCH -t 12:00:00
#SBATCH -o logs/%x_%A_%a.out
module load miniforge 2>/dev/null || true
source ~/wargame-env/bin/activate
export RESULTS=${RESULTS:-results_w2}
python3 learn_experiments.py worker
