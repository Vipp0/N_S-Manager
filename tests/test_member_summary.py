"""Dati del pannello dei dettagli: da quando è in gilda, uscita, ban, etichette Nuovo e Rientrato, storico."""
from datetime import date

from gilda_app.models.member import Member
from gilda_app.utils.member_summary import (
    TAG_NEW,
    TAG_REJOINED,
    duration_text,
    summarize,
)

TODAY = date(2026, 10, 30)


def row(previous, new, changed_at, note=None):
    return {"previous_status": previous, "new_status": new, "changed_at": changed_at, "note": note}


def member(status="attivo", joined=None, **kwargs):
    return Member(id=1, family_name="Tsukasa", main_name="Tsu", discord_name="tsu", status=status,
                  data_inserimento=joined, note=None, **kwargs)


def test_duration_text_speaks_like_a_person():
    assert duration_text(date(2026, 10, 29), TODAY) == "1 giorno"
    assert duration_text(date(2026, 10, 25), TODAY) == "5 giorni"
    assert duration_text(date(2026, 2, 15), TODAY) == "8 mesi"
    assert duration_text(date(2025, 9, 30), TODAY) == "1 anno e 1 mese"
    assert duration_text(date(2023, 11, 21), TODAY) == "2 anni e 11 mesi"
    assert duration_text(date(2024, 10, 30), TODAY) == "2 anni"
    assert duration_text(date(2026, 9, 30), TODAY) == "1 mese"
    assert duration_text(date(2026, 9, 29), TODAY) == "1 mese"


def test_a_recent_member_is_new_and_since_when_is_shown():
    summary = summarize(member(joined="2026-10-25"), [row(None, "attivo", "2026-10-25 00:00:00")], TODAY)
    assert summary.tag == TAG_NEW
    assert summary.in_guild == "Dal 25-10-2026 · da 5 giorni"
    assert not summary.missing_join_date and summary.first_join == ""
    assert [(h.key, h.day, h.tone) for h in summary.history] == [("joined", "25-10-2026", "good")]


def test_joined_today_says_since_today():
    summary = summarize(member(joined="2026-10-30"), [row(None, "attivo", "2026-10-30 00:00:00")], TODAY)
    assert summary.in_guild == "Dal 30-10-2026 · da oggi" and summary.tag == TAG_NEW


def test_an_old_member_has_no_tag():
    summary = summarize(member(joined="2022-11-03"), [row(None, "attivo", "2022-11-03 00:00:00")], TODAY)
    assert summary.tag is None and summary.in_guild == "Dal 03-11-2022 · da 3 anni e 11 mesi"


def test_a_member_without_a_joining_date_says_so_instead_of_guessing():
    summary = summarize(member(joined=None), [row(None, "attivo", "2026-10-30 09:00:00")], TODAY)
    assert summary.missing_join_date and summary.in_guild == "" and summary.tag is None


def test_a_member_who_came_back_is_rejoined_with_the_first_join_kept():
    history = [
        row(None, "attivo", "2025-02-14 00:00:00"),
        row("attivo", "ex_membro", "2026-03-12 10:00:00"),
        row("ex_membro", "attivo", "2026-10-29 18:00:00"),
    ]
    summary = summarize(member(joined="2025-02-14"), history, TODAY)
    assert summary.tag == TAG_REJOINED
    assert summary.in_guild == "Rientrato il 29-10-2026 · da 1 giorno"
    assert summary.first_join == "Primo ingresso il 14-02-2025"
    assert [h.key for h in summary.history] == ["rejoined", "left", "joined"]  # dal più recente
    assert [h.tone for h in summary.history] == ["good", "bad", "good"]


def test_coming_back_from_a_ban_counts_as_a_rejoin_too():
    history = [row(None, "attivo", "2024-01-01 00:00:00"), row("attivo", "bannato", "2025-01-01 00:00:00", "litigi"),
               row("bannato", "attivo", "2026-10-20 00:00:00")]
    summary = summarize(member(joined="2024-01-01"), history, TODAY)
    assert summary.tag == TAG_REJOINED and summary.in_guild.startswith("Rientrato il 20-10-2026")


def test_an_ex_member_says_when_he_left_and_after_how_long():
    history = [row(None, "attivo", "2026-02-15 00:00:00"), row("attivo", "ex_membro", "2026-10-27 10:00:00")]
    summary = summarize(member("ex_membro", joined="2026-02-15"), history, TODAY)
    assert summary.in_guild == "Il 27-10-2026 · dopo 8 mesi" and summary.tag is None
    assert [h.key for h in summary.history] == ["left", "joined"]


def test_an_ex_member_with_an_unknown_leaving_date():
    summary = summarize(member("ex_membro"), [row(None, "ex_membro", None)], TODAY)
    assert summary.in_guild == "Data di uscita sconosciuta"
    assert [(h.key, h.day) for h in summary.history] == [("added", "data sconosciuta")]


def test_a_banned_member_has_the_date_and_the_reason():
    history = [row(None, "attivo", "2026-04-07 00:00:00"), row("attivo", "bannato", "2026-10-22 10:00:00", "Insulti in chat")]
    summary = summarize(member("bannato", joined="2026-04-07"), history, TODAY)
    assert summary.in_guild == "Il 22-10-2026" and summary.ban_reason == "Insulti in chat"
    assert [h.key for h in summary.history] == ["banned", "joined"] and summary.history[0].note == "Insulti in chat"


def test_a_ban_without_a_recorded_reason_leaves_it_empty():
    history = [row(None, "attivo", "2026-04-07 00:00:00"), row("attivo", "bannato", "2026-10-22 10:00:00")]
    assert summarize(member("bannato", joined="2026-04-07"), history, TODAY).ban_reason == ""


def test_moving_between_ex_and_banned_is_a_neutral_step():
    history = [row(None, "attivo", "2025-01-01 00:00:00"), row("attivo", "ex_membro", "2025-06-01 00:00:00"),
               row("ex_membro", "bannato", "2026-01-01 00:00:00", "tornato a insultare")]
    summary = summarize(member("bannato", joined="2025-01-01"), history, TODAY)
    assert [(h.key, h.tone) for h in summary.history] == [("moved", "neutral"), ("left", "bad"), ("joined", "good")]
    assert summary.ban_reason == "tornato a insultare" and summary.in_guild == "Il 01-01-2026"
