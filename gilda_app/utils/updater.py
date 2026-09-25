"""Aggiornamento automatico dell'app da una release GitHub.

Sequenza (ognuno dei due processi mostra la stessa schermata di avanzamento):
1. l'app in uso fa il backup del database, scarica lo zip della release, ne controlla
   l'integrità (SHA256 se pubblicato) e lo estrae in <app>/_update/new;
2. lancia da lì la NUOVA versione con "--apply-update": l'app in uso non può sostituire i
   propri file finché è aperta, la nuova sì, dopo che la vecchia si è chiusa;
3. la nuova versione mette da parte i file vecchi (rinominandoli in "*.old"), copia quelli
   nuovi e riavvia l'app dalla cartella vera. Se qualcosa fallisce rimette a posto i vecchi.
I file dell'utente (gilda.db, backups/, ...) non fanno parte dello zip e non si toccano.
Le copie "*.old" e la cartella _update si cancellano al primo avvio riuscito."""
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from gilda_app.utils.update_check import ReleaseInfo

APPLY_FLAG = "--apply-update"
UPDATE_DIR_NAME = "_update"
STAGE_DIR_NAME = "new"
OLD_SUFFIX = ".old"
EXE_NAME = "Night_Shade Manager.exe"
DOWNLOAD_TIMEOUT_SECONDS = 30
_CHUNK = 256 * 1024

# progress(frazione 0..1 della fase, chiave della frase da mostrare o None per lasciare la precedente)
Progress = Callable[[float, "str | None"], None]


class UpdateError(Exception):
    pass


def _noop(fraction: float, key: "str | None" = None) -> None:
    pass


def update_dir(app_dir: Path) -> Path:
    return app_dir / UPDATE_DIR_NAME


def stage_dir(app_dir: Path) -> Path:
    return update_dir(app_dir) / STAGE_DIR_NAME


def can_self_update(app_dir: Path) -> bool:
    """Solo dall'eseguibile costruito, e solo se la cartella è scrivibile."""
    if not getattr(sys, "frozen", False):
        return False
    try:
        probe = app_dir / ".write_test"
        probe.write_text("x")
        probe.unlink()
    except OSError:
        return False
    return True


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _retry(action, attempts: int = 20, delay: float = 0.5):
    """L'antivirus può tenere un file aperto per un attimo: si riprova per qualche secondo."""
    for attempt in range(attempts):
        try:
            return action()
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


# -- fase 1: scaricamento ------------------------------------------------------
def download_release(info: ReleaseInfo, dest: Path, progress: Progress = _noop) -> None:
    """Scarica lo zip in `dest` e lo verifica (dimensione e SHA256, se noti)."""
    if not info.asset_url:
        raise UpdateError("no asset")
    request = urllib.request.Request(info.asset_url, headers={"User-Agent": "Night-Shade-Manager"})
    digest = hashlib.sha256()
    received = 0
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, open(dest, "wb") as out:
            total = int(response.headers.get("Content-Length") or info.asset_size or 0)
            while True:
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                progress(received / total if total else 0.0, None)
    except OSError as exc:
        raise UpdateError(f"download: {exc}") from exc
    if info.asset_size and received != info.asset_size:
        raise UpdateError("incomplete download")
    if info.sha256 and digest.hexdigest().lower() != info.sha256.lower():
        raise UpdateError("checksum mismatch")


