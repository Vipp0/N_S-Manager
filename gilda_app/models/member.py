from dataclasses import dataclass, field


STATUS_ATTIVO = "attivo"
STATUS_EX_MEMBRO = "ex_membro"
STATUS_BANNATO = "bannato"

STATUS_LABELS = {
    STATUS_ATTIVO: "Attuali",
    STATUS_EX_MEMBRO: "Ex membri",
    STATUS_BANNATO: "Bannati",
}


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
