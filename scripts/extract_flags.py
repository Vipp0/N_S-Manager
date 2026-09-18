"""Script una tantum: estrae le immagini bandiera (dal pacchetto flagpy, installato
solo temporaneamente per questo script) in PNG piccoli per gilda_app/resources/flags/.
Non e' una dipendenza runtime dell'app: le PNG generate vengono committate nel repo.

Estrae TUTTE le bandiere note a pycountry+flagpy (non solo quelle gia' presenti nel
file Excel attuale), cosi' anche nazionalita' aggiunte in futuro manualmente hanno
gia' l'icona disponibile."""
import pickle
import sys
from pathlib import Path

import pycountry
from PIL import Image

FLAGPY_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\Fabrizio\AppData\Local\Temp\flagcheck\flagpy\flags"
)
OUT_DIR = Path(__file__).resolve().parent.parent / "gilda_app" / "resources" / "flags"
# 42x28 (rapporto 3:2 come la prima estrazione a 36x24, leggermente piu' grande):
# altri tentativi (72x48, poi 48x32) sono risultati via via troppo vistosi.
FLAG_SIZE = (42, 28)

# Alpha2 -> nome file flagpy per i casi dove flagpy usa nomi diversi da pycountry
# (prefisso "The_", "Georgia_(Country)" per disambiguare dallo stato USA, ecc).
MANUAL_FLAGPY_NAMES = {
    "CZ": "The_Czech_Republic",
    "AE": "The_United_Arab_Emirates",
    "GE": "Georgia_(Country)",
    "NL": "The_Netherlands",
    "PS": "Palestine",
    "PH": "The_Philippines",
    "RU": "Russia",
    "GB": "The_United_Kingdom",
    "TR": "Turkey",
    "US": "The_United_States",
}


def norm(s: str) -> str:
    return s.lower().replace("_", "").replace(" ", "").replace(",", "").replace(".", "").replace("'", "")


def main() -> None:
    flagpy_names = [p.stem for p in FLAGPY_DIR.glob("*.pkl")]
    flagpy_norm = {norm(n): n for n in flagpy_names}

    alpha2_to_file: dict[str, str] = {}
    unresolved = []

    for country in pycountry.countries:
        alpha2 = country.alpha_2
        if alpha2 in MANUAL_FLAGPY_NAMES:
            alpha2_to_file[alpha2] = MANUAL_FLAGPY_NAMES[alpha2]
            continue
        candidates = [country.name]
        if hasattr(country, "common_name"):
            candidates.append(country.common_name)
        if hasattr(country, "official_name"):
            candidates.append(country.official_name)
        matched = next((flagpy_norm[norm(c)] for c in candidates if norm(c) in flagpy_norm), None)
        if matched:
            alpha2_to_file[alpha2] = matched
        else:
            unresolved.append((alpha2, country.name))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for alpha2, flagpy_name in sorted(alpha2_to_file.items()):
        pkl_path = FLAGPY_DIR / f"{flagpy_name}.pkl"
        with open(pkl_path, "rb") as f:
            arr = pickle.load(f)
        img = Image.fromarray(arr)
        img = img.resize(FLAG_SIZE, Image.LANCZOS)
        img.save(OUT_DIR / f"{alpha2}.png")

    print(f"Estratte {len(alpha2_to_file)} bandiere in {OUT_DIR}")
    if unresolved:
        print("Non risolte (nessuna immagine disponibile in flagpy):")
        for u in unresolved:
            print(" ", u)


if __name__ == "__main__":
    main()
