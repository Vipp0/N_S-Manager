"""Ritaglia le decorazioni di un tema da uno o più fogli di accessori su sfondo chiaro.

Lo sfondo di un foglio è un grigio/bianco chiaro, a volte sfumato: lo si stima a blocchi, usando solo i pixel
privi di colore, e per ogni pixel si calcola quanto si discosta dal fondo stimato. Due modi per ricavare la
trasparenza:
  - "distance" (Halloween: oggetti scuri e colorati): quella distanza diventa la trasparenza e dal colore si
    toglie il contributo del fondo, così le linee sottili restano morbide e senza alone grigio;
  - "flood" (Natale: pupazzi, neve e ghiaccio, chiari quasi quanto lo sfondo): con la sola distanza le parti
    bianche degli oggetti diventerebbero trasparenti. Qui è fondo solo ciò che somiglia al fondo ED è raggiunto
    dal bordo del foglio passando per pixel simili al fondo; tutto il resto, bianco compreso, resta pieno, e
    solo la fascia di pochi pixel lungo il contorno ha trasparenza graduata.

Ogni decorazione è un rettangolo di un foglio (in pixel dell'originale, vedi HALLOWEEN e NATALE); i pezzi
estranei finiti nel rettangolo si cancellano con "clear"; "flip" la specchia. Alcune sono composte: una fila
di pezzi ("row") oppure un pezzo appeso a un filo ("hang"). Il risultato va in resources/deco_<tema>_<nome>.png.

Uso (dalla cartella del progetto, con il venv):
    python tools/make_decorations.py halloween "immagini_originali/Accessori Halloween.jpg"
    python tools/make_decorations.py natale immagini_originali
"""
import argparse
import sys
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QTransform

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_seasonal_assets import RESOURCES, crop_to_content  # noqa: E402

BLOCK = 16  # lato dei blocchi per stimare il fondo
NEUTRAL = 10  # un pixel è "senza colore" (fondo) se max-min dei canali è sotto questo valore...
MIN_BACKGROUND_LIGHT = 100  # ...e abbastanza chiaro: i neri dentro le decorazioni (occhi, contorni) non sono fondo
T0, T1 = 14.0, 55.0  # distanza dal fondo: sotto T0 trasparente, sopra T1 pieno
FLOOD_BACKGROUND = 11.0  # modo "flood": distanza massima dal fondo per attraversare un pixel dal bordo del foglio
EDGE_BAND = 3  # modo "flood": larghezza in pixel della fascia di contorno con trasparenza graduata

# -- Halloween: un foglio, modo "distance". nome -> (rettangolo nel foglio, lato su cui si fissa la misura, misura)
HALLOWEEN = {
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
}
# rettangoli da cancellare (pezzi di altre decorazioni che cadono dentro quella ritagliata)
HALLOWEEN_CLEAR = {
    "web": [(262, 252, 180, 180), (200, 420, 250, 45)],  # la ragnatela piccola; i gambi delle zucche
    "cluster": [(45, 420, 85, 50), (230, 420, 90, 45), (450, 420, 150, 50)],  # coda della ragnatela, un puntino, zampe del ragno
}

