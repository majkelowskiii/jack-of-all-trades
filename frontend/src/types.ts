import type { PlayerView, PlayerCard } from "./components/TableView";

export type ApiCard = {
  rank: string | null;
  suit: string | null;
};

export type ApiPlayer = {
  seat: number;
  name: string;
  stack: number;
  hole_cards: ApiCard[];
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
  hand_complete: boolean;
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
      holeCards: (player.hole_cards ?? []) as PlayerCard[],
      role,
    };
  });
}

export type BlackjackHandView = {
  id: number;
  cards: ApiCard[];
  bet: number;
  status: string;
  total: number;
  is_soft: boolean;
  is_blackjack: boolean;
  can_split: boolean;
  can_double: boolean;
  can_surrender: boolean;
};

export type BlackjackPlayerState = {
  bankroll: number;
  hands: BlackjackHandView[];
  active_hand_index: number | null;
  bet_limits: { min: number; max: number };
};

export type BlackjackDealerState = {
  cards: ApiCard[];
  hidden_cards: number;
  visible_total: number;
  hole_card_revealed: boolean;
  total?: number;
  is_soft?: boolean;
};

export type BlackjackActions = {
  can_place_bet: boolean;
  can_deal: boolean;
  can_hit: boolean;
  can_stand: boolean;
  can_double: boolean;
  can_split: boolean;
  can_surrender: boolean;
  can_buy_insurance: boolean;
  can_skip_insurance: boolean;
  can_start_next_hand: boolean;
  can_step_dealer: boolean;
};

export type BlackjackSnapshot = {
  phase: string;
  requires_configuration: boolean;
  defaults?: { bankroll: number; shoe_decks: number; min_bet: number };
  hand_number?: number;
  player?: BlackjackPlayerState;
  dealer?: BlackjackDealerState;
  shoe?: {
    decks: number;
    cards_remaining: number;
    total_cards: number;
    needs_shuffle: boolean;
    penetration: number;
  };
  pending_initial_deal?: number;
  insurance?: { current: number; allowed: boolean; max: number };
  available_actions?: Partial<BlackjackActions> & { can_configure?: boolean };
  messages?: string[];
  hand_results?: string[];
  running_count?: number;
  true_count?: number;
  decks_remaining?: number;
  dealer_steps_remaining?: number;
};

export type BlackjackState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: BlackjackSnapshot };
