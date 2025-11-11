# jack-of-all-trades
"Jack of All Trades" let you study most GTO (Game Theory Optimal) for popular deck oriented games.

## Backend demo API

A small Flask API simulates an 8-handed table (stacks, blinds, random hole cards) and exposes two endpoints:

- `GET /api/v1/table` — returns the live snapshot (table metadata, dealer/SB/BB positions, hand number, active seat, available actions, players, pot, call amount).
- `POST /api/v1/table/action` — applies an action for the current active player. Payload:
  ```json
  { "action": "fold" | "check" | "call" | "raise", "amount": 160 }
  ```
  The `amount` field is only required for `raise` and represents the total chips the player will have invested after the raise (as shown on the frontend slider).

Run the demo API from the repository root:

```bash
source .venv/bin/activate
python api.py
# or: python -m api
```

The API sends permissive CORS headers (`Access-Control-Allow-Origin: *`) so the frontend can call it directly during local development.

### Frontend demo (React + Vite)

In another terminal, run the Vite dev server so you can interact with the table UI and action panel:

```bash
source .venv/bin/activate  # optional, but keeps nodeenv/npm aligned if installed there
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 while the Flask API is running. The app automatically fetches snapshots from `GET /api/v1/table` and lets you fold/check/call/raise via `POST /api/v1/table/action`. Set `VITE_API_BASE_URL` in `frontend/.env` if your backend runs elsewhere.

### Smoke tests

Install Python requirements inside the virtual environment and run the pytest suite (using `python -m pytest` ensures the repository root is on `PYTHONPATH`):

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

## Branching & committing

Create focused branches (e.g., `agentic-review-poker`) for new work, commit with conventional messages, and push via:

```bash
git checkout -b agentic-review-poker
git add <files>
git commit -m "feat: describe change"
git push -u origin agentic-review-poker
```

Run `git status --short` frequently to review your working tree before committing.