def extract_release(zip_path: Path, dest: Path, progress: Progress = _noop) -> None:
    """Estrae lo zip in `dest` (svuotata prima). Rifiuta percorsi che escono dalla
    cartella e zip senza l'eseguibile dell'app."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    root = dest.resolve()
    try:
        with zipfile.ZipFile(zip_path) as archive:
            if EXE_NAME not in archive.namelist():
                raise UpdateError("not an app package")
            members = archive.infolist()
            for index, member in enumerate(members):
                target = (dest / member.filename).resolve()
                if root != target and root not in target.parents:
                    raise UpdateError("unsafe path in archive")
                archive.extract(member, dest)
                progress((index + 1) / len(members), None)
    except zipfile.BadZipFile as exc:
        raise UpdateError("bad zip") from exc


def launch_apply(app_dir: Path, pid: int, language: str) -> None:
    """Avvia la nuova versione (già estratta) in modalità "applica aggiornamento"."""
    _spawn(stage_dir(app_dir) / EXE_NAME, [APPLY_FLAG, str(app_dir), str(pid), language])


def relaunch(app_dir: Path) -> None:
    _spawn(app_dir / EXE_NAME, [])


def _spawn(exe: Path, args: list[str]) -> None:
    # PYINSTALLER_RESET_ENVIRONMENT: senza, il figlio riusa le librerie temporanee del padre.
    env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")
    subprocess.Popen([str(exe), *args], cwd=str(exe.parent), env=env, close_fds=True)


# -- fase 2: sostituzione ------------------------------------------------------
def wait_for_exit(pid: int, timeout: float = 60.0) -> bool:
    """Aspetta che l'app in uso si sia chiusa (i suoi file restano bloccati finché vive).
    True se è chiusa, False se scade il tempo."""
    if pid <= 0:
        return True
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return True  # già chiuso
        try:
            return kernel32.WaitForSingleObject(handle, int(timeout * 1000)) == 0
        finally:
            kernel32.CloseHandle(handle)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        time.sleep(0.05)
    return False


def _count_files(path: Path) -> int:
    if path.is_file():
        return 1
    return sum(len(files) for _, _, files in os.walk(path))


def apply_staged_update(stage: Path, target: Path, progress: Progress = _noop) -> None:
    """Sostituisce i file dell'app in `target` con quelli di `stage`. I vecchi si
    conservano come "<nome>.old"; se qualcosa va storto si ripristinano e si solleva
    UpdateError, lasciando l'app com'era."""
    entries = sorted(stage.iterdir())
    total = max(1, sum(_count_files(e) for e in entries))
    backed_up: list[str] = []
    started: list[str] = []
    copied = 0
    try:
        progress(0.0, "update.step.backup")
        for entry in entries:
            dest = target / entry.name
            old = target / (entry.name + OLD_SUFFIX)
            if dest.exists() or dest.is_symlink():
                if old.exists() or old.is_symlink():
                    _retry(lambda old=old: _remove(old))
                _retry(lambda dest=dest, old=old: os.replace(dest, old))
                backed_up.append(entry.name)
        progress(0.0, "update.step.install")
        for entry in entries:
            started.append(entry.name)
            dest = target / entry.name
            if entry.is_file():
                shutil.copy2(entry, dest)
                copied += 1
                progress(copied / total, None)
                continue
            for folder, _, files in os.walk(entry):
                relative = Path(folder).relative_to(entry)
                (dest / relative).mkdir(parents=True, exist_ok=True)
                for name in files:
                    shutil.copy2(Path(folder) / name, dest / relative / name)
                    copied += 1
                    progress(copied / total, None)
    except BaseException as exc:
        _rollback(target, backed_up, started)
        if isinstance(exc, Exception):
            raise UpdateError(str(exc)) from exc
        raise


def _rollback(target: Path, backed_up: list[str], started: list[str]) -> None:
    for name in started:
        try:
            _remove(target / name)
        except OSError:
            pass
    for name in backed_up:
        try:
            _remove(target / name)
            os.replace(target / (name + OLD_SUFFIX), target / name)
        except OSError:
            pass


def cleanup_leftovers(app_dir: Path) -> None:
    """Dopo un avvio riuscito: via la cartella di lavoro e le copie "*.old"."""
    shutil.rmtree(update_dir(app_dir), ignore_errors=True)
    try:
        entries = list(app_dir.iterdir())
    except OSError:
        return
    for path in entries:
        if path.name.endswith(OLD_SUFFIX) and (app_dir / path.name[: -len(OLD_SUFFIX)]).exists():
            try:
                _remove(path)
            except OSError:
                pass
