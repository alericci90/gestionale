"""Service per la gestione degli operatori (broker e segreteria)."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Operatore
from utils.config import Ruolo


def crea_operatore(
    session: Session,
    nome: str,
    ruolo: Ruolo,
    email: Optional[str] = None,
) -> Operatore:
    op = Operatore(nome=nome, ruolo=ruolo.value, email=email, attivo=True)
    session.add(op)
    session.flush()  # popola op.id senza chiudere la transazione
    return op


def get_operatore(session: Session, operatore_id: int) -> Optional[Operatore]:
    return session.get(Operatore, operatore_id)


def lista_operatori(
    session: Session,
    ruolo: Optional[Ruolo] = None,
    solo_attivi: bool = True,
) -> List[Operatore]:
    stmt = select(Operatore)
    if ruolo is not None:
        stmt = stmt.where(Operatore.ruolo == ruolo.value)
    if solo_attivi:
        stmt = stmt.where(Operatore.attivo.is_(True))
    stmt = stmt.order_by(Operatore.nome)
    return list(session.scalars(stmt))
