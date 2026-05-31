"""
Service principale: gestione delle pratiche (ticket).

Contiene la logica di business: creazione di una pratica a partire dai dati del
broker, generazione del numero pratica, ricerca con filtri e ordinamenti per la
segreteria, aggiornamento dello stato e assegnazione a un operatore.

La UI (Streamlit) non parla mai direttamente con il database: passa sempre da qui.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from models import Cliente, Operatore, Pratica
from services import cliente_service, documento_service
from utils.config import (
    StatoPratica,
    TipoCliente,
    TipoDocumento,
    TipoPolizza,
    Urgenza,
)
from utils.validators import normalizza_per_emissione, valida_dati_pratica


class ValidazionePraticaError(ValueError):
    """Sollevata quando i dati della pratica non superano la validazione."""

    def __init__(self, errori: List[str]):
        self.errori = errori
        super().__init__("; ".join(errori))


@dataclass
class FiltriPratiche:
    """Parametri di ricerca per l'elenco pratiche (lato segreteria)."""
    testo: Optional[str] = None                      # ricerca libera (numero/cliente/compagnia)
    stati: List[StatoPratica] = field(default_factory=list)
    urgenze: List[Urgenza] = field(default_factory=list)
    compagnia: Optional[str] = None
    operatore_assegnato_id: Optional[int] = None
    solo_non_assegnate: bool = False
    ordina_per: str = "priorita"   # 'priorita' | 'data' | 'numero'
    ordine_crescente: bool = True  # per 'data': crescente = più vecchie prima (FIFO)


# --------------------------------------------------------------------------- #
# Creazione
# --------------------------------------------------------------------------- #
def _codice_operatore(nome: str) -> str:
    """Prime 4 lettere del cognome, es. 'Filippo Amato' → 'AMAT'."""
    cognome = nome.split()[-1] if nome.split() else nome
    return cognome[:4].upper()


def _genera_numero_pratica(session: Session, broker_nome: str) -> str:
    """Genera un numero pratica nel formato YYYYMMDD-CODICE-NNNN.

    Il contatore ordinale è giornaliero per combinazione data+codice operatore.
    """
    oggi = datetime.now().strftime("%Y%m%d")
    codice = _codice_operatore(broker_nome)
    prefisso = f"{oggi}-{codice}-"
    ultimo = session.scalars(
        select(Pratica.numero_pratica)
        .where(Pratica.numero_pratica.like(f"{prefisso}%"))
        .order_by(Pratica.numero_pratica.desc())
        .limit(1)
    ).first()
    progressivo = int(ultimo.split("-")[-1]) + 1 if ultimo else 1
    return f"{prefisso}{progressivo:04d}"


def crea_pratica(session: Session, dati: Dict[str, Any]) -> Pratica:
    """
    Crea una nuova pratica dai dati inseriti dal broker.

    `dati` deve contenere i campi previsti dal flusso (vedi interfaccia broker).
    Solleva `ValidazionePraticaError` se i dati non sono validi.
    """
    errori = valida_dati_pratica(dati)
    if errori:
        raise ValidazionePraticaError(errori)

    dati = normalizza_per_emissione(dati)

    # 1. Cliente: lo cerca per nome, altrimenti lo crea.
    tipo_cliente = TipoCliente(dati.get("tipo_cliente", TipoCliente.PRIVATO.value))
    cliente = cliente_service.trova_o_crea(
        session,
        nome=dati["nome_cliente"],
        tipo=tipo_cliente,
        codice_fiscale=dati.get("codice_fiscale"),
        partita_iva=dati.get("partita_iva"),
        email=dati.get("email_cliente"),
        telefono=dati.get("telefono_cliente"),
    )

    # 2. Pratica.
    broker_obj = session.get(Operatore, dati["broker_id"])
    broker_nome = broker_obj.nome if broker_obj else "XX"
    pratica = Pratica(
        numero_pratica=_genera_numero_pratica(session, broker_nome),
        cliente_id=cliente.id,
        broker_id=dati["broker_id"],
        gia_cliente=bool(dati.get("gia_cliente")),
        compagnia=dati["compagnia"].strip(),
        tipo_polizza=TipoPolizza(dati["tipo_polizza"]).value,
        emissione_polizza=bool(dati.get("emissione_polizza")),
        n_polizza=dati.get("n_polizza"),
        n_preventivo=dati.get("n_preventivo"),
        data_decorrenza=dati.get("data_decorrenza"),
        importo_polizza=dati.get("importo_polizza"),
        importo_cliente=dati.get("importo_cliente"),
        gia_pagato=bool(dati.get("gia_pagato")),
        incasso=dati.get("incasso"),
        metodo_pagamento=dati.get("metodo_pagamento"),
        invia_mail=dati.get("invia_mail"),
        urgenza=Urgenza(dati.get("urgenza", Urgenza.BASSA.value)).value,
        stato=StatoPratica.NUOVA.value,
        note=dati.get("note"),
    )
    session.add(pratica)
    session.flush()

    # 3. Documenti (per nuovo cliente o caricati comunque).
    for doc in dati.get("documenti", []):
        documento_service.aggiungi_documento(
            session,
            pratica_id=pratica.id,
            tipo_documento=TipoDocumento(doc["tipo_documento"]),
            nome_file=doc["nome_file"],
            contenuto=doc.get("contenuto"),
        )

    return pratica


