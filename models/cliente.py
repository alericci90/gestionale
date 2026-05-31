"""Modello ORM: Cliente (persona fisica o azienda)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class Cliente(Base):
    __tablename__ = "clienti"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nome Cognome (privato) oppure Ragione Sociale (azienda).
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    # 'privato' | 'azienda' (vedi utils.config.TipoCliente)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    codice_fiscale: Mapped[Optional[str]] = mapped_column(String(16))
    partita_iva: Mapped[Optional[str]] = mapped_column(String(11))
    email: Mapped[Optional[str]] = mapped_column(String(180))
    telefono: Mapped[Optional[str]] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    pratiche: Mapped[List["Pratica"]] = relationship(back_populates="cliente")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Cliente #{self.id} {self.nome} ({self.tipo})>"
