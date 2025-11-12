import React, { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ApiCard, BlackjackSnapshot, BlackjackState } from "../../types";

type BlackjackTrainerProps = {
  apiBaseUrl: string;
  onBack: () => void;
};

type PendingState = "idle" | "pending";

const makeEndpoints = (baseUrl: string) => ({
  table: `${baseUrl}/api/v1/blackjack/table`,
  action: `${baseUrl}/api/v1/blackjack/table/action`,
  nextHand: `${baseUrl}/api/v1/blackjack/table/next-hand`,
  config: `${baseUrl}/api/v1/blackjack/config`,
});

const suitSymbols: Record<string, string> = {
  hearts: "♥",
  diamonds: "♦",
  clubs: "♣",
  spades: "♠",
};

const renderCard = (card: ApiCard, idx: number) => {
  if (!card.rank || !card.suit) {
    return (
      <div key={`unknown-${idx}`} className="card card-unknown">
        <span role="img" aria-label="Hidden card">
          🂠
        </span>
      </div>
    );
  }
  const suit = card.suit.toLowerCase();
  const className = `card card-${suit === "hearts" ? "heart" : suit === "diamonds" ? "diamond" : suit === "clubs" ? "club" : "spade"}`;
  const symbol = suitSymbols[suit] ?? card.suit.charAt(0).toUpperCase();
  return (
    <div key={`${card.rank}-${card.suit}-${idx}`} className={className}>
      <span className="card-rank">{card.rank}</span>
      <span className="card-suit" aria-hidden="true">
        {symbol}
      </span>
    </div>
  );
};

