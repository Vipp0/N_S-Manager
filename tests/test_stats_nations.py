"""Classifica delle nazioni nelle Statistiche (con bandiere) e bandiere nella ricerca globale."""
import pytest
from PySide6.QtWidgets import QApplication, QWidget

from gilda_app.db.database import add_member, connect


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def conn(tmp_path):
    return connect(tmp_path / "gilda.db")


def _rows(page):
    from gilda_app.ui.stats_view import NationRow

    return page.content.findChildren(NationRow)


def test_nation_ranking_has_a_flag_a_count_and_a_bar_per_nation(qapp, conn):
    from gilda_app.ui.stats_view import StatsPage

    for index in range(3):
        add_member(conn, f"It{index}", "", "", ["Italy"], "attivo")
    add_member(conn, "Es", "", "", ["Spain"], "attivo")
    add_member(conn, "Doppio", "", "", ["Italy", "Spain"], "attivo")
    add_member(conn, "Uscito", "", "", ["France"], "ex_membro")  # solo i membri attuali

    page = StatsPage(lambda: conn)
    rows = _rows(page)
    assert page._nation_categories == ["Italia", "Spagna"]  # dal più numeroso, senza gli ex membri
    assert len(rows) == 2
    assert [len(page._nation_members[n]) for n in page._nation_categories] == [4, 2]
    from PySide6.QtWidgets import QLabel

    first = rows[0]
    flag = next(label for label in first.findChildren(QLabel) if label.pixmap() is not None and not label.pixmap().isNull())
    assert flag.pixmap().height() > 0
    texts = [label.text() for label in first.findChildren(QLabel)]
    assert "Italia" in texts and "4" in texts


def test_nation_ranking_hover_lists_the_names_and_leaving_hides_them(qapp, conn):
    from gilda_app.ui.stats_view import StatsPage

    add_member(conn, "Beta", "", "", ["Italy"], "attivo")
    add_member(conn, "Alfa", "", "", ["Italy"], "attivo")
    page = StatsPage(lambda: conn)
    row = _rows(page)[0]
    row.hovered.emit(True, 0)
    assert page._nation_hovered_index == 0
    page._show_nation_tooltip()
    assert page._nation_tooltip.text() == "Alfa\nBeta"  # in ordine alfabetico
    row.hovered.emit(False, 0)
    assert page._nation_hovered_index is None and page._nation_tooltip.isHidden()


def test_nation_ranking_without_members_says_there_is_no_data(qapp, conn):
    from gilda_app.ui.stats_view import StatsPage

    page = StatsPage(lambda: conn)
    assert _rows(page) == [] and page._nation_categories == []


def test_global_search_shows_the_flags(qapp, conn):
    from gilda_app.ui.global_search import NATION_COLUMN, GlobalSearchDialog

    add_member(conn, "Bandiera", "", "", ["Italy"], "attivo")
    add_member(conn, "SenzaNazione", "", "", [], "attivo")
    parent = QWidget()  # il dialogo vive finché vive il genitore
    dialog = GlobalSearchDialog(parent, conn)
    dialog.search_box.setText("an")  # Bandiera, SenzaNazione
    items = {dialog.results_table.item(r, 0).text(): dialog.results_table.item(r, NATION_COLUMN) for r in range(2)}
    assert not items["Bandiera"].icon().isNull()
    assert items["SenzaNazione"].icon().isNull()  # nessuna nazione, nessuna bandiera
    dialog.close()
