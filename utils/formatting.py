"""Helper di formattazione per la UI (etichette, valuta, badge colorati)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from utils.config import (
    COLORE_STATO,
    COLORE_URGENZA,
    LABEL_STATO,
    LABEL_TIPO_POLIZZA,
    LABEL_URGENZA,
    StatoPratica,
    TipoPolizza,
    Urgenza,
)


def euro(valore: Optional[float]) -> str:
    """Formatta un importo come valuta italiana, es. 1.234,50 €."""
    if valore is None:
        return "—"
    testo = f"{float(valore):,.2f}"
    # Converte 1,234.50 -> 1.234,50 (separatori all'italiana).
    testo = testo.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{testo} €"


def data_it(valore) -> str:
    """Formatta una data/datetime in gg/mm/aaaa (con ora se datetime)."""
    if valore is None:
        return "—"
    if isinstance(valore, datetime):
        return valore.strftime("%d/%m/%Y %H:%M")
    if isinstance(valore, date):
        return valore.strftime("%d/%m/%Y")
    return str(valore)


def label_stato(stato: str) -> str:
    return LABEL_STATO.get(StatoPratica(stato), stato)


def label_urgenza(urgenza: str) -> str:
    return LABEL_URGENZA.get(Urgenza(urgenza), urgenza)


def label_tipo_polizza(tipo: str) -> str:
    try:
        return LABEL_TIPO_POLIZZA.get(TipoPolizza(tipo), tipo)
    except ValueError:
        return tipo


def badge_html(testo: str, colore: str) -> str:
    """Genera un piccolo badge HTML colorato (per st.markdown unsafe_allow_html)."""
    return (
        f"<span style='background-color:{colore};color:white;"
        f"padding:2px 10px;border-radius:12px;font-size:0.80rem;"
        f"font-weight:600;white-space:nowrap;'>{testo}</span>"
    )


def badge_urgenza(urgenza: str) -> str:
    u = Urgenza(urgenza)
    return badge_html(label_urgenza(urgenza).upper(), COLORE_URGENZA[u])


def badge_stato(stato: str) -> str:
    s = StatoPratica(stato)
    return badge_html(label_stato(stato), COLORE_STATO[s])


def emoji_urgenza(urgenza: str) -> str:
    """Indicatore testuale per le tabelle (dove l'HTML non è renderizzato)."""
    return "🔴 Alta" if urgenza == Urgenza.ALTA.value else "🟢 Bassa"


def emoji_stato(stato: str) -> str:
    return {
        StatoPratica.NUOVA.value: "🆕 Nuova",
        StatoPratica.IN_LAVORAZIONE.value: "⚙️ In lavorazione",
        StatoPratica.COMPLETATA.value: "✅ Completata",
    }.get(stato, stato)
