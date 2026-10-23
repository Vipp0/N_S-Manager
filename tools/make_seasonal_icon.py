"""Ricava l'icona di un tema (icon_<tema>.png, 512x512) ricolorando quella normale.

L'icona normale è un gatto nero con occhi rossi e un bagliore/simbolo bianchi. Qui il bianco diventa il
colore del tema (per Halloween un arancio) e il rosso degli occhi un ambra, lasciando il nero com'è.

Uso (dalla cartella del progetto, con il venv):
    python tools/make_seasonal_icon.py halloween
"""
import argparse
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage

RESOURCES = Path(__file__).resolve().parent.parent / "gilda_app" / "resources"
SIZE = 512

# tema -> (colore dei dettagli chiari, colore degli occhi) come (r, g, b)
THEMES = {
    "halloween": ((255, 128, 24), (255, 176, 20)),
}


def recolor(source: QImage, light: tuple[int, int, int], eyes: tuple[int, int, int]) -> QImage:
    image = source.scaled(SIZE, SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32)  # non premoltiplicato: colore e trasparenza separati
    result = QImage(image.size(), QImage.Format_ARGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            r, g, b, alpha = image.pixelColor(x, y).getRgb()
            strength = max(r, g, b) / 255
            if r > 90 and r > g * 2.2:  # rosso degli occhi
                k = r / 255
                new = (eyes[0] * k, eyes[1] * k, eyes[2] * k)
            elif max(r, g, b) - min(r, g, b) < 45 and max(r, g, b) > 18:  # bianco/grigio: bagliore e dettagli
                bright = max(0.0, (strength - 0.85) / 0.15)  # il nucleo più chiaro vira al giallo pallido
                glow = strength ** 0.75  # il contorno sfumato resta ben visibile anche a 16 px
                new = tuple(c * glow + (255 - c) * 0.35 * bright * glow for c in light)
            else:
                new = (r, g, b)
            result.setPixelColor(x, y, QColor(*(max(0, min(255, int(c))) for c in new), alpha))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("theme", choices=sorted(THEMES))
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - serve a QImage
    light, eyes = THEMES[args.theme]
    icon = recolor(QImage(str(RESOURCES / "app_icon.png")), light, eyes)
    target = RESOURCES / f"icon_{args.theme}.png"
    icon.save(str(target))
    print(f"{target.name} {icon.width()}x{icon.height()}")


if __name__ == "__main__":
    main()
