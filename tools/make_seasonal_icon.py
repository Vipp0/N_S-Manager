"""Ricava l'icona di un tema (icon_<tema>.png, 512x512).

Tre modi:
  - con il logo del tema (PNG trasparente): lo centra e gli mette attorno un contorno luminoso del colore
    del tema, perché a 16-32 px un logo scuro con linee sottili sparirebbe sulle barre scure;
  - con --black-background e un'immagine su sfondo nero (già con il suo contorno chiaro): il nero esterno
    diventa trasparente e l'immagine si centra nella tela;
  - senza logo: ricolora l'icona normale (gatto nero con occhi rossi e bagliore/simbolo bianchi): il bianco
    diventa il colore del tema e il rosso degli occhi un ambra.

Uso (dalla cartella del progetto, con il venv):
    python tools/make_seasonal_icon.py halloween "immagini_originali/Logo Night_Shade Halloween.png"
    python tools/make_seasonal_icon.py natale "immagini_originali/Gatto natalizio con occhi rossi luminosi.png" --black-background
    python tools/make_seasonal_icon.py halloween
"""
import argparse
import math
import sys
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

RESOURCES = Path(__file__).resolve().parent.parent / "gilda_app" / "resources"
SIZE = 512

# tema -> (colore dei dettagli chiari, colore degli occhi) come (r, g, b)
THEMES = {
    "halloween": ((255, 128, 24), (255, 176, 20)),
    "natale": ((200, 225, 255), (255, 60, 60)),
}
DARK = 28  # sotto questa luminosità un pixel è "nero" (sfondo, ma anche il corpo del gatto)
GAP_CLOSING = 3  # il contorno chiaro può avere piccoli varchi: si chiudono per non svuotare il corpo del gatto


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


def transparent_outside_black(image: QImage, margin: int = 16) -> QImage:
    """Immagine su sfondo nero con un contorno chiaro attorno al soggetto -> stesso soggetto su sfondo
    trasparente. Il nero dentro il contorno (il corpo) resta pieno; solo quello raggiunto dal bordo
    dell'immagine, senza attraversare il contorno, diventa trasparente."""
    inner = SIZE - 2 * margin
    image = image.scaled(inner, inner, Qt.KeepAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32)
    width, height = image.width(), image.height()
    light = [[max(image.pixelColor(x, y).getRgb()[:3]) >= DARK for x in range(width)] for y in range(height)]
    # il contorno si ispessisce di GAP_CLOSING pixel: i varchi più piccoli non lasciano passare il fondo
    barrier = [row[:] for row in light]
    for _ in range(GAP_CLOSING):
        grown = [row[:] for row in barrier]
        for y in range(height):
            for x in range(width):
                if barrier[y][x]:
                    for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                        if 0 <= ny < height and 0 <= nx < width:
                            grown[ny][nx] = True
        barrier = grown
    outside = [[False] * width for _ in range(height)]
    queue = deque((y, x) for y in range(height) for x in (0, width - 1))
    queue.extend((y, x) for y in (0, height - 1) for x in range(width))
    while queue:
        y, x = queue.popleft()
        if outside[y][x] or barrier[y][x]:
            continue
        outside[y][x] = True
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width:
                queue.append((ny, nx))
    # il fondo vero arriva fino al contorno: si riprende la fascia ispessita, ma solo dove il pixel è nero
    frontier = deque((y, x, 0) for y in range(height) for x in range(width) if outside[y][x])
    while frontier:
        y, x, depth = frontier.popleft()
        if depth >= GAP_CLOSING:
            continue
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and not outside[ny][nx] and not light[ny][nx]:
                outside[ny][nx] = True
                frontier.append((ny, nx, depth + 1))
    canvas = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    canvas.fill(0)
    left, top = (SIZE - width) // 2, (SIZE - height) // 2
    for y in range(height):
        for x in range(width):
            if not outside[y][x]:
                canvas.setPixelColor(left + x, top + y, image.pixelColor(x, y))
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("theme", choices=sorted(THEMES))
    parser.add_argument("logo", nargs="?", help="logo del tema, PNG trasparente (senza: ricolora l'icona normale)")
    parser.add_argument("--black-background", action="store_true", help="il logo è su sfondo nero: lo rende trasparente")
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - serve a QImage
    light, eyes = THEMES[args.theme]
    if args.logo and args.black_background:
        icon = transparent_outside_black(QImage(args.logo))
    elif args.logo:
        icon = with_glow_outline(QImage(args.logo), light)
    else:
        icon = recolor(QImage(str(RESOURCES / "app_icon.png")), light, eyes)
    target = RESOURCES / f"icon_{args.theme}.png"
    icon.save(str(target))
    print(f"{target.name} {icon.width()}x{icon.height()}")


if __name__ == "__main__":
    main()
