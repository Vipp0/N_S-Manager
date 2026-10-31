"""Il pannello dei dettagli nelle schermate Membri: si apre con un clic su una riga, si chiude in più modi, segue i dati."""
from datetime import date

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from gilda_app.models.member import Member
from gilda_app.ui.member_table import NUMBER_COLUMN, PANEL_BESIDE_MIN_WIDTH, MemberListPage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def make_members():
    return [
        Member(1, "Aldric", "Ald", "aldric_pl", "attivo", None, "Gioca nel weekend", ["Poland"]),
        Member(2, "Dorn", "Dorn", "dorn_pl", "attivo", "2023-11-21", "", ["Poland"]),
        Member(3, "Kaelith", "Kael", "kaelith#0007", "attivo", "2022-11-03", "Officer", ["Italy", "Spain"]),
    ]


HISTORY = {
    3: [
        {"previous_status": None, "new_status": "attivo", "changed_at": "2022-11-03 00:00:00", "note": None},
        {"previous_status": "attivo", "new_status": "ex_membro", "changed_at": "2024-01-10 10:00:00", "note": None},
        {"previous_status": "ex_membro", "new_status": "attivo", "changed_at": "2025-06-01 10:00:00", "note": None},
    ]
}


@pytest.fixture
def page(qapp):
    page = MemberListPage("attivo", history_provider=lambda member_id: HISTORY.get(member_id, []))
    page.resize(1500, 800)
    page.set_members(make_members())
    page.show()
    qapp.processEvents()
    return page


def row_pos(page, row):
    return page.table.visualItemRect(page.table.item(row, 1)).center()


