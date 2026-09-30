import html
import threading
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import MessageBoxBase, ScrollArea, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.server_status_footer import describe_error
from gilda_app.utils.bdo_guild import GuildInfo, PlayerProfile, fetch_player
from gilda_app.utils.bdoalerts_api import ERROR_BAD_RESPONSE, ApiError
from gilda_app.utils.date_format import iso_to_display

DIALOG_MAX_HEIGHT = 520


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

        # Scorrevole: con classi, vite da mestierante e storico gilda il contenuto supera
        # facilmente l'altezza di un popup normale, soprattutto per chi ha tanti personaggi.
        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self._body = QLabel(tr("bdo.profile.loading"), content)
        self._body.setTextFormat(Qt.RichText)
        self._body.setWordWrap(True)
        self._body.setMinimumHeight(120)
        content_layout.addWidget(self._body)
        self._scroll = ScrollArea(self)
        self._scroll.setWidget(content)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setFixedHeight(120)  # ridimensionata al testo vero non appena carica (_fit_scroll)
        self.viewLayout.addWidget(self._scroll)

        self.widget.setMinimumWidth(560)
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
        except Exception:  # risposta inattesa: meglio un messaggio che un "Caricamento..." eterno
            result = ERROR_BAD_RESPONSE
        self._signal.finished.emit(result)

    def _on_loaded(self, result) -> None:
        if isinstance(result, str):
            self._body.setText(html.escape(describe_error(result)[0]))
        else:
            self._body.setText(self._render(result))
        # Il testo appena cambiato non ha ancora l'altezza definitiva finché il layout non
        # gira un'altra volta: si rimanda di un giro di eventi, altrimenti si misura quella
        # vecchia (quella di "Caricamento...", molto più corta).
        QTimer.singleShot(0, self._fit_scroll)

    def _fit_scroll(self) -> None:
        width = self._body.width() or self._scroll.viewport().width()
        height = self._body.heightForWidth(width) if width > 0 else self._body.sizeHint().height()
        self._scroll.setFixedHeight(min(max(height, 60) + 12, DIALOG_MAX_HEIGHT))

    def _render(self, profile: PlayerProfile) -> str:
        rows: list[tuple[str, str]] = []
        ctx = self._context
        master = ctx.guild is not None and ctx.guild.master.casefold() == profile.family_name.casefold()
        if profile.guild:
            text = profile.guild
            if ctx.guild_name and profile.guild.casefold() == ctx.guild_name.casefold():
                text += " — " + tr("bdo.profile.role_master" if master else "bdo.profile.role_member")
            rows.append((tr("bdo.profile.guild"), text))
        elif profile.guild_private:
            rows.append((tr("bdo.profile.guild"), tr("bdo.profile.guild_unknown")))
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

        if profile.characters:
            body += f"<p style='margin-bottom:2px;'><b>{html.escape(tr('bdo.profile.characters'))}</b></p>"
            for char_class, members in profile.characters_by_class():
                names = ", ".join(f"{html.escape(c.name)} {c.level}" for c in members)
                body += f"<p style='margin:0 0 2px 0;'><b>{html.escape(char_class)}</b> &nbsp;{names}</p>"

        if profile.life_skills:
            body += f"<p style='margin:10px 0 2px 0;'><b>{html.escape(tr('bdo.profile.life_skills'))}</b></p>"
            body += "<table cellspacing='4'>" + "".join(
                f"<tr><td>{html.escape(skill.name)}</td>"
                f"<td>&nbsp;&nbsp;{html.escape(tr('bdo.profile.life_skill_value', rank=skill.rank, level=skill.level))}"
                f" &nbsp;<span style='color: #8a8886;'>"
                f"({html.escape(tr('bdo.profile.life_skill_mastery', mastery=skill.mastery))})</span></td></tr>"
                for skill in profile.life_skills
            ) + "</table>"

        if profile.is_private:
            body += f"<p style='color: #8a8886; margin-top:10px;'>{html.escape(tr('bdo.profile.private_note'))}</p>"
        return body
