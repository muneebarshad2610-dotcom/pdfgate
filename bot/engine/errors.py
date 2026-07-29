class HouseOfGamesError(Exception):
    """Base exception for House of Games."""


class SessionFullError(HouseOfGamesError):
    """Session has reached maximum player capacity."""


class SessionLockedError(HouseOfGamesError):
    """Session has already started and is locked."""


class PlayerNotInSessionError(HouseOfGamesError):
    """Player is not part of this session."""


class NotEnoughPlayersError(HouseOfGamesError):
    """Not enough players to start the game."""


class NotSessionHostError(HouseOfGamesError):
    """Only the session host can perform this action."""


class GameAlreadyStartedError(HouseOfGamesError):
    """Game has already started."""


class InvalidGameTypeError(HouseOfGamesError):
    """Unknown or unsupported game type."""


class InvalidPhaseError(HouseOfGamesError):
    """Invalid phase for the current game state."""


class PlayerAlreadyVotedError(HouseOfGamesError):
    """Player has already cast their vote."""


class RoleNotFoundError(HouseOfGamesError):
    """Role not found in the deck."""


class DeckEmptyError(HouseOfGamesError):
    """No cards left in the deck."""


class QuestionNotFoundError(HouseOfGamesError):
    """Question not found in the question bank."""


class TimerExpiredError(HouseOfGamesError):
    """Timer has expired."""
