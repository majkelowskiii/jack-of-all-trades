from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import abort, jsonify, make_response, request, Flask
from common.table import Table
from common.dealer import Dealer
from common.deck import Deck
from common.player import Player

app = Flask(__name__)


def build_demo_table() -> tuple[Table, Dealer, int, int]:
    """Build a demo table: 8 players, 4000 stack each, shuffle, post blinds and deal hole cards."""
    deck = Deck()
    dealer = Dealer(deck)
    table = Table("Table1")

    names = ["john", "mark", "alice", "sara", "tom", "ryan", "mia", "liam"]
    for n in names:
        table.sit_player(Player(n, 4000))

    # shuffle and post blinds
    dealer.shuffle_cards()
    sb_pos, bb_pos = table.post_blinds()

    # deal two hole cards starting from small blind (SB) clockwise
    n_players = len(table.seats)
    for _ in range(2):
        for i in range(n_players):
            idx = (sb_pos + i) % n_players
            player = table.seats[idx]
            if getattr(player, "in_hand", False):
                dealer.deal_card_to_player(player)

    return table, dealer, sb_pos, bb_pos


@dataclass
class GameState:
    table: Table
    dealer: Dealer
    sb_pos: int
    bb_pos: int
    hand_number: int = 1


GAME_STATE: Optional[GameState] = None


def build_players_payload(table: Table) -> list[Dict[str, Any]]:
    """Serialize all seats for API responses."""
    payload: list[Dict[str, Any]] = []
    for i, player in enumerate(table.seats):
        payload.append(
            {
                "seat": i,
                "name": getattr(player, "name", None),
                "stack": getattr(player, "stack", 0),
                "hole_cards": [repr(c) for c in getattr(player, "hole_cards", [])],
                "in_hand": getattr(player, "in_hand", False),
                "player_bet": getattr(player, "player_bet", 0),
            }
        )
    return payload


def get_active_player(table: Table) -> Optional[Player]:
    """Return the player whose turn it is, if any."""
    if table.active_position is None or not table.seats:
        return None
    try:
        return table.seats[table.active_position]
    except IndexError:
        return None


def remaining_players_in_hand(table: Table) -> int:
    return sum(1 for player in table.seats if getattr(player, "in_hand", False))


def has_pending_actions(table: Table) -> bool:
    return any(
        getattr(player, "in_hand", False) and getattr(player, "to_act", False)
        for player in table.seats
    )


def should_start_next_hand(table: Table) -> bool:
    return remaining_players_in_hand(table) <= 1 or not has_pending_actions(table)


def compute_min_raise_total(table: Table) -> int:
    """Return the minimum total bet required for the next raise."""
    current_call = table.call_amount
    min_increment = max(table.big_blind, table.minimal_raise)
    if current_call == 0:
        return table.big_blind * 2
    return current_call + min_increment


def compute_available_actions(table: Table) -> Dict[str, Any]:
    """Compute legal actions for the active player."""
    player = get_active_player(table)
    if player is None:
        return {
            "can_fold": False,
            "can_check": False,
            "can_call": False,
            "call_amount": 0,
            "raise": {"allowed": False, "min_total": 0, "max_total": 0, "increment": table.big_blind},
        }

    current_call = max(0, table.call_amount - getattr(player, "player_bet", 0))
    can_check = current_call == 0
    can_call = current_call > 0 and player.stack > 0
    can_raise = player.stack > current_call

    min_total = compute_min_raise_total(table)

    return {
        "can_fold": player.in_hand,
        "can_check": can_check,
        "can_call": can_call,
        "call_amount": current_call,
        "raise": {
            "allowed": can_raise,
            "min_total": min_total,
            "max_total": getattr(player, "player_bet", 0) + player.stack,
            "increment": table.big_blind,
        },
    }


def sync_pot(table: Table) -> None:
    """Recalculate the pot as the sum of current player bets."""
    table.pot = sum(getattr(player, "player_bet", 0) for player in table.seats)


def advance_to_next_player(table: Table) -> None:
    """Advance the active position to the next player still in the hand."""
    if not table.seats:
        table.active_position = None
        return
    for _ in range(len(table.seats)):
        if table.active_position is None:
            table.active_position = 0
        else:
            table.active_position = (table.active_position + 1) % len(table.seats)
        candidate = table.seats[table.active_position]
        if candidate.in_hand and getattr(candidate, "to_act", False):
            return
    table.active_position = None


def ensure_state() -> GameState:
    """Return the current GameState, building an initial snapshot if needed."""
    global GAME_STATE
    if GAME_STATE is None:
        GAME_STATE = reset_game_state()
    return GAME_STATE