export default function BlackjackTrainer({ apiBaseUrl, onBack }: BlackjackTrainerProps): JSX.Element {
  const endpoints = useMemo(() => makeEndpoints(apiBaseUrl), [apiBaseUrl]);
  const [state, setState] = useState<BlackjackState>({ status: "loading" });
  const [pending, setPending] = useState<PendingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [betAmount, setBetAmount] = useState<number>(10);
  const [insuranceAmount, setInsuranceAmount] = useState<number>(0);
  const [configForm, setConfigForm] = useState({ bankroll: "1000", shoe_decks: "5", min_bet: "10" });
  const [autoStartNextHand, setAutoStartNextHand] = useState(true);
  const [autoBetEnabled, setAutoBetEnabled] = useState(true);
  const [autoDeclineInsurance, setAutoDeclineInsurance] = useState(true);
  const [dealerDisplayCount, setDealerDisplayCount] = useState(0);
  const [countView, setCountView] = useState<"hidden" | "running" | "true">("hidden");
  const defaultsAppliedRef = useRef(false);
  const autoDealTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoNextHandTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dealerRevealTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dealerHandRef = useRef<number | null>(null);

  const fetchSnapshot = useCallback(
    async (signal?: AbortSignal) => {
      const response = await fetch(endpoints.table, { signal });
      if (!response.ok) {
        throw new Error(`Failed to load blackjack snapshot (${response.status})`);
      }
      return (await response.json()) as BlackjackSnapshot;
    },
    [endpoints.table]
  );

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    setState({ status: "loading" });
    fetchSnapshot(controller.signal)
      .then((payload) => {
        if (mounted) {
          setState({ status: "ready", data: payload });
        }
      })
      .catch((err: unknown) => {
        if (!mounted) {
          return;
        }
        const message = err instanceof Error ? err.message : "Unknown error";
        setState({ status: "error", message });
      });
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [fetchSnapshot]);

  useEffect(() => {
    if (state.status !== "ready") {
      return;
    }
    const snapshot = state.data;
    if (snapshot.requires_configuration) {
      if (snapshot.defaults && !defaultsAppliedRef.current) {
        setConfigForm({
          bankroll: String(snapshot.defaults.bankroll ?? 1000),
          shoe_decks: String(snapshot.defaults.shoe_decks ?? 5),
          min_bet: String(snapshot.defaults.min_bet ?? 10),
        });
        defaultsAppliedRef.current = true;
      }
      setInsuranceAmount(0);
      return;
    }

    defaultsAppliedRef.current = false;

    if (snapshot.player?.bet_limits) {
      const minBet = snapshot.player.bet_limits.min;
      const maxBet = Math.max(minBet, snapshot.player.bet_limits.max);
      setBetAmount((value) => Math.min(Math.max(value, minBet), maxBet));
    }
    if (snapshot.insurance && snapshot.insurance.allowed) {
      setInsuranceAmount(snapshot.insurance.max);
    } else {
      setInsuranceAmount(0);
    }
  }, [state]);

  const sendAction = useCallback(
    async (payload: Record<string, unknown>) => {
      setPending("pending");
      setError(null);
      try {
        const response = await fetch(endpoints.action, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error(`Action failed (${response.status})`);
        }
        const json = (await response.json()) as BlackjackSnapshot;
        setState({ status: "ready", data: json });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setPending("idle");
      }
    },
    [endpoints.action]
  );

  const handleConfigure = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending("pending");
    setError(null);
    try {
      const response = await fetch(endpoints.config, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bankroll: Number(configForm.bankroll) || 0,
          shoe_decks: Number(configForm.shoe_decks) || 0,
          min_bet: Number(configForm.min_bet) || 0,
          max_bet: Number(configForm.bankroll) || 0,
        }),
      });
      if (!response.ok) {
        throw new Error(`Configuration failed (${response.status})`);
      }
      const json = (await response.json()) as BlackjackSnapshot;
      setState({ status: "ready", data: json });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPending("idle");
    }
  };

  const handleNextHand = useCallback(async () => {
    setPending("pending");
    setError(null);
    try {
      const response = await fetch(endpoints.nextHand, { method: "POST" });
      if (!response.ok) {
        throw new Error(`Unable to start next hand (${response.status})`);
      }
      const json = (await response.json()) as BlackjackSnapshot;
      setState({ status: "ready", data: json });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPending("idle");
    }
  }, [endpoints.nextHand]);

  useEffect(() => {
    if (autoDealTimer.current) {
      clearTimeout(autoDealTimer.current);
      autoDealTimer.current = null;
    }
    if (state.status !== "ready") {
      return undefined;
    }
    const snapshot = state.data;
    const pendingDeals = snapshot.pending_initial_deal ?? 0;
    const shouldAutoDeal =
      !snapshot.requires_configuration &&
      snapshot.phase === "initial_deal" &&
      pendingDeals > 0 &&
      snapshot.available_actions?.can_deal &&
      pending === "idle";
    if (!shouldAutoDeal) {
      return undefined;
    }
    const timer = setTimeout(() => {
      autoDealTimer.current = null;
      void sendAction({ action: "deal" });
    }, 450);
    autoDealTimer.current = timer;
    return () => {
      clearTimeout(timer);
      autoDealTimer.current = null;
    };
  }, [state, pending, sendAction]);

  useEffect(() => {
    if (state.status !== "ready" || !autoBetEnabled || pending !== "idle") {
      return;
    }
    const snapshot = state.data;
    if (!snapshot.available_actions?.can_place_bet || !snapshot.player?.bet_limits) {
      return;
    }
    const minBet = snapshot.player.bet_limits.min;
    const maxBet = Math.max(minBet, snapshot.player.bet_limits.max);
    const desiredAmount = Math.min(Math.max(betAmount ?? minBet, minBet), maxBet);
    if (desiredAmount !== betAmount) {
      setBetAmount(desiredAmount);
    }
    void sendAction({ action: "place_bet", amount: desiredAmount });
  }, [state, autoBetEnabled, pending, betAmount, sendAction]);

  useEffect(() => {
    if (autoNextHandTimer.current) {
      clearTimeout(autoNextHandTimer.current);
      autoNextHandTimer.current = null;
    }
    if (state.status !== "ready" || !autoStartNextHand || pending !== "idle") {
      return undefined;
    }
    if (!state.data.available_actions?.can_start_next_hand) {
      return undefined;
    }
    const timer = setTimeout(() => {
      autoNextHandTimer.current = null;
      void handleNextHand();
    }, 1500);
    autoNextHandTimer.current = timer;
    return () => {
      clearTimeout(timer);
      autoNextHandTimer.current = null;
    };
  }, [state, autoStartNextHand, pending, handleNextHand]);

  useEffect(() => {
    if (state.status !== "ready" || !autoDeclineInsurance || pending !== "idle") {
      return;
    }
    if (state.data.insurance?.allowed) {
      void sendAction({ action: "skip_insurance" });
    }
  }, [state, autoDeclineInsurance, pending, sendAction]);

  useEffect(() => {
    const clearTimer = () => {
      if (dealerRevealTimer.current) {
        clearTimeout(dealerRevealTimer.current);
        dealerRevealTimer.current = null;
      }
    };

    if (state.status !== "ready") {
      dealerHandRef.current = null;
      setDealerDisplayCount(0);
      clearTimer();
      return undefined;
    }

    const snapshot = state.data;
    const dealerCards = snapshot.dealer?.cards ?? [];
    const hiddenCards = snapshot.dealer?.hidden_cards ?? 0;
    const currentHandNumber = snapshot.hand_number ?? null;

    if (dealerHandRef.current !== currentHandNumber) {
      dealerHandRef.current = currentHandNumber;
      setDealerDisplayCount(dealerCards.length);
      clearTimer();
      return undefined;
    }

    if (hiddenCards > 0) {
      if (dealerDisplayCount !== dealerCards.length) {
        setDealerDisplayCount(dealerCards.length);
      }
      clearTimer();
      return undefined;
    }

    const targetCount = dealerCards.length;
    if (dealerDisplayCount >= targetCount) {
      return undefined;
    }

    if (!dealerRevealTimer.current) {
      dealerRevealTimer.current = setTimeout(() => {
        dealerRevealTimer.current = null;
        setDealerDisplayCount((prev) => Math.min(prev + 1, targetCount));
      }, 450);
    }

    return () => {
      clearTimer();
    };
  }, [state, dealerDisplayCount]);

  useEffect(
    () => () => {
      if (dealerRevealTimer.current) {
        clearTimeout(dealerRevealTimer.current);
      }
    },
    []
  );

  if (state.status === "loading") {
    return (
      <section className="status">
        <p>Loading blackjack session…</p>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="status error">
        <p>Unable to load blackjack data.</p>
        <pre>{state.message}</pre>
        <button type="button" onClick={onBack}>
          Back to game selection
        </button>
      </section>
    );
  }

  const snapshot = state.data;
  if (snapshot.requires_configuration) {
    return (
      <section className="blackjack-config">
        <h2>Configure Blackjack Trainer</h2>
        <p>Set your bankroll and shoe depth to keep the shoe state persistent between hands.</p>
        <form onSubmit={handleConfigure} className="blackjack-config-form">
          <label>
            Bankroll (chips)
            <input
              type="number"
              min={100}
              step={50}
              value={configForm.bankroll}
              onChange={(event) =>
                setConfigForm((prev) => ({ ...prev, bankroll: event.currentTarget.value }))
              }
              required
            />
          </label>
          <label>
            Decks in shoe (default 5)
            <input
              type="number"
              min={1}
              max={8}
              value={configForm.shoe_decks}
              onChange={(event) =>
                setConfigForm((prev) => ({ ...prev, shoe_decks: event.currentTarget.value }))
              }
              required
            />
          </label>
          <label>
            Table minimum bet
            <input
              type="number"
              min={5}
              value={configForm.min_bet}
              onChange={(event) =>
                setConfigForm((prev) => ({ ...prev, min_bet: event.currentTarget.value }))
              }
              required
            />
          </label>
          <div className="blackjack-config-actions">
            <button type="submit" disabled={pending === "pending"}>
              {pending === "pending" ? "Starting session…" : "Start Blackjack session"}
            </button>
            <button type="button" className="secondary" onClick={onBack}>
              Cancel
            </button>
          </div>
        </form>
        {error && (
          <p className="status error" role="alert">
            {error}
          </p>
        )}
      </section>
    );
  }

  const player = snapshot.player!;
  const dealer = snapshot.dealer!;
  const actions = snapshot.available_actions!;
  const shoe = snapshot.shoe!;
  const insurance = snapshot.insurance;
  const isPending = pending === "pending";
  const dealerCardsToShow =
    dealer.hidden_cards > 0
      ? dealer.cards
      : dealer.cards.slice(0, Math.min(dealerDisplayCount, dealer.cards.length));
  const pendingDeals = snapshot.pending_initial_deal ?? 0;
  const isAutoDealingPhase =
    snapshot.phase === "initial_deal" && pendingDeals > 0 && actions.can_deal;
  const runningCount = snapshot.running_count ?? null;
  const trueCount = snapshot.true_count ?? null;
  const decksRemainingDisplay =
    snapshot.decks_remaining ?? Number((shoe.cards_remaining / 52).toFixed(2));
  const formattedRunningCount =
    typeof runningCount === "number" ? runningCount : "N/A";
  const formattedTrueCount =
    typeof trueCount === "number" ? trueCount.toFixed(2) : "N/A";
  const formattedDecksRemaining =
    typeof decksRemainingDisplay === "number" ? decksRemainingDisplay.toFixed(2) : "N/A";

  const handleInsuranceSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!insurance?.allowed) {
      return;
    }
    const amount = Math.min(Math.max(1, insuranceAmount || insurance.max), insurance.max);
    void sendAction({ action: "buy_insurance", amount });
  };

  return (
    <section className="blackjack-layout">
      <header className="blackjack-header">
        <div>
          <h2>Blackjack Trainer</h2>
          <p>
            Hand #{snapshot.hand_number} • Bankroll: <strong>{player.bankroll}</strong> chips • Shoe:{" "}
            {shoe.decks} decks ({shoe.cards_remaining} cards left)
          </p>
        </div>
        <div className="blackjack-header-actions">
          <button type="button" onClick={onBack}>
            Back to game selection
          </button>
          <div className="blackjack-next-hand-control">
            <button
              type="button"
              onClick={handleNextHand}
              disabled={!actions.can_start_next_hand || isPending}
            >
              {isPending ? "Resetting…" : "Start next hand"}
            </button>
            <label className="inline-checkbox">
              <input
                type="checkbox"
                checked={autoStartNextHand}
                onChange={(event) => setAutoStartNextHand(event.currentTarget.checked)}
              />
              Auto start next hand
            </label>
          </div>
        </div>
      </header>

      <div className="blackjack-main">
        <div className="blackjack-primary">
          <div className="blackjack-board">
            <div className="blackjack-dealer">
              <div className="blackjack-section-title">Dealer</div>
              <div className="blackjack-cards">
                {dealerCardsToShow.map((card, idx) => renderCard(card, idx))}
                {dealer.hidden_cards > 0 &&
                  Array.from({ length: dealer.hidden_cards }).map((_, idx) =>
                    renderCard({ rank: null, suit: null }, dealerCardsToShow.length + idx)
                  )}
              </div>
              <p>
                Visible total: {dealer.visible_total}
                {dealer.hidden_cards > 0 && !dealer.hole_card_revealed && " (+ hidden)"}
              </p>
            </div>

            <div className="blackjack-hands">
              {player.hands.map((hand) => {
                const isActive = player.active_hand_index === hand.id && hand.status === "active";
                return (
                  <article
                    key={hand.id}
                    className={`blackjack-hand ${isActive ? "active" : ""} status-${hand.status}`}
                  >
                    <header>
                      <div>
                        Hand #{hand.id + 1} — Bet {hand.bet} chips {hand.is_blackjack && " — Blackjack"}
                      </div>
                      <small>Status: {hand.status}</small>
                    </header>
                    <div className="blackjack-cards">{hand.cards.map((card, idx) => renderCard(card, idx))}</div>
                    <footer>
                      <span>
                        Total: {hand.total} {hand.is_soft ? "(soft)" : ""}
                      </span>
                      <span>
                        {hand.can_split && "Split • "}
                        {hand.can_double && "Double • "}
                        {hand.can_surrender && "Surrender"}
                      </span>
                    </footer>
                  </article>
                );
              })}
            </div>
          </div>

          <section className="blackjack-controls">
            <div className="blackjack-section-title">Betting</div>
            <form
              className="blackjack-bet-form"
              onSubmit={(event) => {
                event.preventDefault();
                void sendAction({ action: "place_bet", amount: betAmount });
              }}
            >
              <label>
                Bet amount
                <input
                  type="number"
                  min={player.bet_limits.min}
                  max={player.bet_limits.max}
                  value={betAmount}
                  onChange={(event) => setBetAmount(Number(event.currentTarget.value))}
                  disabled={!actions.can_place_bet || isPending}
                  required
                />
              </label>
              <div className="bet-actions">
                <button type="submit" disabled={!actions.can_place_bet || isPending}>
                  {actions.can_place_bet ? "Place bet" : "Waiting…"}
                </button>
                <label className="inline-checkbox">
                  <input
                    type="checkbox"
                    checked={autoBetEnabled}
                    onChange={(event) => setAutoBetEnabled(event.currentTarget.checked)}
                  />
                  Auto place bet
                </label>
              </div>
            </form>
            <div className="blackjack-button-row">
              <button
                type="button"
                onClick={() => sendAction({ action: "hit" })}
                disabled={!actions.can_hit || isPending}
              >
                Hit
              </button>
              <button
                type="button"
                onClick={() => sendAction({ action: "stand" })}
                disabled={!actions.can_stand || isPending}
              >
                Stand
              </button>
              <button
                type="button"
                onClick={() => sendAction({ action: "double" })}
                disabled={!actions.can_double || isPending}
              >
                Double
              </button>
              <button
                type="button"
                onClick={() => sendAction({ action: "split" })}
                disabled={!actions.can_split || isPending}
              >
                Split
              </button>
              <button
                type="button"
                onClick={() => sendAction({ action: "surrender" })}
                disabled={!actions.can_surrender || isPending}
              >
                Surrender
              </button>
              <label className="inline-checkbox">
                <input
                  type="checkbox"
                  checked={autoDeclineInsurance}
                  onChange={(event) => setAutoDeclineInsurance(event.currentTarget.checked)}
                />
                Always decline insurance
              </label>
            </div>
            {isAutoDealingPhase && (
              <p className="status inline" role="status">
                Dealing opening cards…
              </p>
            )}
            {shoe.needs_shuffle && (
              <p className="status inline">Shuffle pending — shoe will reset after this hand.</p>
            )}
            {error && (
              <p className="status error" role="alert">
                {error}
              </p>
            )}
          </section>

          <section className="blackjack-status">
            <div>
              <div className="blackjack-section-title">Phase</div>
              <p>{snapshot.phase.replaceAll("_", " ")}</p>
            </div>
            <div>
              <div className="blackjack-section-title">Messages</div>
              <ul>
                {(snapshot.messages ?? []).map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
            {snapshot.hand_results && snapshot.hand_results.length > 0 && (
              <div>
                <div className="blackjack-section-title">Hand results</div>
                <ul>
                  {snapshot.hand_results.map((result) => (
                    <li key={result}>{result}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </div>
        <aside className="blackjack-count-panel">
          <div className="blackjack-section-title">Card counting</div>
          <p>Check your Hi-Lo accuracy without affecting gameplay.</p>
          <div className="count-toggle">
            <button
              type="button"
              className={countView === "running" ? "active" : ""}
              onClick={() => setCountView((prev) => (prev === "running" ? "hidden" : "running"))}
            >
              Show Running Count
            </button>
            <button
              type="button"
              className={countView === "true" ? "active" : ""}
              onClick={() => setCountView((prev) => (prev === "true" ? "hidden" : "true"))}
            >
              Show True Count
            </button>
          </div>
          <div className="count-display">
            {countView === "hidden" ? (
              <p className="muted">Select a metric to reveal its value.</p>
            ) : (
              <>
                <p className="count-label">
                  {countView === "running" ? "Running Count" : "True Count"}
                </p>
                <p className="count-value">
                  {countView === "running" ? formattedRunningCount : formattedTrueCount}
                </p>
              </>
            )}
            <dl className="count-meta">
              <div>
                <dt>Running</dt>
                <dd>{formattedRunningCount}</dd>
              </div>
              <div>
                <dt>True</dt>
                <dd>{formattedTrueCount}</dd>
              </div>
              <div>
                <dt>Decks left</dt>
                <dd>{formattedDecksRemaining}</dd>
              </div>
            </dl>
          </div>
        </aside>
      </div>
      {insurance?.allowed && !autoDeclineInsurance && (
        <div className="blackjack-overlay" role="dialog" aria-modal="true">
          <div className="blackjack-modal">
            <h3>Insurance offered</h3>
            <p>Dealer is showing an Ace. You can insure up to {insurance.max} chips.</p>
            <form className="blackjack-insurance" onSubmit={handleInsuranceSubmit}>
              <label>
                Insurance bet
                <input
                  type="number"
                  min={1}
                  max={insurance.max}
                  value={insuranceAmount}
                  onChange={(event) => setInsuranceAmount(Number(event.currentTarget.value))}
                />
              </label>
              <div className="blackjack-modal-actions">
                <button type="submit" disabled={isPending}>
                  Buy insurance
                </button>
                <button
                  type="button"
                  onClick={() => sendAction({ action: "skip_insurance" })}
                  disabled={isPending}
                >
                  Decline
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
