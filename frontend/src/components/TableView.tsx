import React from "react";

export type PlayerView = {
  name: string;
  stack: number;
  holeCards: [string, string] | string[];
  role?: "D" | "SB" | "BB";
};

type Props = {
  players: PlayerView[]; // expected length 8
};

const SLOT_COUNT = 8;

function angleForIndex(i: number) {
  // put seat 0 at bottom center and go clockwise
  return (360 / SLOT_COUNT) * i - 90;
}

export default function TableView({ players }: Props): JSX.Element {
  const padded = [...players];
  while (padded.length < SLOT_COUNT) padded.push({ name: "empty", stack: 0, holeCards: ["", ""] });

  return (
    <div className="table-wrapper">
      <div className="table">
        {padded.map((p, i) => {
          const angle = angleForIndex(i);
          const transform = `translate(-50%, -50%) rotate(${angle}deg) translate(0, calc(-1 * var(--seat-radius))) rotate(${-angle}deg)`;
          return (
            <div
              key={i}
              className={`seat ${p.stack === 0 ? "empty" : ""}`}
              style={{ transform }}
              aria-label={`seat-${i}-${p.name}`}
            >
              <div className="player-name">
                {p.name}
                {p.role ? ` (${p.role})` : ""}
              </div>
              <div className="player-stack">{p.stack}¢</div>
              <div className="hole-cards">
                <span className="card">{p.holeCards[0] ?? ""}</span>
                <span className="card">{p.holeCards[1] ?? ""}</span>
              </div>
            </div>
          );
        })}
        <div className="table-center">TABLE</div>
      </div>
    </div>
  );
}