# --------------------------------------------------------------------------- #
# Lettura / ricerca
# --------------------------------------------------------------------------- #
def _query_base():
    return select(Pratica).options(
        joinedload(Pratica.cliente),
        joinedload(Pratica.broker),
        joinedload(Pratica.operatore_assegnato),
    )


def get_pratica(session: Session, pratica_id: int) -> Optional[Pratica]:
    return session.scalars(
        _query_base().where(Pratica.id == pratica_id)
    ).first()


def cerca_pratiche(session: Session, filtri: FiltriPratiche) -> List[Pratica]:
    """Ricerca pratiche applicando filtri e ordinamento."""
    stmt = _query_base().join(Pratica.cliente)

    if filtri.testo:
        like = f"%{filtri.testo.strip()}%"
        stmt = stmt.where(
            (Pratica.numero_pratica.ilike(like))
            | (Cliente.nome.ilike(like))
            | (Pratica.compagnia.ilike(like))
        )
    if filtri.stati:
        stmt = stmt.where(Pratica.stato.in_([s.value for s in filtri.stati]))
    if filtri.urgenze:
        stmt = stmt.where(Pratica.urgenza.in_([u.value for u in filtri.urgenze]))
    if filtri.compagnia:
        stmt = stmt.where(Pratica.compagnia == filtri.compagnia)
    if filtri.solo_non_assegnate:
        stmt = stmt.where(Pratica.operatore_assegnato_id.is_(None))
    elif filtri.operatore_assegnato_id is not None:
        stmt = stmt.where(Pratica.operatore_assegnato_id == filtri.operatore_assegnato_id)

    # Ordinamento.
    if filtri.ordina_per == "data":
        col = Pratica.created_at
        stmt = stmt.order_by(col.asc() if filtri.ordine_crescente else col.desc())
    elif filtri.ordina_per == "numero":
        col = Pratica.numero_pratica
        stmt = stmt.order_by(col.asc() if filtri.ordine_crescente else col.desc())
    else:  # 'priorita': urgenza alta prima, poi FIFO sulle più vecchie
        # CASE per dare peso maggiore all'urgenza alta (2) rispetto alla bassa (1).
        peso = case((Pratica.urgenza == Urgenza.ALTA.value, 2), else_=1)
        stmt = stmt.order_by(peso.desc(), Pratica.created_at.asc())

    return list(session.scalars(stmt).unique())


def conta_per_stato(session: Session) -> Dict[str, int]:
    """Conteggio pratiche raggruppate per stato (per le metriche in dashboard)."""
    rows = session.execute(
        select(Pratica.stato, func.count()).group_by(Pratica.stato)
    ).all()
    risultato = {s.value: 0 for s in StatoPratica}
    for stato, n in rows:
        risultato[stato] = n
    return risultato


# --------------------------------------------------------------------------- #
# Aggiornamenti (lato segreteria)
# --------------------------------------------------------------------------- #
def aggiorna_stato(session: Session, pratica_id: int, nuovo_stato: StatoPratica) -> Pratica:
    pratica = session.get(Pratica, pratica_id)
    if pratica is None:
        raise ValueError(f"Pratica #{pratica_id} non trovata.")
    pratica.stato = nuovo_stato.value
    session.flush()
    return pratica


def assegna_operatore(
    session: Session, pratica_id: int, operatore_id: Optional[int]
) -> Pratica:
    pratica = session.get(Pratica, pratica_id)
    if pratica is None:
        raise ValueError(f"Pratica #{pratica_id} non trovata.")
    if operatore_id is not None and session.get(Operatore, operatore_id) is None:
        raise ValueError(f"Operatore #{operatore_id} non trovato.")
    pratica.operatore_assegnato_id = operatore_id
    # Assegnare una pratica nuova la porta automaticamente "in lavorazione".
    if operatore_id is not None and pratica.stato == StatoPratica.NUOVA.value:
        pratica.stato = StatoPratica.IN_LAVORAZIONE.value
    session.flush()
    return pratica


def aggiorna_note(session: Session, pratica_id: int, note: str) -> Pratica:
    pratica = session.get(Pratica, pratica_id)
    if pratica is None:
        raise ValueError(f"Pratica #{pratica_id} non trovata.")
    pratica.note = note
    session.flush()
    return pratica


def aggiorna_urgenza(session: Session, pratica_id: int, urgenza: Urgenza) -> Pratica:
    pratica = session.get(Pratica, pratica_id)
    if pratica is None:
        raise ValueError(f"Pratica #{pratica_id} non trovata.")
    pratica.urgenza = urgenza.value
    session.flush()
    return pratica