# -- Natale: tre fogli, modo "flood". Chiavi dei fogli -> file in immagini_originali/
# (file, distanza massima dal fondo per attraversare un pixel dal bordo). Il foglio 3 ha sotto ogni oggetto
# un'ombra morbida grigia: con una soglia più alta fa parte del fondo e non resta come alone.
NATALE_SHEETS = {
    "s1": ("Accessori natalizi1.png", FLOOD_BACKGROUND),  # 1536x1024, fondo bianco sporco: pupazzo, candele, lanterna, renna
    "s3": ("Accessori natalizi3.jpg", 27.0),  # 1709x608, fondo grigio con ombre: palline, fiocchi, cornici d'angolo
}
# Una decorazione: sheet, box (x, y, larghezza, altezza), side/size come sopra, flip ("h"/"v") e clear opzionali.
# Le composte hanno "row" (lista di pezzi messi in fila, alti tutti `piece_height`) oppure "hang" (pezzo + filo).
S1_SNOWMAN = {"sheet": "s1", "box": (618, 398, 300, 365)}
S1_CANDLES = {"sheet": "s1", "box": (915, 450, 300, 330), "clear": [(1170, 690, 50, 95)]}  # la punta di un corno della renna
S1_HOLLY = {"sheet": "s1", "box": (618, 38, 392, 350)}
S1_DEER = {"sheet": "s1", "box": (1048, 636, 262, 362), "clear": [(1040, 628, 162, 80), (1040, 700, 125, 60)]}  # via gli avanzi delle candele
S1_LANTERN = {"sheet": "s1", "box": (1022, 8, 335, 445)}
S1_BOW = {"sheet": "s1", "box": (5, 385, 396, 326)}
S1_ORNAMENT = {"sheet": "s1", "box": (360, 15, 245, 380)}
S3_SNOWFLAKE_ICE_2 = {"sheet": "s3", "box": (1040, 402, 166, 185)}
S3_BAUBLE_RED = {"sheet": "s3", "box": (698, 442, 106, 134)}
S3_SNOWFLAKE_GEM = {"sheet": "s3", "box": (750, 155, 215, 272)}
S3_SNOWFLAKE_ICE = {"sheet": "s3", "box": (1205, 22, 170, 200)}
S3_CORNER_GOLD = {"sheet": "s3", "box": (1385, 2, 310, 262)}

