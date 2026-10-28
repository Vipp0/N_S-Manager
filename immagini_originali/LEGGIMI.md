# Immagini originali dei temi stagionali

Sono i file di partenza da cui gli strumenti in `tools/` ricavano le risorse del programma
(`gilda_app/resources/`). Il programma, e lo zip delle release, usano solo le risorse già pronte:
questi file servono per rigenerarle (cambiare un ritaglio, un colore, una dimensione).

| File | Cosa è | Strumento | Risorse che produce |
|---|---|---|---|
| `Logo Halloween Night_Shade Manager.png` | scritta "Night_Shade Manager" a tema, sfondo bianco | `tools/make_seasonal_assets.py` | `wordmark_halloween.png` |
| `Night_Shade Manager Halloween.png` | illustrazione 16:9 per il caricamento | `tools/make_seasonal_assets.py` | `splash_halloween.png` |
| `Logo Night_Shade Halloween.png` | gatto del logo in versione Halloween, trasparente | `tools/make_seasonal_icon.py` | `icon_halloween.png` |
| `Accessori Halloween.jpg` | foglio di accessori su sfondo grigio | `tools/make_decorations.py` | `deco_halloween_*.png` |
| `Logo natalizio Night_Shade Manager con cappellino.png` | illustrazione 3:2 per il caricamento di Natale, con il cappellino (quella usata) | `tools/make_seasonal_assets.py` | `splash_natale.png` |
| `Night_Shade Manager Christmas.png` | la stessa illustrazione senza cappellino (alternativa, non usata) | `tools/make_seasonal_assets.py` | |
| `Logo Night_Shade Natale.png` | scritta "Night_Shade Manager" natalizia, sfondo bianco | `tools/make_seasonal_assets.py` | `wordmark_natale.png` |
| `Gatto natalizio con occhi rossi luminosi.png` | gatto del logo con cappellino e agrifoglio, su sfondo nero | `tools/make_seasonal_icon.py` (con `--black-background`) | `icon_natale.png` |
| `Accessori natalizi1.png`, `Accessori natalizi3.jpg` | fogli di accessori natalizi su sfondo chiaro | `tools/make_decorations.py natale immagini_originali` | `deco_natale_*.png` |
| `Accessori natalizi2.png` | foglio di accessori in tinte viola/ghiaccio (non usato) | | |

I comandi esatti sono nell'intestazione di ogni strumento.
