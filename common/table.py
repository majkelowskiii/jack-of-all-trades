from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player

class Table():
    def __init__(self, name: str):
        self.name = name
        self.seats: list[Player] = []
        self.positions: list[str] = []
        self.pot: int = 0
        self.dealer_position: int = 0
        self.active_position: int = 0
        self.call_amount: int = 0
        # new: blinds and minimal_raise defaults (MVP)
        self.big_blind: int = 100
        self.small_blind: int = self.big_blind // 2
        self.minimal_raise: int = self.big_blind
        self.minimal_bet: int = self.big_blind

    def sit_player(self, player: Player) -> None:
        self.seats.append(player)
        player.sit_at_table(self)
        player.seat_id = self.seats.index(player)

    def change_dealer_position(self):
        # guard against empty table
        if not self.seats:
            return
        self.dealer_position += 1
        self.dealer_position %= len(self.seats)
        self.active_position = self.dealer_position

    def post_blinds(self) -> tuple[int, int]:
        """Post SB and BB; set call_amount and active_position (first to act preflop).

        Returns (sb_pos, bb_pos).
        """
        if len(self.seats) < 2:
            raise RuntimeError("Need at least two players to post blinds")

        sb_pos = (self.dealer_position + 1) % len(self.seats)
        bb_pos = (self.dealer_position + 2) % len(self.seats)

        sb = self.seats[sb_pos]
        bb = self.seats[bb_pos]

        # post small blind
        sb_amount = min(self.small_blind, sb.stack)
        sb.stack -= sb_amount
        sb.player_bet += sb_amount

        # post big blind
        bb_amount = min(self.big_blind, bb.stack)
        bb.stack -= bb_amount
        bb.player_bet += bb_amount

        self.call_amount = bb_amount
        # first to act preflop is left of BB
        self.active_position = (bb_pos + 1) % len(self.seats)

        # Ensure blinds can still act: Big Blind (and Small Blind) must be allowed to act
        # (Big Blind needs the option to check or raise if everyone limps).
        if hasattr(sb, "to_act"):
            sb.to_act = True
        if hasattr(bb, "to_act"):
            bb.to_act = True

        return sb_pos, bb_pos

    def settle_bets_into_pot(self) -> int:
        """Move all player_bet into pot and reset player_bet. Returns amount moved."""
        moved = 0
        for p in self.seats:
            # Skip None or players with zero contributed
            try:
                contributed = getattr(p, "player_bet", 0)
            except Exception:
                contributed = 0
            moved += contributed
            if hasattr(p, "player_bet"):
                p.player_bet = 0
        self.pot += moved
        # reset call amount for next round
        self.call_amount = 0
        return moved