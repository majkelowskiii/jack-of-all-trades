from card import Card

class Deck():
    #TODO implement factory function
    #TODO implement setters and getters for Cards
    #TODO implement the iter, len, getitem magic functions and pop function
    default_figures = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    default_suits = ['spades', 'diamonds', 'hearts', 'clubs']


    def __init__(self, figures=None, suits=None):
        figures = figures or self.default_figures
        suits = suits or self.default_suits

        self.deck = [Card(figure, suit) for figure in figures for suit in suits]

    def __repr__(self):
        return f"{self.deck}"
    
    def __iter__(self):
        return iter(self.deck)
    
    def __len__(self):
        return len(self.deck)
    
    def __getitem__(self, index):
        return self.deck[index]
    
    def pop(self, index=-1):
        return self.deck.pop(index)


if __name__ == "__main__":
    d = Deck()

    print(type(d))
    print(d)

    for card in d:
        print(card, f"{card.figure} of {card.suit}")