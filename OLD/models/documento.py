"""Modello ORM: Documento allegato a una pratica (fronte/retro)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class Documento(Base):
    __tablename__ = "documenti"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        ForeignKey("pratiche.id", ondelete="CASCADE"), nullable=False
    )
    # Tipo logico del documento (vedi utils.config.TipoDocumento).
    tipo_documento: Mapped[str] = mapped_column(String(40), nullable=False)
    nome_file: Mapped[str] = mapped_column(String(255), nullable=False)
    # Percorso del file salvato su disco (data/uploads/...).
    percorso: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    pratica: Mapped["Pratica"] = relationship(back_populates="documenti")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Documento #{self.id} {self.tipo_documento} ({self.nome_file})>"
