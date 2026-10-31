#!/bin/bash
# One-time setup on MIT Engaging (run on a login node from the repo's prototype/ folder):
# a Python environment with gurobipy.  The size-limited license that ships with gurobipy is
# enough for the 1-to-3 fleet, so no license file is needed.
set -e
module load miniforge 2>/dev/null || true
python3 -m venv ~/wargame-env
~/wargame-env/bin/pip install --quiet --upgrade pip gurobipy
~/wargame-env/bin/python -c "import gurobipy; print('gurobipy', gurobipy.gurobi.version())"
