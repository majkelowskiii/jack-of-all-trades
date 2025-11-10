"""Smoke tests for the demo API."""

from __future__ import annotations

from typing import Generator

import pytest
from flask.testing import FlaskClient

from api import app, reset_game_state


@pytest.fixture()
def client() -> Generator[FlaskClient, None, None]:
    """Provide a Flask test client for the demo API."""
    app.testing = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def fresh_state() -> Generator[None, None, None]:
    """Reset the global table state before each test for determinism."""
    reset_game_state()
    yield


def test_table_endpoint_returns_valid_snapshot(client: FlaskClient) -> None:
    """Ensure GET /api/v1/table responds with the expected JSON contract."""
    response = client.get("/api/v1/table")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)

    for key in (
        "name",
        "dealer_position",
        "players",
        "pot",
        "call_amount",
        "active_player",
        "hand_number",
    ):
        assert key in payload, f"Missing {key} in response"

    players = payload["players"]
    assert isinstance(players, list) and len(players) == 8

    mandatory_player_keys = {"seat", "name", "stack", "hole_cards", "in_hand", "player_bet"}
    for player in players:
        assert mandatory_player_keys.issubset(player.keys())
        assert isinstance(player["hole_cards"], list) and len(player["hole_cards"]) <= 2

    # Dealer + blinds must point to valid seat indexes
    dealer_pos = payload["dealer_position"]
    assert dealer_pos is not None
    assert 0 <= dealer_pos < len(players)

    for blind_key in ("sb", "bb"):
        blind = payload[blind_key]
        assert blind is not None
        assert 0 <= blind["seat"] < len(players)

    active_actions = payload["available_actions"]
    assert {"can_fold", "can_call", "can_check", "call_amount", "raise"}.issubset(
        active_actions.keys()
    )
    raise_info = active_actions["raise"]
    assert {"allowed", "min_total", "max_total", "increment"}.issubset(raise_info.keys())


def test_action_endpoint_advances_state(client: FlaskClient) -> None:
    """Posting a valid action advances the active seat and updates values."""
    initial = client.get("/api/v1/table").get_json()
    first_active = initial["active_seat"]
    actions = initial["available_actions"]

    if actions["can_call"]:
        payload = {"action": "call"}
    elif actions["can_check"]:
        payload = {"action": "check"}
    else:
        payload = {"action": "fold"}

    response = client.post("/api/v1/table/action", json=payload)
    assert response.status_code == 200
    updated = response.get_json()

    if first_active is not None:
        assert updated["active_seat"] != first_active or not updated["players"][first_active]["in_hand"]
    assert updated["pot"] >= initial["pot"]


def test_action_endpoint_rejects_invalid_raise(client: FlaskClient) -> None:
    """Invalid raises are rejected with 400 responses."""
    snapshot = client.get("/api/v1/table").get_json()
    raise_info = snapshot["available_actions"]["raise"]
    invalid_amount = raise_info["min_total"] - 10

    response = client.post(
        "/api/v1/table/action", json={"action": "raise", "amount": invalid_amount}
    )
    assert response.status_code == 400


def test_hand_counter_increments_after_round_ends(client: FlaskClient) -> None:
    """When every player has acted (or only one remains), a new hand begins."""
    snapshot = client.get("/api/v1/table").get_json()
    starting_hand = snapshot["hand_number"]

    current = snapshot
    safety = 0
    while current["hand_number"] == starting_hand and safety < 20:
        actions = current["available_actions"]
        if actions["can_fold"]:
            payload = {"action": "fold"}
        elif actions["can_call"]:
            payload = {"action": "call"}
        elif actions["can_check"]:
            payload = {"action": "check"}
        else:
            break
        resp = client.post("/api/v1/table/action", json=payload)
        assert resp.status_code == 200
        current = resp.get_json()
        safety += 1

    assert current["hand_number"] == starting_hand + 1


def test_min_raise_rules_enforced(client: FlaskClient) -> None:
    """Raise sizing must match 'difference of previous bets' rule."""
    snapshot = client.get("/api/v1/table").get_json()
    raise_info = snapshot["available_actions"]["raise"]

    # First raise must be at least 2 * BB => min_total should reflect that
    assert raise_info["min_total"] == snapshot["call_amount"] + max(
        snapshot["available_actions"]["raise"]["increment"], 100
    )

    # Perform the minimum allowed raise
    response = client.post(
        "/api/v1/table/action",
        json={"action": "raise", "amount": raise_info["min_total"]},
    )
    assert response.status_code == 200
    after_raise = response.get_json()

    # Next raise minimum should be previous raise plus difference (raise - previous call)
    next_raise = after_raise["available_actions"]["raise"]
    prev_call = snapshot["call_amount"]
    prev_raise = raise_info["min_total"]
    expected_min_total = prev_raise + (prev_raise - prev_call)
    assert next_raise["min_total"] == expected_min_total
