class Card():
    def __init__(self, figure: chr, color: str):
        self.figure = figure
        self.color = color

    def __repr__(self):
        return f"{self.figure}{self.color[0]}"


class Deck():
    def __repr__(self):
        return f"{self.deck}"
    
    def __init__(self):
        figures = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        colors = ['spades', 'diamonds', 'hearts', 'clubs']

        self.deck = []

        for color in colors:
            for figure in figures:
                self.deck.append(Card(figure, color))


if __name__ == "__main__":
    d = Deck()

    print(type(d))
    print(d)