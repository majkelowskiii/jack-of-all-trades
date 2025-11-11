from __future__ import annotations
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .player import Player
    from .table import Table
    from .dealer import Dealer
    from .deck import Deck

class PokerHandEngine():
    def __init__(self, table: 'Table', dealer: 'Dealer'):
        self.table = table
        self.dealer = dealer
        self.raise_count = 0

        # initialize logger for the engine; configure basic logging if nothing is configured
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run_hand(self):
        """High-level entry: initialize and run preflop betting, then settle pot."""
        self.initialize_hand()
        self.pre_flop()
        moved = self.table.settle_bets_into_pot()
        print(f"Preflop finished. Pot: {self.table.pot} (moved {moved})")
        # print players stacks for demo
        for p in self.table.seats:
            print(f"{p} | in_hand={p.in_hand} | stack={p.stack}")

    def initialize_hand(self):
        """Reset state, shuffle and clear cards, and mark players active if they have chips."""
        # reset dealer/deck
        self.dealer.shuffle_cards()
        self.dealer.community_cards.clear()
        # reset players
        for p in self.table.seats:
            p.hole_cards.clear()
            p.in_hand = p.stack > 0
            p.to_act = True
            p.player_bet = 0
        # ensure call amount/raise count cleared
        self.table.call_amount = 0
        self.raise_count = 0

    def pre_flop(self):
        """Deal two hole cards to each player and run a single betting round (preflop)."""
        sb_pos, bb_pos = self.table.post_blinds()

        # Log button/BB/SB positions and players for visibility
        n = len(self.table.seats)
        if n:
            btn_pos = self.table.dealer_position
            btn_player = self.table.seats[btn_pos] if 0 <= btn_pos < n else None
            sb_player = self.table.seats[sb_pos]
            bb_player = self.table.seats[bb_pos]
            self.logger.info(
                "Table positions — BTN: %s (seat %d); SB: %s (seat %d); BB: %s (seat %d)",
                getattr(btn_player, "name", None),
                btn_pos,
                getattr(sb_player, "name", None),
                sb_pos,
                getattr(bb_player, "name", None),
                bb_pos,
            )

        # deal two hole cards starting from small blind (SB) and clockwise
        start = sb_pos
        n = len(self.table.seats)
        for _ in range(2):
            for i in range(n):
                idx = (start + i) % n
                player = self.table.seats[idx]
                # skip players without stack (eliminated)
                if not getattr(player, "in_hand", False):
                    continue
                self.dealer.deal_card_to_player(player)

        # Log hole cards for each player before betting round (use logger so CLI / CI can capture)
        self.logger.info("Hole cards dealt — preflop snapshot:")
        for p in self.table.seats:
            # represent hole cards as a compact string (e.g. "Ah Ks")
            cards_repr = " ".join(repr(c) for c in getattr(p, "hole_cards", []))
            self.logger.info("%s | in_hand=%s | stack=%s | hole_cards=%s", p.name, p.in_hand, p.stack, cards_repr)

        # run betting round
        n_active = sum(1 for p in self.table.seats if getattr(p, "in_hand", False))
        # normalize to_act: everyone in_hand must act except BB who already posted (but may need to act if raised to)
        # We'll rely on loop and flags; start looping
        while True:
            # check if any player still needs to act
            need_act = any(getattr(p, "to_act", False) and getattr(p, "in_hand", False)
                           for p in self.table.seats)
            if not need_act:
                break

            current = self.table.active_position
            player = self.table.seats[current]

            # advance if seat/player not eligible
            if not getattr(player, "in_hand", False) or not getattr(player, "to_act", False):
                self.table.active_position = (self.table.active_position + 1) % n
                continue

            cards_repr = " ".join(repr(c) for c in getattr(player, "hole_cards", []))
            print(
                f"Player to act: {player} | seat={getattr(player,'seat_id',None)} | "
                f"stack={player.stack} | bet={player.player_bet} | call_amount={self.table.call_amount} | hole_cards={cards_repr}"
            )
            self.handle_player_decision(player)

            # advance active_position to next seat
            self.table.active_position = (self.table.active_position + 1) % n

            # break if only one player remains
            remaining = [p for p in self.table.seats if getattr(p, "in_hand", False)]
            if len(remaining) <= 1:
                print("Only one player remaining — hand ends.")
                break

    def handle_player_decision(self, player: 'Player'):
        decision, bet_size = player.make_decision()

        match decision:
            case "e":
                print("Exiting hand.")
                raise SystemExit
            case "f":
                self.handle_fold(player)
            case "c":
                self.handle_call(player)
            case "r":
                assert bet_size is not None
                self.handle_raise(player, bet_size)

    def handle_call(self, player: 'Player'):
        required = max(0, self.table.call_amount - player.player_bet)
        pay = min(required, player.stack)
        player.stack -= pay
        player.player_bet += pay
        player.to_act = False
        print(f"{player} called. Paid {pay}. New bet: {player.player_bet}")

    def handle_fold(self, player: 'Player'):
        player.in_hand = False
        player.to_act = False
        print(f"{player} folded.")

    def handle_raise(self, player: 'Player', raise_amount: int):
        """Interpret raise_amount as additional amount on top of current call_amount."""
        # compute new call target
        new_call = self.table.call_amount + raise_amount
        # amount player must put in total = new_call - player's current contribution
        required = max(0, new_call - player.player_bet)
        pay = min(required, player.stack)
        player.stack -= pay
        player.player_bet += pay

        # update table call amount only if player's contribution reached intended new_call
        # (if payment limited by all-in we still set call_amount to max of previous and player's contribution)
        self.table.call_amount = max(self.table.call_amount, player.player_bet)
        self.raise_count += 1

        # after a raise, all other in-hand players must act again
        for p in self.table.seats:
            if p is not player and getattr(p, "in_hand", False):
                p.to_act = True
        player.to_act = False
        print(f"{player} raised by {raise_amount}. Paid {pay}. New call amount: {self.table.call_amount}")

    def resolve_hand(self):
        # placeholder for showdown logic
        pass


if __name__ == "__main__":
    # runtime imports inside guard to avoid package import cycles when module imported
    from .table import Table
    from .player import Player
    from .dealer import Dealer
    from .deck import Deck

    # demo: 8 players, each with 4000 stack (40 BB at BB=100)
    deck = Deck()
    dealer = Dealer(deck)
    table = Table("Table1")

    player1 = Player("john", 4000)
    player2 = Player("mark", 4000)
    player3 = Player("alice", 4000)
    player4 = Player("sara", 4000)
    player5 = Player("tom", 4000)
    player6 = Player("ryan", 4000)
    player7 = Player("mia", 4000)
    player8 = Player("liam", 4000)

    table.sit_player(player1)
    table.sit_player(player2)
    table.sit_player(player3)
    table.sit_player(player4)
    table.sit_player(player5)
    table.sit_player(player6)
    table.sit_player(player7)
    table.sit_player(player8)

    engine = PokerHandEngine(table, dealer)
    engine.run_hand()