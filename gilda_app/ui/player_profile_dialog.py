import html
import threading
from dataclasses import dataclass

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QLabel
from qfluentwidgets import MessageBoxBase, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.server_status_footer import describe_error
from gilda_app.utils.bdo_guild import GuildInfo, PlayerProfile, fetch_player
from gilda_app.utils.bdoalerts_api import ApiError
from gilda_app.utils.date_format import iso_to_display

CHARACTERS_SHOWN = 12


@dataclass
class BdoContext:
    """Quello che serve per interrogare l'API dal form di un membro."""

    api_key: str
    region: str
    guild_name: str
    guild: GuildInfo | None = None


class _ProfileSignal(QObject):
    finished = Signal(object)


class PlayerProfileDialog(MessageBoxBase):
    """Profilo BDO di un giocatore (dati di terzi da bdoalerts.net), solo da consultare:
    non scrive nulla nel database."""

    def __init__(self, parent, family_name: str, context: BdoContext):
        super().__init__(parent)
        self._context = context
        self._family_name = family_name

        self.viewLayout.addWidget(SubtitleLabel(tr("bdo.profile.title", name=family_name), self))
        self._body = QLabel(tr("bdo.profile.loading"), self)
        self._body.setTextFormat(Qt.RichText)
        self._body.setWordWrap(True)
        self._body.setMinimumHeight(120)
        self.viewLayout.addWidget(self._body)

        self.widget.setMinimumWidth(480)
        self.yesButton.setText(tr("button.close"))
        self.cancelButton.hide()

        self._signal = _ProfileSignal()
        self._signal.finished.connect(self._on_loaded)
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            result = fetch_player(self._context.api_key, self._context.region, self._family_name)
        except ApiError as exc:
            result = exc.kind
        self._signal.finished.emit(result)

    def _on_loaded(self, result) -> None:
        if isinstance(result, str):
            self._body.setText(html.escape(describe_error(result)[0]))
            return
        self._body.setText(self._render(result))

    def _render(self, profile: PlayerProfile) -> str:
        rows: list[tuple[str, str]] = []
        ctx = self._context
        master = ctx.guild is not None and ctx.guild.master.casefold() == profile.family_name.casefold()
        if profile.guild:
            text = profile.guild
            if ctx.guild_name and profile.guild.casefold() == ctx.guild_name.casefold():
                text += " — " + tr("bdo.profile.role_master" if master else "bdo.profile.role_member")
            rows.append((tr("bdo.profile.guild"), text))
        else:
            rows.append((tr("bdo.profile.guild"), tr("bdo.profile.no_guild")))
        main = profile.main_character()
        if main is not None:
            rows.append((tr("bdo.profile.main"), tr("bdo.profile.main_value", cls=main.char_class, level=main.level)))
        rows.append((tr("bdo.profile.characters"), str(len(profile.characters))))
        if profile.max_gear_score is not None:
            rows.append((tr("bdo.profile.gear_score"), str(profile.max_gear_score)))
        if profile.contribution_points is not None:
            rows.append((tr("bdo.profile.contribution"), str(profile.contribution_points)))
        if profile.energy is not None:
            rows.append((tr("bdo.profile.energy"), str(profile.energy)))
        if profile.family_created is not None:
            rows.append((tr("bdo.profile.created"), iso_to_display(profile.family_created.isoformat())))

        body = "<table cellspacing='4'>" + "".join(
            f"<tr><td>{html.escape(a)}</td><td>&nbsp;&nbsp;<b>{html.escape(b)}</b></td></tr>" for a, b in rows
        ) + "</table>"

        ordered = sorted(profile.characters, key=lambda c: (not c.is_main, -c.level))
        shown = [f"{html.escape(c.char_class)} {c.level}" for c in ordered[:CHARACTERS_SHOWN]]
        if shown:
            more = len(ordered) - CHARACTERS_SHOWN
            suffix = f" … +{more}" if more > 0 else ""
            body += f"<p style='color: #8a8886;'>{', '.join(shown)}{suffix}</p>"
        if profile.is_private:
            body += f"<p style='color: #8a8886;'>{html.escape(tr('bdo.profile.private_note'))}</p>"
        return body