def click_row(page, row):
    """Un clic vero sulla riga: pressione (la vede il filtro), scelta della riga da parte di Qt, rilascio."""
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    pos = row_pos(page, row)
    press = QMouseEvent(QEvent.MouseButtonPress, QPointF(pos), QPointF(pos), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    page.eventFilter(page.table.viewport(), press)
    page.table.selectRow(row)
    page._on_table_release(pos)


def test_a_click_on_a_row_opens_the_panel_with_that_member(qapp, page):
    assert not page.detail.isVisible()
    click_row(page, 1)
    assert page.detail.isVisible() and page.detail.member.family_name == "Dorn"
    click_row(page, 0)  # un'altra riga: cambia membro, il pannello resta aperto
    assert page.detail.isVisible() and page.detail.member.family_name == "Aldric"


def test_it_closes_with_the_same_row_again_an_empty_spot_the_x_and_escape(qapp, page):
    click_row(page, 1)
    click_row(page, 1)  # la stessa riga ancora
    assert not page.detail.isVisible() and page.table.selectionModel().selectedRows() == []

    click_row(page, 1)
    page._open_at_press = page._detail_id
    page._on_table_release(QPoint(40, page.table.viewport().height() - 5))  # un punto vuoto sotto le righe
    assert not page.detail.isVisible()

    click_row(page, 1)
    page.detail.close_requested.emit()  # la X
    assert not page.detail.isVisible()

    click_row(page, 1)
    page.close_detail()  # Esc fa la stessa cosa
    assert not page.detail.isVisible()


def test_a_click_outside_the_table_on_the_page_closes_it(qapp, page):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    click_row(page, 1)
    event = QMouseEvent(QEvent.MouseButtonPress, QPointF(5, 5), QPointF(5, 5), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    page.mousePressEvent(event)
    assert not page.detail.isVisible()


def test_a_double_click_to_edit_does_not_toggle_the_panel(qapp, page):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent

    click_row(page, 1)  # il primo clic del doppio clic apre
    assert page.detail.isVisible()
    pos = row_pos(page, 1)
    double = QMouseEvent(QEvent.MouseButtonDblClick, pos, pos, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    page.eventFilter(page.table.viewport(), double)
    release = QMouseEvent(QEvent.MouseButtonRelease, pos, pos, Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    page.eventFilter(page.table.viewport(), release)  # il rilascio del secondo clic: ignorato
    assert page.detail.isVisible()
    click_row(page, 1)  # un clic vero dopo, sulla stessa riga: chiude
    assert not page.detail.isVisible()


def test_choosing_another_row_with_the_keyboard_updates_an_open_panel(qapp, page):
    click_row(page, 0)
    page.table.selectRow(2)
    assert page.detail.member.family_name == "Kaelith"
    page.close_detail()
    page.table.selectRow(1)  # chiuso: scegliere una riga non lo apre
    assert not page.detail.isVisible()


def test_updating_the_data_refreshes_the_open_panel_or_closes_it_if_the_member_is_gone(qapp, page):
    click_row(page, 1)
    members = make_members()
    members[1].note = "Nota nuova"
    page.set_members(members)
    assert page.detail.isVisible() and page.detail.member.note == "Nota nuova"
    selected = page.table.selectionModel().selectedRows()
    assert selected and page.table.item(selected[0].row(), NUMBER_COLUMN).data(Qt.UserRole) == 2  # riga ancora scelta
    page.set_members([m for m in members if m.id != 2])  # il membro non c'è più (spostato, eliminato)
    assert not page.detail.isVisible()


def test_the_panel_sits_beside_the_table_when_wide_and_covers_it_when_narrow(qapp, page):
    click_row(page, 1)
    page.resize(1500, 800)
    qapp.processEvents()
    assert page._body.indexOf(page.detail) >= 0  # accanto: la tabella si restringe
    wide_table = page.table.width()
    page.resize(PANEL_BESIDE_MIN_WIDTH - 100, 800)
    qapp.processEvents()
    assert page._body.indexOf(page.detail) < 0  # sopra: la tabella non perde spazio
    assert page.table.width() > wide_table - 400 and page.detail.isVisible()
    assert page.detail.geometry().right() <= page.width()
    page.resize(1500, 800)
    qapp.processEvents()
    assert page._body.indexOf(page.detail) >= 0


def test_the_panel_buttons_ask_to_edit_and_move_that_member(qapp, page):
    edits, moves = [], []
    page.edit_requested.connect(edits.append)
    page.move_requested.connect(moves.append)
    click_row(page, 2)
    page.detail._edit.click()
    page.detail._move.click()
    assert [m.id for m in edits] == [3] and [m.id for m in moves] == [3]


def test_copy_puts_the_discord_name_on_the_clipboard_and_says_copied(qapp, page):
    click_row(page, 2)
    page.detail._copy_discord()
    assert QGuiApplication.clipboard().text() == "kaelith#0007" and page.detail._copied
    page.detail._copy_done()
    assert not page.detail._copied


def test_a_member_without_a_joining_date_offers_to_add_it(qapp, page):
    edits = []
    page.edit_requested.connect(edits.append)
    click_row(page, 0)  # Aldric non ha la data di ingresso
    assert page.detail._summary.missing_join_date
    from qfluentwidgets import PushButton

    add = next(b for b in page.detail.findChildren(PushButton) if b.text() == "Aggiungi la data")
    add.click()
    assert [m.id for m in edits] == [1]


def test_history_shows_two_steps_and_the_rest_on_request(qapp, page):
    click_row(page, 2)  # Kaelith: entrato, uscito, rientrato
    assert len(page.detail._summary.history) == 3 and not page.detail._history_all
    page.detail._toggle_history()
    assert page.detail._history_all
    click_row(page, 0)  # un altro membro: lo storico torna corto
    click_row(page, 2)
    assert not page.detail._history_all


def test_the_page_works_without_a_history_provider(qapp):
    page = MemberListPage("attivo")
    page.resize(1500, 800)
    page.set_members(make_members())
    page.show()
    qapp.processEvents()
    page.open_detail(make_members()[1])
    assert page.detail.isVisible() and page.detail._summary.in_guild.startswith("Dal 21-11-2023")
