"""Blackjack trainer API endpoints."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest, Conflict

from app.services.blackjack.state_manager import (
    DEFAULT_BANKROLL,
    DEFAULT_DECKS,
    InvalidBlackjackAction,
    MissingConfigurationError,
    blackjack_state_manager,
    serialize_state,
)

blackjack_bp = Blueprint("blackjack", __name__, url_prefix="/api/v1/blackjack")


@blackjack_bp.route("/table", methods=["GET"])
def get_blackjack_table() -> Response:
    """Return current blackjack snapshot."""
    state = blackjack_state_manager.ensure_state()
    return jsonify(serialize_state(state))


@blackjack_bp.route("/config", methods=["POST"])
def configure_blackjack() -> Response:
    """Configure bankroll and shoe before starting."""
    payload = request.get_json(silent=True) or {}
    bankroll = int(payload.get("bankroll", DEFAULT_BANKROLL))
    shoe_decks = int(payload.get("shoe_decks", DEFAULT_DECKS))
    min_bet = payload.get("min_bet")
    max_bet = payload.get("max_bet")
    try:
        state = blackjack_state_manager.configure(
            bankroll=bankroll,
            shoe_decks=shoe_decks,
            min_bet=int(min_bet) if min_bet is not None else None,
            max_bet=int(max_bet) if max_bet is not None else None,
        )
    except InvalidBlackjackAction as exc:
        raise BadRequest(str(exc)) from exc
    return jsonify(serialize_state(state)), HTTPStatus.CREATED


@blackjack_bp.route("/table/action", methods=["POST"])
def blackjack_action() -> Response:
    """Apply a blackjack action."""
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    if not action:
        raise BadRequest("Action is required.")
    try:
        state = blackjack_state_manager.apply_action(action=action, payload=payload)
    except MissingConfigurationError as exc:
        raise Conflict(str(exc)) from exc
    except InvalidBlackjackAction as exc:
        raise BadRequest(str(exc)) from exc
    return jsonify(serialize_state(state))


@blackjack_bp.route("/table/next-hand", methods=["POST"])
def blackjack_next_hand() -> Response:
    """Reset per-hand state while keeping bankroll/shoe."""
    try:
        state = blackjack_state_manager.start_next_hand()
    except MissingConfigurationError as exc:
        raise Conflict(str(exc)) from exc
    except InvalidBlackjackAction as exc:
        raise BadRequest(str(exc)) from exc
    return jsonify(serialize_state(state)), HTTPStatus.OK
