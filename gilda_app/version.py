"""Versione dell'app: l'unico punto da aggiornare a ogni rilascio.

Schema: MAJOR.MINOR[.PATCH]. Ogni modifica tra una release e l'altra alza il terzo numero
(2.0.1, 2.0.2...); la versione pubblicata è invece 2.1, 2.2... (il terzo numero si omette
se è 0), e un fix veloce dopo una release è 2.1.1. Compare nel titolo della finestra e in Impostazioni."""

__version__ = "2.0.8"
