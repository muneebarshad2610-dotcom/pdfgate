from bot.db.repository import LeaderboardRepo
from bot.engine.modes import GameMode
from bot.utils import AttrDict


class LeaderboardManager:

    def __init__(self):
        self._repo = LeaderboardRepo()
        self._session_cache = {}

    async def record_score(self, guild_id: int, discord_id: int, display_name: str, points: int, mode: GameMode, session_id: str = None):
        if mode == GameMode.LOCAL:
            return

        entry = await self._repo.upsert(
            guild_id=guild_id,
            discord_id=discord_id,
            display_name=display_name,
        )

        if mode == GameMode.CAMPAIGN:
            entry.campaign_points += points
        elif mode == GameMode.STANDALONE and session_id:
            key = (discord_id, session_id)
            if key not in self._session_cache:
                self._session_cache[key] = 0
            self._session_cache[key] += points

        await self._repo.save(entry)

    async def get_standings(self, guild_id: int, mode: GameMode, session_id: str = None):
        if mode == GameMode.LOCAL:
            return []

        if mode == GameMode.CAMPAIGN:
            return await self._repo.get_top(guild_id, limit=10)

        if mode == GameMode.STANDALONE:
            results = []
            for (did, sid), pts in self._session_cache.items():
                if sid == session_id:
                    entry = await self._repo.get_by_discord_id(guild_id, did)
                    results.append(AttrDict({
                        "discord_id": did,
                        "display_name": entry.display_name if entry else "Unknown",
                        "session_points": pts,
                    }))
            return sorted(results, key=lambda r: r.session_points, reverse=True)

        return []

    async def get_campaign_standings(self, guild_id: int):
        return await self._repo.get_top(guild_id, limit=10)

    def clear_session_cache(self, session_id: str):
        keys_to_delete = [k for k in self._session_cache if k[1] == session_id]
        for k in keys_to_delete:
            del self._session_cache[k]
