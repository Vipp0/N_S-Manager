"""Una sola copia del programma per volta (per ogni database).

Aprire due copie sullo stesso database fa vedere dati non aggiornati nell'una dopo le
modifiche fatte nell'altra. La prima copia resta in ascolto su un canale locale (un "named
pipe" su Windows); chi parte dopo lo trova, chiede alla prima di venire in primo piano ed esce.
Il canale sparisce da solo quando il processo termina, anche per un arresto anomalo."""
import hashlib
import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

CONNECT_TIMEOUT_MS = 500

_current: "SingleInstance | None" = None


def _channel_name(db_file: Path) -> str:
    # Per database: copie in cartelle diverse (con database diversi) non si ostacolano.
    digest = hashlib.sha1(str(db_file.resolve()).lower().encode("utf-8")).hexdigest()[:16]
    return f"NightShadeManager-{digest}"


class SingleInstance(QObject):
    # Emesso nella prima copia quando ne viene lanciata un'altra.
    activation_requested = Signal()

    def __init__(self, db_file: Path):
        super().__init__()
        self._name = _channel_name(db_file)
        self._server: QLocalServer | None = None

    def acquire(self) -> bool:
        """True se questa è la prima copia (e resta registrata come tale). False se ce n'è già
        un'altra: la si è avvisata e questa copia deve chiudersi. Se il canale non si può
        creare, si parte comunque: meglio due copie che nessuna."""
        global _current
        if self._notify_running_instance():
            return False
        QLocalServer.removeServer(self._name)  # resto di un arresto anomalo (su Windows non serve, altrove sì)
        server = QLocalServer(self)
        if server.listen(self._name):
            server.newConnection.connect(self._on_connection)
            self._server = server
        _current = self
        return True

    def release(self) -> None:
        """Libera il canale: serve prima di lanciare di proposito una nuova copia (riavvio)."""
        global _current
        if self._server is not None:
            self._server.close()
            self._server = None
        if _current is self:
            _current = None

    def _notify_running_instance(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._name)
        if not socket.waitForConnected(CONNECT_TIMEOUT_MS):
            return False
        if os.name == "nt":
            # Chi è appena stato lanciato dall'utente ha il diritto di dare il primo piano:
            # lo si cede alla copia già aperta, altrimenti Windows la farebbe solo lampeggiare.
            try:
                import ctypes

                ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
            except OSError:
                pass
        socket.write(b"show")
        socket.waitForBytesWritten(CONNECT_TIMEOUT_MS)
        socket.disconnectFromServer()
        return True

    def _on_connection(self) -> None:
        while self._server is not None and self._server.hasPendingConnections():
            client = self._server.nextPendingConnection()
            client.disconnected.connect(client.deleteLater)
            client.disconnectFromServer()
            self.activation_requested.emit()


def release_current() -> None:
    if _current is not None:
        _current.release()
