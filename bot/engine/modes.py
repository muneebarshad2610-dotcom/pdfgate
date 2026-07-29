from enum import Enum
from bot.utils import AttrDict


class GameMode(Enum):
    CAMPAIGN = "campaign"
    STANDALONE = "standalone"
    LOCAL = "local"


MODE_CONFIG = AttrDict.from_nested({
    GameMode.CAMPAIGN.value: {
        "name": "Campaign",
        "description": "Full season experience with eliminations",
        "leaderboard_persistent": True,
        "leaderboard_scope": "global",
        "eliminations_enabled": True,
        "min_players": 10,
        "max_players": 10,
    },
    GameMode.STANDALONE.value: {
        "name": "Standalone",
        "description": "Play any single game separately",
        "leaderboard_persistent": False,
        "leaderboard_scope": "session",
        "eliminations_enabled": False,
        "min_players": 3,
        "max_players": 10,
    },
    GameMode.LOCAL.value: {
        "name": "Local",
        "description": "Private/practice games without tracking",
        "leaderboard_persistent": False,
        "leaderboard_scope": "none",
        "eliminations_enabled": False,
        "min_players": 3,
        "max_players": 10,
    },
})


def get_mode_config(mode):
    if mode is None:
        return None
    return MODE_CONFIG.get(mode.value)


def mode_from_string(value):
    try:
        return GameMode(value.lower())
    except ValueError:
        return None
