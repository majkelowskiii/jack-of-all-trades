from .card import Card

class Deck():
    #TODO implement factory function
    #TODO implement setters and getters for Cards
    #TODO implement the iter, len, getitem magic functions and pop function

    def __init__(self):
        figures = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        suits = ['spades', 'diamonds', 'hearts', 'clubs']

        self.deck = []

        for suit in suits:
            for figure in figures:
                card = Card(figure, suit)
                self.deck.append(card)

    def __repr__(self):
        return f"{self.deck}"


if __name__ == "__main__":
    d = Deck()

    print(type(d))
    print(d)

    for card in d:
        print(card)