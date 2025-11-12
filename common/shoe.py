"""Blackjack shoe implementation built on top of Deck."""

from __future__ import annotations

from typing import Iterable, List

from .card import Card
from .deck import Deck


class Shoe(Deck):
    """A multi-deck shoe that keeps state between hands."""

    def __init__(self, num_decks: int = 6, figures: Iterable[str] | None = None, suits: Iterable[str] | None = None):
        if num_decks < 1:
            raise ValueError("Shoe must contain at least one deck")

        self.num_decks = num_decks
        self._figures = list(figures or self.default_figures)
        self._suits = list(suits or self.default_suits)
        self.discard_pile: list[Card] = []

        super().__init__(figures=self._figures, suits=self._suits)
        self._rebuild_shoe()

    def _rebuild_shoe(self) -> None:
        base_cards = list(self.deck)
        cards: List[Card] = []
        for _ in range(self.num_decks):
            for card in base_cards:
                cards.append(Card(card.figure, card.suit))
        self.deck = cards
        self._total_cards = len(self.deck)
        self.shuffle_deck()

    def draw(self) -> Card:
        if not self.deck:
            raise RuntimeError("Shoe is empty. Reset before drawing additional cards.")
        card = self.deck.pop()
        self.discard_pile.append(card)
        return card

    def cards_remaining(self) -> int:
        return len(self.deck)

    def total_cards(self) -> int:
        return self._total_cards

    def penetration(self) -> float:
        if self._total_cards == 0:
            return 1.0
        return 1.0 - (self.cards_remaining() / self._total_cards)

    def needs_shuffle(self, threshold_ratio: float = 0.25) -> bool:
        if not 0 < threshold_ratio <= 1:
            raise ValueError("threshold_ratio must be between 0 and 1")
        return self.cards_remaining() <= int(self._total_cards * threshold_ratio)

    def reset(self) -> None:
        """Rebuild the shoe from scratch and shuffle."""
        self.discard_pile.clear()
        self._rebuild_shoe()
