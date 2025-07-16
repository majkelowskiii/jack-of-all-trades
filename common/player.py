class Player():
    def __init__(self, name):
        self.name = name
        self.hole_cards = []

    def recieve_card(self, card: Card):
        self.hole_cards.append(card)