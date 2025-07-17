from player import Player

class Table():
    def __init__(self, name: str):
        self.name = name
        self.seats: list[Player] = []
        self.positions: list[str] = []
        self.pot: int = 0
        self.dealer_position: int = 0
        self.active_position: int = self.dealer_position % len(self.seats)
        self.call_amount: int = 0
        self.minimal_bet: int = 1

    def sit_player(self, player: Player) -> None:
        self.seats.append(player)
        player.sit_at_table(self)
        player.seat_id = self.seats.index(player)

    def change_dealer_position(self):
        self.dealer_position += 1
        self.dealer_position %= len(self.seats)
        self.active_position = self.dealer_position