import sys
import threading

from gilda_app.utils import error_log


def test_write_entry_appends_with_version_and_title(tmp_path):
    log = tmp_path / "errori.log"
    error_log.write_entry(log, "2.4.8", "prova", "Traceback...\nValueError: x")
    error_log.write_entry(log, "2.4.8", "seconda", "altro")
    text = log.read_text(encoding="utf-8")
    assert "v2.4.8 - prova" in text and "ValueError: x" in text and "seconda" in text
    assert text.index("prova") < text.index("seconda")


def test_write_entry_never_raises(tmp_path):
    error_log.write_entry(tmp_path / "no_such_dir" / "errori.log", "1", "t", "d")  # cartella inesistente


def test_log_is_trimmed_keeping_latest_entries(tmp_path):
    log = tmp_path / "errori.log"
    for i in range(400):
        error_log.write_entry(log, "1", f"entry {i}", "x" * 1000)
    assert log.stat().st_size <= error_log.MAX_BYTES
    text = log.read_text(encoding="utf-8")
    assert "entry 399" in text and "entry 0 " not in text


def test_install_logs_unhandled_exceptions_in_main_and_threads(tmp_path):
    log = tmp_path / "errori.log"
    old_hook, old_thread_hook, old_crash = sys.excepthook, threading.excepthook, error_log._crash_file
    try:
        error_log.install(log, "9.9")
        try:
            raise KeyError("boom-main")
        except KeyError:
            sys.excepthook(*sys.exc_info())

        def worker():
            raise RuntimeError("boom-thread")

        thread = threading.Thread(target=worker, name="worker-x")
        thread.start()
        thread.join()
        text = log.read_text(encoding="utf-8")
        assert "boom-main" in text and "boom-thread" in text and "worker-x" in text and "v9.9" in text
    finally:
        sys.excepthook, threading.excepthook = old_hook, old_thread_hook
        import faulthandler

        faulthandler.disable()
        if error_log._crash_file is not None:
            error_log._crash_file.close()
        error_log._crash_file = old_crash
