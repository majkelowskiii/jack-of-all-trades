import React, { useEffect, useState } from "react";
import TableView, { PlayerView } from "./components/TableView";

type ApiPlayer = {
  seat: number;
  name: string;
  stack: number;
  hole_cards: string[];
  in_hand: boolean;
  player_bet: number;
};

type TableSnapshot = {
  name: string;
  dealer_position: number | null;
  sb: { seat: number; name: string | null } | null;
  bb: { seat: number; name: string | null } | null;
  players: ApiPlayer[];
  pot: number;
  call_amount: number;
};

type TableState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: TableSnapshot };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";
const TABLE_ENDPOINT = `${API_BASE_URL}/api/v1/table`;

function mapPlayers(snapshot: TableSnapshot): PlayerView[] {
  return snapshot.players.map((player) => {
    let role: PlayerView["role"];
    if (snapshot.dealer_position === player.seat) {
      role = "D";
    } else if (snapshot.sb?.seat === player.seat) {
      role = "SB";
    } else if (snapshot.bb?.seat === player.seat) {
      role = "BB";
    }

    return {
      name: player.name ?? `seat-${player.seat}`,
      stack: player.stack,
      holeCards: player.hole_cards,
      role
    };
  });
}

export default function App(): JSX.Element {
  const [state, setState] = useState<TableState>({ status: "loading" });

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function loadTable() {
      try {
        const response = await fetch(TABLE_ENDPOINT, { signal: controller.signal });
        if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
        const payload = (await response.json()) as TableSnapshot;
        if (isMounted) {
          setState({ status: "ready", data: payload });
        }
      } catch (error) {
        if (!isMounted || (error instanceof DOMException && error.name === "AbortError")) return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Unknown error"
        });
      }
    }

    loadTable();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  let mainContent: JSX.Element;
  if (state.status === "loading") {
    mainContent = <p className="status">Loading live table snapshot…</p>;
  } else if (state.status === "error") {
    mainContent = (
      <div className="status error">
        <p>Unable to load table data.</p>
        <pre>{state.message}</pre>
      </div>
    );
  } else {
    mainContent = (
      <>
        <section className="table-meta">
          <p>
            <strong>Table:</strong> {state.data.name} &nbsp;•&nbsp; <strong>Pot:</strong>{" "}
            {state.data.pot}¢ &nbsp;•&nbsp; <strong>Call:</strong> {state.data.call_amount}¢
          </p>
        </section>
        <TableView players={mapPlayers(state.data)} />
      </>
    );
  }

  return (
    <div className="app">
      <header>
        <h1>Jack of All Trades — Preflop Demo</h1>
        <p>Live data from the Flask demo endpoint.</p>
      </header>

      <main>{mainContent}</main>

      <footer>
        <small>
          Snapshot served by <code>GET /api/v1/table</code>. Replace with authenticated API calls in
          production.
        </small>
      </footer>
    </div>
  );
}
