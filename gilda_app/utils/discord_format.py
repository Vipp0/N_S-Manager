"""Formato testo per "Copia per Discord": incollabile direttamente nel canale/form
della gilda su Discord. Etichette ed ordine dei campi sono fissi (decisi dall'utente,
non dalla lingua dell'app) e vanno sempre tutti, anche se vuoti."""
from gilda_app.models.member import Member
from gilda_app.utils.flags import nations_text_english


def discord_copy_text(member: Member) -> str:
    return (
        f"Family: {member.family_name}\n"
        f"Character: {member.main_name or ''}\n"
        f"Discord: {member.discord_name or ''}\n"
        f"Country: {nations_text_english(member.nations)}\n"
        f"Note: {member.note or ''}"
    )
