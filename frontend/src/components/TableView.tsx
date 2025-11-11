import React from "react";

export type PlayerCard = {
  rank: string | null;
  suit: string | null;
};

export type PlayerView = {
  name: string;
  stack: number;
  contributed: number;
  inHand: boolean;
  holeCards: PlayerCard[];
  role?: "D" | "SB" | "BB";
};

type Props = {
  players: PlayerView[]; // expected length 8
  activeSeat?: number | null;
};

const SLOT_COUNT = 8;
const EMPTY_CARD: PlayerCard = { rank: null, suit: null };

const SUIT_META = {
  spades: { symbol: "♠", label: "spades", className: "card-spade" },
  hearts: { symbol: "♥", label: "hearts", className: "card-heart" },
  diamonds: { symbol: "♦", label: "diamonds", className: "card-diamond" },
  clubs: { symbol: "♣", label: "clubs", className: "card-club" },
} as const;

function angleForIndex(i: number) {
  // put seat 0 at bottom center and go clockwise
  return (360 / SLOT_COUNT) * i - 90;
}

function renderCard(card?: PlayerCard) {
  if (!card || !card.rank || !card.suit) {
    return <span className="card card-empty" aria-hidden="true" />;
  }

  const suitKey = card.suit.toLowerCase() as keyof typeof SUIT_META;
  const suitMeta = SUIT_META[suitKey];
  if (!suitMeta) {
    return (
      <span className="card card-unknown">
        <span className="card-rank">{card.rank.toUpperCase()}</span>
      </span>
    );
  }
  return (
    <span
      className={`card ${suitMeta.className}`}
      aria-label={`${card.rank.toUpperCase()} of ${suitMeta.label}`}
    >
      <span className="card-rank">{card.rank.toUpperCase()}</span>
      <span className="card-suit" aria-hidden="true">
        {suitMeta.symbol}
      </span>
    </span>
  );
}

export default function TableView({ players, activeSeat }: Props): JSX.Element {
  const padded = [...players];
  while (padded.length < SLOT_COUNT) {
    padded.push({
      name: "empty",
      stack: 0,
      contributed: 0,
      inHand: false,
      holeCards: [EMPTY_CARD, EMPTY_CARD],
    });
  }

  return (
    <div className="table-wrapper">
      <div className="table">
        {padded.map((p, i) => {
          const angle = angleForIndex(i);
          const transform = `translate(-50%, -50%) rotate(${angle}deg) translate(0, calc(-1 * var(--seat-radius))) rotate(${-angle}deg)`;
          return (
            <div
              key={i}
              className={`seat ${p.stack === 0 ? "empty" : ""} ${!p.inHand ? "folded" : ""} ${
                activeSeat === i ? "active" : ""
              }`}
              style={{ transform }}
              aria-label={`seat-${i}-${p.name}`}
            >
              <div className="player-name">
                {p.name}
                {p.role ? ` (${p.role})` : ""}
              </div>
              <div className="player-stack">{p.stack}¢</div>
              <div className="player-bet">In pot: {p.contributed}¢</div>
              <div className="hole-cards">
                {renderCard(p.holeCards[0])}
                {renderCard(p.holeCards[1])}
              </div>
            </div>
          );
        })}
        <div className="table-center">TABLE</div>
      </div>
    </div>
  );
}
