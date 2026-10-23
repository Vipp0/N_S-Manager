"""Ricava l'icona di un tema (icon_<tema>.png, 512x512).

Due modi:
  - con il logo del tema (PNG trasparente): lo centra e gli mette attorno un contorno luminoso del colore
    del tema, perché a 16-32 px un logo scuro con linee sottili sparirebbe sulle barre scure;
  - senza logo: ricolora l'icona normale (gatto nero con occhi rossi e bagliore/simbolo bianchi): il bianco
    diventa il colore del tema e il rosso degli occhi un ambra.

Uso (dalla cartella del progetto, con il venv):
    python tools/make_seasonal_icon.py halloween "Logo Night_Shade Halloween.png"
    python tools/make_seasonal_icon.py halloween
"""
import argparse
import sys
from pathlib import Path

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

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


def with_glow_outline(logo: QImage, color: tuple[int, int, int], margin: int = 40) -> QImage:
    """Il logo centrato in una tela quadrata, con un contorno luminoso: sagoma del colore del tema ripetuta
    attorno al logo (spessore netto) e, più larga e tenue, per l'alone."""
    inner = SIZE - 2 * margin
    logo = logo.convertToFormat(QImage.Format_ARGB32_Premultiplied).scaled(
        inner, inner, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    left, top = (SIZE - logo.width()) // 2, (SIZE - logo.height()) // 2
    silhouette = QImage(logo.size(), QImage.Format_ARGB32_Premultiplied)
    silhouette.fill(QColor(*color))
    painter = QPainter(silhouette)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, logo)
    painter.end()

    canvas = QImage(SIZE, SIZE, QImage.Format_ARGB32_Premultiplied)
    canvas.fill(0)
    painter = QPainter(canvas)
    # (raggio in pixel, opacità): dall'alone largo al contorno netto
    for radius, opacity in ((30, 0.07), (22, 0.10), (15, 0.16), (9, 0.30), (5, 0.9)):
        painter.setOpacity(opacity)
        for step in range(24):
            angle = 2 * math.pi * step / 24
            offset = QPointF(left + radius * math.cos(angle), top + radius * math.sin(angle))
            painter.drawImage(offset, silhouette)
    painter.setOpacity(1.0)
    painter.drawImage(left, top, logo)
    painter.end()
    return canvas.convertToFormat(QImage.Format_ARGB32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("theme", choices=sorted(THEMES))
    parser.add_argument("logo", nargs="?", help="logo del tema, PNG trasparente (senza: ricolora l'icona normale)")
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - serve a QImage
    light, eyes = THEMES[args.theme]
    if args.logo:
        icon = with_glow_outline(QImage(args.logo), light)
    else:
        icon = recolor(QImage(str(RESOURCES / "app_icon.png")), light, eyes)
    target = RESOURCES / f"icon_{args.theme}.png"
    icon.save(str(target))
    print(f"{target.name} {icon.width()}x{icon.height()}")


if __name__ == "__main__":
    main()
