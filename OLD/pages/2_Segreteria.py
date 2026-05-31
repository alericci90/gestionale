"""Pagina Streamlit per l'interfaccia Segreteria. Logica in app/segreteria/segreteria_app.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.segreteria.segreteria_app import render  # noqa: E402

render()
