"""Ritaglia le decorazioni di un tema da un foglio di accessori su sfondo grigio.

Lo sfondo del foglio è un grigio chiaro sfumato (più scuro ai bordi): lo si stima a blocchi, usando solo i
pixel privi di colore, e per ogni pixel si calcola quanto si discosta dal fondo stimato. Quella distanza
diventa la trasparenza e dal colore si toglie il contributo del fondo, così le linee sottili (ragnatele
dorate) restano morbide e non hanno un alone grigio sopra uno sfondo scuro.

Ogni decorazione è un rettangolo del foglio (BOXES, in pixel dell'originale); i pezzi estranei finiti nel
rettangolo si cancellano con CLEAR. Il risultato va in resources/deco_<tema>_<nome>.png.

Uso (dalla cartella del progetto, con il venv):
    python tools/make_decorations.py halloween "immagini_originali/Accessori Halloween.jpg"
"""
import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_seasonal_assets import RESOURCES, crop_to_content  # noqa: E402

BLOCK = 16  # lato dei blocchi per stimare il fondo
NEUTRAL = 10  # un pixel è "senza colore" (fondo) se max-min dei canali è sotto questo valore...
MIN_BACKGROUND_LIGHT = 100  # ...e abbastanza chiaro: i neri dentro le decorazioni (occhi, contorni) non sono fondo
T0, T1 = 14.0, 55.0  # distanza dal fondo: sotto T0 trasparente, sopra T1 pieno

# nome -> (x, y, larghezza, altezza) nel foglio, e dimensione finale (lato maggiore in pixel)
BOXES = {
    "halloween": {
        "web": ((45, 50, 400, 410), "width", 380),
        "spider": ((470, 50, 190, 410), "height", 360),
        "cluster": ((45, 425, 615, 290), "width", 620),
        "icon": ((695, 440, 250, 260), "height", 220),
        # ai lati del logo nelle liste: a sinistra una zucca, a destra il corvo (guarda verso il logo)
        "header_left": ((695, 440, 250, 260), "height", 150),
        "header_right": ((1205, 555, 185, 170), "height", 150),
        # piccoli ornamenti per l'intestazione delle altre schede (Note, Calendario, BDO, Statistiche, Impostazioni)
        "page_a": ((1040, 50, 360, 190), "height", 130),  # pipistrello
        "page_b": ((1160, 245, 115, 120), "height", 120),  # teschio dorato
        "page_c": ((880, 305, 115, 125), "height", 130),  # teschio rosso
    },
}
# rettangoli da cancellare (pezzi di altre decorazioni che cadono dentro quella ritagliata)
CLEAR = {
    "halloween": {
        "web": [(262, 252, 180, 180), (200, 420, 250, 45)],  # la ragnatela piccola; i gambi delle zucche
        "cluster": [(45, 420, 85, 50), (230, 420, 90, 45), (450, 420, 150, 50)],  # coda della ragnatela, un puntino, zampe del ragno
    },
}


