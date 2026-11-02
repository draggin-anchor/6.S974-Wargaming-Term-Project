# Running the experiments on MIT Engaging

Every game is independent, so the suite runs as many single-core jobs that share one game store
(`results_w2/games/`). Each job keeps taking the next unplayed game, headline setups first, and
skips games already stored, so jobs can be stopped, resubmitted, or run on several partitions at once.

Limits seen in October 2026: `mit_normal` 12 hours per job, about 64 cores per user.
`mit_preemptable` 2 days per job, on idle lab nodes (jobs may be stopped and requeued).

## One-time setup

Log in once at https://orcd-ood.mit.edu (MIT Kerberos). This creates the account, and it also covers
Duo for SSH for about a day. Then:

```
ssh KERB@orcd-login.mit.edu
git clone -b workshop2 https://github.com/draggin-anchor/6.S974-Wargaming-Term-Project.git ~/wargame
cd ~/wargame/prototype
bash cluster/setup.sh
```

The size-limited license that ships with gurobipy is enough for the 1-to-3 fleet, so no license file is needed.

## Before submitting: test the worker locally

Run two workers on a cheap setup, then read the store back. This catches bugs that would otherwise
crash every job after its first game.

```
RESULTS=/tmp/wt python3 -c "
import experiments as E
E.game_list = lambda: [('moderate', 'moderate', 'D0', 'nominal', 0.15, 0.15, s) for s in range(3)]
E.worker(); E.worker()
E.SEEDS = 3; print(E._run(('x', 'moderate', 'moderate', 'D0', 'nominal', 0.15, 0.15))['blue_mean'])"
rm -rf /tmp/wt
```

## Submit

```
cd ~/wargame/prototype
scancel -u $USER                       # only if an earlier run is still queued
rm -rf results_w2/games/claims         # after a scancel, or cancelled games stay blocked for 3 hours
git pull
mkdir -p logs
J1=$(sbatch --parsable --array=0-63 cluster/suite.sbatch)
J2=$(sbatch --parsable --array=0-63 --dependency=afterany:$J1 cluster/suite.sbatch)
sbatch --array=0-63 --dependency=afterany:$J2 cluster/suite.sbatch
sbatch --array=0-199 -p mit_preemptable --requeue cluster/suite.sbatch
```

The second and third `mit_normal` rounds start when the one before ends (12-hour limit).

To record MIP-BR decisions for the GUI instead of playing the suite, submit the same arrays with
`cluster/record.sbatch`.

## Progress and results

```
RESULTS=results_w2 ~/wargame-env/bin/python experiments.py plan    # RESULTS is needed, or it reads results/
squeue -u $USER | head
```

`logs/*.out` also holds logs of earlier, cancelled jobs, so check the job number before reading an error.
To bring the games back:

```
tar czf ~/w2games.tgz results_w2/games/*.csv results_w2/replays     # on Engaging
scp KERB@orcd-login.mit.edu:w2games.tgz ~/Desktop/                  # on the Mac
```

## How long it takes

The Workshop 2 suite (12,400 games, 200 per setup) ran on about 260 workers (64 on `mit_normal`,
the rest on `mit_preemptable`). It started at 11:15 PM and was complete by 9:44 AM the next morning.
About 1,000 games finished in the first 40 minutes. An Engaging node plays a year of MIP-BR against
MIP-BR in a few minutes, against 30 to 40 minutes on a 4-core cloud machine.