def reset_game_state(hand_number: int = 1) -> GameState:
    """Rebuild and store a brand-new GameState (used by tests/demo)."""
    global GAME_STATE
    table, dealer, sb_pos, bb_pos = build_demo_table()
    sync_pot(table)
    GAME_STATE = GameState(table, dealer, sb_pos, bb_pos, hand_number)
    return GAME_STATE


def start_next_hand() -> GameState:
    """Start a fresh hand, incrementing the hand counter."""
    next_hand = 1
    if GAME_STATE is not None:
        next_hand = GAME_STATE.hand_number + 1
    return reset_game_state(hand_number=next_hand)


def serialize_state(state: GameState) -> Dict[str, Any]:
    """Convert GameState to the JSON structure consumed by the frontend."""
    table = state.table
    n = len(table.seats)
    btn_pos = table.dealer_position if n else None
    sb = table.seats[state.sb_pos] if n else None
    bb = table.seats[state.bb_pos] if n else None
    active_player = get_active_player(table)

    data = {
        "name": table.name,
        "dealer_position": btn_pos,
        "sb": {"seat": state.sb_pos, "name": getattr(sb, "name", None)} if sb is not None else None,
        "bb": {"seat": state.bb_pos, "name": getattr(bb, "name", None)} if bb is not None else None,
        "hand_number": state.hand_number,
        "players": build_players_payload(table),
        "pot": table.pot,
        "call_amount": table.call_amount,
        "active_seat": table.active_position,
        "active_player": {
            "seat": getattr(active_player, "seat_id", None),
            "name": getattr(active_player, "name", None),
            "stack": getattr(active_player, "stack", None),
            "current_bet": getattr(active_player, "player_bet", None),
        }
        if active_player
        else None,
        "available_actions": compute_available_actions(table),
    }
    return data


def cors_response(payload: Dict[str, Any]):
    """Attach permissive CORS headers for local development."""
    resp = make_response(jsonify(payload))
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp


@app.route("/api/v1/table", methods=["GET"])
def get_table():
    """Return the current table snapshot."""
    state = ensure_state()
    data = serialize_state(state)
    return cors_response(data)


def handle_fold(table: Table, player: Player) -> None:
    player.in_hand = False
    player.to_act = False
    player.active = False


def handle_check(table: Table, player: Player) -> None:
    # nothing to do; validation handled earlier
    player.to_act = False


def handle_call(table: Table, player: Player, call_amount: int) -> None:
    if call_amount <= 0:
        return
    contribution = min(call_amount, player.stack)
    player.stack -= contribution
    player.player_bet += contribution
    player.to_act = False
    sync_pot(table)


def handle_raise(table: Table, player: Player, raise_to: int) -> None:
    current_bet = getattr(player, "player_bet", 0)
    additional = raise_to - current_bet
    if additional <= 0:
        raise ValueError("Raise must increase total bet")
    if additional > player.stack:
        raise ValueError("Insufficient stack for raise")
    player.stack -= additional
    player.player_bet = raise_to
    previous_call = table.call_amount
    table.call_amount = raise_to
    table.minimal_raise = raise_to - previous_call
    if table.minimal_raise < table.big_blind:
        table.minimal_raise = table.big_blind
    player.to_act = False
    for other in table.seats:
        if other is player:
            continue
        if getattr(other, "in_hand", False):
            other.to_act = True
    sync_pot(table)


@app.route("/api/v1/table/action", methods=["POST", "OPTIONS"])
def act_on_table():
    """Apply an action for the active player and return the updated snapshot."""
    if request.method == "OPTIONS":
        return cors_response({"status": "ok"})

    state = ensure_state()
    table = state.table
    player = get_active_player(table)
    if player is None:
        abort(400, description="No active player available")

    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    if action not in {"fold", "check", "call", "raise"}:
        abort(400, description="Unsupported action")

    actions = compute_available_actions(table)
    call_amount = actions["call_amount"]

    if action == "fold":
        handle_fold(table, player)
    elif action == "check":
        if not actions["can_check"]:
            abort(400, description="Check is not available")
        handle_check(table, player)
    elif action == "call":
        if not actions["can_call"]:
            abort(400, description="Call is not available")
        handle_call(table, player, call_amount)
    elif action == "raise":
        raise_info = actions["raise"]
        if not raise_info["allowed"]:
            abort(400, description="Raise is not available")
        amount = payload.get("amount")
        if not isinstance(amount, int):
            abort(400, description="Raise amount must be integer")
        if not (raise_info["min_total"] <= amount <= raise_info["max_total"]):
            abort(400, description="Raise amount must be within allowed range")
        handle_raise(table, player, amount)

    if should_start_next_hand(table):
        state = start_next_hand()
        table = state.table
    else:
        advance_to_next_player(table)
    data = serialize_state(state)
    return cors_response(data)


if __name__ == "__main__":
    # Run with: python api.py
    app.run(host="0.0.0.0", port=5000, debug=True)
