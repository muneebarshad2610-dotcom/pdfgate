import pytest
from bot.engine.modes import GameMode, get_mode_config, mode_from_string


class TestGameMode:

    def test_mode_values(self):
        assert GameMode.CAMPAIGN.value == "campaign"
        assert GameMode.STANDALONE.value == "standalone"
        assert GameMode.LOCAL.value == "local"

    def test_mode_config_is_accessible(self):
        cfg = get_mode_config(GameMode.CAMPAIGN)
        cfg.new_field = "test"
        assert cfg.new_field == "test"


class TestModeConfig:

    def test_campaign_config(self):
        cfg = get_mode_config(GameMode.CAMPAIGN)
        assert cfg.name == "Campaign"
        assert cfg.leaderboard_persistent == True
        assert cfg.leaderboard_scope == "global"
        assert cfg.eliminations_enabled == True
        assert cfg.min_players == 10

    def test_standalone_config(self):
        cfg = get_mode_config(GameMode.STANDALONE)
        assert cfg.name == "Standalone"
        assert cfg.leaderboard_persistent == False
        assert cfg.leaderboard_scope == "session"
        assert cfg.eliminations_enabled == False

    def test_local_config(self):
        cfg = get_mode_config(GameMode.LOCAL)
        assert cfg.name == "Local"
        assert cfg.leaderboard_persistent == False
        assert cfg.leaderboard_scope == "none"
        assert cfg.eliminations_enabled == False

    def test_get_mode_config_invalid(self):
        assert get_mode_config(None) is None


class TestModeFromString:

    @pytest.mark.parametrize("input,expected", [
        ("campaign", GameMode.CAMPAIGN),
        ("CAMPAIGN", GameMode.CAMPAIGN),
        ("Campaign", GameMode.CAMPAIGN),
        ("standalone", GameMode.STANDALONE),
        ("local", GameMode.LOCAL),
    ])
    def test_valid_strings(self, input, expected):
        assert mode_from_string(input) == expected

    @pytest.mark.parametrize("input", [
        ("invalid"), (""), ("campaign "), ("camp"),
    ])
    def test_invalid_strings(self, input):
        assert mode_from_string(input) is None
