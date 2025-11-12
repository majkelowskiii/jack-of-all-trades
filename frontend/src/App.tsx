import React, { useCallback, useEffect, useMemo, useState } from "react";
import TableView from "./components/TableView";
import {
  ActionRequest,
  TableSnapshot,
  TableState,
  mapPlayers,
} from "./types";
import BlackjackTrainer from "./features/blackjack/BlackjackTrainer";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";
const TABLE_ENDPOINT = `${API_BASE_URL}/api/v1/poker/table`;
const ACTION_ENDPOINT = `${API_BASE_URL}/api/v1/poker/table/action`;
const NEXT_HAND_ENDPOINT = `${API_BASE_URL}/api/v1/poker/table/next-hand`;

const clamp = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, min), max);

type GameKey = "menu" | "poker" | "blackjack";

export default function App(): JSX.Element {
  const [state, setState] = useState<TableState>({ status: "loading" });
  const [actionStatus, setActionStatus] = useState<"idle" | "pending">("idle");
  const [handStatus, setHandStatus] = useState<"idle" | "pending">("idle");
  const [actionError, setActionError] = useState<string | null>(null);
  const [raiseAmount, setRaiseAmount] = useState<number | null>(null);
  const [activeGame, setActiveGame] = useState<GameKey>("menu");
  const isPokerActive = activeGame === "poker";

  const fetchSnapshot = useCallback(async (signal?: AbortSignal) => {
    const response = await fetch(TABLE_ENDPOINT, { signal });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    return (await response.json()) as TableSnapshot;
  }, []);

  useEffect(() => {
    if (!isPokerActive) {
      return undefined;
    }
    let isMounted = true;
    const controller = new AbortController();
    setState({ status: "loading" });

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
  }, [fetchSnapshot, isPokerActive]);

  useEffect(() => {
    if (!isPokerActive || state.status !== "ready") {
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
  }, [state, isPokerActive]);

  const submitAction = useCallback(
    async (payload: ActionRequest) => {
      if (state.status === "ready" && state.data.hand_complete) {
        setActionError("Hand complete. Start the next hand to keep training.");
        return;
      }
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
    [state]
  );

  const startNextHand = useCallback(async () => {
    setHandStatus("pending");
    setActionError(null);
    try {
      const response = await fetch(NEXT_HAND_ENDPOINT, { method: "POST" });
      if (!response.ok) {
        throw new Error(`Next hand failed: ${response.status}`);
      }
      const snapshot = (await response.json()) as TableSnapshot;
      setState({ status: "ready", data: snapshot });
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Unknown error");
    } finally {
      setHandStatus("idle");
    }
  }, []);

  const isActionPending = actionStatus === "pending";
  const isHandPending = handStatus === "pending";

  const pokerContent = useMemo(() => {
    if (!isPokerActive) {
      return null;
    }
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
    const raiseStep = 1;
    const raiseValue = clamp(raiseAmount ?? raiseMin, raiseMin, raiseMax);
    const controlsDisabled = snapshot.hand_complete || isActionPending;

    return (
      <>
        <section className="table-meta">
          <p>
            <strong>Table:</strong> {snapshot.name} &nbsp;•&nbsp; <strong>Hand:</strong> #
            {snapshot.hand_number} &nbsp;•&nbsp; <strong>Pot:</strong> {snapshot.pot}¢ &nbsp;•&nbsp;{" "}
            <strong>Call:</strong> {snapshot.call_amount}¢
          </p>
          <div className="hand-controls">
            <button
              type="button"
              onClick={startNextHand}
              disabled={isHandPending}
              aria-busy={isHandPending}
            >
              {isHandPending ? "Starting new hand…" : "Start new hand"}
            </button>
            {snapshot.hand_complete && (
              <span role="status" className="status inline">
                Hand finished — start a new hand to continue.
              </span>
            )}
          </div>
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
              disabled={!actions.can_fold || controlsDisabled}
            >
              Fold
            </button>
            <button
              onClick={() => submitAction({ action: "check" })}
              disabled={!actions.can_check || controlsDisabled}
            >
              Check
            </button>
            <button
              onClick={() => submitAction({ action: "call" })}
              disabled={!actions.can_call || controlsDisabled}
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
                disabled={controlsDisabled || raiseMin === raiseMax}
              />
              <div className="raise-actions">
                <button
                  onClick={() => submitAction({ action: "raise", amount: raiseValue })}
                  disabled={controlsDisabled}
                >
                  Raise
                </button>
                <span>Increment: 1¢</span>
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
  }, [
    isPokerActive,
    state,
    raiseAmount,
    submitAction,
    isActionPending,
    actionError,
    startNextHand,
    isHandPending,
  ]);

  const headerSubtitle = useMemo(() => {
    switch (activeGame) {
      case "poker":
        return "Control every seat to rehearse ranges and whole-hand decisions.";
      case "blackjack":
        return "Practice one hand at a time, manage the live shoe, and keep count accuracy sharp.";
      default:
        return "Single-player training hub — pick Poker now or preview Blackjack.";
    }
  }, [activeGame]);

  const handleBackToMenu = useCallback(() => {
    setActiveGame("menu");
    setActionError(null);
    setRaiseAmount(null);
  }, []);

  const mainContent = useMemo(() => {
    if (activeGame === "menu") {
      return (
        <section className="game-select">
          <h2>Choose your training module</h2>
          <p>Practice alone, track points, and compare progress across games.</p>
          <div className="game-grid">
            <article className="game-card">
              <h3>Poker ranges lab</h3>
              <p>
                Steer an entire table to internalize pre-flop charts or play whole-hand scenarios
                before facing real opponents.
              </p>
              <ul>
                <li>Self-controlled seats (2-9 handed)</li>
                <li>Pre-flop only or full-hand rehearsals</li>
                <li>Action logging + personal scoring</li>
              </ul>
              <button type="button" onClick={() => setActiveGame("poker")}>
                Train Poker
              </button>
            </article>
            <article className="game-card placeholder">
              <h3>Blackjack trainer</h3>
              <p>
                Coming soon: switch between manual and automated seats to sharpen card counting and
                decision trees.
              </p>
              <ul>
                <li>Single or multi-slot control</li>
                <li>Shoe depth visualizations</li>
                <li>Counting drills with speed targets</li>
              </ul>
              <button type="button" onClick={() => setActiveGame("blackjack")}>
                Train Blackjack
              </button>
            </article>
          </div>
        </section>
      );
    }

    if (activeGame === "blackjack") {
      return <BlackjackTrainer apiBaseUrl={API_BASE_URL} onBack={handleBackToMenu} />;
    }

    return pokerContent;
  }, [activeGame, pokerContent, handleBackToMenu]);

  return (
    <div className="app">
      <header>
        {activeGame !== "menu" && (
          <button type="button" className="back-button" onClick={handleBackToMenu}>
            ← Back to game selection
          </button>
        )}
        <h1>Jack of All Trades — Trainer</h1>
        <p>{headerSubtitle}</p>
      </header>

      <main>{mainContent}</main>

      <footer>
        <small>
          Poker API: <code>GET /api/v1/poker/table</code> &amp; <code>POST /api/v1/poker/table/action</code> ·
          Blackjack API: <code>GET /api/v1/blackjack/table</code> &amp; <code>POST /api/v1/blackjack/table/action</code>
        </small>
      </footer>
    </div>
  );
}
