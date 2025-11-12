"""State manager for the Blackjack trainer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

from common.card import Card
from common.shoe import Shoe

from .models import (
    BlackjackConfig,
    BlackjackHand,
    HandStatus,
    card_value,
    compute_hand_total,
    serialize_card,
)

DEFAULT_BANKROLL = 1_000
DEFAULT_DECKS = 5


class BlackjackPhase(str, Enum):
    """Lifecycle phases for a blackjack hand."""

    NEEDS_CONFIGURATION = "awaiting_configuration"
    WAITING_FOR_BET = "awaiting_bet"
    INITIAL_DEAL = "initial_deal"
    INSURANCE = "insurance_offer"
    PLAYER_ACTION = "player_action"
    DEALER_ACTION = "dealer_action"
    COMPLETE = "hand_complete"


class BlackjackError(RuntimeError):
    """Base blackjack exception."""


class MissingConfigurationError(BlackjackError):
    """Raised when attempting to play without configuring the session."""


class InvalidBlackjackAction(BlackjackError):
    """Raised when an invalid action is requested."""


@dataclass
class BlackjackState:
    """In-memory blackjack session."""

    config: Optional[BlackjackConfig] = None
    shoe: Optional[Shoe] = None
    bankroll: int = 0
    dealer_hand: BlackjackHand = field(default_factory=BlackjackHand)
    player_hands: List[BlackjackHand] = field(default_factory=list)
    phase: BlackjackPhase = BlackjackPhase.NEEDS_CONFIGURATION
    hand_number: int = 0
    pending_initial_sequence: List[Tuple[str, int]] = field(default_factory=list)
    active_hand_index: Optional[int] = None
    insurance_bet: int = 0
    messages: List[str] = field(default_factory=list)
    hand_results: List[str] = field(default_factory=list)
    shoe_needs_shuffle: bool = False
    running_count: int = 0
    pending_hidden_cards: List[Card] = field(default_factory=list)
    pending_dealer_steps: List[Tuple[str, Optional[Card]]] = field(default_factory=list)

    def reset_hand_state(self) -> None:
        self.dealer_hand = BlackjackHand()
        self.player_hands = []
        self.pending_initial_sequence = []
        self.active_hand_index = None
        self.insurance_bet = 0
        self.messages.clear()
        self.hand_results.clear()
        self.pending_hidden_cards.clear()
        self.pending_dealer_steps.clear()
        self.phase = BlackjackPhase.WAITING_FOR_BET if self.config else BlackjackPhase.NEEDS_CONFIGURATION


class BlackjackStateManager:
    """Thread-safe blackjack state manager."""

    def __init__(self) -> None:
        self._state = BlackjackState()
        self._lock = RLock()

    def ensure_state(self) -> BlackjackState:
        return self._state

    def reset(self) -> BlackjackState:
        with self._lock:
            self._state = BlackjackState()
            return self._state

    def configure(
        self,
        *,
        bankroll: int,
        shoe_decks: int,
        min_bet: int | None = None,
        max_bet: int | None = None,
    ) -> BlackjackState:
        if bankroll <= 0:
            raise InvalidBlackjackAction("Bankroll must be positive")
        if shoe_decks <= 0:
            raise InvalidBlackjackAction("Shoe must include at least one deck")
        min_bet = min_bet or 10
        max_bet = max_bet or bankroll
        if min_bet <= 0 or max_bet <= 0:
            raise InvalidBlackjackAction("Bet limits must be positive")
        if min_bet > max_bet:
            raise InvalidBlackjackAction("min_bet cannot exceed max_bet")
        with self._lock:
            config = BlackjackConfig(
                bankroll=bankroll,
                shoe_decks=shoe_decks,
                min_bet=min_bet,
                max_bet=max_bet,
            )
            shoe = Shoe(num_decks=shoe_decks)
            state = BlackjackState(
                config=config,
                shoe=shoe,
                bankroll=bankroll,
                phase=BlackjackPhase.WAITING_FOR_BET,
            )
            self._state = state
            return state

    def start_next_hand(self) -> BlackjackState:
        with self._lock:
            state = self.ensure_state()
            if state.config is None or state.shoe is None:
                raise MissingConfigurationError("Configure blackjack before starting a hand.")
            if state.phase == BlackjackPhase.INITIAL_DEAL:
                raise InvalidBlackjackAction("Initial deal in progress. Finish dealing first.")
            if state.phase == BlackjackPhase.PLAYER_ACTION:
                raise InvalidBlackjackAction("Hand in progress. Finish playing before starting another.")
            if state.shoe_needs_shuffle:
                state.shoe.reset()
                state.shoe_needs_shuffle = False
                state.running_count = 0
                state.pending_hidden_cards.clear()
                state.pending_dealer_steps.clear()
            state.reset_hand_state()
            return state

    def apply_action(self, *, action: str, payload: Dict[str, Any]) -> BlackjackState:
        with self._lock:
            state = self.ensure_state()
            if state.config is None or state.shoe is None:
                raise MissingConfigurationError("Configure blackjack before playing.")

            handlers = {
                "place_bet": self._handle_place_bet,
                "deal": self._handle_deal,
                "hit": self._handle_hit,
                "stand": self._handle_stand,
                "double": self._handle_double,
                "split": self._handle_split,
                "surrender": self._handle_surrender,
                "buy_insurance": self._handle_buy_insurance,
                "skip_insurance": self._handle_skip_insurance,
                "dealer_step": self._handle_dealer_step,
            }
            handler = handlers.get(action)
            if handler is None:
                raise InvalidBlackjackAction(f"Unsupported action '{action}'")
            handler(state, payload)
            return state

    # -- action handlers -------------------------------------------------

    def _handle_place_bet(self, state: BlackjackState, payload: Dict[str, Any]) -> None:
        if state.phase not in {BlackjackPhase.WAITING_FOR_BET, BlackjackPhase.COMPLETE}:
            raise InvalidBlackjackAction("Cannot place a bet during an active hand.")
        amount = payload.get("amount")
        if not isinstance(amount, int):
            raise InvalidBlackjackAction("Bet amount must be integer.")
        amount = max(state.config.min_bet, min(amount, state.config.max_bet))
        if amount > state.bankroll:
            raise InvalidBlackjackAction("Insufficient bankroll for bet.")
        if amount < state.config.min_bet:
            raise InvalidBlackjackAction("Bet amount below table minimum.")
        state.hand_number += 1
        state.player_hands = [BlackjackHand(bet=amount)]
        state.dealer_hand = BlackjackHand()
        state.pending_hidden_cards.clear()
        state.pending_initial_sequence = []
        hand_indices = list(range(len(state.player_hands)))
        # First orbit: everyone (including dealer) sees exactly one card.
        for idx in hand_indices:
            state.pending_initial_sequence.append(("player", idx))
        state.pending_initial_sequence.append(("dealer", 0))
        # Second orbit: players finish their opening hands before the dealer closes the deal.
        for idx in hand_indices:
            state.pending_initial_sequence.append(("player", idx))
        state.pending_initial_sequence.append(("dealer", 0))
        state.active_hand_index = 0
        state.phase = BlackjackPhase.INITIAL_DEAL
        state.bankroll -= amount
        state.insurance_bet = 0
        state.messages = [f"Hand #{state.hand_number} — bet {amount} chips."]
        state.hand_results.clear()

    def _handle_deal(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        if state.phase != BlackjackPhase.INITIAL_DEAL:
            raise InvalidBlackjackAction("Initial deal already finished.")
        if not state.pending_initial_sequence:
            raise InvalidBlackjackAction("All initial cards dealt.")
        target, hand_index = state.pending_initial_sequence.pop(0)
        card = self._draw_card(state)
        if target == "player":
            state.player_hands[hand_index].add_card(card)
            self._apply_running_count(state, card)
        else:
            state.dealer_hand.add_card(card)
            if len(state.dealer_hand.cards) == 1:
                self._apply_running_count(state, card)
            else:
                self._queue_hidden_card(state, card)
        if not state.pending_initial_sequence:
            self._post_initial_deal(state)

    def _handle_hit(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        hand = self._require_active_hand(state)
        card = self._draw_card(state)
        hand.add_card(card)
        self._apply_running_count(state, card)
        hand.has_taken_action = True
        total, _ = compute_hand_total(hand.cards)
        if total > 21:
            hand.status = HandStatus.BUSTED
            state.messages.append(f"Hand {self._hand_label(state)} busts with {total}.")
            self._advance_hand(state)
        elif total == 21:
            hand.status = HandStatus.STANDING
            state.messages.append(f"Hand {self._hand_label(state)} locks at 21.")
            self._advance_hand(state)

    def _handle_stand(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        hand = self._require_active_hand(state)
        hand.status = HandStatus.STANDING
        hand.has_taken_action = True
        state.messages.append(f"Hand {self._hand_label(state)} stands on {hand.total}.")
        self._advance_hand(state)

    def _handle_double(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        hand = self._require_active_hand(state)
        if not hand.can_double:
            raise InvalidBlackjackAction("Double allowed only on two cards before taking another action.")
        if state.bankroll < hand.bet:
            raise InvalidBlackjackAction("Insufficient bankroll to double.")
        state.bankroll -= hand.bet
        hand.bet *= 2
        hand.doubled = True
        hand.has_taken_action = True
        card = self._draw_card(state)
        hand.add_card(card)
        self._apply_running_count(state, card)
        total, _ = compute_hand_total(hand.cards)
        hand.status = HandStatus.BUSTED if total > 21 else HandStatus.STANDING
        state.messages.append(f"Double down {'busts' if total > 21 else 'stands'} with {total}.")
        self._advance_hand(state)

    def _handle_split(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        hand = self._require_active_hand(state)
        if not hand.can_split:
            raise InvalidBlackjackAction("Need a pair to split.")
        if len(state.player_hands) >= state.config.max_hands:
            raise InvalidBlackjackAction("Maximum number of hands reached.")
        if state.bankroll < hand.bet:
            raise InvalidBlackjackAction("Insufficient bankroll to split.")
        state.bankroll -= hand.bet
        moved_card = hand.cards.pop()
        new_hand = BlackjackHand(cards=[moved_card], bet=hand.bet, split_from=state.active_hand_index)
        state.player_hands.insert(state.active_hand_index + 1, new_hand)
        # deal one more card to each split hand
        card_one = self._draw_card(state)
        hand.add_card(card_one)
        self._apply_running_count(state, card_one)
        self._mark_hand_blackjack(state, hand)
        card_two = self._draw_card(state)
        new_hand.add_card(card_two)
        self._apply_running_count(state, card_two)
        self._mark_hand_blackjack(state, new_hand)
        state.messages.append(f"Hand {self._hand_label(state)} splits into two hands.")

    def _handle_surrender(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        hand = self._require_active_hand(state)
        if not hand.can_surrender:
            raise InvalidBlackjackAction("Late surrender not available.")
        refund = hand.bet // 2
        state.bankroll += refund
        hand.status = HandStatus.SURRENDERED
        hand.has_taken_action = True
        state.messages.append(f"Hand {self._hand_label(state)} surrendered. Refunded {refund}.")
        self._advance_hand(state)

    def _handle_buy_insurance(self, state: BlackjackState, payload: Dict[str, Any]) -> None:
        if state.phase != BlackjackPhase.INSURANCE:
            raise InvalidBlackjackAction("Insurance only offered when dealer shows an Ace.")
        amount = payload.get("amount")
        if not isinstance(amount, int):
            raise InvalidBlackjackAction("Insurance amount must be integer.")
        max_allowed = min(state.player_hands[0].bet // 2, state.bankroll)
        if max_allowed <= 0:
            raise InvalidBlackjackAction("Insurance not affordable.")
        if not 0 < amount <= max_allowed:
            raise InvalidBlackjackAction("Insurance exceeds limit.")
        state.bankroll -= amount
        state.insurance_bet = amount
        self._peek_after_insurance(state)

    def _handle_skip_insurance(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        if state.phase != BlackjackPhase.INSURANCE:
            raise InvalidBlackjackAction("No insurance decision pending.")
        self._peek_after_insurance(state, skipped=True)

    def _handle_dealer_step(self, state: BlackjackState, _: Dict[str, Any]) -> None:
        if state.phase != BlackjackPhase.DEALER_ACTION:
            raise InvalidBlackjackAction("Dealer is not acting currently.")
        if not state.pending_dealer_steps:
            raise InvalidBlackjackAction("Dealer has no pending steps.")
        step, card = state.pending_dealer_steps.pop(0)
        if step == "reveal":
            self._reveal_hidden_cards(state)
        elif step == "draw":
            if card is None:
                raise InvalidBlackjackAction("Dealer draw step missing card.")
            state.dealer_hand.add_card(card)
            self._apply_running_count(state, card)
        else:
            raise InvalidBlackjackAction("Unknown dealer step.")
        if not state.pending_dealer_steps:
            self._resolve_hands(state)
    # -- helpers ---------------------------------------------------------

    def _draw_card(self, state: BlackjackState) -> Card:
        assert state.shoe is not None
        card = state.shoe.draw()
        state.shoe_needs_shuffle = state.shoe.needs_shuffle(state.config.cut_card_ratio)
        return card

    @staticmethod
    def _count_delta(card: Card) -> int:
        figure = (card.figure or "").upper()
        if figure in {"2", "3", "4", "5", "6"}:
            return 1
        if figure in {"7", "8", "9"}:
            return 0
        # T, J, Q, K, A or any other defaults to -1
        return -1

    def _apply_running_count(self, state: BlackjackState, card: Card) -> None:
        state.running_count += self._count_delta(card)

    def _queue_hidden_card(self, state: BlackjackState, card: Card) -> None:
        state.pending_hidden_cards.append(card)

    def _reveal_hidden_cards(self, state: BlackjackState) -> None:
        if not state.pending_hidden_cards:
            return
        for card in state.pending_hidden_cards:
            self._apply_running_count(state, card)
        state.pending_hidden_cards.clear()

    def _post_initial_deal(self, state: BlackjackState) -> None:
        player_hand = state.player_hands[0]
        dealer_hand = state.dealer_hand
        player_blackjack = player_hand.is_blackjack
        dealer_blackjack = dealer_hand.is_blackjack

        if player_blackjack:
            player_hand.status = HandStatus.BLACKJACK

        upcard_value = card_value(dealer_hand.cards[0])
        if upcard_value == 11:
            state.phase = BlackjackPhase.INSURANCE
            state.messages.append("Dealer shows an Ace — insurance available.")
            return

        if player_blackjack and not dealer_blackjack:
            self._payout_blackjack(state, player_hand)
            return

        if dealer_blackjack:
            self._resolve_dealer_blackjack(state)
            return

        state.phase = BlackjackPhase.PLAYER_ACTION
        state.active_hand_index = 0
        state.messages.append("Player to act.")

    def _peek_after_insurance(self, state: BlackjackState, skipped: bool = False) -> None:
        dealer_has_blackjack = state.dealer_hand.is_blackjack
        if dealer_has_blackjack:
            self._resolve_dealer_blackjack(state)
            return
        if state.insurance_bet and not skipped:
            state.messages.append("Insurance lost.")
            state.insurance_bet = 0
        if state.player_hands and state.player_hands[0].is_blackjack:
            self._payout_blackjack(state, state.player_hands[0])
            return
        state.phase = BlackjackPhase.PLAYER_ACTION
        state.active_hand_index = 0
        state.messages.append("No dealer blackjack — continue playing.")

    def _resolve_dealer_blackjack(self, state: BlackjackState) -> None:
        self._reveal_hidden_cards(state)
        state.phase = BlackjackPhase.COMPLETE
        state.active_hand_index = None
        dealer_blackjack = True
        player_hand = state.player_hands[0] if state.player_hands else None
        if player_hand and player_hand.is_blackjack:
            state.bankroll += player_hand.bet
            state.hand_results.append("Push vs dealer blackjack.")
        elif player_hand:
            state.hand_results.append("Dealer blackjack — hand lost.")
        if state.insurance_bet:
            state.bankroll += state.insurance_bet * 3
            state.messages.append("Insurance pays 2:1.")
            state.insurance_bet = 0
        state.pending_dealer_steps.clear()
        state.messages.append("Hand complete. Dealer had blackjack.")

    def _require_active_hand(self, state: BlackjackState) -> BlackjackHand:
        if state.phase != BlackjackPhase.PLAYER_ACTION:
            raise InvalidBlackjackAction("Player actions available only during player phase.")
        if state.active_hand_index is None:
            raise InvalidBlackjackAction("No active hand.")
        try:
            hand = state.player_hands[state.active_hand_index]
        except IndexError as exc:
            raise InvalidBlackjackAction("Invalid hand index.") from exc
        if hand.status != HandStatus.ACTIVE:
            raise InvalidBlackjackAction("Selected hand already completed.")
        return hand

    def _hand_label(self, state: BlackjackState) -> str:
        if state.active_hand_index is None:
            return "#"
        return f"#{state.active_hand_index + 1}"

    def _advance_hand(self, state: BlackjackState) -> None:
        if not state.player_hands:
            return
        for i in range(state.active_hand_index + 1 if state.active_hand_index is not None else 0, len(state.player_hands)):
            if state.player_hands[i].status == HandStatus.ACTIVE:
                state.active_hand_index = i
                return
        state.active_hand_index = None
        self._start_dealer_action(state)

    def _start_dealer_action(self, state: BlackjackState) -> None:
        state.phase = BlackjackPhase.DEALER_ACTION
        state.pending_dealer_steps.clear()
        if state.pending_hidden_cards:
            state.pending_dealer_steps.append(("reveal", None))
        temp_hand = BlackjackHand(cards=list(state.dealer_hand.cards))
        all_player_busted = self._all_player_hands_busted(state)
        if not all_player_busted:
            while True:
                total, is_soft = compute_hand_total(temp_hand.cards)
                need_card = False
                if total < 17:
                    need_card = True
                elif total == 17 and state.config.dealer_hits_soft_17 and is_soft:
                    need_card = True
                if not need_card:
                    break
                card = self._draw_card(state)
                state.pending_dealer_steps.append(("draw", card))
                temp_hand.add_card(card)
        if not state.pending_dealer_steps:
            self._reveal_hidden_cards(state)
            self._resolve_hands(state)

    def _all_player_hands_busted(self, state: BlackjackState) -> bool:
        return bool(state.player_hands) and all(hand.status == HandStatus.BUSTED for hand in state.player_hands)

    def _resolve_hands(self, state: BlackjackState) -> None:
        state.pending_dealer_steps.clear()
        dealer_total, _ = compute_hand_total(state.dealer_hand.cards)
        dealer_busted = dealer_total > 21
        state.hand_results.clear()
        for idx, hand in enumerate(state.player_hands):
            label = f"Hand {idx + 1}"
            if hand.status == HandStatus.SURRENDERED:
                state.hand_results.append(f"{label}: surrendered (lose half bet).")
                continue
            if hand.status == HandStatus.BUSTED:
                state.hand_results.append(f"{label}: bust.")
                continue
            if hand.status == HandStatus.BLACKJACK:
                bonus = (hand.bet * state.config.blackjack_payout_num) // state.config.blackjack_payout_den
                state.bankroll += hand.bet + bonus
                state.hand_results.append(f"{label}: blackjack pays 3:2.")
                continue
            hand_total, _ = compute_hand_total(hand.cards)
            if dealer_busted:
                state.bankroll += hand.bet * 2
                state.hand_results.append(f"{label}: dealer busts, you win.")
            elif hand_total > dealer_total:
                state.bankroll += hand.bet * 2
                state.hand_results.append(f"{label}: win with {hand_total} vs dealer {dealer_total}.")
            elif hand_total == dealer_total:
                state.bankroll += hand.bet
                state.hand_results.append(f"{label}: push on {hand_total}.")
            else:
                state.hand_results.append(f"{label}: lose with {hand_total} vs {dealer_total}.")
        state.phase = BlackjackPhase.COMPLETE
        state.active_hand_index = None
        state.messages.append("Hand resolved.")

    def _mark_hand_blackjack(self, state: BlackjackState, hand: BlackjackHand) -> None:
        if not hand.is_blackjack or hand.status != HandStatus.ACTIVE:
            return
        try:
            idx = state.player_hands.index(hand)
        except ValueError:
            return
        hand.status = HandStatus.BLACKJACK
        hand.has_taken_action = True
        state.messages.append(f"Hand {idx + 1} hits blackjack.")
        if state.active_hand_index == idx:
            self._advance_hand(state)

    def _payout_blackjack(self, state: BlackjackState, hand: BlackjackHand) -> None:
        hand.status = HandStatus.BLACKJACK
        bonus = (hand.bet * state.config.blackjack_payout_num) // state.config.blackjack_payout_den
        state.bankroll += hand.bet + bonus
        state.messages.append("Blackjack! Paid 3:2.")
        state.hand_results.append("Blackjack paid.")
        state.phase = BlackjackPhase.COMPLETE
        state.active_hand_index = None

    # -- serialization ---------------------------------------------------

    def serialize_state(self, state: Optional[BlackjackState] = None) -> Dict[str, Any]:
        state = state or self.ensure_state()
        if state.config is None or state.shoe is None:
            return {
                "phase": BlackjackPhase.NEEDS_CONFIGURATION.value,
                "requires_configuration": True,
                "defaults": {"bankroll": DEFAULT_BANKROLL, "shoe_decks": DEFAULT_DECKS, "min_bet": 10},
                "available_actions": {"can_configure": True},
            }

        hands_payload = []
        for idx, hand in enumerate(state.player_hands):
            total, is_soft = compute_hand_total(hand.cards)
            hands_payload.append(
                {
                    "id": idx,
                    "cards": [serialize_card(card) for card in hand.cards],
                    "bet": hand.bet,
                    "status": hand.status.value,
                    "total": total,
                    "is_soft": is_soft,
                    "is_blackjack": hand.status == HandStatus.BLACKJACK,
                    "can_split": hand.can_split
                    and len(state.player_hands) < state.config.max_hands
                    and state.bankroll >= hand.bet,
                    "can_double": hand.can_double and state.bankroll >= hand.bet,
                    "can_surrender": hand.can_surrender,
                }
            )

        reveal_all = (
            state.phase in {BlackjackPhase.DEALER_ACTION, BlackjackPhase.COMPLETE}
            and not state.pending_hidden_cards
        )
        visible_cards = state.dealer_hand.cards if reveal_all else state.dealer_hand.cards[:1]
        hidden_count = 0 if reveal_all else max(0, len(state.dealer_hand.cards) - len(visible_cards))
        visible_total, _ = compute_hand_total(visible_cards)
        dealer_payload: Dict[str, Any] = {
            "cards": [serialize_card(card) for card in visible_cards],
            "hidden_cards": hidden_count,
            "visible_total": visible_total,
            "hole_card_revealed": reveal_all,
        }
        if reveal_all:
            total, is_soft = compute_hand_total(state.dealer_hand.cards)
            dealer_payload["total"] = total
            dealer_payload["is_soft"] = is_soft

        available_actions = {
            "can_place_bet": state.phase == BlackjackPhase.WAITING_FOR_BET
            and state.bankroll >= state.config.min_bet,
            "can_deal": state.phase == BlackjackPhase.INITIAL_DEAL and bool(state.pending_initial_sequence),
            "can_hit": state.phase == BlackjackPhase.PLAYER_ACTION and self._has_active_hand(state),
            "can_stand": state.phase == BlackjackPhase.PLAYER_ACTION and self._has_active_hand(state),
            "can_double": self._current_hand_can(state, "double"),
            "can_split": self._current_hand_can(state, "split"),
            "can_surrender": self._current_hand_can(state, "surrender"),
            "can_buy_insurance": state.phase == BlackjackPhase.INSURANCE,
            "can_skip_insurance": state.phase == BlackjackPhase.INSURANCE,
            "can_start_next_hand": state.phase == BlackjackPhase.COMPLETE,
            "can_step_dealer": state.phase == BlackjackPhase.DEALER_ACTION
            and bool(state.pending_dealer_steps),
        }

        max_bet = min(state.config.max_bet, state.bankroll)
        cards_remaining = state.shoe.cards_remaining()
        decks_remaining = cards_remaining / 52 if cards_remaining > 0 else 0
        true_count = state.running_count / decks_remaining if decks_remaining > 0 else 0.0

        return {
            "phase": state.phase.value,
            "requires_configuration": False,
            "hand_number": state.hand_number,
            "player": {
                "bankroll": state.bankroll,
                "hands": hands_payload,
                "active_hand_index": state.active_hand_index,
                "bet_limits": {"min": state.config.min_bet, "max": max_bet},
            },
            "dealer": dealer_payload,
            "shoe": {
                "decks": state.config.shoe_decks,
                "cards_remaining": state.shoe.cards_remaining(),
                "total_cards": state.shoe.total_cards(),
                "needs_shuffle": state.shoe_needs_shuffle,
                "penetration": state.shoe.penetration(),
            },
            "pending_initial_deal": len(state.pending_initial_sequence),
            "insurance": {
                "current": state.insurance_bet,
                "allowed": state.phase == BlackjackPhase.INSURANCE,
                "max": min(state.player_hands[0].bet // 2 if state.player_hands else 0, state.bankroll),
            },
            "available_actions": available_actions,
            "messages": state.messages,
            "hand_results": state.hand_results,
            "running_count": state.running_count,
            "true_count": round(true_count, 2),
            "decks_remaining": round(decks_remaining, 2),
            "dealer_steps_remaining": len(state.pending_dealer_steps),
        }

    def _has_active_hand(self, state: BlackjackState) -> bool:
        if state.phase != BlackjackPhase.PLAYER_ACTION or state.active_hand_index is None:
            return False
        try:
            hand = state.player_hands[state.active_hand_index]
        except IndexError:
            return False
        return hand.status == HandStatus.ACTIVE

    def _current_hand_can(self, state: BlackjackState, action: str) -> bool:
        if state.phase != BlackjackPhase.PLAYER_ACTION or state.active_hand_index is None:
            return False
        hand = state.player_hands[state.active_hand_index]
        if action == "double":
            return hand.can_double and state.bankroll >= hand.bet
        if action == "split":
            return (
                hand.can_split
                and len(state.player_hands) < state.config.max_hands
                and state.bankroll >= hand.bet
            )
        if action == "surrender":
            return hand.can_surrender
        return False


blackjack_state_manager = BlackjackStateManager()


def serialize_state(state: Optional[BlackjackState] = None) -> Dict[str, Any]:
    """Helper to serialize the blackjack state."""
    return blackjack_state_manager.serialize_state(state)


def reset_blackjack_state() -> BlackjackState:
    """Reset the blackjack state to unconfigured defaults."""
    return blackjack_state_manager.reset()


__all__ = [
    "DEFAULT_BANKROLL",
    "DEFAULT_DECKS",
    "BlackjackState",
    "BlackjackStateManager",
    "BlackjackPhase",
    "BlackjackError",
    "InvalidBlackjackAction",
    "MissingConfigurationError",
    "blackjack_state_manager",
    "serialize_state",
    "reset_blackjack_state",
]
