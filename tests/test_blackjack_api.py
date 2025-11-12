"""Tests for the blackjack trainer API."""

from __future__ import annotations

from typing import Iterable

from flask.testing import FlaskClient

from common.card import Card
from app.services.blackjack.state_manager import blackjack_state_manager


def configure_session(client: FlaskClient, bankroll: int = 1_000, decks: int = 4) -> None:
    response = client.post(
        "/api/v1/blackjack/config",
        json={"bankroll": bankroll, "shoe_decks": decks, "min_bet": 10, "max_bet": bankroll},
    )
    assert response.status_code == 201


def rig_shoe(cards: Iterable[Card]) -> None:
    """Force the shoe to emit cards in the provided order."""
    state = blackjack_state_manager.ensure_state()
    assert state.shoe is not None
    sequence = list(cards)
    state.shoe.deck = list(reversed(sequence))
    state.shoe.discard_pile.clear()


def deal_initial_cards(client: FlaskClient) -> None:
    for _ in range(4):
        resp = client.post("/api/v1/blackjack/table/action", json={"action": "deal"})
        assert resp.status_code == 200


def test_blackjack_requires_configuration(client: FlaskClient) -> None:
    response = client.get("/api/v1/blackjack/table")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["requires_configuration"] is True


def test_blackjack_configuration_sets_initial_bankroll(client: FlaskClient) -> None:
    configure_session(client, bankroll=2_000, decks=6)
    response = client.get("/api/v1/blackjack/table")
    data = response.get_json()
    assert data["phase"] == "awaiting_bet"
    assert data["player"]["bankroll"] == 2_000
    assert data["shoe"]["decks"] == 6


def test_blackjack_hit_to_twenty_one_finishes_hand(client: FlaskClient) -> None:
    configure_session(client)
    rig_shoe(
        [
            Card("9", "hearts"),
            Card("6", "clubs"),
            Card("2", "diamonds"),
            Card("5", "spades"),
            Card("K", "hearts"),
            Card("9", "clubs"),
        ]
    )
    bet_resp = client.post("/api/v1/blackjack/table/action", json={"action": "place_bet", "amount": 100})
    assert bet_resp.status_code == 200
    deal_initial_cards(client)
    hit_resp = client.post("/api/v1/blackjack/table/action", json={"action": "hit"})
    assert hit_resp.status_code == 200
    snapshot = hit_resp.get_json()
    assert snapshot["phase"] == "hand_complete"
    assert snapshot["player"]["hands"][0]["status"] == "standing"
    assert any("win" in result.lower() for result in snapshot["hand_results"])


def test_blackjack_double_down_pays_out(client: FlaskClient) -> None:
    configure_session(client)
    rig_shoe(
        [
            Card("5", "hearts"),
            Card("3", "clubs"),
            Card("6", "diamonds"),
            Card("9", "spades"),
            Card("K", "clubs"),
            Card("8", "hearts"),
        ]
    )
    client.post("/api/v1/blackjack/table/action", json={"action": "place_bet", "amount": 100})
    deal_initial_cards(client)
    response = client.post("/api/v1/blackjack/table/action", json={"action": "double"})
    assert response.status_code == 200
    snapshot = response.get_json()
    assert snapshot["phase"] == "hand_complete"
    assert snapshot["player"]["bankroll"] == 1_200
    assert "double" in " ".join(snapshot["messages"]).lower()


def test_blackjack_split_and_play_both_hands(client: FlaskClient) -> None:
    configure_session(client)
    rig_shoe(
        [
            Card("8", "hearts"),
            Card("6", "clubs"),
            Card("8", "diamonds"),
            Card("9", "spades"),
            Card("2", "hearts"),
            Card("3", "hearts"),
            Card("K", "clubs"),
            Card("7", "diamonds"),
        ]
    )
    client.post("/api/v1/blackjack/table/action", json={"action": "place_bet", "amount": 100})
    deal_initial_cards(client)
    split_resp = client.post("/api/v1/blackjack/table/action", json={"action": "split"})
    assert split_resp.status_code == 200
    first_hit = client.post("/api/v1/blackjack/table/action", json={"action": "hit"})
    assert first_hit.status_code == 200
    client.post("/api/v1/blackjack/table/action", json={"action": "stand"})
    second_stand = client.post("/api/v1/blackjack/table/action", json={"action": "stand"})
    snapshot = second_stand.get_json()
    assert snapshot["phase"] == "hand_complete"
    assert len(snapshot["player"]["hands"]) == 2
    assert snapshot["player"]["bankroll"] == 1_200
    assert all("hand" in result.lower() for result in snapshot["hand_results"])


def test_blackjack_insurance_resolves_on_dealer_blackjack(client: FlaskClient) -> None:
    configure_session(client)
    rig_shoe(
        [
            Card("9", "hearts"),
            Card("A", "spades"),
            Card("9", "clubs"),
            Card("K", "diamonds"),
        ]
    )
    client.post("/api/v1/blackjack/table/action", json={"action": "place_bet", "amount": 100})
    deal_initial_cards(client)
    insurance_resp = client.post(
        "/api/v1/blackjack/table/action",
        json={"action": "buy_insurance", "amount": 50},
    )
    assert insurance_resp.status_code == 200
    snapshot = insurance_resp.get_json()
    assert snapshot["phase"] == "hand_complete"
    assert snapshot["player"]["bankroll"] == 1_000
    assert any("dealer blackjack" in msg.lower() for msg in snapshot["hand_results"])


def test_split_blackjack_counts_as_blackjack(client: FlaskClient) -> None:
    configure_session(client)
    rig_shoe(
        [
            Card("A", "hearts"),
            Card("9", "hearts"),
            Card("A", "spades"),
            Card("5", "clubs"),
            Card("K", "diamonds"),
            Card("Q", "clubs"),
            Card("7", "diamonds"),
        ]
    )
    client.post("/api/v1/blackjack/table/action", json={"action": "place_bet", "amount": 100})
    deal_initial_cards(client)
    response = client.post("/api/v1/blackjack/table/action", json={"action": "split"})
    assert response.status_code == 200
    snapshot = response.get_json()
    assert snapshot["phase"] == "hand_complete"
    statuses = [hand["status"] for hand in snapshot["player"]["hands"]]
    assert statuses == ["blackjack", "blackjack"]
    assert snapshot["player"]["bankroll"] == 1_300
    assert any("blackjack" in result.lower() for result in snapshot["hand_results"])
