from __future__ import annotations
from card import Card

class Player():
    def __init__(self, name):
        self.name = name
        self.hole_cards = []

    def receive_card(self, card: Card):
        self.hole_cards.append(card)