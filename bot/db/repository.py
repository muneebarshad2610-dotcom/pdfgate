import uuid
from sqlalchemy import desc

from bot.db.models import SessionLocal, SessionModel, PlayerModel, LeaderboardEntryModel


class SessionRepo:

    async def create(self, session_data: dict):
        db = SessionLocal()
        try:
            model = SessionModel(id=session_data["id"], **session_data)
            db.add(model)
            db.commit()
            return model
        finally:
            db.close()

    async def get(self, session_id: str):
        db = SessionLocal()
        try:
            return db.query(SessionModel).filter_by(id=session_id).first()
        finally:
            db.close()

    async def update(self, session_id: str, **kwargs):
        db = SessionLocal()
        try:
            model = db.query(SessionModel).filter_by(id=session_id).first()
            if model:
                for key, value in kwargs.items():
                    setattr(model, key, value)
                db.commit()
            return model
        finally:
            db.close()


class PlayerRepo:

    async def bulk_create(self, players: list):
        db = SessionLocal()
        try:
            for p in players:
                model = PlayerModel(
                    id=str(uuid.uuid4()),
                    session_id=p["session_id"],
                    discord_id=p["discord_id"],
                    display_name=p["display_name"],
                )
                db.add(model)
            db.commit()
        finally:
            db.close()

    async def get_by_session(self, session_id: str):
        db = SessionLocal()
        try:
            return db.query(PlayerModel).filter_by(session_id=session_id).all()
        finally:
            db.close()


class LeaderboardRepo:

    async def upsert(self, guild_id: int, discord_id: int, display_name: str):
        db = SessionLocal()
        try:
            entry = db.query(LeaderboardEntryModel).filter_by(
                guild_id=guild_id, discord_id=discord_id
            ).first()
            if entry:
                entry.display_name = display_name
            else:
                entry = LeaderboardEntryModel(
                    id=str(uuid.uuid4()),
                    guild_id=guild_id,
                    discord_id=discord_id,
                    display_name=display_name,
                )
                db.add(entry)
            db.commit()
            return entry
        finally:
            db.close()

    async def save(self, entry):
        db = SessionLocal()
        try:
            db.add(entry)
            db.commit()
        finally:
            db.close()

    async def get_by_discord_id(self, guild_id: int, discord_id: int):
        db = SessionLocal()
        try:
            return db.query(LeaderboardEntryModel).filter_by(
                guild_id=guild_id, discord_id=discord_id
            ).first()
        finally:
            db.close()

    async def get_top(self, guild_id: int, limit: int = 10):
        db = SessionLocal()
        try:
            return db.query(LeaderboardEntryModel).filter_by(
                guild_id=guild_id
            ).order_by(
                desc(LeaderboardEntryModel.campaign_points)
            ).limit(limit).all()
        finally:
            db.close()
