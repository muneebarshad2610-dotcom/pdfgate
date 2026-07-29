import uuid
from bot.utils import AttrDict
from bot.errors import (
    SessionFullError, SessionLockedError, PlayerNotInSessionError,
    NotEnoughPlayersError, NotSessionHostError, GameAlreadyStartedError,
)
from bot.engine.modes import GameMode, get_mode_config
from bot.engine.leaderboard import LeaderboardManager
from bot.engine.timer import RoundTimer


class GameSession:

    def __init__(self, guild_id: int, channel_id: int, host_id: int, mode: GameMode):
        self.id = str(uuid.uuid4())
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.host_id = host_id
        self.mode = mode
        self.mode_config = get_mode_config(mode)
        self.game_type = None
        self.bot = None

        self.state = AttrDict({
            "status": "lobby",
            "current_round": 0,
            "total_rounds": 0,
            "players": {},
            "player_order": [],
            "eliminated": [],
        })

        self.leaderboard = LeaderboardManager()
        self.timer = RoundTimer()

    @property
    def status(self):
        return self.state.status

    @property
    def player_count(self):
        return len(self.state.player_order)

    @property
    def min_players(self):
        return self.mode_config.min_players

    @property
    def max_players(self):
        return self.mode_config.max_players

    @property
    def active_players(self):
        return [p for p in self.state.player_order if p not in self.state.eliminated]

    def add_player(self, discord_id: int, display_name: str):
        if self.state.status != "lobby":
            raise SessionLockedError("Session has already started")

        if self.player_count >= self.mode_config.max_players:
            raise SessionFullError("Session is full")

        if str(discord_id) in self.state.players:
            return False

        player = AttrDict({
            "discord_id": discord_id,
            "display_name": display_name,
            "score": 0,
            "eliminated": False,
            "eliminated_at_round": None,
            "joined_at": None,
        })
        self.state.players[str(discord_id)] = player
        self.state.player_order.append(discord_id)
        return True

    def remove_player(self, discord_id: int):
        if self.state.status != "lobby":
            raise SessionLockedError("Cannot leave after game has started")

        key = str(discord_id)
        if key not in self.state.players:
            raise PlayerNotInSessionError("Player is not in this session")

        del self.state.players[key]
        self.state.player_order = [p for p in self.state.player_order if p != discord_id]
        return True

    def start_game(self, discord_id: int):
        if discord_id != self.host_id:
            raise NotSessionHostError("Only the host can start the game")

        if self.state.status != "lobby":
            raise GameAlreadyStartedError("Game has already started")

        if self.player_count < self.min_players:
            raise NotEnoughPlayersError(
                f"Need {self.min_players} players to start (currently {self.player_count})"
            )

        self.state.status = "in_progress"

    def end_game(self):
        self.state.status = "completed"
        self.timer.cancel_all()

    def score_player(self, discord_id: int, points: int = 1):
        key = str(discord_id)
        if key in self.state.players:
            self.state.players[key].score = (self.state.players[key].score or 0) + points

    def eliminate_player(self, discord_id: int, round_number: int):
        key = str(discord_id)
        if key in self.state.players and not self.state.players[key].eliminated:
            self.state.players[key].eliminated = True
            self.state.players[key].eliminated_at_round = round_number
            self.state.eliminated.append(discord_id)

    def get_player(self, discord_id: int):
        return self.state.players.get(str(discord_id))

    def get_standings(self):
        active = [p for p in self.state.players.values() if not p.eliminated]
        return sorted(active, key=lambda p: p.score, reverse=True)

    def get_all_players_sorted(self):
        return sorted(
            self.state.players.values(),
            key=lambda p: (0 if p.eliminated else 1, p.score),
            reverse=True,
        )

    def to_dict(self):
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "host_id": self.host_id,
            "mode": self.mode.value,
            "status": self.state.status,
            "player_count": self.player_count,
            "min_players": self.min_players,
            "players": [
                {"discord_id": p.discord_id, "display_name": p.display_name, "score": p.score, "eliminated": p.eliminated}
                for p in self.state.players.values()
            ],
        }


class SessionManager:

    def __init__(self):
        self._sessions = {}

    def create_session(self, guild_id: int, channel_id: int, host_id: int, mode: GameMode) -> GameSession:
        session = GameSession(guild_id, channel_id, host_id, mode)
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str):
        return self._sessions.get(session_id)

    def get_session_by_channel(self, channel_id: int):
        for session in self._sessions.values():
            if session.channel_id == channel_id and session.status != "completed":
                return session
        return None

    def get_player_session(self, guild_id: int, discord_id: int):
        for session in self._sessions.values():
            if session.guild_id == guild_id and session.status != "completed":
                if str(discord_id) in session.state.players:
                    return session
        return None

    def end_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session.end_game()
            self._sessions.pop(session_id, None)
            return True
        return False

    def cleanup_stale(self):
        to_remove = []
        for sid, session in self._sessions.items():
            if session.status == "completed":
                to_remove.append(sid)
        for sid in to_remove:
            self._sessions.pop(sid, None)