def estimate_background(raw: bytes, width: int, height: int, stride: int) -> list[list[tuple[float, float, float]]]:
    gx, gy = (width + BLOCK - 1) // BLOCK, (height + BLOCK - 1) // BLOCK
    sums = [[[0, 0, 0, 0] for _ in range(gx)] for _ in range(gy)]
    for y in range(height):
        row, by = y * stride, y // BLOCK
        for x in range(width):
            i = row + x * 3
            r, g, b = raw[i], raw[i + 1], raw[i + 2]
            if max(r, g, b) - min(r, g, b) < NEUTRAL and min(r, g, b) > MIN_BACKGROUND_LIGHT:
                c = sums[by][x // BLOCK]
                c[0] += r
                c[1] += g
                c[2] += b
                c[3] += 1
    grid = [[None] * gx for _ in range(gy)]
    for j in range(gy):
        for i in range(gx):
            c = sums[j][i]
            if c[3] >= 40:
                grid[j][i] = (c[0] / c[3], c[1] / c[3], c[2] / c[3])
    # i blocchi coperti da una decorazione prendono la media dei vicini già stimati
    for _ in range(60):
        changed = False
        for j in range(gy):
            for i in range(gx):
                if grid[j][i] is None:
                    near = [grid[jj][ii] for jj, ii in ((j - 1, i), (j + 1, i), (j, i - 1), (j, i + 1))
                            if 0 <= jj < gy and 0 <= ii < gx and grid[jj][ii] is not None]
                    if near:
                        grid[j][i] = tuple(sum(v[k] for v in near) / len(near) for k in range(3))
                        changed = True
        if not changed:
            break
    return grid


def background_at(grid, x: int, y: int) -> tuple[float, float, float]:
    gy, gx = len(grid), len(grid[0])
    fx, fy = x / BLOCK - 0.5, y / BLOCK - 0.5
    i0, j0 = max(0, min(gx - 1, int(fx // 1))), max(0, min(gy - 1, int(fy // 1)))
    i1, j1 = min(gx - 1, i0 + 1), min(gy - 1, j0 + 1)
    tx, ty = max(0.0, min(1.0, fx - i0)), max(0.0, min(1.0, fy - j0))
    out = []
    for k in range(3):
        top = grid[j0][i0][k] * (1 - tx) + grid[j0][i1][k] * tx
        bottom = grid[j1][i0][k] * (1 - tx) + grid[j1][i1][k] * tx
        out.append(top * (1 - ty) + bottom * ty)
    return out[0], out[1], out[2]


def remove_background(source: QImage) -> QImage:
    image = source.convertToFormat(QImage.Format_RGB888)
    width, height, stride = image.width(), image.height(), image.bytesPerLine()
    raw = bytes(image.constBits())
    grid = estimate_background(raw, width, height, stride)
    result = QImage(width, height, QImage.Format_ARGB32)
    result.fill(0)
    for y in range(height):
        for x in range(width):
            i = y * stride + x * 3
            r, g, b = raw[i], raw[i + 1], raw[i + 2]
            br, bg, bb = background_at(grid, x, y)
            distance = max(abs(r - br), abs(g - bg), abs(b - bb))
            if distance <= T0:
                continue
            alpha = min(1.0, (distance - T0) / (T1 - T0))
            # toglie il contributo del fondo: colore = (pixel - (1 - alpha) * fondo) / alpha
            result.setPixelColor(
                x, y,
                QColor(
                    max(0, min(255, int((r - (1 - alpha) * br) / alpha))),
                    max(0, min(255, int((g - (1 - alpha) * bg) / alpha))),
                    max(0, min(255, int((b - (1 - alpha) * bb) / alpha))),
                    int(alpha * 255),
                ),
            )
    return result


def make_decorations(theme: str, sheet: Path) -> dict[str, QImage]:
    cut = remove_background(QImage(str(sheet)))
    made = {}
    for name, ((x, y, w, h), side, size) in BOXES[theme].items():
        piece = cut.copy(QRect(x, y, w, h))
        for cx, cy, cw, ch in CLEAR.get(theme, {}).get(name, []):
            for yy in range(max(0, cy - y), min(h, cy - y + ch)):
                for xx in range(max(0, cx - x), min(w, cx - x + cw)):
                    piece.setPixel(xx, yy, 0)
        piece = crop_to_content(piece, margin=2)
        scaled = (piece.scaledToWidth(size, Qt.SmoothTransformation) if side == "width"
                  else piece.scaledToHeight(size, Qt.SmoothTransformation))
        scaled.save(str(RESOURCES / f"deco_{theme}_{name}.png"))
        made[name] = scaled
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("theme", help="nome del tema (es. halloween)")
    parser.add_argument("sheet", help="foglio degli accessori su sfondo grigio")
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - serve a QImage
    for name, image in make_decorations(args.theme, Path(args.sheet)).items():
        print(f"deco_{args.theme}_{name}.png {image.width()}x{image.height()}")


if __name__ == "__main__":
    main()
