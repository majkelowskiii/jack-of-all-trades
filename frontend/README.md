# Frontend demo (React + TypeScript + Vite)

From the repo root:

cd frontend
npm install
npm run dev

Open http://localhost:5173

Notes:
- The app expects the Flask backend (`python api.py`) to be running on `http://localhost:5000`. Adjust `VITE_API_BASE_URL` in a `.env` file if you deploy elsewhere.
- Use the action panel to fold/check/call/raise for the active player; the UI stays in sync with responses from `GET /api/v1/table`.
- To build for production: `npm run build`
