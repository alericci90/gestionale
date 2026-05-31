"""Modello ORM: Pratica (la pratica assicurativa, gestita come ticket)."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base
from utils.config import StatoPratica, Urgenza


class Pratica(Base):
    __tablename__ = "pratiche"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Numero leggibile assegnato alla creazione, es. "PRT-2026-0001".
    numero_pratica: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    # --- Relazioni anagrafiche -------------------------------------------- #
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clienti.id"), nullable=False)
    broker_id: Mapped[int] = mapped_column(ForeignKey("operatori.id"), nullable=False)
    operatore_assegnato_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("operatori.id")
    )

    # --- Dati provenienti dal flusso del broker --------------------------- #
    gia_cliente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compagnia: Mapped[str] = mapped_column(String(80), nullable=False)
    # 'auto' | 'rami_elementari'
    tipo_polizza: Mapped[str] = mapped_column(String(30), nullable=False)

    emissione_polizza: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    n_polizza: Mapped[Optional[str]] = mapped_column(String(60))      # se emessa
    n_preventivo: Mapped[Optional[str]] = mapped_column(String(60))   # se NON emessa
    data_decorrenza: Mapped[Optional[date]] = mapped_column(Date)

    importo_polizza: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    importo_cliente: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))

    gia_pagato: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    incasso: Mapped[Optional[bool]] = mapped_column(Boolean)            # se NON pagato
    metodo_pagamento: Mapped[Optional[str]] = mapped_column(String(40))
    invia_mail: Mapped[Optional[bool]] = mapped_column(Boolean)         # mail al cliente

    # --- Gestione ticket (lato segreteria) -------------------------------- #
    urgenza: Mapped[str] = mapped_column(String(10), nullable=False, default=Urgenza.BASSA.value)
    stato: Mapped[str] = mapped_column(String(20), nullable=False, default=StatoPratica.NUOVA.value)
    note: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # --- Relazioni -------------------------------------------------------- #
    cliente: Mapped["Cliente"] = relationship(back_populates="pratiche")
    broker: Mapped["Operatore"] = relationship(
        back_populates="pratiche_inserite", foreign_keys=[broker_id]
    )
    operatore_assegnato: Mapped[Optional["Operatore"]] = relationship(
        back_populates="pratiche_assegnate", foreign_keys=[operatore_assegnato_id]
    )
    documenti: Mapped[List["Documento"]] = relationship(
        back_populates="pratica",
        cascade="all, delete-orphan",
    )

    # --- Proprietà di comodo --------------------------------------------- #
    @property
    def urgenza_enum(self) -> Urgenza:
        return Urgenza(self.urgenza)

    @property
    def stato_enum(self) -> StatoPratica:
        return StatoPratica(self.stato)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Pratica {self.numero_pratica} stato={self.stato} urgenza={self.urgenza}>"
