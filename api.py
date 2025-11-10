from flask import Flask, jsonify, make_response
from common.table import Table
from common.dealer import Dealer
from common.deck import Deck
from common.player import Player

app = Flask(__name__)


def build_demo_table():
    """Build a demo table: 8 players, 4000 stack each, shuffle, post blinds and deal hole cards."""
    deck = Deck()
    dealer = Dealer(deck)
    table = Table("Table1")

    names = ["john", "mark", "alice", "sara", "tom", "ryan", "mia", "liam"]
    for n in names:
        table.sit_player(Player(n, 4000))

    # shuffle and post blinds
    dealer.shuffle_cards()
    sb_pos, bb_pos = table.post_blinds()

    # deal two hole cards starting from small blind (SB) clockwise
    n_players = len(table.seats)
    for _ in range(2):
        for i in range(n_players):
            idx = (sb_pos + i) % n_players
            player = table.seats[idx]
            if getattr(player, "in_hand", False):
                dealer.deal_card_to_player(player)

    return table, dealer, sb_pos, bb_pos


@app.route("/api/v1/table", methods=["GET"])
def get_table():
    table, dealer, sb_pos, bb_pos = build_demo_table()
    n = len(table.seats)
    btn_pos = table.dealer_position if n else None
    sb = table.seats[sb_pos] if n else None
    bb = table.seats[bb_pos] if n else None

    players = []
    for i, p in enumerate(table.seats):
        players.append(
            {
                "seat": i,
                "name": getattr(p, "name", None),
                "stack": getattr(p, "stack", 0),
                "hole_cards": [repr(c) for c in getattr(p, "hole_cards", [])],
                "in_hand": getattr(p, "in_hand", False),
                "player_bet": getattr(p, "player_bet", 0),
            }
        )

    data = {
        "name": table.name,
        "dealer_position": btn_pos,
        "sb": {"seat": sb_pos, "name": getattr(sb, "name", None)} if sb is not None else None,
        "bb": {"seat": bb_pos, "name": getattr(bb, "name", None)} if bb is not None else None,
        "players": players,
        "pot": table.pot,
        "call_amount": table.call_amount,
    }

    resp = make_response(jsonify(data))
    # permissive CORS for local demo; tighten in production
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


if __name__ == "__main__":
    # Run with: python api.py
    app.run(host="0.0.0.0", port=5000, debug=True)
