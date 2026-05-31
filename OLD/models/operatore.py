"""Modello ORM: Operatore (utente del sistema, broker o segreteria)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class Operatore(Base):
    __tablename__ = "operatori"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(180), unique=True)
    # Valori attesi: 'broker' | 'segreteria' (vedi utils.config.Ruolo)
    ruolo: Mapped[str] = mapped_column(String(20), nullable=False)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Pratiche inserite da questo operatore in qualità di broker.
    pratiche_inserite: Mapped[List["Pratica"]] = relationship(
        back_populates="broker",
        foreign_keys="Pratica.broker_id",
    )
    # Pratiche assegnate a questo operatore in qualità di segreteria.
    pratiche_assegnate: Mapped[List["Pratica"]] = relationship(
        back_populates="operatore_assegnato",
        foreign_keys="Pratica.operatore_assegnato_id",
    )

    def __repr__(self) -> str:  # pragma: no cover - utile solo per debug
        return f"<Operatore #{self.id} {self.nome} ({self.ruolo})>"
