import importlib.util
from pathlib import Path

import pytest

from gilda_app.changelog import CHANGELOG

_SPEC = importlib.util.spec_from_file_location(
    "release_notes", Path(__file__).resolve().parent.parent / "tools" / "release_notes.py"
)
rn = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rn)


def test_note_with_a_title_gets_bold_lead_and_final_period():
    assert rn.format_note("Calendario: tasto destro su un evento") == "- **Calendario**: tasto destro su un evento."
    assert rn.format_note("Fatto.") == "- Fatto."
    assert rn.format_note("Cosa è cambiato!") == "- Cosa è cambiato!"


def test_long_or_sentence_like_heads_are_not_bolded():
    long_head = "x" * 80 + ": resto"
    assert rn.format_note(long_head).startswith("- x")
    assert "**" not in rn.format_note(long_head)
    assert "**" not in rn.format_note("Prima frase. Seconda: dettaglio")  # il "titolo" contiene già un punto
    assert "**" not in rn.format_note("minuscolo: non è un titolo")


def test_recent_release_has_short_summary_and_collapsible_details():
    notes = rn.build_notes("2.7.3")
    assert notes.startswith("## Novità in breve")
    assert "<details>" in notes and "</details>" in notes and "<summary>" in notes
    assert notes.index("## Novità in breve") < notes.index("<details>") < notes.index("## Come aggiornare")
    assert "\n\n</details>" in notes  # riga vuota prima della chiusura: serve a GitHub per mostrare l'elenco


def test_old_release_without_popup_text_lists_the_changelog_plainly():
    notes = rn.build_notes("2.5")
    assert notes.startswith("## Cosa cambia") and "<details>" not in notes


def test_update_instructions_depend_on_self_update_being_available():
    assert "Controlla aggiornamenti" in rn.build_notes("2.3")
    assert "Controlla aggiornamenti" not in rn.build_notes("1.11.0")
    assert "sostituendo i file" in rn.build_notes("1.11.0")
    for version in ("2.2", "2.7.3"):
        assert "**Dal programma**" in rn.build_notes(version)


def test_notes_never_promise_to_touch_user_data():
    for version in ("1.8.0", "2.7.3"):
        assert "`gilda.db`" in rn.build_notes(version) and "non vengono toccati" in rn.build_notes(version)


def test_unknown_version_is_refused():
    with pytest.raises(SystemExit):
        rn.build_notes("9.9.9")


@pytest.mark.parametrize("version", [entry["version"] for entry in CHANGELOG])
def test_every_changelog_entry_builds_valid_notes(version):
    notes = rn.build_notes(version)
    assert notes.count("<details>") == notes.count("</details>")
    assert "## Come aggiornare" in notes and len(notes) > 200
