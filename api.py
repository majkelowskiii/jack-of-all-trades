"""App entrypoint for local development."""

from __future__ import annotations

from app import create_app
from app.services.poker.state_manager import reset_game_state

app = create_app()

__all__ = ["app", "reset_game_state"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