NATALE = {
    # ragnatela d'angolo di Halloween -> cornice dorata e argentata; è disegnata per l'angolo in alto a destra e il
    # programma la specchia per metterla lì: qui si specchia prima, per averla "in alto a sinistra" come l'altra.
    "web": {**S3_CORNER_GOLD, "flip": "h", "side": "width", "size": 380},
    # il ragno appeso -> la pallina blu con il fiocco rosso appesa a un filo dorato
    "spider": {"hang": S1_ORNAMENT, "ornament_height": 230, "thread": 140, "side": "height", "size": 370},
    # il gruppo di zucche -> pupazzo di neve, candele e agrifoglio
    "cluster": {"row": [S1_SNOWMAN, S1_CANDLES, S1_HOLLY], "piece_height": 300, "gap": -14, "side": "width", "size": 620},
    "icon": {**S3_BAUBLE_RED, "side": "height", "size": 220},
    "header_left": {**S1_SNOWMAN, "side": "height", "size": 150},
    "header_right": {**S1_DEER, "flip": "h", "side": "height", "size": 150},  # guarda verso il logo
    "page_a": {**S1_BOW, "side": "height", "size": 130},
    "page_b": {**S1_LANTERN, "side": "height", "size": 130},
    "page_c": {**S3_SNOWFLAKE_GEM, "side": "height", "size": 130},
    # neve sparsa: fiocchi chiari, di due misure, che il programma mette qua e là nelle intestazioni
    "snow": {**S3_SNOWFLAKE_ICE, "side": "height", "size": 120},
    "snow2": {**S3_SNOWFLAKE_ICE_2, "side": "height", "size": 120},
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


def _color_over_background(r, g, b, br, bg, bb, alpha):
    """Toglie il contributo del fondo: colore = (pixel - (1 - alpha) * fondo) / alpha."""
    return QColor(
        max(0, min(255, int((r - (1 - alpha) * br) / alpha))),
        max(0, min(255, int((g - (1 - alpha) * bg) / alpha))),
        max(0, min(255, int((b - (1 - alpha) * bb) / alpha))),
        int(alpha * 255),
    )


def remove_background(source: QImage) -> QImage:
    """Modo "distance": la distanza dal fondo diventa la trasparenza."""
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
            result.setPixelColor(x, y, _color_over_background(r, g, b, br, bg, bb, alpha))
    return result


def remove_background_flood(source: QImage, threshold: float = FLOOD_BACKGROUND) -> QImage:
    """Modo "flood": fondo è solo ciò che, partendo dal bordo del foglio, si raggiunge passando per pixel
    simili al fondo; gli oggetti restano pieni anche dove sono chiari come lo sfondo."""
    image = source.convertToFormat(QImage.Format_RGB888)
    width, height, stride = image.width(), image.height(), image.bytesPerLine()
    raw = bytes(image.constBits())
    grid = estimate_background(raw, width, height, stride)
    dist = [0.0] * (width * height)
    back = [None] * (width * height)
    for y in range(height):
        for x in range(width):
            i = y * stride + x * 3
            r, g, b = raw[i], raw[i + 1], raw[i + 2]
            bk = background_at(grid, x, y)
            dist[y * width + x] = max(abs(r - bk[0]), abs(g - bk[1]), abs(b - bk[2]))
            back[y * width + x] = bk
    outside = bytearray(width * height)  # 1 = fondo raggiunto dal bordo
    queue = deque()
    for x in range(width):
        for y in (0, height - 1):
            queue.append(y * width + x)
    for y in range(height):
        for x in (0, width - 1):
            queue.append(y * width + x)
    while queue:
        p = queue.popleft()
        if outside[p] or dist[p] > threshold:
            continue
        outside[p] = 1
        x, y = p % width, p // width
        if x > 0:
            queue.append(p - 1)
        if x < width - 1:
            queue.append(p + 1)
        if y > 0:
            queue.append(p - width)
        if y < height - 1:
            queue.append(p + width)
    # fascia di contorno: i pixel non-fondo entro EDGE_BAND passi dal fondo hanno trasparenza graduata
    band = bytearray(width * height)
    frontier = deque((p, 0) for p in range(width * height) if outside[p])
    seen = bytearray(outside)
    while frontier:
        p, depth = frontier.popleft()
        if depth >= EDGE_BAND:
            continue
        x, y = p % width, p // width
        for q in ((p - 1) if x > 0 else -1, (p + 1) if x < width - 1 else -1,
                  (p - width) if y > 0 else -1, (p + width) if y < height - 1 else -1):
            if q >= 0 and not seen[q]:
                seen[q] = 1
                band[q] = 1
                frontier.append((q, depth + 1))
    result = QImage(width, height, QImage.Format_ARGB32)
    result.fill(0)
    for y in range(height):
        for x in range(width):
            p = y * width + x
            if outside[p]:
                continue
            i = y * stride + x * 3
            r, g, b = raw[i], raw[i + 1], raw[i + 2]
            if band[p]:
                alpha = min(1.0, max(0.0, (dist[p] - T0 / 2) / (T1 - T0 / 2)))
                if alpha <= 0.02:
                    continue
                br, bg, bb = back[p]
                result.setPixelColor(x, y, _color_over_background(r, g, b, br, bg, bb, alpha))
            else:
                result.setPixelColor(x, y, QColor(r, g, b, 255))
    return result


MAIN_BLOCK = 5  # lato dei blocchi con cui si cerca l'oggetto principale: lacune più piccole non lo spezzano


def keep_main_object(image: QImage) -> QImage:
    """Tiene solo l'oggetto più grande del ritaglio e toglie i frammenti dei pezzi vicini finiti nel rettangolo.
    Si ragiona a blocchi di MAIN_BLOCK pixel (con vicinato a 8), così un oggetto fatto di parti staccate di
    poco (la renna con le corna, una candela con la fiamma) resta intero."""
    width, height = image.width(), image.height()
    gx, gy = (width + MAIN_BLOCK - 1) // MAIN_BLOCK, (height + MAIN_BLOCK - 1) // MAIN_BLOCK
    occupied = [[False] * gx for _ in range(gy)]
    for y in range(height):
        for x in range(width):
            if (image.pixel(x, y) >> 24) > 40:
                occupied[y // MAIN_BLOCK][x // MAIN_BLOCK] = True
    label = [[0] * gx for _ in range(gy)]
    sizes = {}
    for j in range(gy):
        for i in range(gx):
            if occupied[j][i] and not label[j][i]:
                tag = len(sizes) + 1
                label[j][i], count, queue = tag, 0, deque([(j, i)])
                while queue:
                    cj, ci = queue.popleft()
                    count += 1
                    for nj in range(max(0, cj - 1), min(gy, cj + 2)):
                        for ni in range(max(0, ci - 1), min(gx, ci + 2)):
                            if occupied[nj][ni] and not label[nj][ni]:
                                label[nj][ni] = tag
                                queue.append((nj, ni))
                sizes[tag] = count
    if not sizes:
        return image
    main = max(sizes, key=sizes.get)
    result = image.copy()
    for y in range(height):
        for x in range(width):
            if label[y // MAIN_BLOCK][x // MAIN_BLOCK] != main:
                result.setPixel(x, y, 0)
    return result


def _clear(piece: QImage, box: tuple, rects: list) -> None:
    x, y, w, h = box
    for cx, cy, cw, ch in rects:
        for yy in range(max(0, cy - y), min(h, cy - y + ch)):
            for xx in range(max(0, cx - x), min(w, cx - x + cw)):
                piece.setPixel(xx, yy, 0)


def _scaled(piece: QImage, side: str, size: int) -> QImage:
    return (piece.scaledToWidth(size, Qt.SmoothTransformation) if side == "width"
            else piece.scaledToHeight(size, Qt.SmoothTransformation))


def make_halloween(sheet: Path) -> dict[str, QImage]:
    cut = remove_background(QImage(str(sheet)))
    made = {}
    for name, (box, side, size) in HALLOWEEN.items():
        piece = cut.copy(QRect(*box))
        _clear(piece, box, HALLOWEEN_CLEAR.get(name, []))
        made[name] = _scaled(crop_to_content(piece, margin=2), side, size)
    return made


def _flip(piece: QImage, flip: str | None) -> QImage:
    if flip == "h":
        return piece.transformed(QTransform().scale(-1, 1))
    if flip == "v":
        return piece.transformed(QTransform().scale(1, -1))
    return piece


def make_natale(folder: Path) -> dict[str, QImage]:
    cuts = {
        key: remove_background_flood(QImage(str(folder / filename)), threshold)
        for key, (filename, threshold) in NATALE_SHEETS.items()
    }

    def piece(spec: dict) -> QImage:
        image = cuts[spec["sheet"]].copy(QRect(*spec["box"]))
        _clear(image, spec["box"], spec.get("clear", []))
        return _flip(crop_to_content(keep_main_object(image), margin=2), spec.get("flip"))

    made = {}
    for name, spec in NATALE.items():
        if "row" in spec:
            height = spec["piece_height"]
            parts = [piece(p).scaledToHeight(height, Qt.SmoothTransformation) for p in spec["row"]]
            width = sum(p.width() for p in parts) + spec["gap"] * (len(parts) - 1)
            canvas = QImage(width, height, QImage.Format_ARGB32)
            canvas.fill(0)
            painter = QPainter(canvas)
            x = 0
            for part in parts:
                painter.drawImage(x, 0, part)
                x += part.width() + spec["gap"]
            painter.end()
            result = canvas
        elif "hang" in spec:
            ornament = piece(spec["hang"]).scaledToHeight(spec["ornament_height"], Qt.SmoothTransformation)
            thread = spec["thread"]
            canvas = QImage(ornament.width(), thread + ornament.height(), QImage.Format_ARGB32)
            canvas.fill(0)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor("#c9a43a"), 3))  # il filo, dorato, fino all'anello della pallina
            painter.drawLine(QPoint(ornament.width() // 2, 0), QPoint(ornament.width() // 2, thread + 6))
            painter.drawImage(0, thread, ornament)
            painter.end()
            result = canvas
        else:
            result = piece(spec)
        made[name] = _scaled(result, spec["side"], spec["size"])
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("theme", choices=("halloween", "natale"))
    parser.add_argument("source", help="halloween: il foglio degli accessori; natale: la cartella con i fogli")
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - serve a QImage
    made = make_halloween(Path(args.source)) if args.theme == "halloween" else make_natale(Path(args.source))
    for name, image in made.items():
        image.save(str(RESOURCES / f"deco_{args.theme}_{name}.png"))
        print(f"deco_{args.theme}_{name}.png {image.width()}x{image.height()}")


if __name__ == "__main__":
    main()
