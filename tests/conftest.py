import pytest
from bot.engine.session import GameSession
from bot.engine.modes import GameMode


@pytest.fixture
def session():
    return GameSession(
        guild_id=123456789,
        channel_id=987654321,
        host_id=111111,
        mode=GameMode.CAMPAIGN,
    )


@pytest.fixture
def filled_session(session):
    for i in range(10):
        session.add_player(1000 + i, f"Player{i+1}")
    return session
