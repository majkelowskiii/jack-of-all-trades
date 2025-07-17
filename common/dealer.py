from __future__ import annotations
from card import Card
from deck import Deck

class Dealer():
    def __init__(self, deck: Deck):
        self.deck = deck
        self.muck = []
        self.community_cards = []

    def shuffle_cards(self):
        self.deck.shuffle_deck()

    def deal_card_to_player(self, player: Player):
        player.receive_card(self.deck.pop())

    def burn_card(self):
        self.muck.append(self.deck.pop())

    def deal_community_card(self, community_card: list):
        self.community_cards.append(self.deck.pop())