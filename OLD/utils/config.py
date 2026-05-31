"""
Configurazione centrale dell'applicazione.

Raccoglie percorsi, costanti di dominio e liste di valori controllati.
Tenere qui i valori "magici" rende il resto del codice leggibile e
facilita future modifiche (es. aggiungere una nuova compagnia).
"""
from __future__ import annotations

import enum
from pathlib import Path

# --------------------------------------------------------------------------- #
# Percorsi
# --------------------------------------------------------------------------- #
# La root del progetto è la cartella che contiene questo package `utils`.
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
UPLOAD_DIR: Path = DATA_DIR / "uploads"
ASSETS_DIR: Path = BASE_DIR / "assets"

# Database SQLite (file unico, semplice da spostare e versionare separatamente).
DB_PATH: Path = DATA_DIR / "gestionale.db"
DB_URL: str = f"sqlite:///{DB_PATH}"

# Assicura che le cartelle dati esistano sempre.
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Enumerazioni di dominio
# --------------------------------------------------------------------------- #
class Ruolo(str, enum.Enum):
    """Ruolo di un operatore nel sistema."""
    BROKER = "broker"
    SEGRETERIA = "segreteria"


class TipoCliente(str, enum.Enum):
    PRIVATO = "privato"
    AZIENDA = "azienda"


class TipoPolizza(str, enum.Enum):
    AUTO = "auto"
    RAMI_ELEMENTARI = "rami_elementari"


class Urgenza(str, enum.Enum):
    """Priorità della pratica (corrisponde al campo `urgenza` del modello)."""
    BASSA = "bassa"
    ALTA = "alta"

    @property
    def peso(self) -> int:
        """Peso numerico per l'ordinamento per priorità (più alto = più urgente)."""
        return {"alta": 2, "bassa": 1}[self.value]


class StatoPratica(str, enum.Enum):
    """Stati del ciclo di vita di una pratica (ticket)."""
    NUOVA = "nuova"
    IN_LAVORAZIONE = "in_lavorazione"
    COMPLETATA = "completata"


class TipoDocumento(str, enum.Enum):
    CARTA_IDENTITA = "carta_identita"
    PATENTE = "patente"
    PASSAPORTO = "passaporto"
    CODICE_FISCALE = "codice_fiscale"
    VISURA = "visura"
    LIBRETTO = "libretto"


# --------------------------------------------------------------------------- #
# Etichette "human friendly" per la UI
# --------------------------------------------------------------------------- #
LABEL_TIPO_POLIZZA = {
    TipoPolizza.AUTO: "Auto",
    TipoPolizza.RAMI_ELEMENTARI: "Rami Elementari",
}

LABEL_URGENZA = {
    Urgenza.BASSA: "Bassa",
    Urgenza.ALTA: "Alta",
}

LABEL_STATO = {
    StatoPratica.NUOVA: "Nuova",
    StatoPratica.IN_LAVORAZIONE: "In lavorazione",
    StatoPratica.COMPLETATA: "Completata",
}

LABEL_TIPO_DOCUMENTO = {
    TipoDocumento.CARTA_IDENTITA: "Carta d'Identità",
    TipoDocumento.PATENTE: "Patente",
    TipoDocumento.PASSAPORTO: "Passaporto",
    TipoDocumento.CODICE_FISCALE: "Codice Fiscale",
    TipoDocumento.VISURA: "Visura camerale",
    TipoDocumento.LIBRETTO: "Libretto veicolo",
}

# Colori usati per evidenziare priorità / stato nelle tabelle e nei badge.
COLORE_URGENZA = {
    Urgenza.ALTA: "#e74c3c",   # rosso
    Urgenza.BASSA: "#27ae60",  # verde
}

COLORE_STATO = {
    StatoPratica.NUOVA: "#3498db",          # blu
    StatoPratica.IN_LAVORAZIONE: "#f39c12",  # arancio
    StatoPratica.COMPLETATA: "#7f8c8d",      # grigio
}

# --------------------------------------------------------------------------- #
# Liste controllate (estendibili)
# --------------------------------------------------------------------------- #
COMPAGNIE = [
    "Adriatic",
    "Allianz",
    "AXA",
    "conte.it",
    "Generali",
    "Groupama",
    "Euroherc",
    "HDI",
    "Helvetia",
    "Linear",
    "Prima",
    "Reale Mutua",
    "Sara Assicurazioni",
    "UnipolSai",
    "Vittoria Assicurazioni",
    "Zurich",
    "Altro",
]

METODI_PAGAMENTO = [
    "Bonifico",
    "Contanti",
    "Assegno",
    "POS",
]

# Prefisso usato per generare il numero pratica leggibile (es. PRT-2026-0001).
PREFISSO_PRATICA = "PRT"
