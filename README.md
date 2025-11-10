# jack-of-all-trades
"Jack of All Trades" let you study most GTO (Game Theory Optimal) for popular deck oriented games.

## Backend demo API

A small demo API is provided to serve the table snapshot (8 players, blinds posted and hole cards dealt).

Run the demo API from the repository root:

```bash
python api.py
# or: python -m api
```

The endpoint (single snapshot) is:

GET http://localhost:5000/api/v1/table

It returns JSON with table info, positions, and each player's seat/name/stack/hole_cards. The response includes an Access-Control-Allow-Origin: * header to allow the frontend demo to fetch it locally.

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
