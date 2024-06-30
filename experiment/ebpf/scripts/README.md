# Scripts

 - [targeted-time.py](targeted-time.py): the final set of relevant kprobes, in groups of ~400 for lammps
 - [time-before-calls.py](time-before-calls.py) subprocess to get a PID THEN compile program. I was worried about missing kprobes.
 - [time-calls.py](time-calls.py) the initial script when I was exploring. 
 - [plot-results.py](plot-results.py) early plotting of stuff, will be expanded.
 
The following were the more finalized variants:

 - [determine-kprobes](determine-kprobes.py) is a semi-automated, logical filtering process to determine kprobes of interest for a program.
 - [wrapped-time.py](wrapped-time.py) is an updated targeted-time.py to take in input files and run a full experiment.

