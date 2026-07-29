from abc import ABC, abstractmethod


class BaseGame(ABC):

    def __init__(self, session):
        self.session = session
        self.name = self.__class__.__name__

    @property
    def state(self):
        return self.session.state

    @property
    def players(self):
        return self.session.state.players

    @property
    def active_players(self):
        return self.session.active_players

    @abstractmethod
    async def on_start(self):
        """Called when the game begins. Set up rounds, deal cards, etc."""

    @abstractmethod
    async def on_round(self, round_number: int):
        """Called at the start of each round."""

    @abstractmethod
    async def on_end(self):
        """Called when the game ends. Calculate final scores, announce winners."""

    async def run(self):
        await self.on_start()
        total = self.state.total_rounds
        for round_num in range(1, total + 1):
            self.state.current_round = round_num
            await self.on_round(round_num)
        await self.on_end()
