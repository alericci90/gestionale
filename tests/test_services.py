"""
Test dei service e della validazione.

Usano un database SQLite in memoria isolato: i service accettano una `Session`
come parametro, quindi i test passano la propria sessione senza toccare il DB reale.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.connection import Base
import models  # noqa: F401  (registra i modelli sulla Base)
from services import operatore_service, pratica_service
from services.pratica_service import FiltriPratiche, ValidazionePraticaError
from utils.config import Ruolo, StatoPratica, TipoPolizza, Urgenza
from utils.validators import valida_dati_pratica


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    s = Session()
    try:
        yield s
        s.commit()
    finally:
        s.close()


@pytest.fixture()
def broker(session):
    op = operatore_service.crea_operatore(session, "Test Broker", Ruolo.BROKER)
    session.flush()
    return op


def _dati_validi(broker_id: int) -> dict:
    return {
        "broker_id": broker_id,
        "gia_cliente": True,
        "tipo_cliente": "privato",
        "nome_cliente": "Mario Rossi",
        "compagnia": "AXA",
        "tipo_polizza": TipoPolizza.AUTO.value,
        "emissione_polizza": True,
        "n_polizza": "123456789",
        "importo_polizza": 400,
        "importo_cliente": 500,
        "gia_pagato": True,
        "metodo_pagamento": "Bonifico",
        "urgenza": Urgenza.BASSA.value,
    }


# --------------------------------------------------------------------------- #
# Validazione
# --------------------------------------------------------------------------- #
def test_validazione_ok():
    assert valida_dati_pratica(_dati_validi(1)) == []


def test_validazione_polizza_emessa_senza_numero():
    dati = _dati_validi(1)
    dati["n_polizza"] = ""
    errori = valida_dati_pratica(dati)
    assert any("numero di polizza" in e for e in errori)


def test_validazione_non_emessa_richiede_preventivo_e_decorrenza():
    dati = _dati_validi(1)
    dati.update(emissione_polizza=False, n_polizza=None)
    errori = valida_dati_pratica(dati)
    assert any("preventivo" in e for e in errori)
    assert any("decorrenza" in e for e in errori)


def test_validazione_non_pagato_richiede_incasso():
    dati = _dati_validi(1)
    dati.update(gia_pagato=False, metodo_pagamento=None, incasso=None)
    errori = valida_dati_pratica(dati)
    assert any("incassato" in e for e in errori)


def test_validazione_nuovo_cliente_richiede_documento_identita():
    dati = _dati_validi(1)
    dati.update(gia_cliente=False, documenti=[])
    errori = valida_dati_pratica(dati)
    assert any("identità" in e for e in errori)


# --------------------------------------------------------------------------- #
# Creazione pratica
# --------------------------------------------------------------------------- #
def test_crea_pratica_genera_numero(session, broker):
    p = pratica_service.crea_pratica(session, _dati_validi(broker.id))
    assert p.numero_pratica.startswith("PRT-")
    assert p.stato == StatoPratica.NUOVA.value
    assert p.cliente.nome == "Mario Rossi"


def test_numeri_pratica_progressivi(session, broker):
    p1 = pratica_service.crea_pratica(session, _dati_validi(broker.id))
    p2 = pratica_service.crea_pratica(session, _dati_validi(broker.id))
    n1 = int(p1.numero_pratica.split("-")[-1])
    n2 = int(p2.numero_pratica.split("-")[-1])
    assert n2 == n1 + 1


def test_crea_pratica_dati_invalidi_solleva(session, broker):
    dati = _dati_validi(broker.id)
    dati["nome_cliente"] = ""
    with pytest.raises(ValidazionePraticaError):
        pratica_service.crea_pratica(session, dati)


def test_cliente_riutilizzato(session, broker):
    pratica_service.crea_pratica(session, _dati_validi(broker.id))
    pratica_service.crea_pratica(session, _dati_validi(broker.id))
    # Stesso nome -> un solo cliente.
    from models import Cliente
    clienti = session.query(Cliente).filter(Cliente.nome == "Mario Rossi").all()
    assert len(clienti) == 1


# --------------------------------------------------------------------------- #
# Ricerca / ordinamento
# --------------------------------------------------------------------------- #
def test_ordinamento_priorita(session, broker):
    bassa = _dati_validi(broker.id)
    alta = _dati_validi(broker.id)
    alta["urgenza"] = Urgenza.ALTA.value
    pratica_service.crea_pratica(session, bassa)
    pratica_service.crea_pratica(session, alta)
    risultati = pratica_service.cerca_pratiche(
        session, FiltriPratiche(ordina_per="priorita")
    )
    assert risultati[0].urgenza == Urgenza.ALTA.value


def test_filtro_per_stato(session, broker):
    p = pratica_service.crea_pratica(session, _dati_validi(broker.id))
    pratica_service.aggiorna_stato(session, p.id, StatoPratica.COMPLETATA)
    completate = pratica_service.cerca_pratiche(
        session, FiltriPratiche(stati=[StatoPratica.COMPLETATA])
    )
    assert len(completate) == 1
    nuove = pratica_service.cerca_pratiche(
        session, FiltriPratiche(stati=[StatoPratica.NUOVA])
    )
    assert len(nuove) == 0


# --------------------------------------------------------------------------- #
# Aggiornamenti
# --------------------------------------------------------------------------- #
def test_assegnazione_porta_in_lavorazione(session, broker):
    seg = operatore_service.crea_operatore(session, "Seg", Ruolo.SEGRETERIA)
    session.flush()
    p = pratica_service.crea_pratica(session, _dati_validi(broker.id))
    pratica_service.assegna_operatore(session, p.id, seg.id)
    assert p.operatore_assegnato_id == seg.id
    assert p.stato == StatoPratica.IN_LAVORAZIONE.value


def test_aggiorna_stato(session, broker):
    p = pratica_service.crea_pratica(session, _dati_validi(broker.id))
    pratica_service.aggiorna_stato(session, p.id, StatoPratica.COMPLETATA)
    assert p.stato == StatoPratica.COMPLETATA.value
