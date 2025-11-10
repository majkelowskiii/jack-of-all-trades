import type { PlayerView } from "./components/TableView";

export type ApiPlayer = {
  seat: number;
  name: string;
  stack: number;
  hole_cards: string[];
  in_hand: boolean;
  player_bet: number;
};

export type BlindInfo = { seat: number; name: string | null } | null;

export type RaiseInfo = {
  allowed: boolean;
  min_total: number;
  max_total: number;
  increment: number;
};

export type AvailableActions = {
  can_fold: boolean;
  can_check: boolean;
  can_call: boolean;
  call_amount: number;
  raise: RaiseInfo;
};

export type ActivePlayerInfo = {
  seat: number | null;
  name: string | null;
  stack: number | null;
  current_bet: number | null;
} | null;

export type TableSnapshot = {
  name: string;
  dealer_position: number | null;
  sb: BlindInfo;
  bb: BlindInfo;
  hand_number: number;
  players: ApiPlayer[];
  pot: number;
  call_amount: number;
  active_seat: number | null;
  active_player: ActivePlayerInfo;
  available_actions: AvailableActions;
};

export type TableState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: TableSnapshot };

export type ActionRequest =
  | { action: "fold" }
  | { action: "check" }
  | { action: "call" }
  | { action: "raise"; amount: number };

export function mapPlayers(snapshot: TableSnapshot): PlayerView[] {
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
      contributed: player.player_bet,
      inHand: player.in_hand,
      holeCards: player.hole_cards,
      role,
    };
  });
}
