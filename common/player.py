from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .table import Table
    from .card import Card

class Player():
    def __init__(self, name: str, stack: int, table: Optional['Table']=None):
        self.name = name
        self.hole_cards: list['Card'] = []
        self.in_hand: bool = True
        self.to_act: bool = True
        self.active: bool = True
        self.stack = stack
        self.seat_id: int = None
        self.position: str = None
        self.player_bet: int = 0
        self.table = table

    def __repr__(self):
        return f"Player {self.name} ({self.stack})"

    def receive_card(self, card: 'Card'):
        self.hole_cards.append(card)

    def make_decision(self) -> tuple[str, int | None]:
        choices = ("c", "f", "r", "e")
        choices_message = "Choose decision [(c)all, (f)old, (r)aise, (e)xit]: "
        bet_size = None

        while True:
            decision = input(f"{choices_message}")
            if decision in choices:
                break
            print("That is not a valid decision.")
        
        if decision == "r":
            bet_size = self.choose_bet_size()        

        return decision, bet_size
    
    def sit_at_table(self, table: 'Table'):
        self.table = table

    def choose_bet_size(self):
        # defensive: ensure table exists
        if self.table is None:
            raise RuntimeError("Player is not seated at a table")
        while True:
            bet_size = input("Choose bet sizing: ")
            if bet_size.isnumeric():
                bet_size = int(bet_size)
                if bet_size >= self.table.minimal_bet:
                    break

        return bet_size