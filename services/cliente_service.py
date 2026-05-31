"""Service per la gestione dei clienti."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Cliente
from utils.config import TipoCliente


def crea_cliente(
    session: Session,
    nome: str,
    tipo: TipoCliente,
    codice_fiscale: Optional[str] = None,
    partita_iva: Optional[str] = None,
    email: Optional[str] = None,
    telefono: Optional[str] = None,
) -> Cliente:
    cliente = Cliente(
        nome=nome.strip(),
        tipo=tipo.value,
        codice_fiscale=(codice_fiscale or "").strip() or None,
        partita_iva=(partita_iva or "").strip() or None,
        email=(email or "").strip() or None,
        telefono=(telefono or "").strip() or None,
    )
    session.add(cliente)
    session.flush()
    return cliente


def trova_per_nome(session: Session, nome: str) -> Optional[Cliente]:
    """Cerca un cliente per nome esatto (case-insensitive)."""
    nome = (nome or "").strip()
    if not nome:
        return None
    stmt = select(Cliente).where(func.lower(Cliente.nome) == nome.lower())
    return session.scalars(stmt).first()


def trova_o_crea(
    session: Session,
    nome: str,
    tipo: TipoCliente,
    **extra,
) -> Cliente:
    """Restituisce il cliente esistente con quel nome, oppure ne crea uno nuovo."""
    esistente = trova_per_nome(session, nome)
    if esistente is not None:
        return esistente
    return crea_cliente(session, nome=nome, tipo=tipo, **extra)


def lista_clienti(session: Session) -> List[Cliente]:
    return list(session.scalars(select(Cliente).order_by(Cliente.nome)))
