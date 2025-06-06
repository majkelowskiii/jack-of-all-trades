class Card():
    def __init__(self, figure, suit):
        self.figure = figure
        self.suit = suit

    def get_figure(self):
        return self.figure
    
    def get_suit(self):
        return self.suit

    def __repr__(self):
        return f"{self.figure}{self.suit[0]}"
