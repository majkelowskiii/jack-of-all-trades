"""Shared pytest fixtures."""

from __future__ import annotations

from typing import Generator

import pytest
from flask.testing import FlaskClient

from app import create_app
from app.services.blackjack.state_manager import reset_blackjack_state
from app.services.poker.state_manager import reset_game_state


@pytest.fixture()
def client() -> Generator[FlaskClient, None, None]:
    """Provide a Flask test client for API tests."""
    flask_app = create_app()
    flask_app.testing = True
    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def fresh_state() -> Generator[None, None, None]:
    """Reset global singletons between tests for determinism."""
    reset_game_state()
    reset_blackjack_state()
    yield
