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
| `Night_Shade Manager Christmas.png` | illustrazione per Natale (tema non ancora attivo) | `tools/make_seasonal_assets.py` | `splash_natale.png` (da fare) |

I comandi esatti sono nell'intestazione di ogni strumento.
