import os
from pathlib import Path
from dotenv import load_dotenv
from bot.utils import AttrDict


load_dotenv()


config = AttrDict.from_nested({
    "discord": {
        "bot_token": os.getenv("DISCORD_BOT_TOKEN", ""),
        "prefix": os.getenv("BOT_PREFIX", "/"),
        "activity": os.getenv("BOT_ACTIVITY", "House of Games"),
        "status": os.getenv("BOT_STATUS", "online"),
    },
    "database": {
        "url": os.getenv("DATABASE_URL", "sqlite:///data/house_of_games.db"),
    },
    "admin_ids": [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ],
    "logging": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "game": {
        "min_players": 10,
        "max_players": 10,
        "round_timeout": 30,
        "vote_timeout": 60,
    },
})

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "bot" / "data"
QUESTIONS_DIR = DATA_DIR / "questions"
