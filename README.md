# jack-of-all-trades
"Jack of All Trades" let you study most GTO (Game Theory Optimal) for popular deck oriented games.

## Branching & committing

To create a dedicated branch for the poker import/type fixes and push it to the remote, run the following from the repository root:

```bash
# inspect working tree
git status --porcelain

# create branch, stage and commit current changes
git checkout -b "Agentic Review Poker"
git add .
git commit -m "chore(poker): fix circular imports using type-only annotations and relative imports"

# push branch and set upstream
git push -u origin "Agentic Review Poker"
```

If you prefer to keep commits atomic, run `git add` only for specific files and repeat `git commit` with focused messages.
