from __future__ import annotations
from typing import TYPE_CHECKING
from .card import Card
from .deck import Deck

if TYPE_CHECKING:
    from .player import Player

class Dealer():
    def __init__(self, deck: Deck):
        self.deck = deck
        self.muck = []
        self.community_cards = []

    def shuffle_cards(self):
        self.deck.shuffle_deck()

    def deal_card_to_player(self, player: 'Player'):
        player.receive_card(self.deck.pop())

    def burn_card(self):
        self.muck.append(self.deck.pop())

    def deal_community_card(self):
        """Deal a single community card from the deck to the community pile."""
        self.community_cards.append(self.deck.pop())