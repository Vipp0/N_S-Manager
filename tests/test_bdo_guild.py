from datetime import date

import pytest

from gilda_app.utils.bdo_guild import compare_guild, parse_guild, parse_player
from gilda_app.utils.bdoalerts_api import ApiError

GUILD = {
    "guild_name": "Gilda_Finta",
    "guild_master": "Capo",
    "member_count": 4,
    "members": ["Capo", "AliceX", "bob", "Nuovo"],
    "members_detailed": [{"family_name": "Capo", "profile_target": "xxx"}],
}
PLAYER = {
    "status": "fresh",
    "family_name": "AliceX",
    "guild": "Gilda_Finta",
    "is_private": True,
    "max_gear_score": 700,
    "energy": 400,
    "contribution_points": 300,
    "family_created": "Jan 26, 2018 (UTC)",
    "characters": [
        {"character_name": "a", "character_class": "Lahn", "level": 66, "is_main": True},
        {"character_name": "b", "character_class": "Shai", "level": 60, "is_main": False},
    ],
    "guild_history": [{"guild_name": "Gilda_Finta", "joined_at": "2026-09-24T07:27:12", "left_at": None}],
}


def test_parse_guild():
    info = parse_guild(GUILD)
    assert info.name == "Gilda_Finta" and info.master == "Capo"
    assert info.members == ["Capo", "AliceX", "bob", "Nuovo"]


def test_parse_guild_rejects_garbage():
    with pytest.raises(ApiError):
        parse_guild({"members": []})
    with pytest.raises(ApiError):
        parse_guild({"nope": 1})


def test_compare_guild():
    result = compare_guild(
        ["Capo", "AliceX", "bob", "Nuovo"],
        {"attivo": ["capo", "alicex", "Sparito"], "ex_membro": ["BOB"], "bannato": []},
    )
    assert result.not_in_app == ["Nuovo"]
    assert result.ex_or_banned_in_game == [("bob", "ex_membro")]
    assert result.active_not_in_game == ["Sparito"]


def test_parse_player():
    profile = parse_player(PLAYER)
    assert profile.family_name == "AliceX"
    assert profile.guild == "Gilda_Finta"
    assert profile.is_private is True
    assert profile.max_gear_score == 700
    assert profile.family_created == date(2018, 1, 26)
    main = profile.main_character()
    assert (main.char_class, main.level) == ("Lahn", 66)


def test_parse_player_without_main_uses_highest_level():
    payload = dict(PLAYER, characters=[
        {"character_name": "a", "character_class": "Lahn", "level": 60, "is_main": False},
        {"character_name": "b", "character_class": "Shai", "level": 63, "is_main": False},
    ])
    assert parse_player(payload).main_character().char_class == "Shai"


def test_parse_player_missing_fields_and_garbage():
    profile = parse_player({"family_name": "Solo"})
    assert profile.guild is None and profile.max_gear_score is None and profile.main_character() is None
    with pytest.raises(ApiError):
        parse_player({"status": "fresh"})
