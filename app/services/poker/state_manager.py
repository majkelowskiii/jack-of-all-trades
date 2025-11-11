"""State manager for the poker training module."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional

from common.table import Table
from common.dealer import Dealer
from common.deck import Deck
from common.player import Player


class HandCompleteError(RuntimeError):
    """Raised when an action is attempted after the hand has ended."""


class InvalidActionError(RuntimeError):
    """Raised when an invalid or unsupported action is requested."""


@dataclass
class GameState:
    """Container for a running poker hand."""

    table: Table
    dealer: Dealer
    sb_pos: int
    bb_pos: int
    hand_number: int = 1
    hand_complete: bool = False


def build_demo_table() -> tuple[Table, Dealer, int, int]:
    """Build the demo table with 8 seated players."""
    deck = Deck()
    dealer = Dealer(deck)
    table = Table("Table1")

    names = ["john", "mark", "alice", "sara", "tom", "ryan", "mia", "liam"]
    for name in names:
        table.sit_player(Player(name, 4000))

    dealer.shuffle_cards()
    sb_pos, bb_pos = table.post_blinds()

    n_players = len(table.seats)
    for _ in range(2):
        for i in range(n_players):
            idx = (sb_pos + i) % n_players
            player = table.seats[idx]
            if getattr(player, "in_hand", False):
                dealer.deal_card_to_player(player)

    table.minimal_raise = table.big_blind
    return table, dealer, sb_pos, bb_pos


def build_players_payload(table: Table) -> list[Dict[str, Any]]:
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
    current_call = table.call_amount
    min_increment = max(table.big_blind, getattr(table, "minimal_raise", table.big_blind))
    if current_call == 0:
        return table.big_blind * 2
    return current_call + min_increment


def compute_available_actions(table: Table, *, hand_complete: bool = False) -> Dict[str, Any]:
    if hand_complete:
        return {
            "can_fold": False,
            "can_check": False,
            "can_call": False,
            "call_amount": 0,
            "raise": {"allowed": False, "min_total": 0, "max_total": 0, "increment": 1},
        }

    player = get_active_player(table)
    if player is None:
        return {
            "can_fold": False,
            "can_check": False,
            "can_call": False,
            "call_amount": 0,
            "raise": {"allowed": False, "min_total": 0, "max_total": 0, "increment": 1},
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
            "increment": 1,
        },
    }


def sync_pot(table: Table) -> None:
    table.pot = sum(getattr(player, "player_bet", 0) for player in table.seats)


def advance_to_next_player(table: Table) -> None:
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


class PokerStateManager:
    """Encapsulates poker state lifecycle and actions."""

    def __init__(self) -> None:
        self._state: Optional[GameState] = None
        self._lock = RLock()

    def ensure_state(self) -> GameState:
        with self._lock:
            if self._state is None:
                self._state = self._build_initial_state()
            return self._state

    def reset_state(self, *, hand_number: int = 1) -> GameState:
        with self._lock:
            self._state = self._build_initial_state(hand_number=hand_number)
            return self._state

    def _build_initial_state(self, *, hand_number: int = 1) -> GameState:
        table, dealer, sb_pos, bb_pos = build_demo_table()
        sync_pot(table)
        return GameState(table=table, dealer=dealer, sb_pos=sb_pos, bb_pos=bb_pos, hand_number=hand_number)

    def force_next_hand(self) -> GameState:
        with self._lock:
            next_hand = 1
            if self._state is not None:
                next_hand = self._state.hand_number + 1
            state = self.reset_state(hand_number=next_hand)
            state.hand_complete = False
            return state

    def apply_action(self, *, action: str, payload: Dict[str, Any]) -> GameState:
        with self._lock:
            state = self.ensure_state()
            if state.hand_complete:
                raise HandCompleteError("Hand complete. Start the next hand to continue.")

            table = state.table
            player = get_active_player(table)
            if player is None:
                raise InvalidActionError("No active player available.")

            actions = compute_available_actions(table)
            call_amount = actions["call_amount"]

            if action == "fold":
                self._handle_fold(player)
            elif action == "check":
                if not actions["can_check"]:
                    raise InvalidActionError("Check is not available")
                self._handle_check(player)
            elif action == "call":
                if not actions["can_call"]:
                    raise InvalidActionError("Call is not available")
                self._handle_call(table, player, call_amount)
            elif action == "raise":
                raise_info = actions["raise"]
                if not raise_info["allowed"]:
                    raise InvalidActionError("Raise is not available")
                amount = payload.get("amount")
                if not isinstance(amount, int):
                    raise InvalidActionError("Raise amount must be integer")
                if not (raise_info["min_total"] <= amount <= raise_info["max_total"]):
                    raise InvalidActionError("Raise amount must be within allowed range")
                self._handle_raise(table, player, amount)
            else:
                raise InvalidActionError(f"Unsupported action '{action}'")

            if should_start_next_hand(table):
                table.active_position = None
                state.hand_complete = True
            else:
                advance_to_next_player(table)

            return state

    def _handle_fold(self, player: Player) -> None:
        player.in_hand = False
        player.to_act = False
        player.active = False

    def _handle_check(self, player: Player) -> None:
        player.to_act = False

    def _handle_call(self, table: Table, player: Player, call_amount: int) -> None:
        if call_amount <= 0:
            player.to_act = False
            return
        contribution = min(call_amount, player.stack)
        player.stack -= contribution
        player.player_bet += contribution
        player.to_act = False
        sync_pot(table)

    def _handle_raise(self, table: Table, player: Player, raise_to: int) -> None:
        current_bet = getattr(player, "player_bet", 0)
        additional = raise_to - current_bet
        if additional <= 0:
            raise InvalidActionError("Raise must increase total bet")
        if additional > player.stack:
            raise InvalidActionError("Insufficient stack for raise")
        player.stack -= additional
        player.player_bet = raise_to
        previous_call = table.call_amount
        table.call_amount = raise_to
        table.minimal_raise = max(raise_to - previous_call, table.big_blind)
        player.to_act = False
        for other in table.seats:
            if other is player:
                continue
            if getattr(other, "in_hand", False):
                other.to_act = True
        sync_pot(table)


state_manager = PokerStateManager()


def serialize_state(state: Optional[GameState] = None) -> Dict[str, Any]:
    state = state or state_manager.ensure_state()
    table = state.table
    n = len(table.seats)
    btn_pos = table.dealer_position if n else None
    sb = table.seats[state.sb_pos] if n else None
    bb = table.seats[state.bb_pos] if n else None
    active_player = get_active_player(table)

    return {
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
        "available_actions": compute_available_actions(table, hand_complete=state.hand_complete),
        "hand_complete": state.hand_complete,
    }


def reset_game_state(hand_number: int = 1) -> GameState:
    """Convenience helper for tests/backwards compatibility."""
    return state_manager.reset_state(hand_number=hand_number)


__all__ = [
    "GameState",
    "HandCompleteError",
    "InvalidActionError",
    "PokerStateManager",
    "state_manager",
    "serialize_state",
    "reset_game_state",
]
