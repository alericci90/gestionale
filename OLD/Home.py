"""
Punto di ingresso dell'applicazione Streamlit (multipagina).

Avvio:
    streamlit run Home.py

Le altre pagine vivono nella cartella `pages/` e vengono mostrate
automaticamente nella barra laterale da Streamlit.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Assicura che la root del progetto sia importabile dalle pagine.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.ui_common import setup_page  # noqa: E402

setup_page("Gestionale Pratiche Assicurative G.A.F.", "🏠")

st.title("🏢 Gestionale Pratiche Assicurative G.A.F.")
st.markdown(
    """
Benvenuto nel gestionale per la gestione delle pratiche assicurative.

Usa il menu a sinistra per accedere alle due interfacce:

- **📝 Broker** — inserimento di nuove pratiche assicurative.
- **📋 Segreteria** — gestione delle pratiche come ticket: filtri, ordinamenti,
  assegnazione agli operatori e aggiornamento dello stato.
"""
)

col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_Broker.py", label="Vai all'inserimento (Broker)", icon="📝")
with col2:
    st.page_link("pages/2_Segreteria.py", label="Vai alla gestione (Segreteria)", icon="📋")
