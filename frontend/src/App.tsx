import React from "react";
import TableView, { PlayerView } from "./components/TableView";

/**
 * Static demo players (mirrors the Python demo).
 * Each player has name, stack and two hole cards represented as strings.
 */
const demoPlayers: PlayerView[] = [
  { name: "john", stack: 4000, holeCards: ["Ah", "Kd"] },
  { name: "mark", stack: 4000, holeCards: ["Qs", "Qs"] },
  { name: "alice", stack: 4000, holeCards: ["Tc", "9c"] },
  { name: "sara", stack: 4000, holeCards: ["7h", "7d"] },
  { name: "tom", stack: 4000, holeCards: ["As", "Kh"] },
  { name: "ryan", stack: 4000, holeCards: ["Jd", "Jh"] },
  { name: "mia", stack: 4000, holeCards: ["4s", "2s"] },
  { name: "liam", stack: 4000, holeCards: ["Kc", "Qc"] }
];

export default function App(): JSX.Element {
  return (
    <div className="app">
      <header>
        <h1>Jack of All Trades — Preflop Demo</h1>
        <p>8 players around the table — stacks and hole cards shown.</p>
      </header>

      <main>
        <TableView players={demoPlayers} />
      </main>

      <footer>
        <small>Demo — frontend only. Replace players with API data later.</small>
      </footer>
    </div>
  );
}
