"""Ricava dalle immagini originali delle feste le due versioni usate dal programma.

  - wordmark_<tema>.png: il logo dell'intestazione, su sfondo trasparente (come wordmark.png). Le
    immagini di partenza hanno lo sfondo bianco: lo si toglie senza rovinare i bagliori, calcolando per
    ogni pixel quanto è lontano dal bianco (quel valore diventa la trasparenza) e togliendo il bianco
    dal colore.
  - splash_<tema>.png: la schermata di caricamento, 720x540 come splash.png. L'originale è 16:9: si
    adatta alla larghezza su una tela nera 4:3, sfumando i bordi in nero, e in basso resta la fascia
    libera per "Loading..." e per la barra dell'aggiornamento.

Uso (dalla cartella del progetto, con il venv):
    python tools/make_seasonal_assets.py halloween "Logo Halloween Night_Shade Manager.png" \\
        "Night_Shade Manager Halloween.png"
"""
import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter

RESOURCES = Path(__file__).resolve().parent.parent / "gilda_app" / "resources"
WORDMARK_HEIGHT = 220  # come wordmark.png
SPLASH_SIZE = (720, 540)  # come splash.png
SPLASH_TOP = 24  # margine nero sopra l'immagine: il logo resta più o meno dov'era in splash.png
EDGE_FADE = 56  # altezza della sfumatura in nero ai bordi superiore/inferiore dell'immagine
MIN_ALPHA = 10  # sotto questa opacità un pixel è alone residuo: si azzera


def remove_white_background(source: QImage) -> QImage:
    """Immagine con sfondo bianco -> immagine con trasparenza (stesso colore sopra qualsiasi sfondo)."""
    image = source.convertToFormat(QImage.Format_RGB32)  # byte per pixel: B, G, R, 0xFF
    data = bytes(image.constBits())
    out = bytearray(len(data))
    for i in range(0, len(data), 4):
        blue, green, red = data[i], data[i + 1], data[i + 2]
        alpha = 255 - min(red, green, blue)
        if alpha < MIN_ALPHA:
            continue
        factor = 255 / alpha
        out[i] = max(0, min(255, int(255 - (255 - blue) * factor)))
        out[i + 1] = max(0, min(255, int(255 - (255 - green) * factor)))
        out[i + 2] = max(0, min(255, int(255 - (255 - red) * factor)))
        out[i + 3] = alpha
    return QImage(bytes(out), image.width(), image.height(), image.width() * 4, QImage.Format_ARGB32).copy()


def crop_to_content(image: QImage, margin: int = 4) -> QImage:
    width, height = image.width(), image.height()
    xs, ys = [], []
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if (image.pixel(x, y) >> 24) > 24:
                xs.append(x)
                ys.append(y)
    left, right = max(0, min(xs) - margin), min(width, max(xs) + margin)
    top, bottom = max(0, min(ys) - margin), min(height, max(ys) + margin)
    return image.copy(left, top, right - left, bottom - top)


def make_wordmark(source_path: Path, target: Path) -> QImage:
    image = crop_to_content(remove_white_background(QImage(str(source_path))))
    result = image.scaledToHeight(WORDMARK_HEIGHT, Qt.SmoothTransformation)
    result.save(str(target))
    return result


def make_splash(source_path: Path, target: Path) -> QImage:
    width, height = SPLASH_SIZE
    art = QImage(str(source_path)).convertToFormat(QImage.Format_RGB32).scaledToWidth(width, Qt.SmoothTransformation)
    canvas = QImage(width, height, QImage.Format_RGB32)
    canvas.fill(QColor("#000000"))
    painter = QPainter(canvas)
    painter.drawImage(QPoint(0, SPLASH_TOP), art)
    top, bottom = SPLASH_TOP, SPLASH_TOP + art.height()
    for y0, y1, opaque_first in ((top, top + EDGE_FADE, True), (bottom - EDGE_FADE, bottom, False)):
        fade = QLinearGradient(0, y0, 0, y1)
        fade.setColorAt(0, QColor(0, 0, 0, 255 if opaque_first else 0))
        fade.setColorAt(1, QColor(0, 0, 0, 0 if opaque_first else 255))
        painter.fillRect(0, y0, width, y1 - y0, fade)
    painter.end()
    canvas.save(str(target))
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("theme", help="nome del tema (es. halloween): dà i nomi dei file in resources/")
    parser.add_argument("logo", help="logo con sfondo bianco")
    parser.add_argument("splash", help="immagine per la schermata di caricamento")
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - serve a QImage/QPainter
    wordmark = make_wordmark(Path(args.logo), RESOURCES / f"wordmark_{args.theme}.png")
    splash = make_splash(Path(args.splash), RESOURCES / f"splash_{args.theme}.png")
    print(f"wordmark_{args.theme}.png {wordmark.width()}x{wordmark.height()}  splash_{args.theme}.png {splash.width()}x{splash.height()}")


if __name__ == "__main__":
    main()
