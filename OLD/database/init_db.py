"""
Inizializzazione del database.

Esegui questo modulo per (ri)creare lo schema e inserire dati di esempio:

    python -m database.init_db            # crea tabelle (se mancano) + seed
    python -m database.init_db --reset    # cancella e ricrea tutto da zero

Lo schema è derivato dai modelli ORM in `models/`, quindi resta sempre
allineato al codice.
"""
from __future__ import annotations

import argparse
from database.connection import Base, engine, get_session
# Import necessario: registra tutti i modelli sulla Base prima del create_all.
import models  # noqa: F401
from models import Operatore
from services import operatore_service
from utils.config import Ruolo


def crea_tabelle(reset: bool = False) -> None:
    """Crea le tabelle. Con reset=True le elimina prima di ricrearle."""
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _esistono_dati() -> bool:
    with get_session() as session:
        return session.query(Operatore).first() is not None


def seed() -> None:
    """Inserisce gli operatori di default (solo se DB vuoto)."""
    if _esistono_dati():
        print("• Operatori già presenti: seed saltato.")
        return

    with get_session() as session:
        operatore_service.crea_operatore(session, "Filippo Amato", Ruolo.BROKER, "filippo@broker.it")
        operatore_service.crea_operatore(session, "Gabriele Cerfoglio", Ruolo.BROKER, "gabriele@broker.it")
        operatore_service.crea_operatore(session, "Andrea Fino", Ruolo.BROKER, "andrea@broker.it")
        operatore_service.crea_operatore(session, "Valeria Bonetto", Ruolo.SEGRETERIA, "valeria@segreteria.it")
        operatore_service.crea_operatore(session, "Ilaria Rizzo", Ruolo.SEGRETERIA, "ilaria@segreteria.it")

    print("• Seed completato: 5 operatori.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inizializza il database del gestionale.")
    parser.add_argument("--reset", action="store_true", help="Elimina e ricrea tutto.")
    args = parser.parse_args()

    crea_tabelle(reset=args.reset)
    print("• Tabelle create/aggiornate.")
    seed()
    print("• Database pronto.")


if __name__ == "__main__":
    main()
