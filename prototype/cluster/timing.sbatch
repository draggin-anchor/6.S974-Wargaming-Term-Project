#!/bin/bash
# Timing job for the multi-period best response: 15 games (3 setups x 5 seeds), one per task.
# Each game logs every solve to logs/timing_*.csv as it goes.
#   cd prototype && mkdir -p logs
#   sbatch --array=0-14 cluster/timing.sbatch
#   ~/wargame-env/bin/python cluster/timing.py summary
#SBATCH -J wgtiming
#SBATCH -p mit_normal
#SBATCH -c 1
#SBATCH --mem=4G
#SBATCH -t 12:00:00
#SBATCH -o logs/%x_%A_%a.out
module load miniforge 2>/dev/null || true
module load gurobi/13.0.2 2>/dev/null || true      # Engaging's Gurobi license (no 2,000-variable cap)
source ~/wargame-env/bin/activate
python3 cluster/timing.py $SLURM_ARRAY_TASK_ID
