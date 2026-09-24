"""Gilda e giocatori di Black Desert da bdoalerts.net: elenco membri della gilda in gioco
(con il Guild Master) e profilo di un singolo giocatore. Sono dati di terzi, da mostrare
come informazione: non modificano mai da soli il database."""
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime

from gilda_app.utils.bdoalerts_api import ERROR_BAD_RESPONSE, ApiError, api_get


def api_region(region: str) -> str:
    """Le regioni dello stato server hanno il trattino ("console-eu"), gli altri endpoint
    accettano il nome con il trattino basso."""
    return region.replace("-", "_")


def _quote(text: str) -> str:
    return urllib.parse.quote(text, safe="")


# -- Gilda -------------------------------------------------------------------
@dataclass
class GuildInfo:
    name: str
    master: str
    members: list[str]


@dataclass
class GuildComparison:
    not_in_app: list[str] = field(default_factory=list)  # in gioco, sconosciuti al programma
    ex_or_banned_in_game: list[tuple[str, str]] = field(default_factory=list)  # (nome, status)
    active_not_in_game: list[str] = field(default_factory=list)  # attivi nel programma, non in gioco


def parse_guild(payload: dict) -> GuildInfo:
    members = payload.get("members")
    if not isinstance(members, list):
        raise ApiError(ERROR_BAD_RESPONSE)
    names = [m for m in members if isinstance(m, str) and m]
    if not names:
        raise ApiError(ERROR_BAD_RESPONSE)
    name = payload.get("guild_name")
    master = payload.get("guild_master")
    return GuildInfo(
        name=name if isinstance(name, str) else "",
        master=master if isinstance(master, str) else "",
        members=names,
    )


def fetch_guild(api_key: str, region: str, guild_name: str) -> GuildInfo:
    return parse_guild(api_get(f"/api/guild/{api_region(region)}/{_quote(guild_name)}", api_key))


def compare_guild(game_members: list[str], app_names_by_status: dict[str, list[str]]) -> GuildComparison:
    """Confronto senza distinguere maiuscole/minuscole tra i nomi in gioco e le liste del
    programma. app_names_by_status: {"attivo": [...], "ex_membro": [...], "bannato": [...]}."""
    game = {name.casefold(): name for name in game_members}
    known: dict[str, str] = {}
    for status, names in app_names_by_status.items():
        for name in names:
            known.setdefault(name.casefold(), status)
    result = GuildComparison()
    for key, name in game.items():
        status = known.get(key)
        if status is None:
            result.not_in_app.append(name)
        elif status != "attivo":
            result.ex_or_banned_in_game.append((name, status))
    for name in app_names_by_status.get("attivo", []):
        if name.casefold() not in game:
            result.active_not_in_game.append(name)
    for items in (result.not_in_app, result.active_not_in_game):
        items.sort(key=str.casefold)
    result.ex_or_banned_in_game.sort(key=lambda item: item[0].casefold())
    return result


# -- Giocatore ---------------------------------------------------------------
@dataclass
class Character:
    name: str
    char_class: str
    level: int
    is_main: bool


@dataclass
class PlayerProfile:
    family_name: str
    guild: str | None
    is_private: bool
    max_gear_score: int | None
    energy: int | None
    contribution_points: int | None
    family_created: date | None
    characters: list[Character] = field(default_factory=list)

    def main_character(self) -> Character | None:
        for character in self.characters:
            if character.is_main:
                return character
        return max(self.characters, key=lambda c: c.level, default=None)


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _parse_created(text) -> date | None:
    if not isinstance(text, str):
        return None
    try:
        return datetime.strptime(text.split(" (")[0].strip(), "%b %d, %Y").date()
    except ValueError:
        return None


def parse_player(payload: dict) -> PlayerProfile:
    family = payload.get("family_name")
    if not isinstance(family, str) or not family:
        raise ApiError(ERROR_BAD_RESPONSE)
    characters = []
    for raw in payload.get("characters") or []:
        if isinstance(raw, dict) and isinstance(raw.get("character_class"), str):
            characters.append(
                Character(
                    name=str(raw.get("character_name") or ""),
                    char_class=raw["character_class"],
                    level=_int(raw.get("level")) or 0,
                    is_main=bool(raw.get("is_main")),
                )
            )
    guild = payload.get("guild")
    return PlayerProfile(
        family_name=family,
        guild=guild if isinstance(guild, str) and guild else None,
        is_private=bool(payload.get("is_private")),
        max_gear_score=_int(payload.get("max_gear_score")),
        energy=_int(payload.get("energy")),
        contribution_points=_int(payload.get("contribution_points")),
        family_created=_parse_created(payload.get("family_created")),
        characters=characters,
    )


def fetch_player(api_key: str, region: str, family_name: str) -> PlayerProfile:
    return parse_player(api_get(f"/api/player/{api_region(region)}/{_quote(family_name)}", api_key))
