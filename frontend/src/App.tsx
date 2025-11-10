import React, { useCallback, useEffect, useMemo, useState } from "react";
import TableView from "./components/TableView";
import {
  ActionRequest,
  TableSnapshot,
  TableState,
  mapPlayers,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";
const TABLE_ENDPOINT = `${API_BASE_URL}/api/v1/table`;
const ACTION_ENDPOINT = `${API_BASE_URL}/api/v1/table/action`;

const clamp = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, min), max);

export default function App(): JSX.Element {
  const [state, setState] = useState<TableState>({ status: "loading" });
  const [actionStatus, setActionStatus] = useState<"idle" | "pending">("idle");
  const [actionError, setActionError] = useState<string | null>(null);
  const [raiseAmount, setRaiseAmount] = useState<number | null>(null);

  const fetchSnapshot = useCallback(async (signal?: AbortSignal) => {
    const response = await fetch(TABLE_ENDPOINT, { signal });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    return (await response.json()) as TableSnapshot;
  }, []);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    fetchSnapshot(controller.signal)
      .then((payload) => {
        if (isMounted) {
          setState({ status: "ready", data: payload });
        }
      })
      .catch((error) => {
        if (!isMounted || (error instanceof DOMException && error.name === "AbortError")) {
          return;
        }
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      });

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [fetchSnapshot]);

  useEffect(() => {
    if (state.status !== "ready") {
      setRaiseAmount(null);
      return;
    }
    const raiseInfo = state.data.available_actions.raise;
    if (!raiseInfo.allowed) {
      setRaiseAmount(null);
      return;
    }
    setRaiseAmount((prev) => {
      if (prev === null) {
        return raiseInfo.min_total;
      }
      return clamp(prev, raiseInfo.min_total, raiseInfo.max_total);
    });
  }, [state]);

  const submitAction = useCallback(
    async (payload: ActionRequest) => {
      setActionStatus("pending");
      setActionError(null);
      try {
        const response = await fetch(ACTION_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error(`Action failed: ${response.status}`);
        }
        const snapshot = (await response.json()) as TableSnapshot;
        setState({ status: "ready", data: snapshot });
      } catch (error) {
        setActionError(error instanceof Error ? error.message : "Unknown error");
      } finally {
        setActionStatus("idle");
      }
    },
    []
  );

  const isActionPending = actionStatus === "pending";

  const mainContent = useMemo(() => {
    if (state.status === "loading") {
      return <p className="status">Loading live table snapshot…</p>;
    }
    if (state.status === "error") {
      return (
        <div className="status error">
          <p>Unable to load table data.</p>
          <pre>{state.message}</pre>
        </div>
      );
    }

    const snapshot = state.data;
    const actions = snapshot.available_actions;
    const activePlayer = snapshot.active_player;
    const raiseInfo = actions.raise;
    const raiseMin = raiseInfo.min_total;
    const raiseMax = Math.max(raiseInfo.min_total, raiseInfo.max_total);
    const raiseStep = Math.max(1, raiseInfo.increment);
    const raiseValue = clamp(raiseAmount ?? raiseMin, raiseMin, raiseMax);

    return (
      <>
        <section className="table-meta">
          <p>
            <strong>Table:</strong> {snapshot.name} &nbsp;•&nbsp; <strong>Hand:</strong> #
            {snapshot.hand_number} &nbsp;•&nbsp; <strong>Pot:</strong> {snapshot.pot}¢ &nbsp;•&nbsp;{" "}
            <strong>Call:</strong> {snapshot.call_amount}¢
          </p>
        </section>
        <TableView players={mapPlayers(snapshot)} activeSeat={snapshot.active_seat} />

        <section className="control-panel" aria-live="polite">
          <h2>Action Panel</h2>
          <div className="active-summary">
            <span>Acting: {activePlayer?.name ?? "—"}</span>
            <span>Stack: {activePlayer?.stack ?? 0}¢</span>
          </div>
          <div className="action-buttons">
            <button
              onClick={() => submitAction({ action: "fold" })}
              disabled={!actions.can_fold || isActionPending}
            >
              Fold
            </button>
            <button
              onClick={() => submitAction({ action: "check" })}
              disabled={!actions.can_check || isActionPending}
            >
              Check
            </button>
            <button
              onClick={() => submitAction({ action: "call" })}
              disabled={!actions.can_call || isActionPending}
            >
              Call {actions.call_amount}¢
            </button>
          </div>

          {raiseInfo.allowed && (
            <div className="raise-control">
              <label htmlFor="raise-slider">
                Raise to: <strong>{raiseValue}¢</strong> (min {raiseMin}¢ / max {raiseMax}¢)
              </label>
              <input
                id="raise-slider"
                type="range"
                min={raiseMin}
                max={raiseMax}
                step={raiseStep}
                value={raiseValue}
                onChange={(event) => setRaiseAmount(Number(event.currentTarget.value))}
                disabled={isActionPending || raiseMin === raiseMax}
              />
              <div className="raise-actions">
                <button
                  onClick={() => submitAction({ action: "raise", amount: raiseValue })}
                  disabled={isActionPending}
                >
                  Raise
                </button>
                <span>Increment: {raiseInfo.increment}¢</span>
              </div>
            </div>
          )}

          {!raiseInfo.allowed && (
            <p className="status">Raise unavailable — player is all-in or capped.</p>
          )}

          {actionError && (
            <p className="status error" role="alert">
              {actionError}
            </p>
          )}
        </section>
      </>
    );
  }, [state, raiseAmount, submitAction, isActionPending]);

  return (
    <div className="app">
      <header>
        <h1>Jack of All Trades — Preflop Demo</h1>
        <p>Live data from the Flask demo endpoint.</p>
      </header>

      <main>{mainContent}</main>

      <footer>
        <small>
          Snapshot served by <code>GET /api/v1/table</code> with actions via{" "}
          <code>POST /api/v1/table/action</code>.
        </small>
      </footer>
    </div>
  );
}
