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


def test_parse_player_life_skills_and_guild_history():
    payload = dict(
        PLAYER,
        life_skills=[
            {"skill_name": "Fishing", "level_rank": "Guru", "level_num": 21, "mastery": 2164},
            {"skill_name": "Barter", "level_rank": "Professional", "level_num": 1, "mastery": 0},
        ],
        guild_history=[
            {"guild_name": "Vecchia_Gilda", "joined_at": "2020-01-01T00:00:00", "left_at": "2021-06-15T00:00:00"},
            {"guild_name": "Gilda_Finta", "joined_at": "2026-09-24T07:27:12", "left_at": None},
        ],
    )
    profile = parse_player(payload)
    assert [s.name for s in profile.life_skills] == ["Fishing", "Barter"]
    fishing = profile.life_skills[0]
    assert (fishing.rank, fishing.level, fishing.mastery) == ("Guru", 21, 2164)
    assert [(h.guild_name, h.joined_at, h.left_at) for h in profile.guild_history] == [
        ("Vecchia_Gilda", "2020-01-01T00:00:00", "2021-06-15T00:00:00"),
        ("Gilda_Finta", "2026-09-24T07:27:12", None),
    ]


def test_parse_player_ignores_garbage_life_skills_and_guild_history():
    payload = dict(
        PLAYER,
        life_skills=["not a dict", {"level_rank": "Guru"}, {"skill_name": "Fishing", "level_rank": "Guru"}],
        guild_history=[123, {"joined_at": "2020-01-01"}, {"guild_name": "X", "joined_at": None, "left_at": None}],
    )
    profile = parse_player(payload)
    assert len(profile.life_skills) == 1 and profile.life_skills[0].name == "Fishing"
    assert profile.life_skills[0].level == 0 and profile.life_skills[0].mastery == 0
    assert len(profile.guild_history) == 1 and profile.guild_history[0].guild_name == "X"


def test_parse_player_missing_fields_has_empty_life_skills_and_history():
    profile = parse_player({"family_name": "Solo"})
    assert profile.life_skills == [] and profile.guild_history == []


def test_characters_by_class_groups_alphabetically_and_sorts_by_level_desc():
    payload = dict(
        PLAYER,
        characters=[
            {"character_name": "Low", "character_class": "Lahn", "level": 10, "is_main": False},
            {"character_name": "High", "character_class": "Lahn", "level": 66, "is_main": True},
            {"character_name": "OnlyShai", "character_class": "Shai", "level": 60, "is_main": False},
        ],
    )
    profile = parse_player(payload)
    groups = profile.characters_by_class()
    assert [cls for cls, _ in groups] == ["Lahn", "Shai"]
    lahn_names = [c.name for _, members in groups if members[0].char_class == "Lahn" for c in members]
    assert lahn_names == ["High", "Low"]  # per livello decrescente, non per ordine d'arrivo


def test_characters_by_class_empty_without_characters():
    assert parse_player({"family_name": "Solo"}).characters_by_class() == []


def test_fetch_player_waits_longer_than_default_timeout():
    from unittest.mock import patch

    from gilda_app.utils import bdo_guild

    with patch.object(bdo_guild, "api_get", return_value={"family_name": "Aeloki"}) as mocked:
        assert bdo_guild.fetch_player("key", "eu", "Aeloki").family_name == "Aeloki"
    assert mocked.call_args.kwargs["timeout"] == bdo_guild.PLAYER_TIMEOUT_SECONDS > 6
