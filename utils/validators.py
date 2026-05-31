"""
Validazione dei dati di una pratica secondo le regole del flusso del broker.

Le regole derivano direttamente dal diagramma fornito:
- Se la polizza è già emessa  -> serve il numero polizza.
- Se NON è emessa            -> servono numero preventivo e data decorrenza.
- Se il cliente ha già pagato -> serve il metodo di pagamento.
- Se NON ha pagato           -> serve l'indicazione di incasso; se non incassato,
                                 va indicato se inviare la mail al cliente.
- Per un nuovo cliente vanno indicati i documenti previsti.

`valida_dati_pratica` restituisce una lista di messaggi di errore: vuota se i
dati sono validi. Tenere la validazione qui (e non nella UI) la rende
riutilizzabile e testabile in modo indipendente.
"""
from __future__ import annotations

from typing import Any, Dict, List

from utils.config import TipoDocumento


def valida_dati_pratica(dati: Dict[str, Any]) -> List[str]:
    """Valida il dizionario dati di una pratica. Ritorna la lista degli errori."""
    errori: List[str] = []

    # --- Anagrafica cliente ---------------------------------------------- #
    if not (dati.get("nome_cliente") or "").strip():
        errori.append("Il nome del cliente (o ragione sociale) è obbligatorio.")

    if not (dati.get("compagnia") or "").strip():
        errori.append("La compagnia assicurativa è obbligatoria.")

    if not dati.get("tipo_polizza"):
        errori.append("Il tipo di polizza è obbligatorio.")

    # --- Emissione polizza ----------------------------------------------- #
    if dati.get("emissione_polizza"):
        if not (dati.get("n_polizza") or "").strip():
            errori.append("La polizza è emessa: inserire il numero di polizza.")
    else:
        if not (dati.get("n_preventivo") or "").strip():
            errori.append("La polizza non è emessa: inserire il numero di preventivo.")
        if not dati.get("data_decorrenza"):
            errori.append("La polizza non è emessa: inserire la data di decorrenza.")

    # --- Importi ---------------------------------------------------------- #
    for campo, etichetta in (("importo_polizza", "importo polizza"),
                             ("importo_cliente", "importo cliente")):
        valore = dati.get(campo)
        if valore is not None and valore < 0:
            errori.append(f"L'{etichetta} non può essere negativo.")

    # --- Pagamento -------------------------------------------------------- #
    if dati.get("gia_pagato"):
        if not (dati.get("metodo_pagamento") or "").strip():
            errori.append("Il cliente ha già pagato: indicare il metodo di pagamento.")
    else:
        if dati.get("incasso") is None:
            errori.append("Il cliente non ha pagato: indicare se l'importo è stato incassato.")
        elif dati.get("incasso") is True:
            # Incassato senza pagamento registrato a monte: serve il metodo.
            if not (dati.get("metodo_pagamento") or "").strip():
                errori.append("Importo incassato: indicare il metodo di incasso.")
        else:  # incasso == False
            if dati.get("invia_mail") is None:
                errori.append(
                    "Importo non incassato: indicare se inviare la mail di pagamento al cliente."
                )

    # --- Documenti per nuovo cliente ------------------------------------- #
    if not dati.get("gia_cliente"):
        tipi_caricati = {d.get("tipo_documento") for d in dati.get("documenti", [])}
        identita = {
            TipoDocumento.CARTA_IDENTITA.value,
            TipoDocumento.PATENTE.value,
            TipoDocumento.PASSAPORTO.value,
        }
        if not (tipi_caricati & identita):
            errori.append(
                "Nuovo cliente: caricare almeno un documento d'identità "
                "(Carta d'Identità, Patente o Passaporto)."
            )

    return errori


def normalizza_per_emissione(dati: Dict[str, Any]) -> Dict[str, Any]:
    """
    Azzera i campi non coerenti con i flag, per non salvare dati 'orfani'.
    Es: se la polizza è emessa, il numero preventivo non ha senso.
    """
    d = dict(dati)
    if d.get("emissione_polizza"):
        d["n_preventivo"] = None
    else:
        d["n_polizza"] = None

    if d.get("gia_pagato"):
        d["incasso"] = None
        d["invia_mail"] = None
    else:
        # Non pagato: nessun metodo se non incassato.
        if d.get("incasso") is False:
            d["metodo_pagamento"] = None
        else:
            d["invia_mail"] = None
    return d
