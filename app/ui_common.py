"""
Helper UI condivisi tra le pagine Streamlit.

- `bootstrap_path()`  : assicura che la root del progetto sia importabile.
- `setup_page()`      : configurazione pagina + iniezione CSS.
- funzioni di rendering riutilizzabili (header, badge).
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


def bootstrap_path() -> None:
    """Aggiunge la root del progetto a sys.path (utile quando Streamlit lancia le pagine)."""
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


# Eseguito all'import così le pagine possono importare i package del progetto.
bootstrap_path()

_CSS = """
<style>
/* Larghezza contenuto più ariosa */
.block-container { padding-top: 2rem; max-width: 1200px; }

/* Titoli sezione del form broker */
.sezione-titolo {
    font-size: 1.05rem; font-weight: 700; color: #1f3a5f;
    border-left: 4px solid #2e6cb6; padding-left: 10px; margin: 0.4rem 0 0.2rem 0;
}

/* Card di dettaglio pratica */
.dettaglio-card {
    background: #f7f9fc; border: 1px solid #e1e8f0; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 12px;
}
.dettaglio-label { color: #6b7a90; font-size: 0.78rem; text-transform: uppercase; letter-spacing: .03em; }
.dettaglio-valore { font-size: 1.0rem; font-weight: 600; color: #1f2d3d; }

/* Riga urgenza alta evidenziata nelle tabelle custom */
.riga-alta { background: #fdecea !important; }
</style>
"""


def setup_page(titolo: str, icona: str) -> None:
    """Configura la pagina Streamlit e inietta il CSS comune."""
    st.set_page_config(page_title=titolo, page_icon=icona, layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)


def sezione(testo: str) -> None:
    st.markdown(f"<div class='sezione-titolo'>{testo}</div>", unsafe_allow_html=True)


def campo_dettaglio(label: str, valore: str) -> None:
    st.markdown(
        f"<div class='dettaglio-label'>{label}</div>"
        f"<div class='dettaglio-valore'>{valore}</div>",
        unsafe_allow_html=True,
    )
