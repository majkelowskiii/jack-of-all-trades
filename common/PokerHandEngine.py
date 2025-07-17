from player import Player
from table import Table
from dealer import Dealer

class PokerHandEngine():
    def __init__(self, table: Table, dealer: Dealer):
        self.table = table
        self.dealer = dealer
        self.raise_count = 0

    def run_hand(self):
        pass

    def initialize_hand(self):
        pass

    def pre_flop():
        pass

    def handle_player_decision(self, player: Player):
        decision, bet_size = player.make_decision()

        match decision:
            case "e":
                #exit
                pass
            case "f":
                self.handle_fold(player)
            case "c":
                self.handle_call(player)
            case "r":
                assert bet_size is not None
                self.handle_raise(player, bet_size) 

    def handle_call(self, player: Player):
        pass

    def handle_fold(self, player: Player):
        pass

    def handle_raise(self, player: Player, bet_size):
        pass

    def resolve_hand(self):
        # could be showdown() ?
        pass
    


