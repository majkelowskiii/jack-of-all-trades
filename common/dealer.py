from __future__ import annotations
from card import Card
from player import Player
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


if __name__ == "__main__":
    player1 = Player("John")
    player2 = Player("Blah")

    dealer = Dealer(deck=Deck())

    print(dealer.deck)
    print()

    dealer.burn_card()
    dealer.burn_card()
    print(dealer.deck)
    print(dealer.muck)

    dealer.shuffle_cards()
    print(dealer.deck)

    print()
    dealer.deal_card_to_player(player1)
    dealer.deal_card_to_player(player2)
    dealer.deal_card_to_player(player1)
    dealer.deal_card_to_player(player2)
    print(dealer.deck)
    print(player1.hole_cards)
    print(player2.hole_cards)