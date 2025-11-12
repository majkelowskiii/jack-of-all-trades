"""Poker training API endpoints."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest, Conflict

from app.services.poker.state_manager import (
    HandCompleteError,
    state_manager,
    InvalidActionError,
    serialize_state,
)

poker_bp = Blueprint("poker", __name__, url_prefix="/api/v1/poker")


@poker_bp.route("/table", methods=["GET"])
def get_table_snapshot() -> Response:
    """Return the latest table snapshot for the poker trainer."""
    state = state_manager.ensure_state()
    return jsonify(serialize_state(state))


@poker_bp.route("/table/action", methods=["POST"])
def act_on_table() -> Response:
    """Apply an action for the active seat."""
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")

    if action is None:
        raise BadRequest("Action field is required")

    try:
        state = state_manager.apply_action(action=action, payload=payload)
    except HandCompleteError as exc:
        raise Conflict(str(exc)) from exc
    except InvalidActionError as exc:
        raise BadRequest(str(exc)) from exc

    return jsonify(serialize_state(state))


@poker_bp.route("/table/next-hand", methods=["POST"])
def start_next_hand() -> Response:
    """Explicitly start the next hand."""
    state = state_manager.force_next_hand()
    return jsonify(serialize_state(state)), HTTPStatus.OK
