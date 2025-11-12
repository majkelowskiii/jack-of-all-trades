"""Supporting models and helpers for the Blackjack trainer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional, Tuple

from common.card import Card


def card_value(card: Card) -> int:
    """Return the blackjack value of a single card."""
    rank = card.figure.upper()
    if rank in {"K", "Q", "J", "T"}:
        return 10
    if rank == "A":
        return 11
    return int(rank)


def compute_hand_total(cards: Iterable[Card]) -> Tuple[int, bool]:
    """Compute total and whether the hand is soft."""
    total = 0
    aces = 0
    for card in cards:
        value = card_value(card)
        if value == 11:
            aces += 1
        total += value
    is_soft = False
    while total > 21 and aces:
        total -= 10
        aces -= 1
    if aces > 0:
        is_soft = True
    return total, is_soft


class HandStatus(str, Enum):
    """Lifecycle state for a blackjack hand."""

    ACTIVE = "active"
    STANDING = "standing"
    BUSTED = "busted"
    SURRENDERED = "surrendered"
    BLACKJACK = "blackjack"

    def is_terminal(self) -> bool:
        return self in {HandStatus.STANDING, HandStatus.BUSTED, HandStatus.SURRENDERED, HandStatus.BLACKJACK}


@dataclass
class BlackjackHand:
    """Represents a single player hand."""

    cards: List[Card] = field(default_factory=list)
    bet: int = 0
    status: HandStatus = HandStatus.ACTIVE
    doubled: bool = False
    split_from: Optional[int] = None
    has_taken_action: bool = False

    @property
    def total(self) -> int:
        value, _ = compute_hand_total(self.cards)
        return value

    @property
    def is_soft(self) -> bool:
        _, is_soft = compute_hand_total(self.cards)
        return is_soft

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.total == 21

    @property
    def can_split(self) -> bool:
        if len(self.cards) != 2:
            return False
        return card_value(self.cards[0]) == card_value(self.cards[1])

    @property
    def can_double(self) -> bool:
        return len(self.cards) == 2 and not self.doubled and self.status == HandStatus.ACTIVE

    @property
    def can_surrender(self) -> bool:
        return (
            len(self.cards) == 2
            and self.status == HandStatus.ACTIVE
            and not self.has_taken_action
            and self.split_from is None
        )

    @property
    def is_done(self) -> bool:
        return self.status.is_terminal()

    def add_card(self, card: Card) -> None:
        self.cards.append(card)


@dataclass
class BlackjackConfig:
    """Runtime configuration for a blackjack training session."""

    bankroll: int
    shoe_decks: int
    min_bet: int = 10
    max_bet: int = 1000
    blackjack_payout_num: int = 3
    blackjack_payout_den: int = 2
    max_hands: int = 4
    cut_card_ratio: float = 0.25
    dealer_hits_soft_17: bool = False

    def clamp_bet(self, amount: int) -> int:
        return max(self.min_bet, min(amount, self.max_bet))


def serialize_card(card: Optional[Card]) -> dict[str, Optional[str]]:
    return {
        "rank": getattr(card, "figure", None),
        "suit": getattr(card, "suit", None),
    }
