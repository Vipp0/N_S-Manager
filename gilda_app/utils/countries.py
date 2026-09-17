"""Elenco di tutte le nazioni (nomi in inglese, come nel resto dei dati importati
da Excel), usato per popolare i menu a tendina di selezione nazionalità."""
import pycountry

ALL_COUNTRIES = sorted(country.name for country in pycountry.countries)
