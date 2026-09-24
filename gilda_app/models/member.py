from dataclasses import dataclass, field

from gilda_app.i18n import tr

STATUS_ATTIVO = "attivo"
STATUS_EX_MEMBRO = "ex_membro"
STATUS_BANNATO = "bannato"


def status_label(status: str) -> str:
    return tr(f"status.{status}")


@dataclass
class Member:
    id: int
    family_name: str
    main_name: str
    discord_name: str
    status: str
    data_inserimento: str | None
    note: str | None
    nations: list[str] = field(default_factory=list)
    still_on_discord: bool = False
    birthday: str | None = None
