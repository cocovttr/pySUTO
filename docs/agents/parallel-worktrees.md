# Parallel worktrees

Rules for an agent that works in its own git worktree (`.claude/worktrees/<name>`, a `feat/`, `fix/`
or `diag/` branch) while other agents or the maintainer use the main checkout. `<wt>` is the
worktree's absolute path, `<main>` the main checkout's.

## Environment

- Activate the `pysuto` env and give **every** `python`, `pytest`, `git commit` (the hook runs the
  suite) and notebook-kernel start an absolute `PYTHONPATH=<wt>/src`. The env's editable install
  points at `<main>`: without the prefix you import and test main's code. A relative path breaks
  as soon as the cwd changes.
- Never `pip install` into `pysuto`. Install and build tests go in a throwaway venv in the
  scratchpad, deleted afterwards.
- A worktree has no `data/proc`. A suite run there leaves gitignored files in the worktree's own
  `data/`: remove them before the next full run.
- Never edit, check out, merge or reset in `<main>` or in another worktree, and never push or tag.

## Pipeline runs

- Copper runs go to `<main>` only (`--data-dir <main>/data`), one at a time, under
  `<main>/data/proc/.stage.lock`; a held lock means wait, never delete it. Check `df -h` first.
- When the code may change during a run, run from a frozen copy: `git archive <rev> | tar -x -C
  <scratch>/frozen`, then drive that copy.
- A toy chain needs no `<main>` data: `python -m pysuto run --case toy --data-dir <scratch>`.
- A measurement is a run id and a number (CLAUDE.md, ADR 0028); report every run id created.

## Tutorial notebooks

- Notebook outputs change only through `scripts/refresh_tutorial.py`, which executes them and writes
  them free of home and temp paths. The kernel inherits the absolute `PYTHONPATH=<wt>/src`.
- `tests/test_tutorial_notebooks.py` checks the shipped notebooks statically; run it after any edit.

## Git

- Stage files by explicit path; never `git add -A`, never `data/`, `logs/`, `leg/`.
- Commit messages use no issue-closing keyword (the hook refuses them); write the message to a file
  and run `git commit -F <file>`.
- Merging a branch that untracks files deletes them from the receiving working tree: after such a
  merge, restore them from the parent commit (`git checkout <parent> -- <paths>`).

## Report

The last message is all the orchestrator sees, under 400 words: branch, commit hashes and files
changed; the test result line; run ids created and the bit-identity result with what was compared;
deviations from the ticket and why; open questions for the maintainer.
