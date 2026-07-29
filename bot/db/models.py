from sqlalchemy import create_engine, Column, String, Integer, Boolean, BigInteger, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

from bot.config import config

Base = declarative_base()


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    host_id = Column(BigInteger, nullable=False)
    mode = Column(String(20), nullable=False)
    game_type = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="lobby")
    created_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)


class PlayerModel(Base):
    __tablename__ = "players"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    discord_id = Column(BigInteger, nullable=False)
    display_name = Column(String(100), nullable=False)
    score = Column(Integer, default=0)
    eliminated = Column(Boolean, default=False)
    eliminated_at_round = Column(Integer, nullable=True)
    joined_at = Column(DateTime, server_default=func.now())


class LeaderboardEntryModel(Base):
    __tablename__ = "leaderboard"

    id = Column(String, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    discord_id = Column(BigInteger, nullable=False)
    display_name = Column(String(100), nullable=False)
    campaign_points = Column(Integer, default=0)
    session_points = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


engine = create_engine(str(config.database.url), echo=False)
SessionLocal = sessionmaker(bind=engine)


async def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
