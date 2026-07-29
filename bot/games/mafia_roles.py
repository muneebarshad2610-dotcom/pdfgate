ROLE_DEFS = [
    {"name": "Mafia", "team": "mafia", "count": 2, "night_action": "see_team", "description": "You are Mafia. See who your fellow mafia members are."},
    {"name": "Henchman", "team": "mafia", "count": 1, "night_action": "see_mafia", "description": "You are the Henchman. You can see who the mafia are, but they don't know who you are."},
    {"name": "Civilian", "team": "civilian", "count": 2, "night_action": None, "description": "You are a Civilian. No special abilities."},
    {"name": "Investigator", "team": "civilian", "count": 1, "night_action": "investigate", "description": "You are the Investigator. Look at one player's card or two center cards."},
    {"name": "Robber", "team": "civilian", "count": 1, "night_action": "rob", "description": "You are the Robber. Swap your card with another player's card."},
    {"name": "Troublemaker", "team": "civilian", "count": 1, "night_action": "trouble", "description": "You are the Troublemaker. Swap two other players' cards."},
    {"name": "Insomniac", "team": "civilian", "count": 1, "night_action": "check_self", "description": "You are the Insomniac. At the end of night, look at your own card."},
    {"name": "Seer", "team": "civilian", "count": 1, "night_action": "seer", "description": "You are the Seer. Check if a player is mafia or look at two center cards."},
    {"name": "Masons", "team": "civilian", "count": 2, "night_action": "see_masons", "description": "You are a Mason. See who your fellow mason is."},
    {"name": "Tanner", "team": "tanner", "count": 1, "night_action": None, "description": "You are the Tanner. Your goal is to be voted out."},
]

ROLE_ORDER = [
    "Mafia",
    "Investigator",
    "Seer",
    "Robber",
    "Insomniac",
    "Troublemaker",
    "Masons",
    "Henchman",
]

TEAMS = {
    "mafia": {"name": "Mafia", "win_condition": "mafia_not_voted_out"},
    "civilian": {"name": "Civilian", "win_condition": "mafia_voted_out"},
    "tanner": {"name": "Tanner", "win_condition": "tanner_voted_out"},
}


def build_deck():
    deck = []
    for role in ROLE_DEFS:
        for _ in range(role["count"]):
            deck.append({
                "name": role["name"],
                "team": role["team"],
                "night_action": role["night_action"],
                "description": role["description"],
            })
    return deck


def get_role_info(role_name):
    for role in ROLE_DEFS:
        if role["name"] == role_name:
            return role
    return None


def evaluate_winner(roles_at_end, voted_out_id, player_roles):
    if voted_out_id is not None:
        voted_role = player_roles.get(str(voted_out_id), {}).get("name", "")

        if voted_role == "Tanner":
            return "tanner"

        if voted_role in ("Henchman",):
            return "mafia"

        if voted_role == "Mafia":
            return "civilian"

    mafia_players = [
        did for did, r in player_roles.items()
        if r.get("name") == "Mafia"
    ]
    if voted_out_id in mafia_players:
        return "civilian"

    return "mafia"
